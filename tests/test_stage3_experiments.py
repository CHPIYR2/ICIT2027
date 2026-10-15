"""Unit and counterexample tests for Stage 3 Audit-Response Baselines, Ablations, and Evaluation Metrics."""
from __future__ import annotations
import json
from pathlib import Path

from experiments.stage3.ablations.no_provenance_dedup import run_ablation_without_provenance_dedup
from experiments.stage3.evaluation.case_studies import run_synthetic_known_answer_counterexamples
from experiments.stage3.evaluation.metrics import dist_stats, paired_window_difference_stats
from experiments.stage3.evaluation.physical_state_comparison import (
    BRIDGE_REL_TOL,
    classify_numeric,
    classify_to_zero_post,
    combine_sides,
)
from experiments.stage3.run_stage3 import verify_frozen_engine_integrity


def test_stage3_frozen_engine_integrity_matches_manifest():
    repo_root = Path(__file__).resolve().parents[1]
    freeze = json.loads((repo_root / "configs/etgi/method_freeze.v1.json").read_text(encoding="utf-8"))
    check = verify_frozen_engine_integrity(freeze, repo_root)
    assert check["verified"] is True
    assert check["module_count"] == 30


def test_stage3_synthetic_known_answer_counterexamples_all_pass():
    cases = run_synthetic_known_answer_counterexamples()
    assert len(cases) == 4
    by_id = {c["synthetic_case_id"]: c for c in cases}

    # S-KA1: test bit + opposing direction -> explicit_evidence_constraint_conflict in B1, blocked in MIRAGE-OT
    ska1 = by_id["S_KA1_test_bit_and_opposing_direction"]
    assert ska1["passed_known_answer"] is True
    assert ska1["B1_temporal_only_candidates"] == 1
    assert ska1["B1_explicit_constraint_conflicts"] == 1
    assert ska1["A1_ungated_unsupported_promotions"] == 1
    assert ska1["MIRAGE_OT_supported_bridges"] == 0

    # S-KA2: 1 ASDU x 2 IOAs x 2 mirror vantages + 2 IPAL rows = 6 raw observations, 1 true container
    ska2 = by_id["S_KA2_mirror_and_same_asdu_and_ipal_duplication"]
    assert ska2["passed_known_answer"] is True
    assert ska2["A2_naive_raw_observation_count"] == 6
    assert ska2["A2_true_cross_vantage_mirror_duplicate_count"] == 2
    assert ska2["A2_same_asdu_different_ioa_point_count"] == 1
    assert ska2["A2_ipal_derived_count"] == 2
    assert ska2["MIRAGE_OT_distinct_source_container_count"] == 1

    # S-KA3: cross-device links from unverified switch are unsubstantiated_temporal_candidates (0 explicit conflicts)
    ska3 = by_id["S_KA3_unverified_switch_vs_verified_cross_rtu_line_bridge"]
    assert ska3["passed_known_answer"] is True
    assert ska3["B1_unsubstantiated_candidates"] == 2
    assert ska3["B1_explicit_constraint_conflicts"] == 0
    assert ska3["B1_corroborated_same_device_candidates"] == 1
    assert ska3["MIRAGE_OT_verified_bridges"] == ["line.4"]

    # S-KA4: multi-event communication_change anchor on single vantage has 0 mirror duplicates
    ska4 = by_id["S_KA4_communication_anchor_multi_event_not_mirror_duplicate"]
    assert ska4["passed_known_answer"] is True
    assert ska4["A2_true_cross_vantage_mirror_duplicate_count"] == 0
    assert ska4["A2_distinct_messages_in_same_tcp_session_count"] == 1
    assert ska4["A2_distinct_time_network_events_in_anchor_count"] == 2


