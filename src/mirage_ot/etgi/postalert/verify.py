"""Check each claim against the indexed rows, then render the published text.

Four claim kinds are accepted: observation_claim, measurement_claim,
relation_claim, and absence_claim. Free prose in `statement` is not trusted as
a verified fact. When a claim passes, `rendered_text` is built from the bound
rows and endpoints.
"""
from __future__ import annotations

_LEVELS = {"observed_fact", "temporal_cooccurrence", "supported_inference", "unresolved", "disputed"}
_CAUSAL = (" cause", " caused", " because of the attack", " triggered by ")
_CLAIM_KINDS = ("observation_claim", "measurement_claim", "relation_claim", "absence_claim")


def verify_claims(db, claims: list[dict], relations: list[dict], timeline: list[dict] | None = None) -> dict:
    verified = []
    rejected = []
    timeline_by_id = {event["timeline_id"]: event for event in (timeline or []) if event.get("timeline_id")}
    edge_by_id = {relation["edge_id"]: relation for relation in relations if relation.get("edge_id")}
    for index, raw in enumerate(claims):
        if not isinstance(raw, dict):
            rejected.append({"claim_index": index, "reasons": ["claim_not_an_object"]})
            continue
        claim = _normalize(raw, timeline_by_id, edge_by_id)
        reasons, rendered = _check(db, claim, relations, timeline_by_id, edge_by_id)
        record = {"claim_index": index, **claim, "reasons": reasons}
        if reasons:
            rejected.append(record)
        else:
            record["rendered_text"] = rendered
            record["verified_prose"] = rendered
            if claim.get("statement"):
                record["unverified_model_statement"] = claim["statement"]
            verified.append(record)
    return {"verified": verified, "rejected": rejected}


def _normalize(raw: dict, timeline_by_id: dict, edge_by_id: dict) -> dict:
    claim = dict(raw)
    if claim.get("claim_type") not in _CLAIM_KINDS:
        claim["claim_type"] = _infer_kind(claim, timeline_by_id, edge_by_id)
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    if fact_id in timeline_by_id:
        event = timeline_by_id[fact_id]
        claim.setdefault("evidence_ids", list(event.get("evidence_ids") or []))
        claim.setdefault("entity", event.get("entity"))
        if claim.get("time") is None and claim.get("start_time") is None:
            if event.get("time") == event.get("time_end"):
                claim["time"] = event.get("time")
            else:
                claim["start_time"] = event.get("time")
                claim["end_time"] = event.get("time_end")
        if claim["claim_type"] == "measurement_claim" and claim.get("value") is None:
            claim["value"] = event.get("value")
    edge_id = claim.get("edge_id")
    if edge_id in edge_by_id:
        edge = edge_by_id[edge_id]
        claim.setdefault("relation_type", edge.get("relation_type"))
        claim.setdefault("source_entity", edge.get("source_entity"))
        claim.setdefault("target_entity", edge.get("target_entity"))
        claim.setdefault("evidence_ids", list(edge.get("evidence_ids") or []))
        claim.setdefault("claim_level", edge.get("claim_level"))
    time_value = claim.get("time")
    if isinstance(time_value, dict):
        claim.setdefault("start_time", time_value.get("start"))
        claim.setdefault("end_time", time_value.get("end"))
        claim["time"] = None
    return claim


def _infer_kind(claim: dict, timeline_by_id: dict, edge_by_id: dict) -> str:
    if claim.get("edge_id") in edge_by_id or (claim.get("source_entity") and claim.get("target_entity")):
        return "relation_claim"
    if claim.get("absent_role") or claim.get("absent_kind"):
        return "absence_claim"
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    if fact_id in timeline_by_id:
        role = timeline_by_id[fact_id].get("role")
        return "measurement_claim" if role in ("electrical_change", "electrical_report") else "observation_claim"
    value = claim.get("value")
    if value is not None and not isinstance(value, bool):
        return "measurement_claim"
    return "observation_claim"


def _check(db, claim: dict, relations: list[dict], timeline_by_id: dict, edge_by_id: dict) -> tuple[list[str], str]:
    reasons = []
    statement = str(claim.get("statement") or "").lower()
    if any(token in f" {statement} " for token in _CAUSAL):
        reasons.append("causal_claim_not_established")
    level = claim.get("claim_level")
    if level and level not in _LEVELS:
        reasons.append("unknown_claim_level")
    kind = claim.get("claim_type")
    if kind == "absence_claim":
        return _check_absence(db, claim, reasons)
    ids = [str(item) for item in claim.get("evidence_ids") or [] if str(item).startswith("EV-")]
    if not ids:
        reasons.append("missing_evidence_ids")
        return reasons, ""
    rows = db.get(ids)["rows"]
    found = {row["evidence_id"]: row for row in rows}
    missing = [item for item in ids if item not in found]
    if missing:
        reasons.append("evidence_id_not_in_database:" + ",".join(missing[:6]))
    if not rows:
        return reasons, ""
    if kind == "observation_claim":
        return _check_observation(claim, rows, timeline_by_id, reasons)
    if kind == "measurement_claim":
        return _check_measurement(claim, rows, timeline_by_id, reasons)
    if kind == "relation_claim":
        return _check_relation(claim, rows, relations, edge_by_id, reasons)
    reasons.append("unknown_claim_type")
    return reasons, ""


