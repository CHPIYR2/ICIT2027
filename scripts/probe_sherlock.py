#!/usr/bin/env python3
"""Inspect complete ZIP members, including during a resumable download.

This is a preliminary structural probe, not a replacement for archive hashing.
Only stored/deflated entries with explicit 32-bit lengths are supported in partial
files. Stop at incomplete entries; never infer values for unavailable members.
"""

from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
MAX_MEMBER = 64 * 1024 * 1024


def selected(name):
    return name.endswith(("/events.json", "/events.jsonl", "/rules.py", "/initial_state.json", "/data-point-map.json")) or name.endswith(".state.gz")


def complete_members(path):
    available = path.stat().st_size
    with path.open("rb") as stream:
        while True:
            header_offset = stream.tell()
            header = stream.read(30)
            if len(header) != 30 or header[:4] != b"PK\x03\x04":
                return
            _, _, flags, method, _, _, crc, compressed, size, nl, el = struct.unpack("<IHHHHHIIIHH", header)
            raw_name = stream.read(nl)
            extra = stream.read(el)
            if len(raw_name) != nl or len(extra) != el:
                return
            name = raw_name.decode("utf-8" if flags & 0x800 else "cp437")
            if flags & 9 or compressed == 0xFFFFFFFF or size == 0xFFFFFFFF:
                return
            if stream.tell() + compressed > available:
                return
            if selected(name) and size <= MAX_MEMBER and compressed <= MAX_MEMBER:
                payload = stream.read(compressed)
                if method == 8:
                    inflater = zlib.decompressobj(-15)
                    data = inflater.decompress(payload, MAX_MEMBER + 1)
                    if not inflater.eof or inflater.unused_data:
                        raise ValueError(f"Incomplete/oversized deflate stream: {name}")
                elif method == 0:
                    data = payload
                else:
                    continue
                if len(data) != size or zlib.crc32(data) & 0xFFFFFFFF != crc:
                    raise ValueError(f"Member size/CRC mismatch: {name}")
                yield name, data, header_offset
            else:
                stream.seek(compressed, 1)


def summarize(name, data):
    result = {"member": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "crc_valid": True}
    if name.endswith("/events.json"):
        events = json.loads(data)
        benign = sum("(benign event)" in str(e.get("id", "")) for e in events)
        descriptions = Counter(e.get("description") for e in events)
        result.update(kind="evaluator_events", count=len(events), benign_id_count=benign,
                      other_id_count=len(events)-benign,
                      label_note="Counts use literal '(benign event)' ID marker; other IDs are not automatically assigned a final research label.",
                      keys=sorted({k for e in events for k in e}), descriptions=dict(descriptions),
                      earliest_start=min((e["start"] for e in events), default=None),
                      latest_end=max((e["end"] for e in events), default=None),
                      recovery_present=sum("recovery" in e for e in events))
    elif name.endswith("/events.jsonl"):
        records = [json.loads(line) for line in data.splitlines() if line.strip()]
        result.update(kind="evaluator_notification_log", notification_count=len(records),
                      event_count_note="Notification rows are NOT independent research events.",
                      keys=sorted({k for r in records for k in r}),
                      notification_keys=sorted({k for r in records for k in r.get("notification_data", {})}),
                      first_simulation_clock_record=next((r for r in records if r.get("notification_data", {}).get("event") == "simulation"), None))
    elif name.endswith(".state.gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            first = stream.readline(4 * 1024 * 1024)
            if not first.endswith(b"\n"):
                raise ValueError("State first record is too large or not line-delimited")
        record = json.loads(first)
        state = record["state"]
        result.update(kind="first_state_record_only", keys=sorted(record), timestamp=record["timestamp"],
                      state_field_count=len(state), state_fields=sorted(state),
                      first_row_null_count=sum(v is None for v in state.values()),
                      first_row_zero_count=sum(not isinstance(v, bool) and v == 0 for v in state.values()),
                      first_state_sha256=hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest(),
                      lineage_fields_present=[k for k in record if any(w in k.lower() for w in ("parent", "packet", "source", "lineage"))])
    elif name.endswith("/initial_state.json"):
        state = json.loads(data)
        result.update(kind="initial_state", field_count=len(state),
                      state_sha256=hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest())
    elif name.endswith("/rules.py"):
        text = data.decode()
        result.update(kind="transformation_source_not_executed",
                      nan_to_zero_pattern_count=text.count("0 if x[0]!=x[0] else x[0]"))
    else:
        parsed = json.loads(data)
        result.update(kind="mapping", top_level_type=type(parsed).__name__, top_level_count=len(parsed),
                      entry_keys=sorted({k for r in parsed.values() for k in r}),
                      contexts=dict(Counter(r.get("context") for r in parsed.values())),
                      units=dict(Counter(r.get("unit") for r in parsed.values())),
                      scales=dict(Counter(r.get("scale") for r in parsed.values())))
    return result


def probe(root=ROOT):
    results = []
    for path in sorted((root / "data/raw/sherlock/v3").glob("*.zip*")):
        if not path.name.endswith((".zip", ".zip.part")):
            continue
        for name, data, offset in complete_members(path):
            result = summarize(name, data)
            result.update(archive=path.name, local_header_offset=offset,
                          archive_hash_status="pending" if path.name.endswith(".part") else "see sherlock_manifest.json")
            results.append(result)
    output = {"status": "preliminary_only", "not_for_training": True,
              "warning": "Member CRC checks do not replace full archive MD5/SHA256 verification. State inspection samples first records only.",
              "members": results}
    (root / "data/manifests/sherlock_preliminary.json").write_text(json.dumps(output, indent=2) + "\n")
    return output


if __name__ == "__main__":
    summary = probe()
    print(f"Inspected {len(summary['members'])} complete members; PRELIMINARY ONLY")
