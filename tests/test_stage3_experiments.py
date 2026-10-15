"""Unit and counterexample tests for Stage 3 Baselines (B1, B2), Ablations (A1, A2, A3), and Evaluation Metrics."""
from __future__ import annotations
from pathlib import Path

from experiments.stage3.evaluation.case_studies import run_synthetic_known_answer_counterexamples
from experiments.stage3.evaluation.metrics import dist_stats, paired_window_difference_stats
from experiments.stage3.run_stage3 import verify_frozen_engine_integrity
import json


def test_stage3_frozen_engine_integrity_matches_manifest():
    repo_root = Path(__file__).resolve().parents[1]
    freeze = json.loads((repo_root / "configs/etgi/method_freeze.v1.json").read_text(encoding="utf-8"))
    check = verify_frozen_engine_integrity(freeze, repo_root)
    assert check["verified"] is True
    assert check["module_count"] == 30


def test_stage3_synthetic_known_answer_counterexamples_all_pass():
    cases = run_synthetic_known_answer_counterexamples()
    assert len(cases) == 3
    by_id = {c["synthetic_case_id"]: c for c in cases}

    # S-KA1: test bit + opposing direction blocked by MIRAGE-OT, promoted by B1 and A1
    ska1 = by_id["S_KA1_test_bit_and_opposing_direction"]
    assert ska1["passed_known_answer"] is True
    assert ska1["B1_temporal_only_candidates"] == 1
    assert ska1["A1_ungated_unsupported_promotions"] == 1
    assert ska1["MIRAGE_OT_supported_bridges"] == 0
    assert ska1["MIRAGE_OT_sequential_rejected"] == 1

    # S-KA2: 1 ASDU x 2 IOAs x 2 mirror vantages + 2 IPAL rows = 6 raw observations, 1 true container
    ska2 = by_id["S_KA2_mirror_and_same_asdu_and_ipal_duplication"]
    assert ska2["passed_known_answer"] is True
    assert ska2["A2_naive_raw_observation_count"] == 6
    assert ska2["A2_mirror_duplicate_count"] == 2
    assert ska2["A2_same_asdu_expansion_count"] == 1
    assert ska2["A2_ipal_derived_count"] == 2
    assert ska2["MIRAGE_OT_distinct_source_container_count"] == 1

    # S-KA3: unverified switch report kept unresolved while corroborated cross-RTU line.4 forms 1 bridge
    ska3 = by_id["S_KA3_unverified_switch_vs_verified_cross_rtu_line_bridge"]
    assert ska3["passed_known_answer"] is True
    assert ska3["MIRAGE_OT_verified_bridges"] == ["line.4"]
    assert ska3["MIRAGE_OT_unresolved_branches"] == 2


def test_stage3_dist_stats_and_paired_window_difference():
    d = dist_stats([1, 2, 3, 4, 100])
    assert d["total"] == 110
    assert d["median"] == 3.0
    assert d["max"] == 100

    p = paired_window_difference_stats([10, 20, 30, 0], [2, 5, 10, 0])
    assert p["n_paired_windows"] == 4
    assert p["windows_where_baseline_exceeds_mirage"] == 3
    assert p["windows_tied"] == 1
    assert p["mean_difference_bootstrap_95ci"][0] > 0