def _check_observation(claim: dict, rows: list[dict], timeline_by_id: dict, reasons: list[str]) -> tuple[list[str], str]:
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    entity = claim.get("entity")
    if not fact_id and not entity:
        reasons.append("missing_observation_anchor")
        return reasons, ""
    if fact_id and fact_id not in timeline_by_id:
        reasons.append("unknown_fact_id")
    value = claim.get("value")
    if value is not None and not isinstance(value, bool):
        if not any(row["kind"] == "tcp_packet" and _same_number(row.get("value"), value) for row in rows):
            reasons.append("unexpected_value_on_observation_claim")
    matching = [row for row in rows if _entity_matches(row, entity)] if entity else list(rows)
    if not matching:
        reasons.append("entity_does_not_match_cited_rows")
        return reasons, ""
    _check_time(claim, matching, reasons)
    if reasons:
        return reasons, ""
    first = matching[0]
    ids = ", ".join(row["evidence_id"] for row in matching[:4])
    span = _format_span(matching)
    return [], f"Observed {first['kind']} on {first['entity']} at {span} ({ids})."


def _check_measurement(claim: dict, rows: list[dict], timeline_by_id: dict, reasons: list[str]) -> tuple[list[str], str]:
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    if fact_id and fact_id not in timeline_by_id:
        reasons.append("unknown_fact_id")
    entity = claim.get("entity")
    value = claim.get("value")
    if not entity:
        reasons.append("missing_entity")
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        reasons.append("value_must_be_numeric")
        return reasons, ""
    atomic = [
        row for row in rows
        if row["kind"] in ("electrical_update", "iec104_asdu")
        and row.get("value_present")
        and _entity_matches(row, entity)
        and _same_number(row.get("value"), value)
        and _row_in_time(claim, row)
    ]
    if not atomic:
        if not any(_entity_matches(row, entity) for row in rows):
            reasons.append("entity_does_not_match_cited_rows")
        elif not any(row.get("value_present") and _same_number(row.get("value"), value) for row in rows):
            reasons.append("value_does_not_match_cited_rows")
        elif not any(_row_in_time(claim, row) for row in rows):
            reasons.append("time_outside_cited_rows")
        else:
            reasons.append("fields_do_not_match_same_row")
        return reasons, ""
    direction = claim.get("direction")
    if direction in ("increase", "decrease", "unchanged"):
        same_entity = sorted(
            (row for row in rows if row.get("value_present") and _entity_matches(row, entity)),
            key=lambda row: row["timestamp"],
        )
        if len(same_entity) < 2:
            reasons.append("direction_without_two_values_for_entity")
        else:
            delta = same_entity[-1]["value"] - same_entity[0]["value"]
            expected = {"increase": delta > 0, "decrease": delta < 0, "unchanged": abs(delta) <= 1e-6}[direction]
            if not expected:
                reasons.append("direction_does_not_match_cited_values")
    if reasons:
        return reasons, ""
    chosen = atomic[0]
    return [], (
        f"Reported {chosen['kind']} for {chosen['entity']} at {chosen['timestamp']} is "
        f"{chosen['value']} ({chosen['evidence_id']}). Network-reported, not independent physical truth."
    )


def _check_relation(claim: dict, rows: list[dict], relations: list[dict], edge_by_id: dict,
                    reasons: list[str]) -> tuple[list[str], str]:
    edge = edge_by_id.get(claim.get("edge_id"))
    source = claim.get("source_entity") or (edge or {}).get("source_entity")
    target = claim.get("target_entity") or (edge or {}).get("target_entity")
    rel_type = claim.get("relation_type") or (edge or {}).get("relation_type")
    if not source or not target or not rel_type:
        reasons.append("relation_missing_endpoints_or_type")
        return reasons, ""
    if edge is None:
        edge = next((
            item for item in relations
            if {item.get("source_entity"), item.get("target_entity")} == {source, target}
            and item.get("relation_type") == rel_type
        ), None)
    if edge is None:
        reasons.append("relation_not_supported_by_timeline")
        return reasons, ""
    left_rows = [row for row in rows if _entity_matches(row, source)]
    right_rows = [row for row in rows if _entity_matches(row, target)]
    if not left_rows or not right_rows:
        reasons.append("relation_missing_endpoint_evidence")
        return reasons, ""
    if _same_underlying_source(left_rows, right_rows) and rel_type not in ("shared_source", "same_frame"):
        reasons.append("same_source_counted_as_independent_evidence")
    level = claim.get("claim_level") or edge.get("claim_level")
    edge_level = edge.get("claim_level")
    if level == "supported_inference" and edge_level == "temporal_cooccurrence":
        reasons.append("time_proximity_is_not_supported_inference")
    if level == "observed_fact" and edge_level != "observed_fact":
        reasons.append("claim_level_exceeds_relation_check")
    if level == "supported_inference" and edge_level not in ("observed_fact", "supported_inference"):
        reasons.append("claim_level_exceeds_relation_check")
    if edge.get("status") == "disputed" and level in ("observed_fact", "supported_inference"):
        reasons.append("relation_is_disputed")
    if reasons:
        return reasons, ""
    ids = ", ".join(dict.fromkeys([left_rows[0]["evidence_id"], right_rows[0]["evidence_id"]]))
    return [], (
        f"Relation {rel_type} between {source} and {target} has claim_level={edge.get('claim_level')} "
        f"and status={edge.get('status')} ({ids}). Causal status: not_established."
    )


