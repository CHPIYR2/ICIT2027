"""Stage 3 Baseline, Ablation & Paper Evidence Runner (`stage3a` 12-window pilot & `stage3b` 103-window full suite).

Answers the five core Stage 3 research questions using identical Sherlock v3 windows,
Evidence Indexes, and raw observations without modifying any frozen engine module:
1. Why temporal proximity alone (`B1_temporal_only`) cannot establish incident relations.
2. Why pure IEC-104 transaction reconstruction (`B2_protocol_only`) is insufficient for full OT incident investigation.
3. Which unsupported promotions and constraint violations are blocked by the Behavioral Consistency Gate (`A1`).
4. How Provenance Deduplication (`A2`) prevents mirror-port, multi-IOA ASDU, and IPAL source inflation.
5. What traceable incident structure and competing explanations are added by Four-Layer Incident Synthesis (`A3`).
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
    """Deterministically select 1 window from each observation stratum (S1, S2, S3, S4) per scenario (12 total)."""
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


def aggregate_scenario_evaluations(evals: list[dict]) -> dict:
    n = len(evals)
    b2_app = [e for e in evals if e["B2"]["is_applicable_to_window"]]
    b2_not_app = [e for e in evals if not e["B2"]["is_applicable_to_window"]]

    return {
        "window_count": n,
        "B2_applicability_breakdown": {
            "applicable_control_command_windows": len(b2_app),
            "not_applicable_no_control_command_windows": len(b2_not_app),
        },
        "Q1_temporal_only_vs_mirage": {
            "B1_candidate_temporal_relations": dist_stats([e["B1"]["candidate_temporal_relation_count"] for e in evals]),
            "B1_unbounded_15s_temporal_pairs": dist_stats([e["B1"]["unbounded_15s_temporal_pair_count"] for e in evals]),
            "B1_conflicting_or_unsupported_candidates": dist_stats([e["B1"]["total_conflicting_or_unsupported_candidate_count"] for e in evals]),
            "B1_lacking_device_or_session_support": dist_stats([e["B1"]["lacking_device_or_session_support_count"] for e in evals]),
            "B1_cross_device_candidates": dist_stats([e["B1"]["cross_device_candidate_count"] for e in evals]),
            "B1_same_asdu_co_report_chained": dist_stats([e["B1"]["same_asdu_co_report_chained_count"] for e in evals]),
            "B1_quality_or_test_bit_conflicts": dist_stats([e["B1"]["quality_or_test_bit_conflict_count"] for e in evals]),
            "B1_transient_not_sustained_conflicts": dist_stats([e["B1"]["transient_not_sustained_conflict_count"] for e in evals]),
            "B1_same_device_direction_or_type_conflicts": dist_stats([e["B1"]["same_device_direction_or_type_conflict_count"] for e in evals]),
            "MIRAGE_OT_supported_storyline_steps": dist_stats([e["B1"]["mirage_comparison"]["mirage_supported_storyline_step_count"] for e in evals]),
            "MIRAGE_OT_cross_rtu_verified_bridges": dist_stats([e["B1"]["mirage_comparison"]["mirage_cross_rtu_verified_bridge_count"] for e in evals]),
            "paired_test_unsupported_candidates_B1_minus_MIRAGE": paired_window_difference_stats(
                [e["B1"]["total_conflicting_or_unsupported_candidate_count"] for e in evals],
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
            "paired_test_verified_anchors_MIRAGE_minus_B2": paired_window_difference_stats(
                [e["B2"]["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"] for e in evals],
                [0 for _ in evals],
            ),
        },
        "Q3_ablation_A1_without_behavioral_gate": {
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
            "paired_test_unsupported_promotions_A1_minus_MIRAGE": paired_window_difference_stats(
                [e["A1"]["unsupported_promotion_total_count"] for e in evals],
                [0 for _ in evals],
            ),
        },
        "Q4_ablation_A2_without_provenance_dedup": {
            "raw_observation_count": dist_stats([e["A2"]["raw_observation_count"] for e in evals]),
            "distinct_source_container_count": dist_stats([e["A2"]["distinct_source_container_count"] for e in evals]),
            "distinct_asdu_container_count": dist_stats([e["A2"]["distinct_asdu_container_count"] for e in evals]),
            "distinct_rtu_count": dist_stats([e["A2"]["distinct_rtu_count"] for e in evals]),
            "mirror_duplicate_count": dist_stats([e["A2"]["mirror_duplicate_count"] for e in evals]),
            "same_asdu_multi_point_expansion_count": dist_stats([e["A2"]["same_asdu_multi_point_expansion_count"] for e in evals]),
            "ipal_derived_observation_count": dist_stats([e["A2"]["ipal_derived_observation_count"] for e in evals]),
            "falsely_counted_independent_sources": dist_stats([e["A2"]["falsely_counted_independent_source_count"] for e in evals]),
            "source_inflation_factor": dist_stats([e["A2"]["source_inflation_factor"] for e in evals]),
            "spurious_multi_source_storylines_without_dedup": dist_stats(
                [e["A2"]["spurious_multi_source_storyline_count_without_dedup"] for e in evals]
            ),
            "paired_test_inflated_sources_A2_minus_MIRAGE": paired_window_difference_stats(
                [e["A2"]["raw_observation_count"] for e in evals],
                [e["A2"]["distinct_source_container_count"] for e in evals],
            ),
        },
        "Q5_ablation_A3_without_incident_synthesis": {
            "local_storyline_count": dist_stats([e["A3"]["with_full_synthesis"]["local_storyline_count"] for e in evals]),
            "deduplicated_source_containers": dist_stats([e["A3"]["with_full_synthesis"]["deduplicated_source_container_count"] for e in evals]),
            "rtu_asdu_bundles": dist_stats([e["A3"]["with_full_synthesis"]["rtu_asdu_bundle_count"] for e in evals]),
            "co_reported_points_collapsed": dist_stats([e["A3"]["with_full_synthesis"]["co_reported_points_collapsed_into_bundles"] for e in evals]),
            "cross_rtu_verified_bridges": dist_stats([e["A3"]["with_full_synthesis"]["cross_rtu_verified_element_bridge_count"] for e in evals]),
            "multi_bundle_bridged_components": dist_stats([e["A3"]["with_full_synthesis"]["multi_bundle_bridged_component_count"] for e in evals]),
            "candidate_scenario_phases": dist_stats([e["A3"]["with_full_synthesis"]["candidate_scenario_phase_count"] for e in evals]),
            "competing_explanations_generated": dist_stats([e["A3"]["with_full_synthesis"]["competing_explanations_with_missing_evidence_count"] for e in evals]),
            "all_bundles_and_bridges_100pct_traceable": all(
                e["A3"]["with_full_synthesis"]["traceability_verification"]["all_bundles_cite_evidence_ids"]
                and e["A3"]["with_full_synthesis"]["traceability_verification"]["all_bridges_cite_evidence_ids"]
                for e in evals
            ),
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
            "B1_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_method_evaluation_timings_s"]["B1_temporal_only_s"] for e in evals]
            ),
            "B2_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_method_evaluation_timings_s"]["B2_protocol_only_s"] for e in evals]
            ),
            "A1_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_method_evaluation_timings_s"]["A1_no_behavioral_gate_s"] for e in evals]
            ),
            "A2_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_method_evaluation_timings_s"]["A2_no_provenance_dedup_s"] for e in evals]
            ),
            "A3_evaluation_s": dist_stats(
                [e["eval"]["E4_computational_cost"]["stage3_method_evaluation_timings_s"]["A3_no_incident_synthesis_s"] for e in evals]
            ),
            "full_artifacts_mib": dist_stats([e["eval"]["E4_computational_cost"]["full_artifacts_mib"] for e in evals]),
        },
    }


def main() -> None:
    t0_proc = time.perf_counter()
    parser = argparse.ArgumentParser(description="Run Stage 3 Baseline, Ablation & Paper Evidence Suite")
    parser.add_argument("--mode", choices=("stage3a", "stage3b"), required=True)
    parser.add_argument("--freeze-manifest", type=Path, default=Path("configs/etgi/method_freeze.v1.json"))
    parser.add_argument("--stage1-dir", type=Path, default=Path("runs/etgi/stage1-basic-frozen-20261015"))
    parser.add_argument("--stage2-dir", type=Path, default=Path("runs/etgi/stage2-cross-scenario-frozen-20261015"))
    parser.add_argument("--out-root", type=Path, default=Path("runs/etgi/stage3-baseline-ablation-20261015"))
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
        })
    for w in s2_summary["semiurban_windows"]:
        all_entries.append({
            "scenario": "02-Semiurban",
            "episode_id": w["episode_id"],
            "window_summary": w,
            "recon_dir": args.stage2_dir / "semiurban" / "reconstruction" / w["episode_id"],
        })
    for w in s2_summary["rural_windows"]:
        all_entries.append({
            "scenario": "03-Rural",
            "episode_id": w["episode_id"],
            "window_summary": w,
            "recon_dir": args.stage2_dir / "rural" / "reconstruction" / w["episode_id"],
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
        )
        t_a2 = round(time.perf_counter() - t0, 5)

        t0 = time.perf_counter()
        a3 = run_ablation_without_incident_synthesis(
            tx_result=tx_res, anchor_result=anc_res,
            mirage_event_graph=eg_res, mirage_storylines=sl_res, mirage_synthesis=syn_res,
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

        record = {
            "scenario": scen,
            "episode_id": ep,
            "observation_profile": w_sum["observation_profile"],
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
            f"B1_cand={b1['candidate_temporal_relation_count']}(viol={b1['total_conflicting_or_unsupported_candidate_count']}), "
            f"B2_app={b2['is_applicable_to_window']}(omitted_anc={b2['omitted_compared_to_full_mirage']['omitted_verified_non_command_anchor_count']}), "
            f"A1_prom={a1['unsupported_promotion_total_count']}, "
            f"A2_infl={a2['falsely_counted_independent_source_count']}({a2['source_inflation_factor']}x), "
            f"MIRAGE_brg={a3['with_full_synthesis']['cross_rtu_verified_element_bridge_count']}"
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

    out_payload = {
        "stage": f"Stage 3 Baseline & Ablation Suite ({args.mode})",
        "freeze_verification": freeze_check,
        "strict_input_isolation_verified": True,
        "window_count_evaluated": len(evaluated_records),
        "runtime_seconds": round(time.perf_counter() - t0_proc, 3),
        "combined_summary": combined_all,
        "by_scenario": by_scenario,
        "representative_real_sherlock_case_studies": real_case_studies,
        "synthetic_known_answer_counterexamples_separate_from_sherlock": synthetic_cases,
        "per_window_summaries": [
            {
                "scenario": r["scenario"],
                "episode_id": r["episode_id"],
                "observation_profile": r["observation_profile"],
                "B1_candidate_temporal_relations": r["B1"]["candidate_temporal_relation_count"],
                "B1_conflicting_or_unsupported": r["B1"]["total_conflicting_or_unsupported_candidate_count"],
                "B1_unbounded_15s_pairs": r["B1"]["unbounded_15s_temporal_pair_count"],
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
                "A2_mirror_duplicates": r["A2"]["mirror_duplicate_count"],
                "A2_same_asdu_expansion": r["A2"]["same_asdu_multi_point_expansion_count"],
                "A2_ipal_derived_rows": r["A2"]["ipal_derived_observation_count"],
                "A2_falsely_inflated_sources": r["A2"]["falsely_counted_independent_source_count"],
                "A2_source_inflation_factor": r["A2"]["source_inflation_factor"],
                "A3_local_storylines": r["A3"]["with_full_synthesis"]["local_storyline_count"],
                "MIRAGE_rtu_asdu_bundles": r["A3"]["with_full_synthesis"]["rtu_asdu_bundle_count"],
                "MIRAGE_cross_rtu_verified_bridges": r["A3"]["with_full_synthesis"]["cross_rtu_verified_element_bridge_count"],
                "MIRAGE_bridged_components": r["A3"]["with_full_synthesis"]["multi_bundle_bridged_component_count"],
                "MIRAGE_competing_explanations": r["A3"]["with_full_synthesis"]["competing_explanations_with_missing_evidence_count"],
            }
            for r in evaluated_records
        ],
    }

    fname = "stage3a_pilot_summary.json" if args.mode == "stage3a" else "stage3b_full_summary.json"
    (args.out_root / fname).write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Stage 3 ({args.mode}) complete in {out_payload['runtime_seconds']}s. Output: {args.out_root / fname}")


if __name__ == "__main__":
    main()
