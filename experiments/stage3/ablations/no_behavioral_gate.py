"""Ablation A1: Without Behavioral Consistency Gate.

Preserves the exact same Event Anchors and same-device candidate pairs (`same_device_stem`,
`separate_asdu`, `0 <= dt <= 15.0s`), as well as post-command same-device feedback pairs,
but removes `evaluate_behavioral_relation_consistency()` and `evaluate_command_effect_inference()`.

Terminology rule:
Without external ground-truth labels on every internal relation, promoted edges that fail
evidentiary constraints are NEVER called "False Positives"; they are recorded precisely as
`unsupported_promotion` with explicit `evidence_constraint_violation` categories:
- `quality_or_test_bit_violation`
- `persistence_insufficient_violation`
- `prior_state_baseline_missing_violation`
- `change_type_mismatch_violation`
- `magnitude_or_direction_conflict_violation`
- `non_complementary_or_disjoint_interval_violation`
"""
from __future__ import annotations


def _categorize_behavioral_failed_conditions(failed_conditions: list[str], left_issues: list[str], right_issues: list[str]) -> list[str]:
    cats: list[str] = []
    cond_set = set(failed_conditions)
    all_issues = [*left_issues, *right_issues]

    if (
        "left_quality_or_test_bit_not_good" in cond_set
        or "right_quality_or_test_bit_not_good" in cond_set
        or any("quality" in iss or "test_bit" in iss or "conflict" in iss for iss in all_issues)
    ):
        cats.append("quality_or_test_bit_violation")

    if (
        "left_not_sustained" in cond_set
        or "right_not_sustained" in cond_set
        or any("not_sustained" in iss or "insufficient_post_samples" in iss for iss in all_issues)
    ):
        cats.append("persistence_insufficient_violation")

    if any("no_prior_state_value_in_window" in iss or "pre_sample_gap_exceeded" in iss for iss in all_issues):
        cats.append("prior_state_baseline_missing_violation")

    if (
        "change_type_mismatch" in cond_set
        or "state_to_measurement_change_mismatch" in cond_set
        or "state_to_measurement_attribute_incompatible" in cond_set
        or "unsupported_anchor_type_pair" in cond_set
    ):
        cats.append("change_type_mismatch_violation")

    if any(
        c.startswith("magnitude_direction_mismatch")
        or c.startswith("magnitude_ratio_mismatch")
        or c.startswith("active_power_flow_sign_mismatch")
        for c in cond_set
    ):
        cats.append("magnitude_or_direction_conflict_violation")

    if (
        "endpoints_not_complementary" in cond_set
        or "transition_intervals_disjoint" in cond_set
        or "no_shared_measurement_quantity" in cond_set
    ):
        cats.append("non_complementary_or_disjoint_interval_violation")

    if not cats and cond_set:
        cats.append("other_evidence_constraint_violation")
    return cats


