"""Cross-phase check that one quality decision is used everywhere.

Transaction gate, event-graph edge and node metadata, storyline status, and the
report must agree on the same pre/post quality and COT test bits. Any
disagreement is listed; nothing is repaired here.
"""
from __future__ import annotations

VERIFIED = ("verified_state_transition", "verified_measurement_transition")
VERIFIED_STORY = ("complete_with_verified_transition", "partial_missing_cot10_but_verified_measurement_transition")


def check_quality_consistency(tx_result: dict, event_graph: dict, storylines: dict, report: dict) -> dict:
    nodes = {n["fact_id"]: n for n in event_graph["nodes"]}
    edges = event_graph["edges"]
    stories = {s["transaction_id"]: s for s in storylines["storylines"] if s.get("transaction_id")}
    summaries = {t["transaction_id"]: t for t in report.get("transaction_summaries") or []}
    issues: list[dict] = []
    checks: list[dict] = []

    for tx in tx_result.get("transactions") or []:
        tx_id = tx["transaction_id"]
        mt = tx.get("measurement_transition")
        fb = (tx.get("protocol_state_feedback") or [None])[0]
        if mt is not None:
            gate, target_role, entity = mt.get("consistency_gate") or {}, "post_command_measurement", mt["measurement_entity"]
        elif fb is not None:
            gate, target_role, entity = fb.get("consistency_gate") or {}, "spontaneous_state_feedback", fb["entity"]
        else:
            continue
        passed = bool(gate.get("gate_passed"))
        status_verified = tx["device_state_change_status"] in VERIFIED

        target = next((n for n in nodes.values()
                       if n.get("transaction_id") == tx_id and n["role"] == target_role and n["entity"] == entity), None)
        inference_edges = [e for e in edges if e["relation_category"] == "inference_hypothesis"
                           and target is not None and e["target_fact_id"] == target["fact_id"]]
        graph_supported = any(e["claim_level"] == "supported_inference" for e in inference_edges)
        story = stories.get(tx_id)
        story_verified = bool(story and story["completeness_status"] in VERIFIED_STORY)
        story_supported_steps = bool(story and any(
            st["claim_level"] == "supported_inference" for st in story["confirmed_and_supported_steps"]))
        summary_gate = (summaries.get(tx_id) or {}).get("inference_gate") or {}

        row = {
            "transaction_id": tx_id,
            "transaction_gate_passed": passed,
            "transaction_status_verified": status_verified,
            "graph_supported_inference": graph_supported,
            "storyline_verified_status": story_verified,
            "storyline_has_supported_inference_step": story_supported_steps,
            "report_gate_passed": summary_gate.get("gate_passed"),
        }
        checks.append(row)
        if status_verified != passed:
            issues.append({"transaction_id": tx_id, "issue": "status_disagrees_with_transaction_gate"})
        if graph_supported != passed:
            issues.append({"transaction_id": tx_id, "issue": "graph_inference_disagrees_with_transaction_gate"})
        if story is not None and story_verified != passed:
            issues.append({"transaction_id": tx_id, "issue": "storyline_status_disagrees_with_transaction_gate"})
        if story_supported_steps and not passed:
            issues.append({"transaction_id": tx_id, "issue": "storyline_uses_inference_rejected_by_gate"})
        if summary_gate.get("gate_passed") != gate.get("gate_passed"):
            issues.append({"transaction_id": tx_id, "issue": "report_gate_disagrees_with_transaction_gate"})
        for key in ("pre_quality_invalid", "post_quality_invalid", "pre_quality_flags_set",
                    "post_quality_flags_set", "test_bits"):
            if summary_gate.get(key) != gate.get(key):
                issues.append({"transaction_id": tx_id, "issue": f"report_{key}_differs"})
        if target is not None:
            meta = target.get("protocol_meta") or {}
            node_iv = meta.get("quality_invalid", meta.get("post_quality_invalid"))
            if node_iv != gate.get("post_quality_invalid"):
                issues.append({"transaction_id": tx_id, "issue": "graph_node_post_quality_differs"})

    for edge in edges:
        if edge["claim_level"] == "supported_inference" and \
                edge.get("graph_consistency_gate_status") != "passed_noncausal_inference_gate":
            issues.append({"edge_id": edge["edge_id"], "issue": "supported_inference_without_passed_gate"})

    verified_in_report = len(report.get("verified_device_transitions") or [])
    verified_in_tx = sum(1 for tx in tx_result.get("transactions") or [] if tx["device_state_change_status"] in VERIFIED)
    if verified_in_report != verified_in_tx:
        issues.append({"issue": "report_verified_transition_count_differs",
                       "report": verified_in_report, "transactions": verified_in_tx})
    return {"consistent": not issues, "checks": checks, "issues": issues}
