"""Check each model claim against the indexed rows. Rejections are kept."""
from __future__ import annotations

_LEVELS = {"observed_fact", "temporal_cooccurrence", "supported_inference", "unresolved", "disputed"}
_CAUSAL = (" cause", " caused", " because of the attack")


def verify_claims(db, claims: list[dict], relations: list[dict]) -> dict:
    verified = []
    rejected = []
    for index, claim in enumerate(claims):
        reasons = _reasons(db, claim, relations)
        record = {"claim_index": index, **claim, "reasons": reasons}
        if reasons:
            rejected.append(record)
        else:
            verified.append(record)
    return {"verified": verified, "rejected": rejected}


def _reasons(db, claim: dict, relations: list[dict]) -> list[str]:
    reasons = []
    statement = str(claim.get("statement") or "").lower()
    if any(token in f" {statement}" for token in _CAUSAL):
        reasons.append("causal_claim_not_established")
    ids = [str(item) for item in claim.get("evidence_ids") or [] if str(item).startswith("EV-")]
    if not ids:
        reasons.append("missing_evidence_ids")
        return reasons
    rows = db.get(ids)["rows"]
    found = {row["evidence_id"] for row in rows}
    missing = [item for item in ids if item not in found]
    if missing:
        reasons.append("evidence_id_not_in_database:" + ",".join(missing[:6]))
    if not rows:
        return reasons
    entity = claim.get("entity")
    if entity and not any(row["entity"] == entity or row.get("ca_ioa") == entity for row in rows):
        reasons.append("entity_does_not_match_cited_rows")
    if claim.get("time") is not None:
        try:
            stamp = float(claim["time"])
        except (TypeError, ValueError):
            reasons.append("time_not_numeric")
        else:
            if stamp < min(row["timestamp"] for row in rows) - 1 or stamp > max(row["timestamp"] for row in rows) + 1:
                reasons.append("time_outside_cited_rows")
    if claim.get("value") is not None:
        if not any(_same_value(row.get("value"), claim["value"]) for row in rows if row.get("value_present")):
            reasons.append("value_does_not_match_cited_rows")
    direction = claim.get("direction")
    if direction in ("increase", "decrease", "unchanged"):
        ordered = sorted((row for row in rows if row.get("value_present")), key=lambda row: row["timestamp"])
        if len(ordered) < 2:
            reasons.append("direction_without_two_values")
        else:
            delta = ordered[-1]["value"] - ordered[0]["value"]
            expected = {"increase": delta > 0, "decrease": delta < 0, "unchanged": abs(delta) <= 1e-6}[direction]
            if not expected:
                reasons.append("direction_does_not_match_cited_values")
    fingerprints = [row.get("fingerprint") for row in rows if row.get("fingerprint")]
    modalities = {row["modality"] for row in rows}
    if len(modalities) > 1 and len(fingerprints) != len(set(fingerprints)):
        reasons.append("same_packet_counted_as_independent_evidence")
    level = claim.get("claim_level")
    if level and level not in _LEVELS:
        reasons.append("unknown_claim_level")
    if level in ("observed_fact", "supported_inference"):
        if not _relation_supports(ids, level, relations):
            reasons.append("relation_not_supported_by_timeline")
    if level == "supported_inference" and _only_time(ids, relations):
        reasons.append("time_proximity_is_not_supported_inference")
    return reasons


def _relation_supports(ids: list[str], level: str, relations: list[dict]) -> bool:
    cited = set(ids)
    for relation in relations:
        if relation.get("claim_level") != level:
            continue
        if cited & set(relation.get("evidence_ids") or []):
            return True
    return False


def _only_time(ids: list[str], relations: list[dict]) -> bool:
    cited = set(ids)
    matches = [relation for relation in relations if cited & set(relation.get("evidence_ids") or [])]
    return bool(matches) and all(relation.get("claim_level") == "temporal_cooccurrence" for relation in matches)


def _same_value(stored, claimed) -> bool:
    try:
        return abs(float(stored) - float(claimed)) <= 1e-3
    except (TypeError, ValueError):
        return str(stored) == str(claimed)
