"""Scores that do not use the model's own text as gold."""
from __future__ import annotations


def gold_facts(db, start: float, end: float) -> dict:
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
    return {
        "measurement_id": None if measurement is None else measurement["evidence_id"],
        "measurement_entity": None if measurement is None else measurement["entity"],
        "measurement_value": None if measurement is None else measurement["value"],
        "tcp_ids": [] if pair is None else [pair["left_id"], pair["right_id"]],
    }


def score_run(prepared: dict, result: dict, gold: dict) -> dict:
    timeline_ids = {evidence_id for event in prepared["timeline"] for evidence_id in event["evidence_ids"]}
    claims = result["model"]["claims"]
    return {
        "timeline_events": len(prepared["timeline"]),
        "measurement_in_timeline": gold["measurement_id"] in timeline_ids if gold["measurement_id"] else None,
        "tcp_pair_in_timeline": all(item in timeline_ids for item in gold["tcp_ids"]) if gold["tcp_ids"] else None,
        "observed_relations": sum(item.get("claim_level") == "observed_fact" for item in prepared["relations"]),
        "cooccurrence_relations": sum(item.get("claim_level") == "temporal_cooccurrence" for item in prepared["relations"]),
        "supported_inferences": sum(item.get("claim_level") == "supported_inference" for item in prepared["relations"]),
        "disputed_relations": sum(item.get("claim_level") == "disputed" for item in prepared["relations"]),
        "model_claims": len(claims),
        "model_abstained": result["model"]["abstain"],
        "verified_claims": len(result["verification"].get("verified") or []),
        "rejected_claims": len(result["verification"].get("rejected") or []),
        "published_claims": len(result["published_claims"]),
        "minimum_report": result["minimum"],
        "citation_validity": _citation_validity(prepared, claims),
        "rejected_reasons": _reasons(result),
    }


def _citation_validity(prepared, claims) -> float | None:
    known = {evidence_id for event in prepared["timeline"] for evidence_id in event["evidence_ids"]}
    cited = [str(item) for claim in claims for item in (claim.get("evidence_ids") or [])]
    if not cited:
        return None
    return sum(item in known for item in cited) / len(cited)


def _reasons(result) -> dict:
    counts = {}
    for claim in result["verification"].get("rejected") or []:
        for reason in claim.get("reasons") or []:
            key = reason.split(":", 1)[0]
            counts[key] = counts.get(key, 0) + 1
    return counts
