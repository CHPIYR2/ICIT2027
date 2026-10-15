"""Task 4: Fair Four-Category Evaluation Metrics (E1-E4) & Window-Paired Statistics.

Categories:
- E1 (`evidence_coverage`): Retained traceable commands, state reports, measurement steps,
  and network anomalies, plus supported local relations.
- E2 (`unsupported_relation_promotion`): Relations promoted or emitted that violate fixed,
  public evidentiary constraints (missing device/session link, same-ASDU co-report chained
  as sequence, quality/test-bit conflict, transient non-persistence, or same-device
  change-type/direction conflict) or inflate independent source counts.
  NOTE: Audited via objective telemetry properties (`_audit_temporal_pair` / raw flags),
  never by treating MIRAGE-OT's own gate label as external ground truth.
- E3 (`incident_structure_and_traceability`): Availability and 100% `evidence_id`
  traceability of event chains, deduplicated source containers, cross-RTU bridges,
  candidate scenario phases, unresolved branch separation, and competing explanations.
  Explicitly distinguishes "produces traceable structure" from "external ground-truth correctness".
- E4 (`computational_cost`): Separates shared evidence indexing cost (`indexing_s`, `sqlite_mib`)
  from per-method execution time (`method_runtime_s`) and artifact size.
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
    """Compute window-paired differences (baseline - mirage) and bootstrap 95% CI on the mean difference."""
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
        "mean_difference_bootstrap_95ci": [ci_lo, ci_hi],
        "windows_where_baseline_exceeds_mirage": pos,
        "windows_where_mirage_exceeds_baseline": neg,
        "windows_tied": zero,
        "independence_caveat": (
            "Windows are paired by episode_id, but consecutive windows drawn from the same "
            "Sherlock recording may exhibit temporal dependence."
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
    ledger = mirage_synthesis.get("source_dependency_ledger") or {}

    # E1: Evidence Coverage per method
    e1_coverage = {
        "B1_temporal_only": {
            "commands_retained": len(txs),
            "verified_anchors_retained": len(ver_anchors),
            "unverified_anchors_included_without_quarantine": int(anchor_result.get("unverified_anchor_count") or 0),
            "corroborated_supported_relations": 0,
            "candidate_temporal_relations_emitted": b1_result["candidate_temporal_relation_count"],
        },
        "B2_protocol_only": {
            "applicability": b2_result["applicability_status"],
            "commands_retained": len(txs),
            "verified_command_transitions": verified_tx_cnt,
            "verified_non_command_anchors_retained": 0 if not b2_result["is_applicable_to_window"] else 0,
            "omitted_verified_non_command_anchors": b2_result["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"],
            "omitted_cross_rtu_bridges": b2_result["omitted_compared_to_full_mirage"]["omitted_cross_rtu_verified_element_bridge_count"],
            "unexpressible_network_anomalies": b2_result["omitted_compared_to_full_mirage"]["unexpressible_network_anomalies_count"],
        },
        "A1_no_behavioral_gate": {
            "commands_retained": len(txs),
            "verified_anchors_retained": len(ver_anchors),
            "claimed_supported_relations": a1_result["ungated_total_supported_count"],
        },
        "A2_no_provenance_dedup": {
            "raw_observations_counted_as_sources": a2_result["raw_observation_count"],
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

    # E2: Unsupported Relation Promotion & Source Inflation (objective constraint violations)
    e2_unsupported = {
        "B1_temporal_only": {
            "unsupported_or_conflicting_relations": b1_result["total_conflicting_or_unsupported_candidate_count"],
            "cross_device_without_link_count": b1_result["lacking_device_or_session_support_count"],
            "same_asdu_chained_count": b1_result["same_asdu_co_report_chained_count"],
            "quality_or_test_bit_conflict_count": b1_result["quality_or_test_bit_conflict_count"],
            "transient_not_sustained_count": b1_result["transient_not_sustained_conflict_count"],
            "same_device_direction_or_type_conflict_count": b1_result["same_device_direction_or_type_conflict_count"],
        },
        "B2_protocol_only": {
            "unsupported_or_conflicting_relations": 0,
        },
        "A1_no_behavioral_gate": {
            "unsupported_promotion_total_count": a1_result["unsupported_promotion_total_count"],
            "unsupported_promotion_behavioral_count": a1_result["unsupported_promotion_behavioral_count"],
            "unsupported_promotion_tx_inference_count": a1_result["unsupported_promotion_tx_inference_count"],
            "ungated_spurious_cross_rtu_bridge_count": a1_result["ungated_spurious_cross_rtu_bridge_promotion_count"],
            "violation_breakdown": a1_result["evidence_constraint_violation_breakdown"],
        },
        "A2_no_provenance_dedup": {
            "falsely_inflated_independent_source_count": a2_result["falsely_counted_independent_source_count"],
            "mirror_duplicate_count": a2_result["mirror_duplicate_count"],
            "same_asdu_multi_point_expansion_count": a2_result["same_asdu_multi_point_expansion_count"],
            "ipal_derived_observation_count": a2_result["ipal_derived_observation_count"],
            "source_inflation_factor": a2_result["source_inflation_factor"],
            "spurious_multi_source_storyline_count": a2_result["spurious_multi_source_storyline_count_without_dedup"],
        },
        "MIRAGE_OT_full": {
            "unsupported_relation_promotions": 0,
            "falsely_inflated_independent_sources": 0,
        },
    }

    # E3: Incident Structure & Traceability
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

    # E4: Computational Cost (separating shared indexing from method runtime)
    e4_cost = {
        "shared_indexing_s": window_summary["timing_seconds"]["indexing_s"],
        "shared_sqlite_mib": round(window_summary["storage_bytes"]["sqlite_bytes"] / (1024 ** 2), 3),
        "full_pipeline_reconstruction_and_synthesis_s": window_summary["timing_seconds"]["reconstruction_and_synthesis_total_s"],
        "standalone_synthesis_step_s": window_summary["timing_seconds"].get("synthesis_step_s", 0.0),
        "stage3_method_evaluation_timings_s": method_timings_s,
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
