"""Task 4: Fair Four-Category Evaluation Metrics (E1-E4) & Window-Paired Statistics (Audit Hardened).

Categories:
- E1 (`evidence_coverage`): Retained traceable commands, state reports, measurement steps,
  and network anomalies, plus supported local relations.
- E2 (`unsupported_relation_promotion`):
  - For B1 (`Temporal-Only`): Separates `unsubstantiated_temporal_candidates` (temporally
    proximate without direct link evidence; NOT proven false) from
    `explicit_evidence_constraint_conflicts` (direct quality, test-bit, persistence,
    direction, change-type, or same-ASDU ordering conflicts).
  - For A1 (`Without Behavioral Gate`): Counterfactual `unsupported_promotion` counts broken
    down by explicit `evidence_constraint_violation` categories (plus sensitivity analysis
    excluding the max outlier window `ev_52f5eee28f8b95e702fd`).
  - For A2 (`Without Provenance Deduplication`): Separates `true_cross_vantage_mirror_duplicate_count`,
    `same_asdu_different_ioa_point_count`, `distinct_messages_in_same_tcp_session_count`,
    `distinct_time_network_events_in_anchor_count`, `ipal_derived_observation_count`, and
    `unknown_provenance_relation_count`.
- E3 (`incident_structure_and_traceability`): Distinguishes four levels of traceability:
  (1) `1_evidence_citation_presence`, (2) `2_evidence_id_resolution`,
  (3) `3_evidence_to_fact_anchor_consistency`, and (4) `4_full_lineage_consistency`
  (preserving `ev_5dd0102bf58bf2ce9487` as `False` on levels 3 and 4).
- E4 (`computational_cost`): Separates shared indexing cost, full pipeline reconstruction/synthesis
  runtime, and Stage 3 cached artifact evaluation runtime.
"""
from __future__ import annotations
import math
import random
import statistics


def dist_stats(values: list[float | int]) -> dict:
    if not values:
        return {"total": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0}
    s = sorted(float(v) for v in values)
    n = len(s)
    p95_idx = min(n - 1, max(0, math.ceil(0.95 * n) - 1))
    is_flt = any(isinstance(v, float) for v in values)
    return {
        "total": round(sum(values), 4) if is_flt else int(sum(values)),
        "mean": round(sum(s) / n, 3),
        "median": round(statistics.median(s), 3),
        "p95": round(s[p95_idx], 3),
        "max": round(s[-1], 3) if is_flt else int(s[-1]),
    }


def paired_window_difference_stats(
    baseline_vals: list[float | int],
    mirage_vals: list[float | int],
    *,
    seed: int = 1,
    n_boot: int = 1000,
) -> dict:
    """Compute window-paired differences and descriptive bootstrap 95% intervals."""
    if len(baseline_vals) != len(mirage_vals) or not baseline_vals:
        return {}
    diffs = [float(b) - float(m) for b, m in zip(baseline_vals, mirage_vals)]
    n = len(diffs)
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    zero = n - pos - neg

    rng = random.Random(seed)
    boot_means = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    ci_lo = round(boot_means[int(0.025 * n_boot)], 3)
    ci_hi = round(boot_means[int(0.975 * n_boot)], 3)

    return {
        "n_paired_windows": n,
        "difference_distribution": dist_stats(diffs),
        "descriptive_bootstrap_95ci": [ci_lo, ci_hi],
        "windows_where_baseline_exceeds_mirage": pos,
        "windows_where_mirage_exceeds_baseline": neg,
        "windows_tied": zero,
        "independence_caveat": (
            "Descriptive non-parametric bootstrap interval across the evaluated windows. "
            "Because multiple windows are sliced from the same continuous Sherlock recording, "
            "windows are not strictly i.i.d.; this interval is a descriptive summary of "
            "sample variability rather than a formal i.i.d. hypothesis test."
        ),
    }


