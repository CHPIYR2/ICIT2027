"""One timeline event per observation, with derivatives attached to their packet."""
from __future__ import annotations


def build_timeline(selection: dict) -> list[dict]:
    events = []
    for index, item in enumerate(selection["selected"], start=1):
        rows = item["group"]["rows"]
        kind = rows[0]["kind"]
        vantages = list(dict.fromkeys(row.get("vantage") for row in rows if row.get("vantage")))
        ids = list(dict.fromkeys(
            [row["evidence_id"] for row in rows]
            + [row["parent_evidence_id"] for row in rows if row.get("parent_evidence_id")]
        ))
        role, record_class = _role(rows)
        present = [row for row in rows if row.get("value_present")]
        value = present[0]["value"] if present else None
        events.append({
            "timeline_id": f"TL{index:03d}",
            "time": min(row["timestamp"] for row in rows),
            "time_end": max(row["timestamp"] for row in rows),
            "entity": rows[0]["entity"],
            "source": {
                "modality": rows[0]["modality"],
                "kind": kind,
                "vantages": vantages,
                "trust": rows[0].get("trust"),
            },
            "observation": _observation(rows, value)[:400],
            "evidence_ids": ids[:4],
            "evidence_id_count": len(ids),
            "role": role,
            "record_class": record_class,
            "value": value,
            "value_present": value is not None,
            "ca_ioa": next((row.get("ca_ioa") for row in rows if row.get("ca_ioa")), None),
            "fingerprint": next((row.get("fingerprint") for row in rows if row.get("fingerprint")), None),
            "src_ip": rows[0].get("src_ip"),
            "dst_ip": rows[0].get("dst_ip"),
            "protocol_class": rows[0].get("protocol_class"),
            "lineage": [row["parent_evidence_id"] for row in rows if row.get("parent_evidence_id")],
            "independent": not rows[0].get("parent_evidence_id"),
            "score": item["score"],
        })
    merged = _merge_same_frame(events)
    merged = _merge_same_flow(merged)
    merged.sort(key=lambda event: (event["time"], event["timeline_id"]))
    return merged


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


def _observation(rows: list[dict], value) -> str:
    row = rows[0]
    shown = "missing" if value is None else value
    vantages = ",".join(dict.fromkeys(item.get("vantage") or "" for item in rows if item.get("vantage")))
    return f"{row['kind']} {row['entity']} value {shown} vantage {vantages or 'unspecified'}"


def _merge_same_flow(events: list[dict]) -> list[dict]:
    """The same TCP 5-tuple at several switches is one communication."""
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
        prior["source"]["vantages"] = list(dict.fromkeys([*prior["source"]["vantages"], *event["source"]["vantages"]]))
        prior["evidence_ids"] = list(dict.fromkeys([*prior["evidence_ids"], *event["evidence_ids"]]))[:4]
        prior["evidence_id_count"] = prior.get("evidence_id_count", 0) + event.get("evidence_id_count", 0)
        prior["time"] = min(prior["time"], event["time"])
        prior["time_end"] = max(prior["time_end"], event["time_end"])
    return kept


def _merge_same_frame(events: list[dict]) -> list[dict]:
    """One Ethernet frame seen at several switches stays one timeline event."""
    by_print = {}
    merged = []
    for event in events:
        fingerprint = event.get("fingerprint")
        if not fingerprint or event["role"] == "electrical_change":
            merged.append(event)
            continue
        prior = by_print.get(fingerprint)
        if prior is None:
            by_print[fingerprint] = event
            merged.append(event)
            continue
        prior["source"]["vantages"] = list(dict.fromkeys([*prior["source"]["vantages"], *event["source"]["vantages"]]))
        prior["evidence_ids"] = list(dict.fromkeys([*prior["evidence_ids"], *event["evidence_ids"]]))[:4]
        prior["evidence_id_count"] = prior.get("evidence_id_count", 0) + event.get("evidence_id_count", 0)
        prior["time"] = min(prior["time"], event["time"])
        prior["time_end"] = max(prior["time_end"], event["time_end"])
        prior["observation"] = (prior["observation"] + "; also " + event["observation"])[:400]
    return merged