def _check_absence(db, claim: dict, reasons: list[str]) -> tuple[list[str], str]:
    kind = claim.get("absent_kind")
    if kind not in ("arp_packet", "iec104_control"):
        reasons.append("unsupported_absence_claim")
        return reasons, ""
    start = db.incident_start if claim.get("start_time") is None else float(claim["start_time"])
    end = db.incident_end if claim.get("end_time") is None else float(claim["end_time"])
    if kind == "arp_packet":
        count = db.conn.execute(
            "SELECT COUNT(*) FROM evidence WHERE kind = 'arp_packet' AND timestamp >= ? AND timestamp < ?",
            (start, end),
        ).fetchone()[0]
    else:
        count = db.conn.execute(
            """SELECT COUNT(*) FROM evidence WHERE kind = 'iec104_asdu' AND protocol_class = 'control'
               AND timestamp >= ? AND timestamp < ?""",
            (start, end),
        ).fetchone()[0]
    if count != 0:
        reasons.append("claimed_absent_kind_is_present")
        return reasons, ""
    return [], f"No {kind} rows are indexed between {start} and {end}."


def _same_underlying_source(left_rows: list[dict], right_rows: list[dict]) -> bool:
    for left in left_rows:
        for right in right_rows:
            if left["evidence_id"] == right["evidence_id"]:
                return True
            if left.get("fingerprint") and left["fingerprint"] == right.get("fingerprint"):
                return True
            if left.get("parent_evidence_id") and left["parent_evidence_id"] in (
                    right["evidence_id"], right.get("parent_evidence_id")):
                return True
            if right.get("parent_evidence_id") and right["parent_evidence_id"] == left["evidence_id"]:
                return True
            if left.get("ca_ioa") and left["ca_ioa"] == right.get("ca_ioa") and left["modality"] != right["modality"]:
                return True
    return False


def _entity_matches(row: dict, entity: str | None) -> bool:
    if not entity:
        return False
    return row.get("entity") == entity or row.get("ca_ioa") == entity


def _check_time(claim: dict, rows: list[dict], reasons: list[str]) -> None:
    if claim.get("time") is None and claim.get("start_time") is None and claim.get("end_time") is None:
        return
    if not any(_row_in_time(claim, row) for row in rows):
        if not _time_parseable(claim):
            reasons.append("time_not_numeric")
        else:
            reasons.append("time_outside_cited_rows")


def _time_parseable(claim: dict) -> bool:
    for key in ("time", "start_time", "end_time"):
        value = claim.get(key)
        if value is None or isinstance(value, bool):
            if isinstance(value, bool):
                return False
            continue
        try:
            float(value)
        except (TypeError, ValueError):
            return False
    return True


def _row_in_time(claim: dict, row: dict) -> bool:
    if not _time_parseable(claim):
        return False
    stamp = row["timestamp"]
    if claim.get("time") is not None:
        return abs(stamp - float(claim["time"])) <= 1.0
    start = None if claim.get("start_time") is None else float(claim["start_time"])
    end = None if claim.get("end_time") is None else float(claim["end_time"])
    if start is not None and end is not None and end < start:
        return False
    if start is not None and stamp < start - 1.0:
        return False
    if end is not None and stamp > end + 1.0:
        return False
    return True


def _same_number(stored, claimed) -> bool:
    if isinstance(stored, bool) or isinstance(claimed, bool):
        return False
    try:
        return abs(float(stored) - float(claimed)) <= 1e-3
    except (TypeError, ValueError):
        return False


def _format_span(rows: list[dict]) -> str:
    low = min(row["timestamp"] for row in rows)
    high = max(row["timestamp"] for row in rows)
    return f"{low}" if low == high else f"{low}..{high}"
