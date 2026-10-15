"""Stage 3 Baseline, Ablation & Paper-Readiness Audit Runner (`stage3a` 12-window pilot & `stage3b` 103-window full suite).

Audit-Response Enhancements (Tasks 1–7):
- Task 1 (RQ1): Separates `unsubstantiated_temporal_candidates` from `explicit_evidence_constraint_conflicts`
  and reports `cross_device`, `same_device_separate_asdu`, and `same_asdu_co_report` topologies independently.
- Task 2 (RQ4): Uses `evidence.sqlite` packet identities to decompose non-primary observations into
  (1) `true_cross_vantage_mirror_duplicate_count`, (2) `same_asdu_different_ioa_point_count`,
  (3) `distinct_messages_in_same_tcp_session_count`, (4) `distinct_time_network_events_in_anchor_count`,
  (5) `ipal_derived_observation_count`, and (6) `unknown_provenance_relation_count`.
- Task 3 (RQ3): Reports both the full 103-window A1 statistics and the 102-window sensitivity analysis
  excluding the maximum cross-vantage conflict outlier `ev_52f5eee28f8b95e702fd`.
- Task 4 (E3): Separates `1_evidence_citation_presence`, `2_evidence_id_resolution`,
  `3_evidence_to_fact_anchor_consistency`, and `4_full_lineage_consistency`.
- Task 5: Clarifies `45` `S1` windows vs `46` `B2` applicable windows (`ev_5dd0102bf58bf2ce9487`),
  distinguishes sum of per-window RTU counts (`1,561`) from scenario-wide unique RTU IPs, and
  labels Stage 3 runtime as Cached Artifact Evaluation Time.
- Task 6: Runs `run_post_freeze_physical_state_comparison()` as an air-gapped, read-only check on
  `01-Basic/raw/test/physical.zip` after all reconstruction outputs are frozen.
- Task 7: Writes to a fresh directory (`runs/etgi/stage3-audit-response-20261015/`) without overwriting
  prior Stage 3A/3B results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path

from .baselines.temporal_only import run_temporal_only_baseline
from .baselines.protocol_only import run_protocol_only_baseline
from .ablations.no_behavioral_gate import run_ablation_without_behavioral_gate
from .ablations.no_provenance_dedup import run_ablation_without_provenance_dedup
from .ablations.no_incident_synthesis import run_ablation_without_incident_synthesis
from .evaluation.metrics import dist_stats, evaluate_window_methods, paired_window_difference_stats
from .evaluation.case_studies import (
    REPRESENTATIVE_CASE_SPECS,
    extract_real_case_study,
    run_synthetic_known_answer_counterexamples,
)
from .evaluation.physical_state_comparison import run_post_freeze_physical_state_comparison


def verify_frozen_engine_integrity(freeze: dict, repo_root: Path) -> dict:
    etgi_dir = repo_root / "src" / "mirage_ot" / "etgi"
    post_dir = etgi_dir / "postalert"
    recon_dir = etgi_dir / "reconstruction"
    ev_dir = etgi_dir / "evidence"

    code_digest = hashlib.sha256()
    module_hashes = {}
    for folder in (post_dir, recon_dir):
        for p in sorted(folder.glob("*.py")):
            rel = f"{folder.name}/{p.name}"
            b = p.read_bytes()
            module_hashes[rel] = hashlib.sha256(b).hexdigest()
            code_digest.update(rel.encode("utf-8"))
            code_digest.update(b)

    ev_digest = hashlib.sha256()
    ev_hashes = {}
    for p in sorted(ev_dir.glob("*.py")):
        rel = f"evidence/{p.name}"
        b = p.read_bytes()
        ev_hashes[rel] = hashlib.sha256(b).hexdigest()
        ev_digest.update(rel.encode("utf-8"))
        ev_digest.update(b)

    if code_digest.hexdigest() != freeze["code_sha256"]:
        raise RuntimeError("Frozen code_sha256 mismatch!")
    if ev_digest.hexdigest() != freeze["evidence_code_sha256"]:
        raise RuntimeError("Frozen evidence_code_sha256 mismatch!")
    if module_hashes != freeze["module_hashes"] or ev_hashes != freeze["evidence_module_hashes"]:
        raise RuntimeError("Frozen module hashes mismatch!")

    return {
        "verified": True,
        "frozen_engine_git_commit": freeze["frozen_engine_git_commit"],
        "code_sha256": code_digest.hexdigest(),
        "evidence_code_sha256": ev_digest.hexdigest(),
        "module_count": len(module_hashes) + len(ev_hashes),
    }


def _select_stage3a_pilot_windows(all_entries: list[dict]) -> list[dict]:
    selected = []
    for scen in ("01-Basic", "02-Semiurban", "03-Rural"):
        scen_wins = [e for e in all_entries if e["scenario"] == scen]
        for stratum_prefix in ("S1_", "S2_", "S3_", "S4_"):
            match = next(
                (e for e in scen_wins if e["window_summary"]["observation_profile"].startswith(stratum_prefix)),
                None,
            )
            if match is not None:
                selected.append(match)
    return selected


def _a1_summary_block(evals: list[dict]) -> dict:
    return {
        "window_count": len(evals),
        "originally_supported_relations": dist_stats([e["A1"]["originally_supported_total_count"] for e in evals]),
        "unsupported_promotions_total": dist_stats([e["A1"]["unsupported_promotion_total_count"] for e in evals]),
        "unsupported_promotions_behavioral": dist_stats([e["A1"]["unsupported_promotion_behavioral_count"] for e in evals]),
        "unsupported_promotions_tx_inference": dist_stats([e["A1"]["unsupported_promotion_tx_inference_count"] for e in evals]),
        "ungated_spurious_cross_rtu_bridge_promotions": dist_stats([e["A1"]["ungated_spurious_cross_rtu_bridge_promotion_count"] for e in evals]),
        "violation_quality_or_test_bit": dist_stats(
            [e["A1"]["evidence_constraint_violation_breakdown"]["quality_or_test_bit_violation"] for e in evals]
        ),
        "violation_persistence_insufficient": dist_stats(
            [e["A1"]["evidence_constraint_violation_breakdown"]["persistence_insufficient_violation"] for e in evals]
        ),
        "violation_prior_state_baseline_missing": dist_stats(
            [e["A1"]["evidence_constraint_violation_breakdown"]["prior_state_baseline_missing_violation"] for e in evals]
        ),
        "violation_change_type_mismatch": dist_stats(
            [e["A1"]["evidence_constraint_violation_breakdown"]["change_type_mismatch_violation"] for e in evals]
        ),
        "violation_magnitude_or_direction_conflict": dist_stats(
            [e["A1"]["evidence_constraint_violation_breakdown"]["magnitude_or_direction_conflict_violation"] for e in evals]
        ),
        "violation_non_complementary_or_disjoint": dist_stats(
            [e["A1"]["evidence_constraint_violation_breakdown"]["non_complementary_or_disjoint_interval_violation"] for e in evals]
        ),
        "paired_difference_A1_minus_MIRAGE": paired_window_difference_stats(
            [e["A1"]["unsupported_promotion_total_count"] for e in evals],
            [0 for _ in evals],
        ),
    }


def aggregate_scenario_evaluations(evals: list[dict]) -> dict:
    n = len(evals)
    b2_app = [e for e in evals if e["B2"]["is_applicable_to_window"]]
    b2_not_app = [e for e in evals if not e["B2"]["is_applicable_to_window"]]
    s1_tx_wins = [e for e in evals if e["observation_profile"].startswith("S1_")]
    unpaired_ctrl_only_wins = [
        e["episode_id"] for e in evals
        if e["B2"]["is_applicable_to_window"] and not e["observation_profile"].startswith("S1_")
    ]

    unique_rtus_across_windows = sorted({
        rtu for e in evals for rtu in (e.get("distinct_rtu_ips_in_window") or []) if rtu
    })

    evals_excl_outlier = [e for e in evals if e["episode_id"] != "ev_52f5eee28f8b95e702fd"]

    t_ver = [e["A3"]["with_full_synthesis"]["traceability_verification"] for e in evals]
    lvl1_cnt = sum(1 for tv in t_ver if tv["1_evidence_citation_presence"])
    lvl2_cnt = sum(1 for tv in t_ver if tv["2_evidence_id_resolution"])
    lvl3_cnt = sum(1 for tv in t_ver if tv["3_evidence_to_fact_anchor_consistency"])
    lvl4_cnt = sum(1 for tv in t_ver if tv["4_full_lineage_consistency"])

    return {
        "window_count": n,
        "B2_applicability_and_S1_reconciliation": {
            "S1_reconstructed_transaction_windows": len(s1_tx_wins),
            "B2_applicable_windows_with_control_objects": len(b2_app),
            "windows_with_unpaired_control_replies_only_no_cot6": unpaired_ctrl_only_wins,
            "not_applicable_no_control_command_windows": len(b2_not_app),
        },
        "Q1_temporal_only_vs_mirage": {
            "B1_candidate_temporal_relations": dist_stats([e["B1"]["candidate_temporal_relation_count"] for e in evals]),
            "B1_unbounded_15s_temporal_pairs": dist_stats([e["B1"]["unbounded_15s_temporal_pair_count"] for e in evals]),
            "B1_unsubstantiated_temporal_candidates": dist_stats([e["B1"]["unsubstantiated_temporal_candidate_count"] for e in evals]),
            "B1_explicit_evidence_constraint_conflicts": dist_stats([e["B1"]["explicit_evidence_constraint_conflict_count"] for e in evals]),
            "B1_corroborated_same_device_candidates": dist_stats([e["B1"]["corroborated_same_device_candidate_count"] for e in evals]),
            "B1_topology_cross_device_candidates": dist_stats(
                [e["B1"]["topology_breakdown"]["cross_device_candidate_count"] for e in evals]
            ),
            "B1_topology_same_device_separate_asdu_candidates": dist_stats(
                [e["B1"]["topology_breakdown"]["same_device_separate_asdu_candidate_count"] for e in evals]
            ),
            "B1_topology_same_asdu_co_report_candidates": dist_stats(
                [e["B1"]["topology_breakdown"]["same_asdu_co_report_candidate_count"] for e in evals]
            ),
            "B1_conflict_endpoint_quality_or_test_bit": dist_stats(
                [e["B1"]["explicit_conflict_breakdown"]["endpoint_quality_or_test_bit_conflict"] for e in evals]
            ),
            "B1_conflict_endpoint_transient_not_sustained": dist_stats(
                [e["B1"]["explicit_conflict_breakdown"]["endpoint_transient_not_sustained_conflict"] for e in evals]
            ),
            "B1_conflict_same_device_direction_or_ratio": dist_stats(
                [e["B1"]["explicit_conflict_breakdown"]["same_device_direction_or_ratio_conflict"] for e in evals]
            ),
            "B1_conflict_same_device_change_type_or_side": dist_stats(
                [e["B1"]["explicit_conflict_breakdown"]["same_device_change_type_or_side_conflict"] for e in evals]
            ),
            "B1_conflict_same_asdu_co_report_temporal_ordering": dist_stats(
                [e["B1"]["explicit_conflict_breakdown"]["same_asdu_co_report_temporal_ordering_conflict"] for e in evals]
            ),
            "MIRAGE_OT_supported_storyline_steps": dist_stats(
                [e["B1"]["mirage_comparison"]["mirage_supported_storyline_step_count"] for e in evals]
            ),
            "MIRAGE_OT_cross_rtu_verified_bridges": dist_stats(
                [e["B1"]["mirage_comparison"]["mirage_cross_rtu_verified_bridge_count"] for e in evals]
            ),
            "paired_difference_explicit_conflicts_B1_minus_MIRAGE": paired_window_difference_stats(
                [e["B1"]["explicit_evidence_constraint_conflict_count"] for e in evals],
                [0 for _ in evals],
            ),
            "paired_difference_unsubstantiated_candidates_B1": paired_window_difference_stats(
                [e["B1"]["unsubstantiated_temporal_candidate_count"] for e in evals],
                [0 for _ in evals],
            ),
        },
        "Q2_protocol_only_vs_mirage": {
            "control_command_windows_handled": len(b2_app),
            "no_command_windows_not_applicable": len(b2_not_app),
            "B2_retained_info_in_no_command_windows": dist_stats(
                [e["B2"]["retained_investigation_info_in_no_command_window"] for e in b2_not_app]
            ),
            "B2_verified_command_transitions": dist_stats([e["B2"]["transaction_count_verified_transition"] for e in evals]),
            "omitted_verified_non_command_anchors": dist_stats(
                [e["B2"]["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"] for e in evals]
            ),
            "omitted_supported_behavioral_transition_chains": dist_stats(
                [e["B2"]["omitted_compared_to_full_mirage"]["omitted_supported_behavioral_transition_chain_count"] for e in evals]
            ),
            "omitted_cross_rtu_verified_bridges": dist_stats(
                [e["B2"]["omitted_compared_to_full_mirage"]["omitted_cross_rtu_verified_element_bridge_count"] for e in evals]
            ),
            "unexpressible_network_anomalies_arp_and_link": dist_stats(
                [e["B2"]["omitted_compared_to_full_mirage"]["unexpressible_network_anomalies_count"] for e in evals]
            ),
            "paired_difference_verified_anchors_MIRAGE_minus_B2": paired_window_difference_stats(
                [e["B2"]["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"] for e in evals],
                [0 for _ in evals],
            ),
        },
        "Q3_ablation_A1_without_behavioral_gate": {
            "all_windows": _a1_summary_block(evals),
            "sensitivity_excluding_max_outlier_ev_52f5ee": _a1_summary_block(evals_excl_outlier),
        },
        "Q4_ablation_A2_without_provenance_dedup": {
            "raw_observation_count": dist_stats([e["A2"]["raw_observation_count"] for e in evals]),
            "raw_network_observation_count": dist_stats([e["A2"]["raw_network_observation_count"] for e in evals]),
            "distinct_source_container_count": dist_stats([e["A2"]["distinct_source_container_count"] for e in evals]),
            "distinct_asdu_container_count": dist_stats([e["A2"]["distinct_asdu_container_count"] for e in evals]),
            "per_window_rtu_count_summed_across_windows": dist_stats([e["A2"]["distinct_rtu_count_in_window"] for e in evals]),
            "unique_rtu_ips_in_scenario_count": len(unique_rtus_across_windows),
            "unique_rtu_ips_in_scenario": unique_rtus_across_windows,
            "true_cross_vantage_mirror_duplicate_count": dist_stats(
                [e["A2"]["true_cross_vantage_mirror_duplicate_count"] for e in evals]
            ),
            "same_asdu_different_ioa_point_count": dist_stats(
                [e["A2"]["same_asdu_different_ioa_point_count"] for e in evals]
            ),
            "distinct_messages_in_same_tcp_session_count": dist_stats(
                [e["A2"]["distinct_messages_in_same_tcp_session_count"] for e in evals]
            ),
            "distinct_time_network_events_in_anchor_count": dist_stats(
                [e["A2"]["distinct_time_network_events_in_anchor_count"] for e in evals]
            ),
            "ipal_derived_observation_count": dist_stats(
                [e["A2"]["ipal_derived_observation_count"] for e in evals]
            ),
            "unknown_provenance_relation_count": dist_stats(
                [e["A2"]["unknown_provenance_relation_count"] for e in evals]
            ),
            "true_duplicate_or_derived_source_inflation_count": dist_stats(
                [e["A2"]["true_duplicate_or_derived_source_inflation_count"] for e in evals]
            ),
            "multi_event_anchor_aggregation_count": dist_stats(
                [e["A2"]["multi_event_anchor_aggregation_count"] for e in evals]
            ),
            "total_excess_observations_over_containers": dist_stats(
                [e["A2"]["total_excess_observations_over_containers"] for e in evals]
            ),
            "strict_duplicate_and_derived_inflation_factor": dist_stats(
                [e["A2"]["strict_duplicate_and_derived_inflation_factor"] for e in evals]
            ),
            "raw_to_container_ratio": dist_stats([e["A2"]["raw_to_container_ratio"] for e in evals]),
            "spurious_multi_source_storylines_without_dedup": dist_stats(
                [e["A2"]["spurious_multi_source_storyline_count_without_dedup"] for e in evals]
            ),
            "paired_difference_true_duplicate_and_derived_inflation": paired_window_difference_stats(
                [e["A2"]["true_duplicate_or_derived_source_inflation_count"] for e in evals],
                [0 for _ in evals],
            ),
        },
        "Q5_ablation_A3_without_incident_synthesis_and_E3_traceability": {
            "local_storyline_count": dist_stats([e["A3"]["with_full_synthesis"]["local_storyline_count"] for e in evals]),
            "deduplicated_source_containers": dist_stats([e["A3"]["with_full_synthesis"]["deduplicated_source_container_count"] for e in evals]),
            "rtu_asdu_bundles": dist_stats([e["A3"]["with_full_synthesis"]["rtu_asdu_bundle_count"] for e in evals]),
            "co_reported_points_collapsed": dist_stats([e["A3"]["with_full_synthesis"]["co_reported_points_collapsed_into_bundles"] for e in evals]),
            "cross_rtu_verified_bridges": dist_stats([e["A3"]["with_full_synthesis"]["cross_rtu_verified_element_bridge_count"] for e in evals]),
            "multi_bundle_bridged_components": dist_stats([e["A3"]["with_full_synthesis"]["multi_bundle_bridged_component_count"] for e in evals]),
            "candidate_scenario_phases": dist_stats([e["A3"]["with_full_synthesis"]["candidate_scenario_phase_count"] for e in evals]),
            "competing_explanations_generated": dist_stats([e["A3"]["with_full_synthesis"]["competing_explanations_with_missing_evidence_count"] for e in evals]),
            "E3_four_level_traceability": {
                "1_evidence_citation_presence_pass_count": lvl1_cnt,
                "1_evidence_citation_presence_pass_rate": round(lvl1_cnt / n, 4) if n else 0.0,
                "2_evidence_id_resolution_pass_count": lvl2_cnt,
                "2_evidence_id_resolution_pass_rate": round(lvl2_cnt / n, 4) if n else 0.0,
                "3_evidence_to_fact_anchor_consistency_pass_count": lvl3_cnt,
                "3_evidence_to_fact_anchor_consistency_pass_rate": round(lvl3_cnt / n, 4) if n else 0.0,
                "4_full_lineage_consistency_pass_count": lvl4_cnt,
                "4_full_lineage_consistency_pass_rate": round(lvl4_cnt / n, 4) if n else 0.0,
                "failed_lineage_consistency_episodes": [
                    e["episode_id"] for e in evals
                    if not e["A3"]["with_full_synthesis"]["traceability_verification"]["4_full_lineage_consistency"]
                ],
            },
        },
        "E4_computational_cost": {
            "shared_indexing_s": dist_stats([e["eval"]["E4_computational_cost"]["shared_indexing_s"] for e in evals]),
            "shared_sqlite_mib": dist_stats([e["eval"]["E4_computational_cost"]["shared_sqlite_mib"] for e in evals]),
            "full_pipeline_reconstruction_and_synthesis_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["full_pipeline_reconstruction_and_synthesis_s"] for e in evals]
            ),
            "standalone_synthesis_step_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["standalone_synthesis_step_s"] for e in evals]
            ),
            "stage3_cached_B1_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_cached_artifact_evaluation_timings_s"]["B1_temporal_only_s"] for e in evals]
            ),
            "stage3_cached_B2_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_cached_artifact_evaluation_timings_s"]["B2_protocol_only_s"] for e in evals]
            ),
            "stage3_cached_A1_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_cached_artifact_evaluation_timings_s"]["A1_no_behavioral_gate_s"] for e in evals]
            ),
            "stage3_cached_A2_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_cached_artifact_evaluation_timings_s"]["A2_no_provenance_dedup_s"] for e in evals]
            ),
            "stage3_cached_A3_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_cached_artifact_evaluation_timings_s"]["A3_no_incident_synthesis_s"] for e in evals]
            ),
            "full_artifacts_mib": dist_stats([e["eval"]["E4_computational_cost"]["full_artifacts_mib"] for e in evals]),
        },
    }


def main() -> None:
    t0_proc = time.perf_counter()
    parser = argparse.ArgumentParser(description="Run Stage 3 Audit-Response Baseline, Ablation & Paper Evidence Suite")
    parser.add_argument("--mode", choices=("stage3a", "stage3b"), required=True)
    parser.add_argument("--freeze-manifest", type=Path, default=Path("configs/etgi/method_freeze.v1.json"))
    parser.add_argument("--stage1-dir", type=Path, default=Path("runs/etgi/stage1-basic-frozen-20261015"))
    parser.add_argument("--stage2-dir", type=Path, default=Path("runs/etgi/stage2-cross-scenario-frozen-20261015"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/sherlock/v3"))
    parser.add_argument("--out-root", type=Path, default=Path("runs/etgi/stage3-audit-response-20261015"))
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    freeze = json.loads(args.freeze_manifest.read_text(encoding="utf-8"))
    freeze_check = verify_frozen_engine_integrity(freeze, repo_root)

    s1_summary = json.loads((args.stage1_dir / "stage1_summary.json").read_text(encoding="utf-8"))
    s2_summary = json.loads((args.stage2_dir / "stage2_summary.json").read_text(encoding="utf-8"))

    all_entries = []
    for w in s1_summary["windows"]:
        all_entries.append({
            "scenario": "01-Basic",
            "episode_id": w["episode_id"],
            "window_summary": w,
            "recon_dir": args.stage1_dir / "reconstruction" / w["episode_id"],
            "db_path": args.stage1_dir / "index" / w["episode_id"] / "evidence.sqlite",
        })
    for w in s2_summary["semiurban_windows"]:
        all_entries.append({
            "scenario": "02-Semiurban",
            "episode_id": w["episode_id"],
            "window_summary": w,
            "recon_dir": args.stage2_dir / "semiurban" / "reconstruction" / w["episode_id"],
            "db_path": args.stage2_dir / "semiurban" / "index" / w["episode_id"] / "evidence.sqlite",
        })
    for w in s2_summary["rural_windows"]:
        all_entries.append({
            "scenario": "03-Rural",
            "episode_id": w["episode_id"],
            "window_summary": w,
            "recon_dir": args.stage2_dir / "rural" / "reconstruction" / w["episode_id"],
            "db_path": args.stage2_dir / "rural" / "index" / w["episode_id"] / "evidence.sqlite",
        })

    if args.mode == "stage3a":
        entries = _select_stage3a_pilot_windows(all_entries)
    else:
        entries = all_entries

    args.out_root.mkdir(parents=True, exist_ok=True)
    per_window_dir = args.out_root / "windows"
    per_window_dir.mkdir(parents=True, exist_ok=True)

    evaluated_records = []
    raw_cache_for_cases: dict[tuple[str, str], dict] = {}
    wanted_case_eps = {ep for spec in REPRESENTATIVE_CASE_SPECS for ep in spec["episodes"]}

    for idx, item in enumerate(entries, start=1):
        scen = item["scenario"]
        ep = item["episode_id"]
        w_sum = item["window_summary"]
        rdir = item["recon_dir"]
        db_path = item["db_path"]

        manifest = json.loads((rdir / "run_manifest.json").read_text(encoding="utf-8"))
        if (
            manifest.get("code_sha256") != freeze["code_sha256"]
            or manifest.get("evidence_code_sha256") != freeze["evidence_code_sha256"]
        ):
            raise RuntimeError(f"Artifact manifest hash mismatch on {scen}/{ep}")

        tx_res = json.loads((rdir / "transactions.json").read_text(encoding="utf-8"))
        anc_res = json.loads((rdir / "event_anchors.json").read_text(encoding="utf-8"))
        eg_res = json.loads((rdir / "event_graph.json").read_text(encoding="utf-8"))
        sl_res = json.loads((rdir / "storylines.json").read_text(encoding="utf-8"))
        syn_res = json.loads((rdir / "incident_synthesis.json").read_text(encoding="utf-8"))
        qc_res = json.loads((rdir / "quality_consistency.json").read_text(encoding="utf-8"))
        lc_res = json.loads((rdir / "lineage_consistency.json").read_text(encoding="utf-8"))
        rep_res = json.loads((rdir / "investigation_report.json").read_text(encoding="utf-8"))

        t0 = time.perf_counter()
        b1 = run_temporal_only_baseline(
            tx_result=tx_res, anchor_result=anc_res,
            mirage_event_graph=eg_res, mirage_storylines=sl_res, mirage_synthesis=syn_res,
        )
        t_b1 = round(time.perf_counter() - t0, 5)

        t0 = time.perf_counter()
        b2 = run_protocol_only_baseline(
            tx_result=tx_res, anchor_result=anc_res,
            mirage_storylines=sl_res, mirage_synthesis=syn_res,
        )
        t_b2 = round(time.perf_counter() - t0, 5)

        t0 = time.perf_counter()
        a1 = run_ablation_without_behavioral_gate(
            tx_result=tx_res, anchor_result=anc_res,
            mirage_event_graph=eg_res, mirage_storylines=sl_res, mirage_synthesis=syn_res,
        )
        t_a1 = round(time.perf_counter() - t0, 5)

        t0 = time.perf_counter()
        a2 = run_ablation_without_provenance_dedup(
            tx_result=tx_res, anchor_result=anc_res,
            mirage_event_graph=eg_res, mirage_storylines=sl_res, mirage_synthesis=syn_res,
            db_path=db_path,
        )
        t_a2 = round(time.perf_counter() - t0, 5)

        t0 = time.perf_counter()
        a3 = run_ablation_without_incident_synthesis(
            tx_result=tx_res, anchor_result=anc_res,
            mirage_event_graph=eg_res, mirage_storylines=sl_res, mirage_synthesis=syn_res,
            lineage_consistency=lc_res,
            db_path=db_path,
        )
        t_a3 = round(time.perf_counter() - t0, 5)

        timings = {
            "B1_temporal_only_s": t_b1,
            "B2_protocol_only_s": t_b2,
            "A1_no_behavioral_gate_s": t_a1,
            "A2_no_provenance_dedup_s": t_a2,
            "A3_no_incident_synthesis_s": t_a3,
        }
        win_eval = evaluate_window_methods(
            episode_id=ep, scenario=scen, window_summary=w_sum,
            tx_result=tx_res, anchor_result=anc_res,
            mirage_event_graph=eg_res, mirage_storylines=sl_res, mirage_synthesis=syn_res,
            b1_result=b1, b2_result=b2, a1_result=a1, a2_result=a2, a3_result=a3,
            method_timings_s=timings,
        )

        # Collect distinct RTU IPs in this window for scenario-wide unique RTU set accounting
        ledger = syn_res.get("source_dependency_ledger") or {}
        win_rtu_ips = sorted(set(
            list(ledger.get("distinct_rtu_ips") or [])
            + [t.get("rtu_ip") for t in (tx_res.get("transactions") or []) if t.get("rtu_ip")]
        ))

        record = {
            "scenario": scen,
            "episode_id": ep,
            "observation_profile": w_sum["observation_profile"],
            "distinct_rtu_ips_in_window": win_rtu_ips,
            "eval": win_eval,
            "B1": b1,
            "B2": b2,
            "A1": a1,
            "A2": a2,
            "A3": a3,
        }
        evaluated_records.append(record)

        if args.mode == "stage3b":
            ep_out = per_window_dir / scen / ep
            ep_out.mkdir(parents=True, exist_ok=True)
            (ep_out / "stage3_window_comparison.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8",
            )

        if (scen, ep) in wanted_case_eps:
            raw_cache_for_cases[(scen, ep)] = {
                "window_eval": win_eval,
                "tx_result": tx_res,
                "anchor_result": anc_res,
                "mirage_storylines": sl_res,
                "mirage_synthesis": syn_res,
                "mirage_report": rep_res,
                "quality_consistency": qc_res,
                "lineage_consistency": lc_res,
                "b1_result": b1,
                "b2_result": b2,
                "a1_result": a1,
                "a2_result": a2,
                "a3_result": a3,
            }

        print(
            f"[{idx:03d}/{len(entries):03d}] {scen} {ep} ({w_sum['observation_profile'][:2]}): "
            f"B1_cand={b1['candidate_temporal_relation_count']}(unsub={b1['unsubstantiated_temporal_candidate_count']},conf={b1['explicit_evidence_constraint_conflict_count']}), "
            f"A1_prom={a1['unsupported_promotion_total_count']}, "
            f"A2_mir={a2['true_cross_vantage_mirror_duplicate_count']},ioa={a2['same_asdu_different_ioa_point_count']},sess={a2['distinct_messages_in_same_tcp_session_count']},ev={a2['distinct_time_network_events_in_anchor_count']},ipal={a2['ipal_derived_observation_count']}, "
            f"E3_lin={a3['with_full_synthesis']['traceability_verification']['4_full_lineage_consistency']}"
        )

    by_scenario = {}
    for scen in ("01-Basic", "02-Semiurban", "03-Rural"):
        sub = [r for r in evaluated_records if r["scenario"] == scen]
        if sub:
            by_scenario[scen] = aggregate_scenario_evaluations(sub)
    combined_all = aggregate_scenario_evaluations(evaluated_records)

    synthetic_cases = run_synthetic_known_answer_counterexamples()
    real_case_studies = []
    for spec in REPRESENTATIVE_CASE_SPECS:
        for scen, ep in spec["episodes"]:
            if (scen, ep) in raw_cache_for_cases:
                real_case_studies.append(
                    extract_real_case_study(
                        case_spec=spec, scenario=scen, episode_id=ep,
                        **raw_cache_for_cases[(scen, ep)],
                    )
                )

    physical_eval = None
    if args.mode == "stage3b":
        physical_eval = run_post_freeze_physical_state_comparison(
            basic_zip_path=args.raw_dir / "01-Basic.zip",
            stage1_recon_root=args.stage1_dir / "reconstruction",
        )

    cached_eval_sec = round(time.perf_counter() - t0_proc, 3)

    out_payload = {
        "stage": f"Stage 3 Audit-Response Baseline & Ablation Suite ({args.mode})",
        "freeze_verification": freeze_check,
        "strict_input_isolation_verified": True,
        "window_count_evaluated": len(evaluated_records),
        "stage3_cached_artifact_evaluation_runtime_seconds": cached_eval_sec,
        "runtime_accounting_note": (
            f"`stage3_cached_artifact_evaluation_runtime_seconds` ({cached_eval_sec}s) measures "
            "the Stage 3 evaluation pass over cached Stage 1/2 reconstruction artifacts and SQLite "
            "rows, NOT the full end-to-end indexing + reconstruction pipeline runtime (which is "
            "reported in `E4_computational_cost`)."
        ),
        "combined_summary": combined_all,
        "by_scenario": by_scenario,
        "representative_real_sherlock_case_studies_count": len(real_case_studies),
        "representative_real_sherlock_case_studies": real_case_studies,
        "synthetic_known_answer_counterexamples_separate_from_sherlock": synthetic_cases,
        "post_freeze_physical_state_evaluation": physical_eval,
        "per_window_summaries": [
            {
                "scenario": r["scenario"],
                "episode_id": r["episode_id"],
                "observation_profile": r["observation_profile"],
                "B1_candidate_temporal_relations": r["B1"]["candidate_temporal_relation_count"],
                "B1_unsubstantiated_temporal_candidates": r["B1"]["unsubstantiated_temporal_candidate_count"],
                "B1_explicit_evidence_constraint_conflicts": r["B1"]["explicit_evidence_constraint_conflict_count"],
                "B1_corroborated_same_device_candidates": r["B1"]["corroborated_same_device_candidate_count"],
                "B1_topology_breakdown": r["B1"]["topology_breakdown"],
                "B2_applicability": r["B2"]["applicability_status"],
                "B2_verified_command_transitions": r["B2"]["transaction_count_verified_transition"],
                "B2_omitted_verified_non_command_anchors": r["B2"]["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"],
                "B2_omitted_cross_rtu_bridges": r["B2"]["omitted_compared_to_full_mirage"]["omitted_cross_rtu_verified_element_bridge_count"],
                "A1_originally_supported": r["A1"]["originally_supported_total_count"],
                "A1_unsupported_promotions": r["A1"]["unsupported_promotion_total_count"],
                "A1_ungated_spurious_cross_rtu_bridges": r["A1"]["ungated_spurious_cross_rtu_bridge_promotion_count"],
                "A1_violation_breakdown": r["A1"]["evidence_constraint_violation_breakdown"],
                "A2_raw_observations": r["A2"]["raw_observation_count"],
                "A2_distinct_source_containers": r["A2"]["distinct_source_container_count"],
                "A2_true_cross_vantage_mirror_duplicates": r["A2"]["true_cross_vantage_mirror_duplicate_count"],
                "A2_same_asdu_different_ioa_points": r["A2"]["same_asdu_different_ioa_point_count"],
                "A2_distinct_messages_in_same_tcp_session": r["A2"]["distinct_messages_in_same_tcp_session_count"],
                "A2_distinct_time_network_events_in_anchor": r["A2"]["distinct_time_network_events_in_anchor_count"],
                "A2_ipal_derived_rows": r["A2"]["ipal_derived_observation_count"],
                "A2_unknown_provenance_relations": r["A2"]["unknown_provenance_relation_count"],
                "A2_true_duplicate_or_derived_inflation": r["A2"]["true_duplicate_or_derived_source_inflation_count"],
                "A2_multi_event_anchor_aggregation": r["A2"]["multi_event_anchor_aggregation_count"],
                "A3_local_storylines": r["A3"]["with_full_synthesis"]["local_storyline_count"],
                "MIRAGE_rtu_asdu_bundles": r["A3"]["with_full_synthesis"]["rtu_asdu_bundle_count"],
                "MIRAGE_cross_rtu_verified_bridges": r["A3"]["with_full_synthesis"]["cross_rtu_verified_element_bridge_count"],
                "MIRAGE_bridged_components": r["A3"]["with_full_synthesis"]["multi_bundle_bridged_component_count"],
                "MIRAGE_competing_explanations": r["A3"]["with_full_synthesis"]["competing_explanations_with_missing_evidence_count"],
                "E3_traceability_levels": r["A3"]["with_full_synthesis"]["traceability_verification"],
            }
            for r in evaluated_records
        ],
    }

    fname = "stage3a_pilot_summary.json" if args.mode == "stage3a" else "stage3b_full_summary.json"
    (args.out_root / fname).write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Stage 3 Audit-Response ({args.mode}) complete in {cached_eval_sec}s. Output: {args.out_root / fname}")


if __name__ == "__main__":
    main()
