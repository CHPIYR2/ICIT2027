"""Rank incident rows against a background interval.

The score uses a change relative to the background, whether a value is present,
and whether a device or CA/IOA mapping exists. IEC type-id classes are the
decoder's monitor/control/system ranges. They are not attack labels.
The category quotas below are a fixed coverage policy so one high-frequency
modality does not crowd out the others; they are not an attack importance rule.
"""
from __future__ import annotations
from ..evidence.store import public_row

_HOLD = {"hold", "initial"}
COVERAGE_POLICY_NOTE = (
    "Fixed category quotas ensure network flows, decoded ASDUs, and IPAL electrical updates "
    "remain represented when present. They are an exposure policy, not an attack classifier."
)


def select_evidence(db, start: float, end: float, *, background_start: float | None = None,
                    background_end: float | None = None, limit: int = 24) -> dict:
    background_end = start if background_end is None else background_end
    background_start = background_end if background_start is None else background_start
    incident_seconds = max(end - start, 1.0)
    background_seconds = max(background_end - background_start, 0.0)
    incident = _load(db, start, end)
    background = _load(db, background_start, background_end) if background_start < background_end else []
    excluded = []
    kept_rows = []
    for row in incident:
        reason = _exclude_reason(row)
        if reason:
            excluded.append({"evidence_id": row["evidence_id"], "reason": reason})
        else:
            kept_rows.append(row)
    groups = _groups(kept_rows)
    collapsed = []
    for row in kept_rows:
        if row.get("parent_evidence_id"):
            collapsed.append({"evidence_id": row["evidence_id"], "reason": "same_packet_derivative",
                              "attached_to": row["parent_evidence_id"]})
    background_groups = _groups([row for row in background if _exclude_reason(row) is None])
    ranked = []
    for key, group in groups.items():
        score, detail = _score(
            key, group, background_groups.get(key),
            incident_seconds=incident_seconds, background_seconds=background_seconds,
        )
        ranked.append({"key": key, "group": group, "score": score, "score_detail": detail})
    ranked.sort(key=lambda item: (-item["score"], item["group"]["time"]))
    selected = []
    selected_keys = set()
    for kind, quota in (("tcp", 8), ("packet_control", 3), ("packet", 5), ("electrical", 8)):
        kept = 0
        for item in ranked:
            if item["key"][0] != kind or item["key"] in selected_keys:
                continue
            selected.append(item)
            selected_keys.add(item["key"])
            kept += 1
            if kept >= quota or len(selected) >= limit:
                break
    for item in ranked:
        if len(selected) >= limit:
            break
        if item["key"] in selected_keys:
            continue
        selected.append(item)
        selected_keys.add(item["key"])
    for item in ranked:
        if item["key"][0] != "tcp" or item["key"] in selected_keys:
            continue
        reverse = _reverse_key(item["key"])
        if reverse in selected_keys and len(selected) < limit + 8:
            item["score_detail"] = {**item["score_detail"], "included_because": "reverse_direction_of_a_selected_flow"}
            selected.append(item)
            selected_keys.add(item["key"])
    counts: dict[str, int] = {}
    for item in excluded:
        counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    collapsed_counts: dict[str, int] = {}
    for item in collapsed:
        collapsed_counts[item["reason"]] = collapsed_counts.get(item["reason"], 0) + 1
    return {
        "query": {
            "table": "evidence",
            "incident_start": start,
            "incident_end": end,
            "background_start": background_start,
            "background_end": background_end,
            "incident_seconds": incident_seconds,
            "background_seconds": background_seconds,
            "order": "score descending, then time",
            "limit": limit,
            "coverage_policy": COVERAGE_POLICY_NOTE,
        },
        "incident_rows": len(incident),
        "background_rows": len(background),
        "available_by_modality": _modality_counts(kept_rows),
        "available_by_kind": _kind_counts(kept_rows),
        "excluded_count": len(excluded),
        "excluded_by_reason": counts,
        "collapsed_by_reason": collapsed_counts,
        "excluded_ids_sample": excluded[:40],
        "candidates": len(ranked),
        "selected": selected,
    }


