"""Build a windowed evidence database from a Sherlock v3 ZIP.

The ZIP is not extracted. `events.json`, attack labels, and `physical.zip`
are never opened. Electrical values stay marked as network-reported state.
"""
from __future__ import annotations
import json
import re
import zipfile
from pathlib import Path
from . import iec104
from .store import connect, create, get_meta, insert_evidence, set_meta
from ..ids import evidence_id
from ...ipal import iter_state
from ...pcap import iter_pcap

_VANTAGE = re.compile(r"switch-(n\d+)")
_ALIAS = {":is_closed": ":closed", ":is_connected": ":connected"}


def discover_members(archive: Path, scenario: str, recording: str) -> dict:
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    blocked = [name for name in names if name.endswith("events.json") or name.endswith("events.jsonl")
               or name.endswith("physical.zip")]
    state = [name for name in names if Path(name).name.startswith(f"{recording}.") and name.endswith(".state.gz")]
    initial = [name for name in names if name.endswith(f"ipal/{recording}/initial_state.json")]
    point_map = [name for name in names if name.endswith(f"raw/{recording}/data-point-map.json")]
    pcaps = sorted(name for name in names if f"/raw/{recording}/pcap/" in name and name.endswith(".pcap"))
    if scenario not in archive.name and not any(scenario in name for name in names):
        raise FileNotFoundError(f"{scenario} is not in {archive}")
    if len(state) != 1 or len(point_map) != 1 or not pcaps:
        raise FileNotFoundError(
            f"Need one state file, one point map, and pcaps for {scenario} {recording}; "
            f"found state={state}, map={point_map}, pcaps={len(pcaps)}"
        )
    return {
        "state": state[0],
        "initial_state": initial[0] if initial else None,
        "point_map": point_map[0],
        "pcaps": pcaps,
        "not_opened": blocked,
    }


def index_window(archive: Path, *, scenario: str, recording: str, start: float, end: float,
                 out: Path, context_seconds: float = 15.0, work: Path | None = None,
                 modalities: str = "both") -> dict:
    """Index [start - context, end + context). Incident bounds are stored as metadata."""
    if end <= start:
        raise ValueError("Incident end must be after start")
    members = discover_members(archive, scenario, recording)
    window_start = start - context_seconds
    window_end = end + context_seconds
    conn = connect(out)
    create(conn)
    point_map = _read_json(archive, members["point_map"])
    by_ioa, by_entity = _point_indexes(point_map)
    initial = _read_json(archive, members["initial_state"]) if members["initial_state"] else None
    if not isinstance(initial, dict):
        initial = None
    counts = {"electrical_new": 0, "electrical_initial": 0, "electrical_hold_entities": 0,
              "tcp_packets": 0, "arp_packets": 0, "iec104_objects": 0, "iec104_unmatched": 0}
    if modalities in ("both", "electrical"):
        _index_state(conn, archive, members["state"], initial, by_entity, by_ioa,
                     window_start, window_end, counts)
    packet_index = {}
    decoder_note = "network modality not requested"
    cross = None
    if modalities in ("both", "network"):
        packet_index = _index_pcaps(conn, archive, members["pcaps"], window_start, window_end, counts)
        decoder_note, decoded = _index_iec104(
            conn, archive, members["pcaps"], by_ioa, packet_index, window_start, window_end, counts, work, out,
        )
        cross = _cross_check(conn)
    else:
        decoded = 0
    limitations = [
        "events.json, events.jsonl, malicious flags, and physical.zip were not opened",
        "electrical values are IPAL state reported from the network, not independent physical truth",
        "holds are one summary per entity, not a new measurement at every second",
        "TCP payloads are not stored and TCP streams are not reassembled",
        "same-frame dependencies use the Ethernet frame hash",
        decoder_note,
    ]
    meta = {
        "scenario": scenario,
        "recording": recording,
        "incident_start": start,
        "incident_end": end,
        "indexed_start": window_start,
        "indexed_end": window_end,
        "context_seconds": context_seconds,
        "archive": str(archive),
        "members": members,
        "counts": counts,
        "iec104_rows": decoded,
        "cross_check": cross,
        "limitations": limitations,
        "modalities_indexed": modalities,
    }
    for key, value in meta.items():
        set_meta(conn, key, value)
    conn.commit()
    conn.close()
    return meta


