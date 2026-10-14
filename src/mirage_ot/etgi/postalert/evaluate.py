"""Post-alert structural and audit metrics.

Important boundary:
- `sanity_checks` below check whether deterministic index queries or top-ranked
  pipeline items appear in the timeline/exposure. They are pipeline sanity
  checks, NOT an independent human-annotated event-importance gold or edge
  precision/recall benchmark.
"""
from __future__ import annotations
from .verify import verify_claims


def gold_facts(db, start: float, end: float, prepared: dict | None = None) -> dict:
    """Pipeline sanity probes (not independent event-importance gold)."""
    measurement = db.conn.execute(
        """SELECT evidence_id, entity, value FROM evidence
           WHERE kind = 'electrical_update' AND update_status = 'new' AND value_present = 1
             AND timestamp >= ? AND timestamp < ?
           ORDER BY evidence_id LIMIT 1""",
        (start, end),
    ).fetchone()
    pair = db.conn.execute(
        """SELECT a.evidence_id AS left_id, b.evidence_id AS right_id
           FROM evidence a JOIN evidence b
             ON a.kind = 'tcp_packet' AND b.kind = 'tcp_packet'
            AND a.src_ip = b.dst_ip AND a.dst_ip = b.src_ip
            AND a.src_port = b.dst_port AND a.dst_port = b.src_port
            AND a.evidence_id < b.evidence_id
            AND a.timestamp >= ? AND a.timestamp < ?
           LIMIT 1""",
        (start, end),
    ).fetchone()
    top_electrical = None
    top_comm = None
    if prepared:
        top_electrical = next((e for e in prepared["timeline"] if e.get("role") == "electrical_change"), None)
        top_comm = next((r for r in prepared["relations"] if r.get("relation_type") == "communication"), None)
    return {
        "note": "Pipeline sanity probes only. Not an independent event-importance or edge-precision gold.",
        "arbitrary_first_measurement_id": None if measurement is None else measurement["evidence_id"],
        "arbitrary_first_measurement_entity": None if measurement is None else measurement["entity"],
        "arbitrary_first_measurement_value": None if measurement is None else measurement["value"],
        "arbitrary_tcp_ids": [] if pair is None else [pair["left_id"], pair["right_id"]],
        "top_selected_electrical": None if top_electrical is None else {
            "timeline_id": top_electrical["timeline_id"],
            "entity": top_electrical["entity"],
            "value": top_electrical.get("value"),
            "evidence_ids": top_electrical["evidence_ids"],
        },
        "top_selected_communication": None if top_comm is None else {
            "edge_id": top_comm["edge_id"],
            "source_entity": top_comm["source_entity"],
            "target_entity": top_comm["target_entity"],
            "evidence_ids": top_comm["evidence_ids"],
        },
    }


