#!/usr/bin/env python3
"""Offline structural/semantic audit of verified Sherlock v3 archives.

Scan every state row and PCAP record; cross-check every IPAL event against raw
notifications. Inventory quarantined nested archives and sample their schemas.
Never execute dataset Python, unpickle data, train models, or expose labels to X.
"""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import struct
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat()


def event_audit(events, raw):
    at_time = defaultdict(list)
    ends = defaultdict(list)
    for row in raw:
        at_time[row["timestamp"]].append(row)
        d = row.get("notification_data", {})
        if d.get("mark") == "end":
            ends[d.get("id")].append(row)
    results = []
    for e in events:
        matches = [r for r in at_time[e["start"]]
                   if r.get("notification_data", {}).get("mark") == "start"
                   and r.get("notification_data", {}).get("type") == "procedure"]
        raw_label = matches[0]["notification_data"].get("malicious") if len(matches) == 1 else None
        id_benign = "(benign event)" in str(e["id"])
        matching_end = ends.get(matches[0]["notification_data"].get("id"), []) if len(matches) == 1 else []
        results.append({**e, "raw_start_matches": len(matches), "raw_malicious": raw_label,
                        "id_label_agrees": type(raw_label) is bool and raw_label == (not id_benign),
                        "raw_procedure_end_times": [r["timestamp"] for r in matching_end],
                        "ipal_end_minus_raw_end_seconds": e["end"]-matching_end[0]["timestamp"] if len(matching_end) == 1 else None})
    ordered = sorted(results, key=lambda e: e["start"])
    overlaps = []
    for i, a in enumerate(ordered):
        for b in ordered[i+1:]:
            stop = a.get("recovery", a["end"])
            if b["start"] < stop:
                overlaps.append([a["id"], b["id"], stop-b["start"]])
    return {"count": len(results), "cyber": sum(e["raw_malicious"] is True for e in results),
            "benign": sum(e["raw_malicious"] is False for e in results),
            "unresolved": sum(e["raw_malicious"] is None for e in results),
            "label_disagreements": [e["id"] for e in results if not e["id_label_agrees"]],
            "description_counts": dict(Counter(e["description"] for e in results)),
            "raw_notification_count": len(raw), "overlaps_through_recovery": overlaps,
            "min_start_gap_seconds": min((b["start"]-a["start"] for a,b in zip(ordered,ordered[1:])), default=None),
            "events": results}


def state_audit(zipped, name, initial):
    n = 0
    first = last = previous = None
    topkeys, fieldcounts, labeltypes, deltas = Counter(), Counter(), Counter(), Counter()
    nulls = total_values = nonfinite = timestamp_regressions = fieldset_changes = 0
    labels = Counter()
    first_state = None
    all_fields = set()
    unchanged_rows = 0
    previous_state = None
    def constant(s):
        nonlocal nonfinite
        nonfinite += 1
        return float(s)
    with zipped.open(name) as raw, gzip.GzipFile(fileobj=raw) as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line, parse_constant=constant)
            t = row["timestamp"]
            if not isinstance(t, (int,float)) or not math.isfinite(t):
                raise ValueError(f"Invalid state timestamp in {name}")
            state = row["state"]
            if n == 0:
                first = t
                first_state = state.copy()
            else:
                delta = t-previous
                deltas[str(round(delta,6))] += 1
                timestamp_regressions += delta < 0
                unchanged_rows += state == previous_state
                fieldset_changes += state.keys() != previous_state.keys()
            last = previous = t
            previous_state = state
            n += 1
            topkeys.update(row.keys())
            fieldcounts[len(state)] += 1
            label = row.get("malicious")
            labeltypes[type(label).__name__] += 1
            labels[json.dumps(label, sort_keys=True)] += 1
            values = list(state.values())
            nulls += values.count(None)
            total_values += len(values)
            all_fields.update(state.keys())
            if n % 10000 == 0:
                print(f"STATE {name}: {n} rows", flush=True)
    return {"scope": "every JSON row", "rows": n, "first_timestamp": first, "last_timestamp": last,
            "first_utc": utc(first), "last_utc": utc(last), "duration_seconds": last-first,
            "top_level_key_counts": dict(topkeys), "field_count_histogram": dict(fieldcounts),
            "all_fields": sorted(all_fields), "malicious_type_counts": dict(labeltypes),
            "malicious_label_row_counts_evaluator_only": dict(labels),
            "null_values": nulls, "total_state_values": total_values, "nonfinite_json_literals": nonfinite,
            "timestamp_regressions": timestamp_regressions, "timestep_histogram": dict(deltas),
            "fieldset_change_rows": fieldset_changes, "unchanged_adjacent_rows": unchanged_rows,
            "first_state_equals_initial_state": first_state == initial,
            "freshness_note": "Unchanged aggregate state does not prove a fresh measurement or physical stability.",
            "crc_valid": True}