def open_indexed(path: Path):
    conn = connect(path, readonly=True)
    return conn, {
        "incident_start": get_meta(conn, "incident_start"),
        "incident_end": get_meta(conn, "incident_end"),
        "indexed_start": get_meta(conn, "indexed_start"),
        "indexed_end": get_meta(conn, "indexed_end"),
        "context_seconds": get_meta(conn, "context_seconds"),
        "counts": get_meta(conn, "counts"),
        "limitations": get_meta(conn, "limitations"),
        "cross_check": get_meta(conn, "cross_check"),
    }


def _read_json(archive: Path, member: str):
    with zipfile.ZipFile(archive) as zf:
        return json.loads(zf.read(member))


def _point_indexes(raw: dict) -> tuple[dict, dict]:
    by_ioa = {}
    by_entity: dict[str, list[str]] = {}
    for key, point in raw.items():
        entity = f"{point['element']}:{point['attribute']}"
        by_ioa[str(key)] = {"entity": entity, "context": point.get("context", ""), "element": point.get("element")}
        by_entity.setdefault(entity, []).append(str(key))
    return by_ioa, {entity: sorted(keys) for entity, keys in by_entity.items()}


def _canonical(entity: str) -> tuple[str, str | None]:
    for suffix, replacement in _ALIAS.items():
        if entity.endswith(suffix):
            return entity[: -len(suffix)] + replacement, entity
    return entity, None


def _index_state(conn, archive, member, initial, by_entity, by_ioa, start, end, counts) -> None:
    holds: dict[str, dict] = {}
    seen: dict[tuple, str] = {}
    source = f"{Path(archive).name}:{member}"
    with zipfile.ZipFile(archive) as zf, zf.open(member) as handle:
        observations = iter_state(
            handle, source=source, start=start, end=end, initial_state=initial, updates_only=False,
        )
        for obs in observations:
            entity, alias = _canonical(obs.entity)
            status = (obs.attrs or {}).get("update", "new")
            ioas = by_entity.get(entity) or by_entity.get(obs.entity) or []
            context = by_ioa.get(ioas[0], {}).get("context") if len(ioas) == 1 else None
            if status == "hold":
                bucket = holds.setdefault(entity, {"count": 0, "first": obs.timestamp, "last": obs.timestamp,
                                                    "value": obs.value, "sources": []})
                bucket["count"] += 1
                bucket["last"] = obs.timestamp
                bucket["value"] = obs.value
                if len(bucket["sources"]) < 3:
                    bucket["sources"].append(obs.source_id)
                continue
            kind = "electrical_update" if status == "new" else "electrical_initial"
            key = (entity, obs.timestamp, kind)
            if key in seen:
                continue
            row_id = evidence_id(obs.source_id, entity, status)
            seen[key] = row_id
            insert_evidence(conn, {
                "evidence_id": row_id,
                "timestamp": obs.timestamp,
                "modality": "electrical",
                "entity": entity,
                "kind": kind,
                "value": obs.value,
                "value_present": True,
                "source_ref": obs.source_id,
                "archive_member": member,
                "vantage": _state_vantage(member),
                "update_status": status,
                "trust": "network-reported-not-simulator-truth",
                "ca_ioa": ioas[0] if len(ioas) == 1 else None,
                "ipal_context": context,
                "payload": {
                    "ca_ioa_candidates": ioas,
                    "collapsed_alias": alias,
                    "physical_trust": "network-reported-not-simulator-truth",
                },
            })
            counts["electrical_new" if status == "new" else "electrical_initial"] += 1
    for entity, bucket in holds.items():
        ioas = by_entity.get(entity) or []
        insert_evidence(conn, {
            "evidence_id": evidence_id(member, entity, "hold", bucket["first"], bucket["last"]),
            "timestamp": bucket["last"],
            "modality": "electrical",
            "entity": entity,
            "kind": "electrical_hold_summary",
            "value": bucket["value"],
            "value_present": True,
            "source_ref": bucket["sources"][0] if bucket["sources"] else f"{member}:{entity}:hold",
            "archive_member": member,
            "vantage": _state_vantage(member),
            "update_status": "hold",
            "trust": "network-reported-not-simulator-truth",
            "ca_ioa": ioas[0] if len(ioas) == 1 else None,
            "payload": {
                "hold_count": bucket["count"],
                "first_timestamp": bucket["first"],
                "last_timestamp": bucket["last"],
                "not_a_new_measurement": True,
                "sample_source_refs": bucket["sources"],
            },
        })
    counts["electrical_hold_entities"] = len(holds)
    conn.commit()