def score_run(prepared: dict, result: dict, gold: dict, *, db=None) -> dict:
    lineage = prepared.get("lineage") or {}
    timeline_ids = {
        evidence_id
        for event in prepared["timeline"]
        for evidence_id in (lineage.get(event["timeline_id"]) or event["evidence_ids"])
    }
    exposed_ids = {
        evidence_id
        for event in (prepared.get("exposed_timeline") or [])
        for evidence_id in event.get("evidence_ids") or []
    }
    claims = result["model"]["claims"]
    verified = result["verification"].get("verified") or []
    rejected = result["verification"].get("rejected") or []
    if result["report"].get("level") == "B4":
        audit_verified = len(verified)
        audit_rejected = len(rejected)
    elif "offline_audit_verified" in result["verification"]:
        audit_verified = len(result["verification"].get("offline_audit_verified") or [])
        audit_rejected = len(result["verification"].get("offline_audit_rejected") or [])
    elif db is not None and claims:
        audited = verify_claims(db, claims, prepared["relations"], prepared["timeline"], lineage=lineage)
        audit_verified = len(audited["verified"])
        audit_rejected = len(audited["rejected"])
    else:
        audit_verified = 0
        audit_rejected = 0
    top_el = gold.get("top_selected_electrical")
    top_comm = gold.get("top_selected_communication")
    unverified_raw = result.get("unverified_model_claims") or []
    return {
        "timeline_events": len(prepared["timeline"]),
        "exposed_events": len(prepared.get("exposed_timeline") or []),
        "exposed_electrical_changes": sum(
            item.get("role") == "electrical_change" for item in (prepared.get("exposed_timeline") or [])
        ),
        "sanity_top_electrical_exposed": bool(top_el and set(top_el["evidence_ids"]) & exposed_ids) if top_el else None,
        "sanity_top_communication_in_relations": bool(top_comm) if top_comm is not None else False,
        "sanity_arbitrary_measurement_in_timeline": (
            gold["arbitrary_first_measurement_id"] in timeline_ids
            if gold.get("arbitrary_first_measurement_id") else None
        ),
        "observed_relations": sum(
            item.get("claim_level") == "observed_fact" and item.get("verification_status") == "supported"
            for item in prepared["relations"]
        ),
        "cooccurrence_relations": sum(
            item.get("claim_level") == "temporal_cooccurrence" for item in prepared["relations"]
        ),
        "supported_inferences": sum(
            item.get("claim_level") == "supported_inference" and item.get("verification_status") == "supported"
            for item in prepared["relations"]
        ),
        "disputed_relations": sum(
            item.get("verification_status") == "disputed" for item in prepared["relations"]
        ),
        "model_claims": len(claims),
        "partial_output": bool(result["model"].get("partial_output")),
        "salvaged_claim_count": int(result["model"].get("salvaged_claim_count") or 0),
        "model_abstained": result["model"]["abstain"],
        "verified_claims": len(verified),
        "rejected_claims": len(rejected),
        "offline_audit_verified_claims": audit_verified,
        "offline_audit_rejected_claims": audit_rejected,
        "claim_verification_rate": (audit_verified / len(claims)) if claims else None,
        "published_verified_claims": len(result["published_claims"]),
        "unverified_baseline_claims": len(unverified_raw),
        "confirmed_inferred_relations": len(result["report"].get("confirmed_inferred_relations") or []),
        "minimum_report": result["minimum"],
        "published_record_links": sum(
            claim.get("claim_type") == "relation_claim" and claim.get("canonical_origin") == "observed"
            for claim in result["published_claims"]
        ),
        "same_frame_relations": sum(item.get("relation_type") == "same_frame" for item in prepared["relations"]),
        "citation_presence_in_timeline": _citation_presence(timeline_ids, claims),
        "rejected_reasons": _reasons(result),
        **_attribution_counts(result),
    }


def _attribution_counts(result) -> dict:
    verification = result["verification"]
    pool = [
        *(verification.get("verified") or []), *(verification.get("rejected") or []),
        *(verification.get("offline_audit_verified") or []), *(verification.get("offline_audit_rejected") or []),
    ]
    time_match: dict[str, int] = {}
    for claim in pool:
        key = str(claim.get("time_match"))
        time_match[key] = time_match.get(key, 0) + 1
    return {
        "claims_with_model_supplied_evidence_ids": sum(bool(claim.get("model_supplied_evidence_ids")) for claim in pool),
        "claims_with_system_resolved_evidence_ids": sum(bool(claim.get("system_resolved_evidence_ids")) for claim in pool),
        "model_selected_fact_ids": sorted({item for claim in pool for item in claim.get("model_selected_fact_ids") or []}),
        "model_selected_edge_ids": sorted({item for claim in pool for item in claim.get("model_selected_edge_ids") or []}),
        "time_match": time_match,
    }


def _citation_presence(known: set[str], claims: list[dict]) -> float | None:
    cited = [str(item) for claim in claims for item in (claim.get("evidence_ids") or [])]
    if not cited:
        return None
    return sum(item in known for item in cited) / len(cited)


def _reasons(result) -> dict:
    counts = {}
    pool = result["verification"].get("rejected") or result["verification"].get("offline_audit_rejected") or []
    for claim in pool:
        for reason in claim.get("reasons") or []:
            key = reason.split(":", 1)[0]
            counts[key] = counts.get(key, 0) + 1
    return counts
