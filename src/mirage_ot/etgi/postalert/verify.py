"""Check each claim against the indexed rows, then render the published text.

Four claim kinds are accepted: observation_claim, measurement_claim,
relation_claim, and absence_claim. Free prose in `statement` is not trusted as
a verified fact. When a claim passes, `rendered_text` is built from the bound
rows and endpoints.

Canonical anchor binding:
- When `fact_id` (`timeline_id`) or `edge_id` is supplied, it acts as the
  primary key into the trusted timeline or relation table.
- Any explicitly supplied field (`entity`, `source_entity`, `target_entity`,
  `relation_type`, `claim_level`, `evidence_ids`) must match the canonical
  anchor and its lineage; conflicting fields or level upgrades (such as
  promoting an `observed_fact` record link to `supported_inference`) are
  rejected.
"""
from __future__ import annotations

TIME_TOLERANCE_SECONDS = 1.0
_LEVELS = {"observed_fact", "temporal_cooccurrence", "supported_inference", "unresolved", "disputed"}
_CAUSAL = (" cause", " caused", " because of the attack", " triggered by ")
_CLAIM_KINDS = ("observation_claim", "measurement_claim", "relation_claim", "absence_claim")


def verify_claims(db, claims: list[dict], relations: list[dict], timeline: list[dict] | None = None,
                  lineage: dict[str, list[str]] | None = None) -> dict:
    verified = []
    rejected = []
    timeline_by_id = {event["timeline_id"]: event for event in (timeline or []) if event.get("timeline_id")}
    edge_by_id = {relation["edge_id"]: relation for relation in relations if relation.get("edge_id")}
    lineage_map = _build_lineage_map(timeline_by_id, lineage)
    for index, raw in enumerate(claims):
        if not isinstance(raw, dict):
            rejected.append({"claim_index": index, "reasons": ["claim_not_an_object"]})
            continue
        claim = _normalize(raw, timeline_by_id, edge_by_id, lineage_map)
        reasons, rendered, meta = _check(db, claim, raw, relations, timeline_by_id, edge_by_id, lineage_map)
        record = {"claim_index": index, **claim, **meta, **_attribution(raw, claim, timeline_by_id),
                  "reasons": reasons}
        if reasons:
            rejected.append(record)
        else:
            record["rendered_text"] = rendered
            record["verified_prose"] = rendered
            if claim.get("statement"):
                record["unverified_model_statement"] = claim["statement"]
            verified.append(record)
    return {"verified": verified, "rejected": rejected}


def _attribution(raw: dict, claim: dict, timeline_by_id: dict) -> dict:
    """Separate what the model chose from what the system filled in."""
    fact_id = raw.get("fact_id") or raw.get("timeline_id")
    supplied = [str(item) for item in raw.get("evidence_ids") or []]
    resolved = [] if supplied else [str(item) for item in claim.get("evidence_ids") or []]
    return {
        "model_selected_fact_ids": [fact_id] if fact_id else [],
        "model_selected_edge_ids": [raw["edge_id"]] if raw.get("edge_id") else [],
        "model_supplied_evidence_ids": supplied,
        "system_resolved_evidence_ids": resolved,
        "time_tolerance_seconds": TIME_TOLERANCE_SECONDS,
        "time_match": _time_match(raw, timeline_by_id.get(fact_id) if fact_id else None),
    }


def _time_match(raw: dict, event: dict | None) -> str:
    supplied = [raw.get(key) for key in ("time", "start_time", "end_time") if raw.get(key) is not None]
    if not supplied:
        return "inherited_from_anchor" if event else "no_time_supplied"
    if event is None:
        return "row_tolerance_only"
    try:
        stamps = [float(item) for item in supplied]
    except (TypeError, ValueError):
        return "not_numeric"
    low = float(event["time"])
    high = float(event.get("time_end", event["time"]))
    if all(low <= stamp <= high for stamp in stamps):
        return "exact_anchor"
    if all(low - TIME_TOLERANCE_SECONDS <= stamp <= high + TIME_TOLERANCE_SECONDS for stamp in stamps):
        return "tolerance_aligned"
    return "outside_tolerance"