def evaluate_window_methods(
    *,
    episode_id: str,
    scenario: str,
    window_summary: dict,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
    b1_result: dict,
    b2_result: dict,
    a1_result: dict,
    a2_result: dict,
    a3_result: dict,
    method_timings_s: dict[str, float],
) -> dict:
    txs = list(tx_result.get("transactions") or [])
    verified_tx_cnt = int(tx_result.get("verified_state_or_measurement_transition_count") or 0)
    anchors = list(anchor_result.get("anchors") or [])
    ver_anchors = [a for a in anchors if a.get("verification_status") == "verified_observation"]
    part_counts = (mirage_synthesis.get("local_storyline_partition") or {}).get("counts") or {}

    e1_coverage = {
        "B1_temporal_only": {
            "commands_retained": len(txs),
            "verified_anchors_retained": len(ver_anchors),
            "unverified_anchors_included_without_quarantine": int(anchor_result.get("unverified_anchor_count") or 0),
            "corroborated_same_device_candidates": b1_result["corroborated_same_device_candidate_count"],
            "candidate_temporal_relations_emitted": b1_result["candidate_temporal_relation_count"],
        },
        "B2_protocol_only": {
            "applicability": b2_result["applicability_status"],
            "commands_retained": len(txs),
            "verified_command_transitions": verified_tx_cnt,
            "verified_non_command_anchors_retained": 0,
            "omitted_verified_non_command_anchors": b2_result["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"],
            "omitted_cross_rtu_bridges": b2_result["omitted_compared_to_full_mirage"]["omitted_cross_rtu_verified_element_bridge_count"],
            "unexpressible_network_anomalies": b2_result["omitted_compared_to_full_mirage"]["unexpressible_network_anomalies_count"],
        },
        "A1_no_behavioral_gate": {
            "commands_retained": len(txs),
            "verified_anchors_retained": len(ver_anchors),
            "counterfactual_supported_relations": a1_result["ungated_total_supported_count"],
        },
        "A2_no_provenance_dedup": {
            "raw_observations_counted": a2_result["raw_observation_count"],
            "true_distinct_source_containers": a2_result["distinct_source_container_count"],
        },
        "A3_no_incident_synthesis": {
            "local_storylines_retained": a3_result["without_synthesis"]["local_storyline_count"],
            "verified_local_storylines": a3_result["without_synthesis"]["verified_local_storyline_count"],
            "cross_rtu_bridges_formed": 0,
        },
        "MIRAGE_OT_full": {
            "commands_retained": len(txs),
            "verified_command_transitions": verified_tx_cnt,
            "verified_anchors_retained": len(ver_anchors),
            "quarantined_unverified_anchors_preserved": int(anchor_result.get("unverified_anchor_count") or 0),
            "supported_multi_node_storylines": int(part_counts.get("supported_multi_node_storyline_count") or 0),
            "verified_single_anchor_storylines": int(part_counts.get("verified_single_anchor_storyline_count") or 0),
            "cross_rtu_verified_element_bridges": len(mirage_synthesis.get("verified_element_bridges") or []),
        },
    }

    e2_unsupported = {
        "B1_temporal_only": {
            "unsubstantiated_temporal_candidate_count": b1_result["unsubstantiated_temporal_candidate_count"],
            "explicit_evidence_constraint_conflict_count": b1_result["explicit_evidence_constraint_conflict_count"],
            "explicit_conflict_breakdown": b1_result["explicit_conflict_breakdown"],
            "topology_breakdown": b1_result["topology_breakdown"],
        },
        "B2_protocol_only": {
            "explicit_evidence_constraint_conflict_count": 0,
        },
        "A1_no_behavioral_gate": {
            "unsupported_promotion_total_count": a1_result["unsupported_promotion_total_count"],
            "unsupported_promotion_behavioral_count": a1_result["unsupported_promotion_behavioral_count"],
            "unsupported_promotion_tx_inference_count": a1_result["unsupported_promotion_tx_inference_count"],
            "ungated_spurious_cross_rtu_bridge_count": a1_result["ungated_spurious_cross_rtu_bridge_promotion_count"],
            "violation_breakdown": a1_result["evidence_constraint_violation_breakdown"],
        },
        "A2_no_provenance_dedup": {
            "true_cross_vantage_mirror_duplicate_count": a2_result["true_cross_vantage_mirror_duplicate_count"],
            "same_asdu_different_ioa_point_count": a2_result["same_asdu_different_ioa_point_count"],
            "distinct_messages_in_same_tcp_session_count": a2_result["distinct_messages_in_same_tcp_session_count"],
            "distinct_time_network_events_in_anchor_count": a2_result["distinct_time_network_events_in_anchor_count"],
            "ipal_derived_observation_count": a2_result["ipal_derived_observation_count"],
            "unknown_provenance_relation_count": a2_result["unknown_provenance_relation_count"],
            "true_duplicate_or_derived_source_inflation_count": a2_result["true_duplicate_or_derived_source_inflation_count"],
            "multi_event_anchor_aggregation_count": a2_result["multi_event_anchor_aggregation_count"],
        },
        "MIRAGE_OT_full": {
            "unsupported_relation_promotions": 0,
            "true_duplicate_or_derived_source_inflation": 0,
        },
    }

    e3_structure = {
        "B1_temporal_only": {
            "has_source_deduplicated_containers": False,
            "has_cross_rtu_bridges": False,
            "has_candidate_scenario_phases": False,
            "separates_supported_from_unresolved": False,
            "has_competing_explanations_with_missing_evidence": False,
        },
        "B2_protocol_only": {
            "has_source_deduplicated_containers": True,
            "has_cross_rtu_bridges": False,
            "has_candidate_scenario_phases": False,
            "separates_supported_from_unresolved": True,
            "has_competing_explanations_with_missing_evidence": False,
        },
        "A3_no_incident_synthesis": a3_result["without_synthesis"],
        "MIRAGE_OT_full": a3_result["with_full_synthesis"],
    }

    e4_cost = {
        "shared_indexing_s": window_summary["timing_seconds"]["indexing_s"],
        "shared_sqlite_mib": round(window_summary["storage_bytes"]["sqlite_bytes"] / (1024 ** 2), 3),
        "full_pipeline_reconstruction_and_synthesis_s": window_summary["timing_seconds"]["reconstruction_and_synthesis_total_s"],
        "standalone_synthesis_step_s": window_summary["timing_seconds"].get("synthesis_step_s", 0.0),
        "stage3_cached_artifact_evaluation_timings_s": method_timings_s,
        "full_artifacts_mib": round(window_summary["storage_bytes"]["reconstruction_artifacts_bytes"] / (1024 ** 2), 3),
        "peak_rss_mib": window_summary.get("peak_rss_mib"),
    }

    return {
        "episode_id": episode_id,
        "scenario": scenario,
        "observation_profile": window_summary["observation_profile"],
        "E1_evidence_coverage": e1_coverage,
        "E2_unsupported_relation_promotion": e2_unsupported,
        "E3_incident_structure_and_traceability": e3_structure,
        "E4_computational_cost": e4_cost,
    }
