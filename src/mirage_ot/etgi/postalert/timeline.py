"""One timeline event per observation, with derivatives attached to their packet.

TCP packet lengths are stored in `packet_bytes` rather than `value`, so a byte
count is not mistaken for an electrical measurement. Complete evidence id
lineage is returned alongside the truncated preview list.

An IEC-104 event covers one information object (entity, CA/IOA). Its parent
frame is shared lineage with the other objects carried in that frame, so those
sibling events are not independent sources and their values are never merged.
The same frame seen at several vantages is one sample.
"""
from __future__ import annotations


def build_timeline(selection: dict) -> list[dict]:
    events, _lineage = build_timeline_with_lineage(selection)
    return events


def build_timeline_with_lineage(selection: dict) -> tuple[list[dict], dict[str, list[str]]]:
    events = []
    full_ids: dict[str, list[str]] = {}
    frames: dict[str, set[str]] = {}
    for index, item in enumerate(selection["selected"], start=1):
        rows = sorted(item["group"]["rows"], key=lambda row: (row["timestamp"], row["evidence_id"]))
        kind = rows[0]["kind"]
        vantages = list(dict.fromkeys(row.get("vantage") for row in rows if row.get("vantage")))
        ids = list(dict.fromkeys(
            [row["evidence_id"] for row in rows]
            + [row["parent_evidence_id"] for row in rows if row.get("parent_evidence_id")]
        ))
        role, record_class = _role(rows)
        value_fields = _value_fields(rows, kind)
        timeline_id = f"TL{index:03d}"
        full_ids[timeline_id] = list(ids)
        frames[timeline_id] = {row.get("fingerprint") or row["evidence_id"] for row in rows}
        events.append({
            "timeline_id": timeline_id,
            "time": min(row["timestamp"] for row in rows),
            "time_end": max(row["timestamp"] for row in rows),
            "entity": rows[0]["entity"],
            "source": {
                "modality": rows[0]["modality"],
                "kind": kind,
                "vantages": vantages,
                "trust": rows[0].get("trust"),
            },
            "observation": _observation(rows, value_fields)[:400],
            "evidence_ids": ids[:4],
            "evidence_id_count": len(ids),
            "lineage_ref": f"lineage.json#{timeline_id}",
            "role": role,
            "record_class": record_class,
            **value_fields,
            "ca_ioa": next((row.get("ca_ioa") for row in rows if row.get("ca_ioa")), None),
            "fingerprint": next((row.get("fingerprint") for row in rows if row.get("fingerprint")), None),
            "src_ip": rows[0].get("src_ip"),
            "dst_ip": rows[0].get("dst_ip"),
            "protocol_class": rows[0].get("protocol_class"),
            "lineage": list(dict.fromkeys(row["parent_evidence_id"] for row in rows if row.get("parent_evidence_id"))),
            "source_frame_count": len(frames[timeline_id]),
            "source_container": "iec104_frame" if kind == "iec104_asdu" else None,
            "independent": not rows[0].get("parent_evidence_id"),
            "score": item["score"],
        })
    merged = _merge_same_frame(events, full_ids)
    merged = _merge_same_flow(merged, full_ids, frames)
    merged.sort(key=lambda event: (event["time"], event["timeline_id"]))
    kept_ids = {event["timeline_id"]: full_ids[event["timeline_id"]] for event in merged}
    for event in merged:
        event["evidence_id_count"] = len(kept_ids[event["timeline_id"]])
    return merged, kept_ids


def _value_fields(rows: list[dict], kind: str) -> dict:
    if kind != "tcp_packet":
        rows = _one_row_per_frame(rows)
    present = [
        row["value"] for row in rows
        if row.get("value_present") and isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)
    ]
    if kind == "tcp_packet":
        by_vantage: dict[str, int] = {}
        for row in rows:
            name = str(row.get("vantage") or "unspecified")
            by_vantage[name] = by_vantage.get(name, 0) + 1
        return {
            "value": None,
            "value_present": False,
            "value_semantics": "packet_length_bytes",
            "packet_count": len(rows),
            "packet_count_by_vantage": by_vantage,
            "distinct_frame_count": len({row.get("fingerprint") or row["evidence_id"] for row in rows}),
            "packet_bytes_min": min(present) if present else None,
            "packet_bytes_max": max(present) if present else None,
        }
    if not present:
        return {"value": None, "value_present": False, "value_semantics": "measurement"}
    return {
        "value": present[0],
        "value_first": present[0],
        "value_last": present[-1],
        "value_min": min(present),
        "value_max": max(present),
        "sample_count": len(present),
        "sample_basis": "distinct_source_frames",
        "value_present": True,
        "value_semantics": "network_reported_measurement",
    }