def run_ablation_without_behavioral_gate(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
) -> dict:
    edges = list(mirage_event_graph.get("edges") or [])
    nodes_by_id = {n["fact_id"]: n for n in (mirage_event_graph.get("nodes") or [])}

    originally_supported_behavioral = [
        e for e in edges
        if e.get("relation_type") == "corroborated_same_device_behavioral_transition"
        and e.get("verification_status") == "supported"
    ]
    sequential_rejected_by_gate = [
        e for e in edges
        if e.get("relation_type") == "same_entity_sequential_observation"
    ]

    # Also check command-to-device transitions rejected by the transaction consistency gate
    originally_supported_tx_inferences = [
        e for e in edges
        if e.get("relation_category") == "inference_hypothesis"
        and e.get("claim_level") == "supported_inference"
    ]
    rejected_tx_inferences = [
        e for e in edges
        if e.get("relation_category") == "inference_hypothesis"
        and e.get("claim_level") != "supported_inference"
    ]

    violation_breakdown = {
        "quality_or_test_bit_violation": 0,
        "persistence_insufficient_violation": 0,
        "prior_state_baseline_missing_violation": 0,
        "change_type_mismatch_violation": 0,
        "magnitude_or_direction_conflict_violation": 0,
        "non_complementary_or_disjoint_interval_violation": 0,
    }
    unsupported_promotions: list[dict] = []

    for e in sequential_rejected_by_gate:
        gate = e.get("consistency_gate") or {}
        failed_conds = list(gate.get("failed_conditions") or [])
        l_iss = list(gate.get("left_verification_issues") or [])
        r_iss = list(gate.get("right_verification_issues") or [])
        cats = _categorize_behavioral_failed_conditions(failed_conds, l_iss, r_iss)
        for c in cats:
            if c in violation_breakdown:
                violation_breakdown[c] += 1

        src_node = nodes_by_id.get(e["source_fact_id"]) or {}
        dst_node = nodes_by_id.get(e["target_fact_id"]) or {}
        sm = src_node.get("protocol_meta") or {}
        dm = dst_node.get("protocol_meta") or {}
        would_form_cross_rtu_bridge = bool(
            sm.get("rtu_ip") and dm.get("rtu_ip") and sm.get("rtu_ip") != dm.get("rtu_ip")
        )
        unsupported_promotions.append({
            "edge_id": e["edge_id"],
            "promotion_kind": "behavioral_same_device_edge",
            "source_fact_id": e["source_fact_id"],
            "target_fact_id": e["target_fact_id"],
            "source_entity": e["source_entity"],
            "target_entity": e["target_entity"],
            "from_rtu_ip": sm.get("rtu_ip"),
            "to_rtu_ip": dm.get("rtu_ip"),
            "would_form_cross_rtu_bridge_if_ungated": would_form_cross_rtu_bridge,
            "failed_conditions": failed_conds,
            "evidence_constraint_violations": cats,
            "evidence_ids": list(e.get("evidence_ids") or []),
        })

    for e in rejected_tx_inferences:
        src_node = nodes_by_id.get(e["source_fact_id"]) or {}
        tx_id = src_node.get("transaction_id")
        tx = next((t for t in (tx_result.get("transactions") or []) if t["transaction_id"] == tx_id), None)
        failed_conds = []
        if tx:
            if tx.get("measurement_transition"):
                failed_conds = list((tx["measurement_transition"].get("consistency_gate") or {}).get("failed_conditions") or [])
            elif tx.get("protocol_state_feedback"):
                failed_conds = list((tx["protocol_state_feedback"][0].get("consistency_gate") or {}).get("failed_conditions") or [])
        cats = []
        if any("quality" in c or "test_bit" in c for c in failed_conds):
            cats.append("quality_or_test_bit_violation")
            violation_breakdown["quality_or_test_bit_violation"] += 1
        if any("pre_value_missing" in c or "baseline" in c for c in failed_conds) or not failed_conds:
            cats.append("prior_state_baseline_missing_violation")
            violation_breakdown["prior_state_baseline_missing_violation"] += 1
        if any("direction" in c or "setpoint" in c or "shifted" in c for c in failed_conds):
            cats.append("magnitude_or_direction_conflict_violation")
            violation_breakdown["magnitude_or_direction_conflict_violation"] += 1
        unsupported_promotions.append({
            "edge_id": e["edge_id"],
            "promotion_kind": "command_to_state_or_measurement_edge",
            "source_fact_id": e["source_fact_id"],
            "target_fact_id": e["target_fact_id"],
            "source_entity": e["source_entity"],
            "target_entity": e["target_entity"],
            "would_form_cross_rtu_bridge_if_ungated": False,
            "failed_conditions": failed_conds,
            "evidence_constraint_violations": cats,
            "evidence_ids": list(e.get("evidence_ids") or []),
        })

    ungated_cross_rtu_bridges = sum(1 for p in unsupported_promotions if p["would_form_cross_rtu_bridge_if_ungated"])

    return {
        "ablation_id": "A1_without_behavioral_consistency_gate",
        "method_description": (
            "Retains identical Event Anchors and same-device candidate relations (`same_device_stem`, "
            "`separate_asdu`, `0 <= dt <= 15.0s`), but removes `evaluate_behavioral_relation_consistency` "
            "and `evaluate_command_effect_inference` gate restrictions."
        ),
        "observations_used": ["Identical to full MIRAGE-OT"],
        "information_removed": [
            "Behavioral Consistency Gate (`evaluate_behavioral_relation_consistency`)",
            "Transaction Command-Effect Consistency Gate (`evaluate_command_effect_inference`)",
        ],
        "allowed_claims": [
            "Promotes any same-device separate-ASDU pair within 15s and any post-command feedback to supported",
        ],
        "originally_supported_behavioral_edge_count": len(originally_supported_behavioral),
        "originally_supported_tx_inference_edge_count": len(originally_supported_tx_inferences),
        "originally_supported_total_count": len(originally_supported_behavioral) + len(originally_supported_tx_inferences),
        "unsupported_promotion_behavioral_count": len(sequential_rejected_by_gate),
        "unsupported_promotion_tx_inference_count": len(rejected_tx_inferences),
        "unsupported_promotion_total_count": len(unsupported_promotions),
        "ungated_total_supported_count": (
            len(originally_supported_behavioral)
            + len(originally_supported_tx_inferences)
            + len(unsupported_promotions)
        ),
        "ungated_spurious_cross_rtu_bridge_promotion_count": ungated_cross_rtu_bridges,
        "evidence_constraint_violation_breakdown": violation_breakdown,
        "sample_unsupported_promotions": unsupported_promotions[:30],
    }