def ethernet_tcp(frame):
    """Parse framing only; do not reassemble TCP or interpret attack semantics."""
    if len(frame) < 14:
        return "short_ethernet", None
    offset, ethertype = 14, int.from_bytes(frame[12:14], "big")
    while ethertype in (0x8100, 0x88a8):
        if len(frame) < offset+4:
            return "short_vlan", None
        ethertype = int.from_bytes(frame[offset+2:offset+4], "big")
        offset += 4
    if ethertype != 0x800:
        return f"ethertype_{ethertype:04x}", None
    ip = frame[offset:]
    if len(ip) < 20 or ip[0] >> 4 != 4:
        return "short_ipv4", None
    ihl = (ip[0] & 15)*4
    total = int.from_bytes(ip[2:4], "big")
    if ihl < 20 or total < ihl or total > len(ip):
        return "invalid_ipv4_length", None
    ip = ip[:total]
    if int.from_bytes(ip[6:8], "big") & 0x3fff:
        return "ipv4_fragment", None
    if ip[9] != 6:
        return f"ip_protocol_{ip[9]}", None
    tcp = ip[ihl:]
    if len(tcp) < 20:
        return "short_tcp", None
    hlen = (tcp[12] >> 4)*4
    if hlen < 20 or hlen > len(tcp):
        return "invalid_tcp_length", None
    src, dst = struct.unpack("!HH", tcp[:4])
    return "tcp", {"src_port": src, "dst_port": dst,
                   "src": ".".join(str(x) for x in ip[12:16]),
                   "dst": ".".join(str(x) for x in ip[16:20]),
                   "payload": tcp[hlen:], "ip_bytes": ip, "flags": tcp[13]}


def complete_apdus(payload):
    """Yield whole APDUs already contained in one TCP segment, or report remainder.

    This is a structural availability probe, not an IEC/TCP production decoder.
    A fragmented APDU is not interpreted or silently stitched together.
    """
    offset = 0
    out = []
    while offset < len(payload):
        if len(payload)-offset < 2 or payload[offset] != 0x68:
            return out, len(payload)-offset
        size = payload[offset+1]+2
        if size < 6 or offset+size > len(payload):
            return out, len(payload)-offset
        out.append(payload[offset:offset+size])
        offset += size
    return out, 0


