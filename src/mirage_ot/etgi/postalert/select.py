"""Rank incident rows against a background interval.

An IEC-104 frame can carry several information objects. The frame is kept as
the source container in lineage, but each (class, entity, CA/IOA) point is its
own observation group, so values of different points are never mixed.

Scores are log-scaled and comparable only within one role. The category quotas
are a fixed exposure policy so one high-frequency modality does not crowd out
the others; neither the score nor the quotas are an event-importance gold.
IEC type-id classes are decoder ranges, not attack labels.
"""
from __future__ import annotations
import math
from ..evidence.store import public_row

_HOLD = {"hold", "initial"}
SCORE_CAP = 10.0
RELATIVE_FLOOR = 0.01
COVERAGE_POLICY_NOTE = (
    "Fixed category quotas keep network flows, decoded ASDU points, and IPAL electrical updates "
    "represented when present. They are an exposure policy, not an attack classifier or importance gold."
)


def select_evidence(db, start: float, end: float, *, background_start: float | None = None,
                    background_end: float | None = None, limit: int = 24) -> dict:
    background_end = start if background_end is None else background_end
    background_start = background_end if background_start is None else background_start
    incident_seconds = max(end - start, 1.0)
    background = _load(db, background_start, background_end) if background_start < background_end else []
    background_seconds = _observed_span(background, background_start, background_end)
    background_status = _background_status(background, background_start, background_end)
    incident = _load(db, start, end)
    excluded = []
    kept_rows = []
    for row in incident:
        reason = _exclude_reason(row)
        if reason:
            excluded.append({"evidence_id": row["evidence_id"], "reason": reason})
        else:
            kept_rows.append(row)
    groups = _groups(kept_rows)
    collapsed = [
        {"evidence_id": row["evidence_id"], "reason": "same_packet_derivative", "attached_to": row["parent_evidence_id"]}
        for row in kept_rows if row.get("parent_evidence_id")
    ]
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
            "background_seconds_requested": max(background_end - background_start, 0.0),
            "background_seconds_observed": background_seconds,
            "background_status": background_status,
            "order": "score descending within each role quota, then time",
            "score_scale": f"min(log1p(z), {SCORE_CAP}); comparable within one role only",
            "limit": limit,
            "coverage_policy": COVERAGE_POLICY_NOTE,
        },
        "incident_rows": len(incident),
        "background_rows": len(background),
        "available_by_modality": _modality_counts(kept_rows),
        "available_by_kind": _kind_counts(kept_rows),
        "candidate_groups_by_kind": _group_kind_counts(groups),
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


def _observed_span(rows: list[dict], start: float, end: float) -> float:
    if not rows:
        return 0.0
    low = max(start, min(row["timestamp"] for row in rows))
    high = min(end, max(row["timestamp"] for row in rows))
    return max(high - low, 0.0)


def _background_status(rows: list[dict], start: float, end: float) -> str:
    if end <= start:
        return "none_requested"
    if not rows:
        return "empty_not_indexed_or_no_rows"
    return "observed"


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
        elif row["kind"] == "iec104_asdu":
            kind_key = "packet_control" if row.get("protocol_class") == "control" else "packet"
            key = (kind_key, row.get("entity"), row.get("ca_ioa"))
        else:
            key = ("row", row["evidence_id"])
        bucket = grouped.setdefault(key, {"rows": [], "time": row["timestamp"]})
        bucket["rows"].append(row)
        bucket["time"] = min(bucket["time"], row["timestamp"])
    return grouped


def _numeric(rows: list[dict]) -> list[float]:
    return [
        float(row["value"]) for row in rows
        if row.get("value_present") and isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)
    ]


def _score(key, group, background, *, incident_seconds: float, background_seconds: float) -> tuple[float, dict]:
    rows = group["rows"]
    if key[0] == "tcp":
        frames = len({row.get("fingerprint") or row["evidence_id"] for row in rows})
        base_frames = len({row.get("fingerprint") or row["evidence_id"] for row in background["rows"]}) if background else 0
        incident_rate = frames / max(incident_seconds, 1.0)
        background_rate = (base_frames / background_seconds) if background and background_seconds > 0 else None
        basis = "rate_minus_background" if background_rate is not None else "rate_without_background"
        excess = incident_rate - (background_rate or 0.0)
        mapped = 1.0 if rows[0].get("src_ip") and rows[0].get("dst_ip") else 0.5
        score = min(math.log1p(max(excess, 0.0)), SCORE_CAP) * mapped
        return score, {
            "basis": basis,
            "packets_at_vantage": len(rows),
            "distinct_frames": frames,
            "background_distinct_frames": base_frames,
            "frames_per_second": round(incident_rate, 4),
            "background_frames_per_second": None if background_rate is None else round(background_rate, 4),
            "mapped": mapped == 1.0,
        }
    values = _numeric(rows)
    background_values = _numeric(background["rows"]) if background else []
    z, basis = _robust_change(values, background_values)
    quality = 1.0 if values else 0.25
    mapped = 1.0 if any(row.get("ca_ioa") or ":" in str(row.get("entity") or "") for row in rows) else 0.6
    score = min(math.log1p(z), SCORE_CAP) * quality * mapped
    return score, {
        "basis": basis, "z": round(z, 4), "quality": quality, "mapped": mapped == 1.0,
        "samples": len(values), "background_values": len(background_values),
        "iec_class": rows[0].get("protocol_class"),
    }


def _robust_change(values: list[float], background: list[float]) -> tuple[float, str]:
    """Change in units of background spread, or of 1% of the level when spread is zero."""
    if not values:
        return 0.0, "no_numeric_value"
    if len(background) >= 3:
        center = _median(background)
        spread = 1.4826 * _mad(background, center)
        if spread > 0:
            return max(abs(value - center) for value in values) / spread, "background_robust_z"
        scale = max(abs(center) * RELATIVE_FLOOR, 1e-6)
        return max(abs(value - center) for value in values) / scale, "background_flat_relative_1pct"
    if background:
        center = _median(background)
        scale = max(abs(center) * RELATIVE_FLOOR, 1e-6)
        return max(abs(value - center) for value in values) / scale, "background_sparse_relative_1pct"
    if len(values) >= 2:
        center = _median(values)
        scale = max(abs(center) * RELATIVE_FLOOR, 1e-6)
        return (max(values) - min(values)) / scale, "within_window_range_relative_1pct"
    return 0.0, "single_sample_no_background"


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


def _group_kind_counts(groups: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in groups:
        counts[key[0]] = counts.get(key[0], 0) + 1
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