def _load(db, start: float, end: float) -> list[dict]:
    found = db.conn.execute(
        """SELECT * FROM evidence WHERE timestamp >= ? AND timestamp < ?
           ORDER BY timestamp, evidence_id""",
        (start, end),
    ).fetchall()
    return [public_row(row) for row in found]


def _exclude_reason(row: dict) -> str | None:
    if row.get("update_status") in _HOLD or row.get("kind") == "electrical_hold_summary":
        return "forward_filled_or_initial_state"
    return None


def _groups(rows: list[dict]) -> dict:
    grouped = {}
    for row in rows:
        if row["kind"] == "tcp_packet":
            key = ("tcp", row.get("entity"), row.get("vantage"))
        elif row["kind"] == "electrical_update":
            key = ("electrical", row.get("entity"))
        elif row.get("parent_evidence_id") or (row.get("fingerprint") and row["kind"] == "iec104_asdu"):
            kind_key = "packet_control" if row.get("protocol_class") == "control" else "packet"
            key = (kind_key, row.get("parent_evidence_id") or row.get("fingerprint"))
        else:
            key = ("row", row["evidence_id"])
        bucket = grouped.setdefault(key, {"rows": [], "time": row["timestamp"]})
        bucket["rows"].append(row)
        bucket["time"] = min(bucket["time"], row["timestamp"])
    return grouped


def _score(key, group, background, *, incident_seconds: float, background_seconds: float) -> tuple[float, dict]:
    rows = group["rows"]
    if key[0] == "tcp":
        current = len(rows)
        base = len(background["rows"]) if background else 0
        incident_rate = current / max(incident_seconds, 1.0)
        background_rate = (base / background_seconds) if background and background_seconds > 0 else 0.0
        mapped = 1.0 if rows[0].get("src_ip") and rows[0].get("dst_ip") else 0.5
        return max(incident_rate - background_rate, 0.0) * mapped, {
            "packets": current,
            "background_packets": base,
            "packets_per_second": round(incident_rate, 4),
            "background_packets_per_second": round(background_rate, 4),
            "mapped": mapped == 1.0,
        }
    values = [
        row["value"] for row in rows
        if row.get("value_present") and isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)
    ]
    background_values = []
    if background:
        background_values = [
            row["value"] for row in background["rows"]
            if row.get("value_present") and isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)
        ]
    quality = 1.0 if values else 0.25
    mapped = 1.0 if any(row.get("ca_ioa") or ":" in str(row.get("entity") or "") for row in rows) else 0.6
    if background_values and values:
        center = _median(background_values)
        scale = _mad(background_values, center) or 1e-3
        change = max(abs(value - center) / scale for value in values)
    elif len(values) >= 2:
        change = max(values) - min(values)
    elif values:
        change = 1.0
    else:
        change = 0.0
    iec = 1.0
    if any(row.get("protocol_class") == "control" for row in rows):
        iec = 2.0
    return change * quality * mapped * iec, {
        "change": change, "quality": quality, "mapped": mapped == 1.0,
        "iec_class_weight": iec, "background_values": len(background_values),
    }


def _modality_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        mod = str(row.get("modality") or "unknown")
        counts[mod] = counts.get(mod, 0) + 1
    return counts


def _kind_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        kind = str(row.get("kind") or "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _reverse_key(key):
    if key[0] != "tcp" or not key[1] or "->" not in key[1] or not str(key[1]).endswith("/TCP"):
        return None
    body = key[1][: -len("/TCP")]
    left, right = body.split("->", 1)
    return ("tcp", f"{right}->{left}/TCP", key[2])


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _mad(values: list[float], center: float) -> float:
    return _median([abs(value - center) for value in values])