def pcap_audit(stream, mapping):
    magic = stream.read(4)
    formats = {b"\xd4\xc3\xb2\xa1": ("<", 1e6), b"\xa1\xb2\xc3\xd4": (">", 1e6),
               b"\x4d\x3c\xb2\xa1": ("<", 1e9), b"\xa1\xb2\x3c\x4d": (">", 1e9)}
    if magic not in formats:
        raise ValueError(f"Unsupported capture magic {magic.hex()}")
    endian, resolution = formats[magic]
    rest = stream.read(20)
    if len(rest) != 20:
        raise ValueError("Truncated global PCAP header")
    major, minor, tz, sig, snaplen, linktype = struct.unpack(endian+"HHiIII", rest)
    if linktype != 1:
        raise ValueError(f"Expected Ethernet linktype, got {linktype}")
    count = captured = truncated = regressions = payload_segments = remainders = 0
    first = last = prev = None
    classes, types, cots, apci = Counter(), Counter(), Counter(), Counter()
    endpoint = set()
    mapped, unmapped = set(), set()
    nan_float = quality_flagged = observed_values = 0
    samples = {}
    example = None
    element_sizes = {1:1, 3:1, 5:2, 7:5, 9:3, 11:3, 13:5, 15:5,
                     30:8, 31:8, 32:9, 33:12, 34:10, 35:10, 36:12, 37:12,
                     45:1, 46:1, 47:1, 48:3, 49:3, 50:5, 51:5, 100:1, 103:7}
    while True:
        header = stream.read(16)
        if not header:
            break
        if len(header) != 16:
            raise ValueError("Truncated PCAP record header")
        secs, sub, incl, orig = struct.unpack(endian+"IIII", header)
        if incl > snaplen or incl > 16*1024*1024:
            raise ValueError("Invalid captured packet length")
        frame = stream.read(incl)
        if len(frame) != incl:
            raise ValueError("Truncated PCAP record payload")
        t = secs+sub/resolution
        if first is None:
            first = t
        regressions += prev is not None and t < prev
        last = prev = t
        count += 1
        captured += incl
        truncated += incl < orig
        kind, tcp = ethernet_tcp(frame)
        classes[kind] += 1
        if tcp is None:
            continue
        endpoint.update((tcp["src"], tcp["dst"]))
        if 2404 not in (tcp["src_port"], tcp["dst_port"]):
            continue
        payload = tcp["payload"]
        if not payload:
            continue
        payload_segments += 1
        if len(samples) < 2000:
            h = hashlib.sha256(tcp["ip_bytes"]).hexdigest()
            samples.setdefault(h, {"packet_index": count, "timestamp": t})
        pdus, remainder = complete_apdus(payload)
        remainders += bool(remainder)
        for pdu in pdus:
            if pdu[2] & 1:
                apci["S" if pdu[2]&3 == 1 else "U"] += 1
                continue
            apci["I"] += 1
            if len(pdu) < 12:
                classes["short_asdu"] += 1
                continue
            type_id, vsq = pdu[6:8]
            cot = pdu[8] & 0x3f
            ca = int.from_bytes(pdu[10:12], "little")
            types[type_id] += 1
            cots[cot] += 1
            if type_id not in element_sizes:
                classes["unparsed_asdu_type"] += 1
                continue
            offset, ioa = 12, None
            for i in range(vsq & 0x7f):
                if i == 0 or not vsq & 0x80:
                    if len(pdu) < offset+3:
                        classes["incomplete_information_object"] += 1
                        break
                    ioa = int.from_bytes(pdu[offset:offset+3], "little")
                    offset += 3
                else:
                    ioa += 1
                size = element_sizes[type_id]
                if len(pdu) < offset+size:
                    classes["incomplete_information_object"] += 1
                    break
                key = f"{ca}.{ioa}"
                (mapped if key in mapping else unmapped).add(key)
                if type_id == 13:
                    value = struct.unpack("<f", pdu[offset:offset+4])[0]
                    nan_float += not math.isfinite(value)
                    quality_flagged += bool(pdu[offset+4] & 0xf0)
                    observed_values += 1
                    if example is None and key in mapping and math.isfinite(value):
                        example = {"packet_index": count, "timestamp": t, "ca_ioa": key,
                                   "type_id": type_id, "value": value, "quality_octet": pdu[offset+4],
                                   "mapped_attribute": mapping[key]["attribute"],
                                   "mapped_unit": mapping[key]["unit"]}
                offset += size
    return {"scope": "every PCAP record; application probe uses complete in-segment APDUs only",
            "pcap_version": f"{major}.{minor}", "timestamp_resolution": "microsecond" if resolution == 1e6 else "nanosecond",
            "linktype": linktype, "snaplen": snaplen, "packets": count, "captured_bytes": captured,
            "truncated_packets": truncated, "timestamp_regressions": regressions,
            "first_timestamp": first, "last_timestamp": last, "protocol_counts": dict(classes),
            "ip_endpoint_count": len(endpoint), "tcp2404_payload_segments": payload_segments,
            "segments_with_unparsed_remainder": remainders, "apci_counts": dict(apci),
            "asdu_type_counts": dict(types), "cot_counts": dict(cots),
            "mapped_ca_ioas": sorted(mapped), "unmapped_ca_ioas": sorted(unmapped),
            "type13_observed_objects": observed_values, "type13_nonfinite_values": nan_float,
            "type13_quality_flagged_objects": quality_flagged, "example_observable_value": example,
            "crc_valid": True}, samples