def _build_lineage_map(timeline_by_id: dict[str, dict], lineage: dict[str, list[str]] | None) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for tid, event in timeline_by_id.items():
        ids = set(event.get("evidence_ids") or []) | set(event.get("lineage") or [])
        if lineage and tid in lineage:
            ids |= set(lineage[tid] or [])
        out[tid] = ids
    return out


def _normalize(raw: dict, timeline_by_id: dict, edge_by_id: dict, lineage_map: dict[str, set[str]]) -> dict:
    claim = dict(raw)
    if claim.get("claim_type") not in _CLAIM_KINDS:
        claim["claim_type"] = _infer_kind(claim, timeline_by_id, edge_by_id)
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    if fact_id in timeline_by_id:
        event = timeline_by_id[fact_id]
        if not claim.get("evidence_ids"):
            claim["evidence_ids"] = list(event.get("evidence_ids") or [])
        if not claim.get("entity"):
            claim["entity"] = event.get("entity")
        if claim.get("time") is None and claim.get("start_time") is None and claim.get("end_time") is None:
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
        if not claim.get("relation_type"):
            claim["relation_type"] = edge.get("relation_type")
        if not claim.get("source_entity"):
            claim["source_entity"] = edge.get("source_entity")
        if not claim.get("target_entity"):
            claim["target_entity"] = edge.get("target_entity")
        if not claim.get("evidence_ids"):
            claim["evidence_ids"] = list(edge.get("evidence_ids") or [])
        if not claim.get("claim_level"):
            claim["claim_level"] = edge.get("claim_level")
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


def _check(db, claim: dict, raw: dict, relations: list[dict], timeline_by_id: dict,
           edge_by_id: dict, lineage_map: dict[str, set[str]]) -> tuple[list[str], str, dict]:
    reasons = []
    statement = str(claim.get("statement") or "").lower()
    if any(token in f" {statement} " for token in _CAUSAL):
        reasons.append("causal_claim_not_established")
    level = claim.get("claim_level")
    if level and level not in _LEVELS:
        reasons.append("unknown_claim_level")
    kind = claim.get("claim_type")
    if kind == "absence_claim":
        out_reasons, text = _check_absence(db, claim, reasons)
        return out_reasons, text, {"canonical_claim_level": "observed_fact", "canonical_origin": "observed"}
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    if fact_id and fact_id not in timeline_by_id:
        reasons.append("unknown_fact_id")
        return reasons, "", {}
    edge_id = claim.get("edge_id")
    if edge_id and edge_id not in edge_by_id:
        reasons.append("unknown_edge_id")
        return reasons, "", {}
    ids = [str(item) for item in claim.get("evidence_ids") or [] if str(item).startswith("EV-")]
    if not ids:
        reasons.append("missing_evidence_ids")
        return reasons, "", {}
    rows = db.get(ids)["rows"]
    found = {row["evidence_id"]: row for row in rows}
    missing = [item for item in ids if item not in found]
    if missing:
        reasons.append("evidence_id_not_in_database:" + ",".join(missing[:6]))
    if not rows:
        return reasons, "", {}
    if kind == "observation_claim":
        out_reasons, text = _check_observation(claim, raw, rows, timeline_by_id, lineage_map, reasons)
        return out_reasons, text, {"canonical_claim_level": "observed_fact", "canonical_origin": "observed"}
    if kind == "measurement_claim":
        out_reasons, text = _check_measurement(claim, raw, rows, timeline_by_id, lineage_map, reasons)
        return out_reasons, text, {"canonical_claim_level": "observed_fact", "canonical_origin": "observed"}
    if kind == "relation_claim":
        return _check_relation(claim, raw, rows, relations, timeline_by_id, edge_by_id, lineage_map, reasons)
    reasons.append("unknown_claim_type")
    return reasons, "", {}