def _index_pcaps(conn, archive, members, start, end, counts) -> dict:
    index = {}
    for member in members:
        vantage = _vantage(member)
        source = f"{Path(archive).name}:{member}"
        with zipfile.ZipFile(archive) as zf, zf.open(member) as handle:
            for obs in iter_pcap(handle, source=source, start=start, end=end):
                attrs = obs.attrs or {}
                fingerprint = attrs.get("frame_sha256")
                row_id = evidence_id(obs.source_id)
                insert_evidence(conn, {
                    "evidence_id": row_id,
                    "timestamp": obs.timestamp,
                    "modality": "network",
                    "entity": obs.entity,
                    "kind": obs.kind,
                    "value": obs.value,
                    "value_present": True,
                    "source_ref": obs.source_id,
                    "archive_member": member,
                    "vantage": vantage,
                    "update_status": "packet",
                    "trust": "captured-frame",
                    "fingerprint": fingerprint,
                    "src_ip": attrs.get("source_ip"),
                    "dst_ip": attrs.get("destination_ip"),
                    "src_port": attrs.get("source_port"),
                    "dst_port": attrs.get("destination_port"),
                    "protocol_class": "iec104_candidate" if attrs.get("iec104_candidate") else obs.kind,
                    "payload": {
                        "tcp_flags": attrs.get("tcp_flags"),
                        "tcp_seq": attrs.get("tcp_seq"),
                        "payload_bytes": attrs.get("payload_bytes"),
                        "iec104_candidate": attrs.get("iec104_candidate"),
                        "op": attrs.get("op"),
                    },
                })
                if obs.kind == "tcp_packet":
                    counts["tcp_packets"] += 1
                    key = _packet_key(vantage, attrs.get("source_ip"), attrs.get("destination_ip"),
                                      attrs.get("source_port"), attrs.get("destination_port"), obs.timestamp)
                    index.setdefault(key, []).append({"evidence_id": row_id, "fingerprint": fingerprint})
                else:
                    counts["arp_packets"] += 1
        conn.commit()
    return index