def test_stage3_real_ev_cbe1e5_communication_anchor_does_not_misclassify_events_as_mirror_duplicates():
    """Task 2 counterexample: ev_cbe1e5bef23346604396 communication_change & ARP anchors have 0 mirror duplicates."""
    repo_root = Path(__file__).resolve().parents[1]
    s1_dir = repo_root / "runs/etgi/stage1-basic-frozen-20261015"
    ep = "ev_cbe1e5bef23346604396"
    db_path = s1_dir / "index" / ep / "evidence.sqlite"
    if not db_path.exists():
        return
    rdir = s1_dir / "reconstruction" / ep
    a2 = run_ablation_without_provenance_dedup(
        tx_result=json.loads((rdir / "transactions.json").read_text(encoding="utf-8")),
        anchor_result=json.loads((rdir / "event_anchors.json").read_text(encoding="utf-8")),
        mirage_event_graph=json.loads((rdir / "event_graph.json").read_text(encoding="utf-8")),
        mirage_storylines=json.loads((rdir / "storylines.json").read_text(encoding="utf-8")),
        mirage_synthesis=json.loads((rdir / "incident_synthesis.json").read_text(encoding="utf-8")),
        db_path=db_path,
    )
    assert a2["distinct_source_container_count"] == 4
    assert a2["true_cross_vantage_mirror_duplicate_count"] == 0
    assert a2["same_asdu_different_ioa_point_count"] == 0
    assert a2["distinct_messages_in_same_tcp_session_count"] == 20
    assert a2["distinct_time_network_events_in_anchor_count"] == 19
    assert a2["unknown_provenance_relation_count"] == 0


def test_stage3_dist_stats_and_paired_window_difference():
    d = dist_stats([1, 2, 3, 4, 100])
    assert d["total"] == 110
    assert d["median"] == 3.0
    assert d["max"] == 100

    p = paired_window_difference_stats([10, 20, 30, 0], [2, 5, 10, 0])
    assert p["n_paired_windows"] == 4
    assert p["windows_where_baseline_exceeds_mirage"] == 3
    assert p["windows_tied"] == 1
    assert p["descriptive_bootstrap_95ci"][0] > 0


def test_physical_comparison_separates_exact_tolerance_and_nan_semantics():
    exact = classify_numeric(1.0, 1.0, 0.05, criterion="transaction_pre_numeric_rel_0.05")
    assert exact["agreement_class"] == "exact_numeric"

    tolerant = classify_numeric(100.0, 103.0, 0.05, criterion="transaction_pre_numeric_rel_0.05")
    assert tolerant["agreement_class"] == "within_tolerance"

    mismatch = classify_numeric(4.7134, 3.9929, BRIDGE_REL_TOL, criterion="to_zero_pre_numeric_rel_0.10")
    assert mismatch["agreement_class"] == "numeric_mismatch"

    missing = classify_numeric(1.0, None, BRIDGE_REL_TOL, criterion="to_zero_pre_numeric_rel_0.10")
    assert missing["checked"] is False
    assert missing["agreement_class"] == "unchecked_missing_physical"

    semantic = classify_to_zero_post(0.0, float("nan"))
    assert semantic["agreement_class"] == "semantic_deenergized_nan_vs_iec104_zero"
    assert semantic["agreement_class"] != "exact_numeric"

    numeric_zero = classify_to_zero_post(0.0, 0.0)
    assert numeric_zero["agreement_class"] == "exact_numeric"


def test_to_zero_does_not_treat_an_unchecked_or_mismatched_pre_value_as_agreement():
    pre_mismatch = classify_numeric(
        0.1746, -0.0918, BRIDGE_REL_TOL, criterion="to_zero_pre_numeric_rel_0.10"
    )
    post_semantic = classify_to_zero_post(0.0, float("nan"))
    combined = combine_sides(pre_mismatch, post_semantic)
    assert post_semantic["checked"] is True
    assert combined["compatible"] is False
    assert combined["agreement_class"] == "not_agreed"

    unchecked_pre = classify_numeric(10.0, None, BRIDGE_REL_TOL, criterion="to_zero_pre_numeric_rel_0.10")
    post_zero = classify_to_zero_post(0.0, 0.0)
    blocked = combine_sides(unchecked_pre, post_zero)
    assert blocked["agreement_class"] == "incomplete_unchecked"
    assert blocked["compatible"] is False

    pre_ok = classify_numeric(-807307.688, -807430.5532, BRIDGE_REL_TOL, criterion="to_zero_pre_numeric_rel_0.10")
    agreed = combine_sides(pre_ok, post_zero)
    assert agreed["compatible"] is True
    assert agreed["numeric_agreement"] is True