def _check_fact_anchor(raw: dict, claim: dict, timeline_by_id: dict, lineage_map: dict[str, set[str]],
                       reasons: list[str]) -> dict | None:
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    if not fact_id:
        return None
    if fact_id not in timeline_by_id:
        reasons.append("unknown_fact_id")
        return None
    event = timeline_by_id[fact_id]
    if raw.get("entity") and raw.get("entity") not in (event.get("entity"), event.get("ca_ioa")):
        reasons.append("fact_id_entity_mismatch")
    allowed = lineage_map.get(fact_id) or set(event.get("evidence_ids") or [])
    if raw.get("evidence_ids"):
        supplied = {str(item) for item in raw["evidence_ids"] if str(item).startswith("EV-")}
        if not supplied or not (supplied <= allowed):
            reasons.append("fact_id_evidence_mismatch")
    if raw.get("time") is not None or raw.get("start_time") is not None or raw.get("end_time") is not None:
        if not _event_time_matches_claim(claim, event):
            reasons.append("fact_id_time_mismatch")
    if raw.get("claim_level") and raw.get("claim_level") not in ("observed_fact", "unresolved"):
        reasons.append("fact_claim_level_mismatch")
    return event


def _event_time_matches_claim(claim: dict, event: dict) -> bool:
    if not _time_parseable(claim):
        return False
    low = float(event["time"])
    high = float(event.get("time_end", event["time"]))
    if claim.get("time") is not None:
        stamp = float(claim["time"])
        return low - TIME_TOLERANCE_SECONDS <= stamp <= high + TIME_TOLERANCE_SECONDS
    start = low if claim.get("start_time") is None else float(claim["start_time"])
    end = high if claim.get("end_time") is None else float(claim["end_time"])
    if end < start:
        return False
    return start <= high + TIME_TOLERANCE_SECONDS and end >= low - TIME_TOLERANCE_SECONDS


def _check_observation(claim: dict, raw: dict, rows: list[dict], timeline_by_id: dict,
                       lineage_map: dict[str, set[str]], reasons: list[str]) -> tuple[list[str], str]:
    fact_id = claim.get("fact_id") or claim.get("timeline_id")
    entity = claim.get("entity")
    if not fact_id and not entity:
        reasons.append("missing_observation_anchor")
        return reasons, ""
    _check_fact_anchor(raw, claim, timeline_by_id, lineage_map, reasons)
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


def _check_measurement(claim: dict, raw: dict, rows: list[dict], timeline_by_id: dict,
                       lineage_map: dict[str, set[str]], reasons: list[str]) -> tuple[list[str], str]:
    _check_fact_anchor(raw, claim, timeline_by_id, lineage_map, reasons)
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