def _role(rows: list[dict]) -> tuple[str, str]:
    kind = rows[0]["kind"]
    if any(not row.get("value_present") for row in rows) and kind != "tcp_packet":
        record = "missing"
    elif kind == "tcp_packet" or kind == "arp_packet":
        record = "direct_observation"
    else:
        record = "transcription"
    protocol = rows[0].get("protocol_class")
    if kind == "tcp_packet":
        return "communication", "direct_observation"
    if protocol == "control":
        return "command", record
    if kind == "iec104_asdu":
        return "electrical_report" if rows[0].get("value_present") else "response", record
    if kind == "electrical_update":
        return "electrical_change", record
    return "communication", record


def _observation(rows: list[dict], value_fields: dict) -> str:
    row = rows[0]
    vantages = ",".join(dict.fromkeys(item.get("vantage") or "" for item in rows if item.get("vantage"))) or "unspecified"
    if row["kind"] == "tcp_packet":
        low = value_fields.get("packet_bytes_min")
        high = value_fields.get("packet_bytes_max")
        size = f"{low}B" if low == high else f"{low}..{high}B"
        return f"tcp_packet {row['entity']} packets={len(rows)} frame_bytes={size} vantage {vantages}"
    if not value_fields.get("value_present"):
        return f"{row['kind']} {row['entity']} measurement=missing vantage {vantages}"
    first = value_fields.get("value_first")
    last = value_fields.get("value_last")
    shown = f"{first}" if first == last else f"{first}->{last} (min={value_fields.get('value_min')}, max={value_fields.get('value_max')})"
    point = f" ca_ioa={row['ca_ioa']}" if row.get("ca_ioa") else ""
    return f"{row['kind']} {row['entity']}{point} measurement={shown} vantage {vantages}"


def _one_row_per_frame(rows: list[dict]) -> list[dict]:
    seen = set()
    kept = []
    for row in rows:
        key = row.get("fingerprint") or row["evidence_id"]
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def _merge_same_flow(events: list[dict], full_ids: dict[str, list[str]], frames: dict[str, set[str]]) -> list[dict]:
    """The same TCP 5-tuple at several switches is one communication.

    `packet_count` sums per-vantage captures; `distinct_frame_count` counts each
    frame once by fingerprint.
    """
    by_entity = {}
    kept = []
    for event in events:
        if event["role"] != "communication":
            kept.append(event)
            continue
        prior = by_entity.get(event["entity"])
        if prior is None:
            by_entity[event["entity"]] = event
            kept.append(event)
            continue
        tid = prior["timeline_id"]
        other_tid = event["timeline_id"]
        full_ids[tid] = list(dict.fromkeys([*full_ids.get(tid, []), *full_ids.get(other_tid, [])]))
        prior["source"]["vantages"] = list(dict.fromkeys([*prior["source"]["vantages"], *event["source"]["vantages"]]))
        prior["evidence_ids"] = full_ids[tid][:4]
        prior["evidence_id_count"] = len(full_ids[tid])
        prior["packet_count"] = int(prior.get("packet_count") or 0) + int(event.get("packet_count") or 0)
        by_vantage = dict(prior.get("packet_count_by_vantage") or {})
        for name, count in (event.get("packet_count_by_vantage") or {}).items():
            by_vantage[name] = by_vantage.get(name, 0) + count
        prior["packet_count_by_vantage"] = by_vantage
        frames[tid] = frames.get(tid, set()) | frames.get(other_tid, set())
        prior["distinct_frame_count"] = len(frames[tid])
        prior["source_frame_count"] = len(frames[tid])
        prior["time"] = min(prior["time"], event["time"])
        prior["time_end"] = max(prior["time_end"], event["time_end"])
    return kept


def _merge_same_frame(events: list[dict], full_ids: dict[str, list[str]]) -> list[dict]:
    """One observation of one point seen at several switches stays one event.

    Events from the same frame but a different entity or CA/IOA are distinct
    information objects and are kept apart.
    """
    by_print = {}
    merged = []
    for event in events:
        fingerprint = event.get("fingerprint")
        if not fingerprint or event["role"] in ("electrical_change", "communication"):
            merged.append(event)
            continue
        key = (fingerprint, event.get("entity"), event.get("ca_ioa"))
        prior = by_print.get(key)
        if prior is None:
            by_print[key] = event
            merged.append(event)
            continue
        tid = prior["timeline_id"]
        other_tid = event["timeline_id"]
        full_ids[tid] = list(dict.fromkeys([*full_ids.get(tid, []), *full_ids.get(other_tid, [])]))
        prior["source"]["vantages"] = list(dict.fromkeys([*prior["source"]["vantages"], *event["source"]["vantages"]]))
        prior["evidence_ids"] = full_ids[tid][:4]
        prior["evidence_id_count"] = len(full_ids[tid])
        prior["time"] = min(prior["time"], event["time"])
        prior["time_end"] = max(prior["time_end"], event["time_end"])
        prior["observation"] = (prior["observation"] + "; also " + event["observation"])[:400]
    return merged