def nested_audit(zipped, name):
    # Nested ZIPs need random access. Spool once to disk rather than repeatedly
    # inflating a GB-sized parent for each seek. All temporary bytes are removed.
    with tempfile.TemporaryFile() as tmp:
        with zipped.open(name) as source:
            shutil.copyfileobj(source, tmp, 8*1024*1024)
        tmp.seek(0)
        with zipfile.ZipFile(tmp) as nested:
            useful = [i for i in nested.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
            times = []
            for entry in useful:
                m = re.search(r"TS(\d+)-(\d+)\.json$", entry.filename)
                if m:
                    times.append(float(m[1]+"."+m[2]))
            probes = []
            for item in useful[:1]:
                with nested.open(item) as stream:
                    if item.filename.endswith(".jsonl"):
                        line = stream.readline(8*1024*1024)
                        parsed = json.loads(line)
                    elif item.filename.endswith(".json") and item.file_size < 8*1024*1024:
                        parsed = json.loads(stream.read())
                    else:
                        parsed = None
                    probes.append({"path": item.filename, "bytes": item.file_size,
                                   "sample_top_keys": sorted(parsed) if isinstance(parsed,dict) else None,
                                   "sample_preview": str(parsed)[:800]})
            return {"scope": "all nested member headers; first non-resource-fork data member schema only",
                    "parent_crc_valid": True, "total_members": len(nested.infolist()),
                    "data_files": len(useful), "data_uncompressed_bytes": sum(i.file_size for i in useful),
                    "resource_forks_excluded": sum(i.filename.startswith("__MACOSX/") for i in nested.infolist()),
                    "suffix_counts": dict(Counter(Path(i.filename).suffix for i in useful)),
                    "filename_timestamp_range": [min(times),max(times)] if times else None,
                    "samples": probes, "access": "quarantined; no model or retrieval input"}


def audit_archive(root, archive):
    outdir = root / "data/manifests/content_audit"
    scenario = archive.stem
    manifest = json.loads((root/"data/manifests/sherlock_manifest.json").read_text())
    receipt = next(x for x in manifest["archives"] if x["filename"] == archive.name)
    if receipt["status"] != "verified" or archive.stat().st_size != receipt["local_bytes"]:
        raise ValueError("Archive has not been verified")
    result = {"scenario": scenario, "archive_sha256": receipt["sha256"],
              "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "status": "running", "recordings": {}, "members": {}}
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        rules = zipped.read(f"{scenario}/ipal/rules.py")
        tree = ast.parse(rules.decode())
        rule_names = []
        for node in ast.walk(tree):
            if isinstance(node,ast.Dict):
                for k,v in zip(node.keys,node.values):
                    if isinstance(k,ast.Constant) and k.value == "name" and isinstance(v,ast.Constant):
                        rule_names.append(v.value)
        result["rules"] = {"source_sha256": hashlib.sha256(rules).hexdigest(), "executed": False,
                           "nan_to_zero_patterns": rules.decode().count("0 if x[0]!=x[0] else x[0]"),
                           "named_rules": len(rule_names), "unique_names": len(set(rule_names)),
                           "duplicate_names": {k:v for k,v in Counter(rule_names).items() if v>1}}
        for split in ("train", "test"):
            prefix = f"{scenario}/raw/{split}"
            if prefix+"/events.jsonl" not in names:
                continue
            raw = [json.loads(line) for line in zipped.read(prefix+"/events.jsonl").splitlines() if line.strip()]
            events = json.loads(zipped.read(f"{scenario}/ipal/{split}/events.json"))
            mapping = json.loads(zipped.read(prefix+"/data-point-map.json"))
            initial = json.loads(zipped.read(f"{scenario}/ipal/{split}/initial_state.json"))
            config = json.loads(zipped.read(prefix+"/sherlock-config.yml"))
            clock_records = [r for r in raw if any(k in r.get("notification_data",{}) for k in ("wall_time","sim_time","clock_speed"))]
            rec = {"events": event_audit(events,raw), "clock_records": clock_records,
                   "config": {k:config.get(k) for k in ("vantage_points","duration_seconds","wattson_speed")},
                   "mapping": {"count": len(mapping), "field_keys": sorted({k for v in mapping.values() for k in v}),
                               "contexts": dict(Counter(v["context"] for v in mapping.values())),
                               "units": dict(Counter(v["unit"] for v in mapping.values())),
                               "attributes": sorted({v["attribute"] for v in mapping.values()}),
                               "initial_state_fields": len(initial)}, "pcaps": {}}
            result["recordings"][split] = rec
            save(outdir/f"{scenario}.json",result)
            print(f"METADATA {scenario}/{split}: {len(events)} events",flush=True)
            all_samples = {}
            for name in names:
                if name.startswith(prefix+"/pcap/") and name.endswith(".pcap"):
                    with zipped.open(name) as stream:
                        info, samples = pcap_audit(stream,mapping)
                    rec["pcaps"][name] = info
                    all_samples[name] = samples
                    print(f"PCAP {name}: {info['packets']} records",flush=True)
                    save(outdir/f"{scenario}.json",result)
            shared = []
            pcaps = list(all_samples)
            for i,a in enumerate(pcaps):
                for b in pcaps[i+1:]:
                    common = all_samples[a].keys() & all_samples[b].keys()
                    if common:
                        h = sorted(common)[0]
                        shared.append({"left":a,"right":b,"shared_ip_packet_hashes_in_samples":len(common),
                                       "example_sha256":h,"left_reference":all_samples[a][h],"right_reference":all_samples[b][h]})
            rec["cross_vantage_sample_duplicates"] = shared
            state_name = next(n for n in names if n.startswith(f"{scenario}/{split}.") and n.endswith(".state.gz"))
            rec["state_member"] = state_name
            rec["state"] = state_audit(zipped,state_name,initial)
            state_vantage = Path(state_name).name.split(".")[1]
            primary = next(p for n,p in rec["pcaps"].items() if f"switch-{state_vantage}-" in n)
            rec["alignment"] = {"state_vantage": state_vantage,
                                "state_first_minus_pcap_first_seconds": rec["state"]["first_timestamp"]-primary["first_timestamp"],
                                "state_last_minus_pcap_last_seconds": rec["state"]["last_timestamp"]-primary["last_timestamp"],
                                "events_outside_pcap_scope": [e["id"] for e in events if not primary["first_timestamp"] <= e["start"] <= e.get("recovery",e["end"]) <= primary["last_timestamp"]]}
            rec["mapping"]["state_fields_not_in_rule_names"] = sorted(set(rec["state"]["all_fields"])-set(rule_names))
            rec["mapping"]["state_fields_not_in_mapping"] = sorted(set(rec["state"]["all_fields"])-{f"{v['element']}:{v['attribute']}" for v in mapping.values()})
            save(outdir/f"{scenario}.json",result)
        # Inspect supporting source files, including all logs and nested archives.
        for member in zipped.infolist():
            if member.is_dir():
                continue
            name = member.filename
            if name.endswith((".pcap", ".state.gz")):
                continue
            if name.endswith(".zip"):
                result["members"][name] = nested_audit(zipped,name)
                print(f"NESTED {name}: inventoried, quarantined",flush=True)
            else:
                data = zipped.read(name)
                item = {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"crc_valid":True}
                if name.endswith(".log"):
                    text = data.decode("utf-8",errors="replace")
                    item.update(lines=len(text.splitlines()),sample_first_line=text.splitlines()[0] if text else "", access="quarantined")
                elif name.endswith(".svg"):
                    xml = ET.fromstring(data)
                    labels = ["".join(e.itertext()) for e in xml.iter() if e.tag.rsplit('}',1)[-1] == 'text']
                    item.update(xml_valid=True, topology_role_labels=[s for s in labels if re.search(r"control|mtu|n302|n406|n402",s,re.I)])
                elif name.endswith(".json"):
                    json.loads(data)
                    item["json_valid"] = True
                elif name.endswith(".yml"):
                    json.loads(data)  # These particular .yml files contain JSON.
                    item["actual_format"] = "JSON"
                result["members"][name] = item
        result["status"] = "complete"
        result["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["limitations"] = ["No production TCP reassembly; APDU availability counts are segment-scoped.",
                                 "Nested quarantined archives fully inventoried, only first data member schema sampled.",
                                 "No per-packet-to-state reconstruction or inference of sensor independence.",
                                 "Official transcriber version used to create this release is not present in the inspected metadata."]
        save(outdir/f"{scenario}.json",result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", choices=["01-Basic","02-Semiurban","03-Rural"])
    args = p.parse_args()
    paths = sorted((ROOT/"data/raw/sherlock/v3").glob("*.zip"))
    for path in paths:
        if not args.scenario or path.stem == args.scenario:
            audit_archive(ROOT,path)