def _check_relation(claim: dict, raw: dict, rows: list[dict], relations: list[dict],
                    timeline_by_id: dict, edge_by_id: dict, lineage_map: dict[str, set[str]],
                    reasons: list[str]) -> tuple[list[str], str, dict]:
    edge_id = claim.get("edge_id")
    edge = edge_by_id.get(edge_id) if edge_id else None
    if edge_id and edge is None:
        reasons.append("unknown_edge_id")
        return reasons, "", {}
    if edge is not None:
        if raw.get("relation_type") and raw.get("relation_type") != edge.get("relation_type"):
            reasons.append("edge_relation_type_mismatch")
        if raw.get("source_entity") or raw.get("target_entity"):
            claimed_pair = {raw.get("source_entity") or edge.get("source_entity"),
                            raw.get("target_entity") or edge.get("target_entity")}
            canonical_pair = {edge.get("source_entity"), edge.get("target_entity")}
            if claimed_pair != canonical_pair:
                reasons.append("edge_endpoint_mismatch")
        allowed_ids = _edge_allowed_ids(edge, timeline_by_id, lineage_map)
        if raw.get("evidence_ids"):
            supplied = {str(item) for item in raw["evidence_ids"] if str(item).startswith("EV-")}
            if not supplied or not (supplied <= allowed_ids):
                reasons.append("edge_evidence_not_in_edge_provenance")
    source = edge.get("source_entity") if edge else claim.get("source_entity")
    target = edge.get("target_entity") if edge else claim.get("target_entity")
    rel_type = edge.get("relation_type") if edge else claim.get("relation_type")
    if not source or not target or not rel_type:
        reasons.append("relation_missing_endpoints_or_type")
        return reasons, "", {}
    if edge is None:
        edge = next((
            item for item in relations
            if {item.get("source_entity"), item.get("target_entity")} == {source, target}
            and item.get("relation_type") == rel_type
        ), None)
    if edge is None:
        reasons.append("relation_not_supported_by_timeline")
        return reasons, "", {}
    left_rows = [row for row in rows if _entity_matches(row, source)]
    right_rows = [row for row in rows if _entity_matches(row, target)]
    if not left_rows or not right_rows:
        reasons.append("relation_missing_endpoint_evidence")
        return reasons, "", {}
    if _same_underlying_source(left_rows, right_rows) and rel_type not in ("shared_source", "same_frame"):
        reasons.append("same_source_counted_as_independent_evidence")
    edge_level = edge.get("claim_level")
    claimed_level = raw.get("claim_level") or claim.get("claim_level") or edge_level
    if claimed_level == "supported_inference" and edge_level == "temporal_cooccurrence":
        reasons.append("time_proximity_is_not_supported_inference")
    elif claimed_level == "supported_inference" and edge_level == "observed_fact":
        reasons.append("observed_link_cannot_be_upgraded_to_inference")
    elif claimed_level != edge_level:
        reasons.append("claim_level_does_not_match_canonical_edge")
    if edge.get("status") == "disputed" and claimed_level in ("observed_fact", "supported_inference"):
        reasons.append("relation_is_disputed")
    canonical_origin = "inferred" if edge_level in ("supported_inference", "temporal_cooccurrence") else "observed"
    meta = {
        "canonical_claim_level": edge_level,
        "canonical_origin": canonical_origin,
        "canonical_status": edge.get("verification_status") or edge.get("status"),
    }
    if reasons:
        return reasons, "", meta
    ids = ", ".join(dict.fromkeys([left_rows[0]["evidence_id"], right_rows[0]["evidence_id"]]))
    return [], (
        f"Relation {rel_type} between {source} and {target} has claim_level={edge_level} "
        f"and status={edge.get('status')} ({ids}). Causal status: not_established."
    ), meta


def _edge_allowed_ids(edge: dict, timeline_by_id: dict, lineage_map: dict[str, set[str]]) -> set[str]:
    """The edge's own ids plus the lineage of its two endpoint facts, not every fact on the same entity."""
    allowed = set(edge.get("evidence_ids") or [])
    for tid in (edge.get("source_fact_id"), edge.get("target_fact_id")):
        if tid and tid in timeline_by_id:
            allowed |= lineage_map.get(tid, set(timeline_by_id[tid].get("evidence_ids") or []))
    return allowed


def _check_absence(db, claim: dict, reasons: list[str]) -> tuple[list[str], str]:
    kind = claim.get("absent_kind")
    if kind not in ("arp_packet", "iec104_control"):
        reasons.append("unsupported_absence_claim")
        return reasons, ""
    if db.incident_start is None or db.incident_end is None:
        reasons.append("absence_window_not_indexed")
        return reasons, ""
    start = float(db.incident_start) if claim.get("start_time") is None else float(claim["start_time"])
    end = float(db.incident_end) if claim.get("end_time") is None else float(claim["end_time"])
    if end <= start or start < float(db.incident_start) - 1e-6 or end > float(db.incident_end) + 1e-6:
        reasons.append("absence_range_outside_indexed_incident_window")
        return reasons, ""
    total_rows = db.conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE timestamp >= ? AND timestamp < ?",
        ( float(db.incident_start), float(db.incident_end) ),
    ).fetchone()[0]
    if total_rows == 0:
        reasons.append("absence_window_has_no_indexed_observations")
        return reasons, ""
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
        return abs(stamp - float(claim["time"])) <= TIME_TOLERANCE_SECONDS
    start = None if claim.get("start_time") is None else float(claim["start_time"])
    end = None if claim.get("end_time") is None else float(claim["end_time"])
    if start is not None and end is not None and end < start:
        return False
    if start is not None and stamp < start - TIME_TOLERANCE_SECONDS:
        return False
    if end is not None and stamp > end + TIME_TOLERANCE_SECONDS:
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