def _index_iec104(conn, archive, members, by_ioa, packet_index, start, end, counts, work, out) -> tuple[str, int]:
    work_dir = Path(work) if work else Path(out).parent / "pcap-slices"
    work_dir.mkdir(parents=True, exist_ok=True)
    notes = []
    decoded = 0
    for member in members:
        vantage = _vantage(member)
        dest = work_dir / f"{vantage}.pcap"
        with zipfile.ZipFile(archive) as zf, zf.open(member) as handle:
            kept = iec104.slice_pcap_stream(handle, dest, start, end)
        rows, note = iec104.decode_slice(dest)
        notes.append(f"{vantage}: sliced {kept}; {note}; asdu_rows {len(rows)}")
        for row in rows:
            for obj in iec104.split_fields(row):
                if obj["timestamp"] is None:
                    continue
                mapped = by_ioa.get(obj["ca_ioa"] or "", {})
                entity = mapped.get("entity")
                if entity is None and obj["ca_ioa"]:
                    entity = f"ca_ioa:{obj['ca_ioa']}"
                elif entity is None:
                    entity = f"{obj['src_ip']}:{obj['src_port']}->{obj['dst_ip']}:{obj['dst_port']}/IEC104"
                key = _packet_key(vantage, obj["src_ip"], obj["dst_ip"], obj["src_port"], obj["dst_port"], obj["timestamp"])
                matches = packet_index.get(key) or []
                parent = matches[0]["evidence_id"] if len(matches) == 1 else None
                fingerprint = matches[0]["fingerprint"] if len(matches) == 1 else None
                if parent is None:
                    counts["iec104_unmatched"] += 1
                    fingerprint = fingerprint or evidence_id("unmatched", member, obj["timestamp"], obj["ca_ioa"], obj["type_id"])
                row_id = evidence_id(member, obj["timestamp"], obj["ca_ioa"], obj["type_id"], obj["ioa"], obj["alignment"])
                insert_evidence(conn, {
                    "evidence_id": row_id,
                    "timestamp": obj["timestamp"],
                    "modality": "network",
                    "entity": entity,
                    "kind": "iec104_asdu",
                    "value": obj["value"],
                    "value_present": obj["value_present"],
                    "source_ref": f"{Path(archive).name}:{member}#t={obj['timestamp']}&ioa={obj['ca_ioa']}",
                    "archive_member": member,
                    "vantage": vantage,
                    "update_status": "decoded",
                    "trust": "tshark-iec60870-asdu",
                    "ca": obj["ca"],
                    "ioa": obj["ioa"],
                    "ca_ioa": obj["ca_ioa"],
                    "ipal_context": mapped.get("context"),
                    "fingerprint": fingerprint,
                    "parent_evidence_id": parent,
                    "src_ip": obj["src_ip"],
                    "dst_ip": obj["dst_ip"],
                    "src_port": obj["src_port"],
                    "dst_port": obj["dst_port"],
                    "protocol_class": obj["protocol_class"],
                    "payload": {
                        "cause": obj["cause"],
                        "type_id": obj["type_id"],
                        "alignment": obj["alignment"],
                        "apci_type": obj["apci_type"],
                        "packet_match": "unique" if parent else "unmatched_or_ambiguous",
                    },
                })
                decoded += 1
                counts["iec104_objects"] += 1
        conn.commit()
    return "; ".join(notes), decoded


def _cross_check(conn, limit: int = 400) -> dict:
    """Compare decoded IEC-104 numbers with a nearby IPAL state value of the same point."""
    rows = conn.execute(
        """SELECT evidence_id, timestamp, entity, value FROM evidence
           WHERE kind = 'iec104_asdu' AND value_present = 1 AND entity NOT LIKE 'ca_ioa:%'
           ORDER BY timestamp LIMIT ?""",
        (limit,),
    ).fetchall()
    compared = matched = 0
    for row in rows:
        later = conn.execute(
            """SELECT value FROM evidence
               WHERE modality = 'electrical' AND entity = ? AND value_present = 1
                 AND timestamp >= ? AND timestamp < ?
               ORDER BY timestamp LIMIT 1""",
            (row["entity"], row["timestamp"] - 0.05, row["timestamp"] + 2.0),
        ).fetchone()
        if later is None:
            continue
        compared += 1
        scale = max(1.0, abs(row["value"]), abs(later["value"]))
        matched += int(abs(row["value"] - later["value"]) <= 1e-3 * scale)
    return {
        "compared": compared,
        "matched": matched,
        "match_rate": (matched / compared) if compared else None,
        "rule": "nearest electrical value of the same entity in [-0.05s, +2s]",
    }


def _packet_key(vantage, src, dst, sport, dport, timestamp) -> tuple:
    return (vantage, src, dst, sport, dport, round(float(timestamp), 6))


def _state_vantage(member: str) -> str:
    found = re.search(r"\.(n\d+)\.state", member)
    return f"{found.group(1)}-state" if found else "state"


def _vantage(member: str) -> str:
    found = _VANTAGE.search(member)
    return found.group(1) if found else Path(member).stem
