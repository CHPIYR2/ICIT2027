"""T3 Pilot Evaluation using the 44 author-validated reference labels.

Guarantees:
- Recursively locates `PILOT-W*_AI_expert_response.json` under the pilot directory
  and never modifies the author-validated files.
- Maps all 44 blind unit IDs (`U001`..`U022` in `PILOT-W01` and `PILOT-W02`) to
  canonical `unit_id` and `timeline_id` via `custodian_key.json`, verifying
  bijective coverage, score fidelity (`needed=2, useful=1, not_needed=0`), and
  permutation invariance across Annotator Pack A and Pack B.
- Strictly separates Stage 1 (Evidence Selection: candidate pool -> 10 Fact Cards)
  from Stage 2 (LLM Fact Selection: same 10 Fact Cards -> model-chosen Fact/Edge IDs).
- Does not treat the 1,195 unlabeled full-pool candidates as Not Needed (0);
  marks full-pool Recall (and full-pool Precision when unlabeled units appear in
  top-K) as `NOT_ESTIMABLE`.
- Never counts `system_resolved_evidence_ids` or edge endpoints as autonomous
  model-selected facts.
"""
from __future__ import annotations
import hashlib
import json
import random
from pathlib import Path
from ..agent.ollama import OllamaClient
from ..evidence.index import open_indexed
from ..evidence.queries import EvidenceDB
from .eval_t3 import (
    GAIN_MAP, build_full_candidate_pool, canonical_unit_id, evaluate_with_gold,
    label_distribution, score_ranking, stage1_baselines, stage2_selection,
)
from .pipeline import prepare, run_manifest
from .position_bias import PERMUTATIONS, run_single_permutation, summarize_consistency

VALID_LABELS = {"needed", "useful", "not_needed", "cannot_judge"}


def load_and_verify_author_labels(pilot_dir: Path) -> dict:
    """Recursively find, validate, and unmap the 44 author-validated labels."""
    found_files = sorted(pilot_dir.rglob("PILOT-W*_AI_expert_response.json"))
    if len(found_files) != 2:
        raise FileNotFoundError(
            f"Expected 2 PILOT-W*_AI_expert_response.json files under {pilot_dir}, found {len(found_files)}"
        )
    custodian_path = next(pilot_dir.rglob("custodian_key.json"))
    custodian = json.loads(custodian_path.read_text(encoding="utf-8"))

    windows_out = {}
    total_units = 0

    for path in found_files:
        raw_bytes = path.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        data = json.loads(raw_bytes.decode("utf-8"))
        wid = data.get("blind_window_id")
        if wid not in custodian:
            raise KeyError(f"Window {wid} not found in custodian_key.json")

        c_entry = custodian[wid]
        inv_map = c_entry["unit_inverse_map_blind_to_unit"]
        fwd_map = c_entry["unit_forward_map_timeline_to_blind"]

        judgments = data.get("unit_judgments")
        if not isinstance(judgments, list) or len(judgments) != 22:
            raise ValueError(f"{wid}: expected 22 unit_judgments, got {len(judgments) if isinstance(judgments, list) else type(judgments)}")

        seen_blind = set()
        seen_canon_uid = set()
        seen_tid = set()
        mapped_records = []
        gains_by_uid: dict[str, int] = {}
        gains_by_tid: dict[str, int] = {}
        labels_by_uid: dict[str, str] = {}

        for item in judgments:
            b_id = item.get("blind_unit_id")
            label = str(item.get("necessity") or "").strip().lower()
            side = str(item.get("side") or "").strip().lower()
            basis = str(item.get("basis") or "").strip()
            if not b_id or b_id in seen_blind:
                raise ValueError(f"{wid}: duplicate or missing blind_unit_id {b_id}")
            if b_id not in inv_map:
                raise KeyError(f"{wid}: {b_id} not in custodian inverse map")
            if label not in VALID_LABELS:
                raise ValueError(f"{wid} {b_id}: invalid necessity label {label!r}")
            seen_blind.add(b_id)
            target = inv_map[b_id]
            uid = target["unit_id"]
            tid = target["timeline_id"]
            if uid in seen_canon_uid or tid in seen_tid:
                raise ValueError(f"{wid}: duplicate mapped canonical unit {uid} / {tid}")
            seen_canon_uid.add(uid)
            seen_tid.add(tid)

            score = GAIN_MAP[label]
            gains_by_uid[uid] = score
            gains_by_tid[tid] = score
            labels_by_uid[uid] = label
            mapped_records.append({
                "blind_unit_id": b_id,
                "timeline_id": tid,
                "canonical_unit_id": uid,
                "entity": target["entity"],
                "ca_ioa": target["ca_ioa"],
                "role": target["role"],
                "modality": target["modality"],
                "necessity": label,
                "score": score,
                "side": side,
                "basis": basis,
            })

        # Verify Pack A and Pack B permutation invariance
        pack_a_path = next(pilot_dir.rglob(f"{wid}_annotator_A.json"))
        pack_b_path = next(pilot_dir.rglob(f"{wid}_annotator_B.json"))
        pack_a = json.loads(pack_a_path.read_text(encoding="utf-8"))
        pack_b = json.loads(pack_b_path.read_text(encoding="utf-8"))
        units_a = {u["blind_unit_id"]: u for u in pack_a["units"]}
        units_b = {u["blind_unit_id"]: u for u in pack_b["units"]}
        pack_order_differs = [u["blind_unit_id"] for u in pack_a["units"]] != [u["blind_unit_id"] for u in pack_b["units"]]
        pack_content_identical = (units_a == units_b) and (set(units_a) == seen_blind)
        fwd_inv_consistent = all(fwd_map.get(rec["timeline_id"]) == rec["blind_unit_id"] for rec in mapped_records)
        if not (pack_content_identical and fwd_inv_consistent):
            raise AssertionError(f"{wid}: annotator pack mapping consistency check failed")

        mapped_records.sort(key=lambda r: r["timeline_id"])
        total_units += len(mapped_records)
        dist = {
            "needed": sum(1 for r in mapped_records if r["score"] == 2),
            "useful": sum(1 for r in mapped_records if r["score"] == 1),
            "not_needed": sum(1 for r in mapped_records if r["score"] == 0),
        }
        by_mod_needed = {
            "network_needed": sum(1 for r in mapped_records if r["score"] == 2 and r["modality"] == "network"),
            "electrical_needed": sum(1 for r in mapped_records if r["score"] == 2 and r["modality"] == "electrical"),
            "network_useful": sum(1 for r in mapped_records if r["score"] == 1 and r["modality"] == "network"),
            "electrical_useful": sum(1 for r in mapped_records if r["score"] == 1 and r["modality"] == "electrical"),
            "network_not_needed": sum(1 for r in mapped_records if r["score"] == 0 and r["modality"] == "network"),
            "electrical_not_needed": sum(1 for r in mapped_records if r["score"] == 0 and r["modality"] == "electrical"),
        }
        windows_out[wid] = {
            "blind_window_id": wid,
            "episode_id": c_entry["episode_id"],
            "source_file": str(path),
            "source_sha256": sha256,
            "annotator_id": data.get("annotator_id"),
            "window_sufficiency": data.get("window_sufficiency"),
            "unit_count": len(mapped_records),
            "unique_blind_ids": len(seen_blind),
            "unique_canonical_unit_ids": len(seen_canon_uid),
            "annotator_pack_orders_differ": pack_order_differs,
            "annotator_pack_permutation_invariant": pack_content_identical and fwd_inv_consistent,
            "label_distribution": dist,
            "modality_label_breakdown": by_mod_needed,
            "gains_by_unit_id": gains_by_uid,
            "gains_by_timeline_id": gains_by_tid,
            "labels_by_unit_id": labels_by_uid,
            "records": mapped_records,
        }

    if total_units != 44:
        raise ValueError(f"Expected 44 total author-validated units across both windows, got {total_units}")

    return {
        "validation_status": "VERIFIED_44_UNITS",
        "total_validated_units": total_units,
        "note": (
            "Author-validated reference labels on PILOT-W01 and PILOT-W02 (44 units total). "
            "Single author-reviewed AI-assisted pilot reference set; not claimed as dual-human inter-annotator consensus."
        ),
        "windows": windows_out,
    }


def stage2_non_llm_baselines_on_10_cards(exposed_cards: list[dict], timeline: list[dict],
                                         gains_by_uid: dict[str, int], *, seeds: int = 50) -> dict:
    """Compute non-LLM selection baselines (random and statistical score top-K) within the same 10 Fact Cards."""
    exposed_uids = [canonical_unit_id(card) for card in exposed_cards]
    exposed_set = set(exposed_uids)
    score_by_tid = {e["timeline_id"]: float(e.get("score") or 0.0) for e in timeline}
    cards_by_score = sorted(
        exposed_cards,
        key=lambda c: (-score_by_tid.get(c["timeline_id"], 0.0), c["time"]),
    )
    score_ranked_uids = [canonical_unit_id(c) for c in cards_by_score]

    random_runs = []
    for s in range(seeds):
        rng = random.Random(3000 + s)
        shuffled = list(exposed_uids)
        rng.shuffle(shuffled)
        random_runs.append(shuffled)

    out = {
        "exposed_10_distribution": label_distribution(exposed_uids, gains_by_uid, k=10),
        "score_top_k_within_10_cards": {},
        "random_within_10_cards_50_seeds_mean": {},
    }
    for k in (1, 2, 3, 5):
        out["score_top_k_within_10_cards"][f"K={k}"] = {
            "selected_unit_ids": score_ranked_uids[:k],
            "distribution": label_distribution(score_ranked_uids[:k], gains_by_uid, k=k),
            "within_exposed_10": score_ranking(score_ranked_uids[:k], gains_by_uid, ks=(k,), ideal_pool_ids=exposed_set),
            "within_labeled_22": score_ranking(score_ranked_uids[:k], gains_by_uid, ks=(k,)),
        }
        rand_e10 = [score_ranking(r[:k], gains_by_uid, ks=(k,), ideal_pool_ids=exposed_set) for r in random_runs]
        rand_l22 = [score_ranking(r[:k], gains_by_uid, ks=(k,)) for r in random_runs]
        out["random_within_10_cards_50_seeds_mean"][f"K={k}"] = {
            "within_exposed_10": {
                m: round(sum(item[m] for item in rand_e10) / len(rand_e10), 4) for m in rand_e10[0]
            },
            "within_labeled_22": {
                m: round(sum(item[m] for item in rand_l22) / len(rand_l22), 4) for m in rand_l22[0]
            },
        }
    return out


def run_author_validated_pilot_evaluation(
    pilot_dir: Path,
    out_dir: Path,
    *,
    models: tuple[str, ...] = ("qwen3.5:9b-q4_K_M", "gemma4:12b-it-q4_K_M"),
    levels: tuple[str, ...] = ("B2", "B4"),
    endpoint: str = "http://127.0.0.1:11434",
) -> dict:
    if out_dir.exists():
        raise FileExistsError(f"{out_dir} already exists; refusing to overwrite")
    out_dir.mkdir(parents=True)

    ref_labels = load_and_verify_author_labels(pilot_dir)
    (out_dir / "reference_labels.json").write_text(
        json.dumps(ref_labels, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    custodian_path = next(pilot_dir.rglob("custodian_key.json"))
    custodian = json.loads(custodian_path.read_text(encoding="utf-8"))

    stage1_results = {}
    stage2_non_llm = {}
    stage2_llm_rows = []
    consistency_summary = {}
    failure_cases = []
    manifest_record = None

    for wid in ("PILOT-W01", "PILOT-W02"):
        c_info = custodian[wid]
        w_ref = ref_labels["windows"][wid]
        gains_by_uid = w_ref["gains_by_unit_id"]
        gains_by_tid = w_ref["gains_by_timeline_id"]
        records_by_tid = {r["timeline_id"]: r for r in w_ref["records"]}

        db_path = Path("runs/etgi/memory-comparison-20261014/ev_3e4d36008b29595ef246/evidence.sqlite")
        conn, _meta = open_indexed(db_path)
        start = float(c_info["incident_start"])
        end = float(c_info["incident_end"])
        bg_start = float(c_info["background_start"])
        bg_end = float(c_info["background_end"])
        db = EvidenceDB(conn, incident_start=start, incident_end=end)

        prepared = prepare(db, start, end, background_start=bg_start, background_end=bg_end, limit=24)
        full_pool = build_full_candidate_pool(db, start, end, background_start=bg_start, background_end=bg_end)

        if manifest_record is None:
            manifest_record = run_manifest(
                db, evaluation="t3_author_validated_pilot", models=list(models),
                levels=list(levels), permutations=list(PERMUTATIONS),
                temperature=0, seed=1, num_ctx=8192, num_predict=512,
            )
            (out_dir / "run_manifest.json").write_text(
                json.dumps(manifest_record, indent=2, default=str), encoding="utf-8",
            )

        s1_base = stage1_baselines(
            full_pool, prepared["exposed_timeline"], prepared_timeline=prepared["timeline"], k=10, seeds=50,
        )
        dummy_s2 = stage2_selection(
            prepared["exposed_timeline"], prepared["timeline"], prepared["relations"],
            [], {"verified": [], "rejected": []},
        )
        s1_eval = evaluate_with_gold(s1_base, dummy_s2, gold_labels=gains_by_uid)

        # Detailed per-card breakdown of the 10 exposed Fact Cards vs 12 unexposed in the 22-unit pool
        exposed_tids = [c["timeline_id"] for c in prepared["exposed_timeline"]]
        exposed_set_tids = set(exposed_tids)
        exposed_card_details = [
            {
                "display_rank_in_original": idx + 1,
                **records_by_tid[tid],
                "selector_score": round(
                    next(e["score"] for e in prepared["timeline"] if e["timeline_id"] == tid), 4
                ),
            }
            for idx, tid in enumerate(exposed_tids)
        ]
        missed_needed_in_stage1 = [
            {
                **r,
                "selector_score": round(
                    next(e["score"] for e in prepared["timeline"] if e["timeline_id"] == r["timeline_id"]), 4
                ),
            }
            for r in w_ref["records"]
            if r["score"] == 2 and r["timeline_id"] not in exposed_set_tids
        ]
        if missed_needed_in_stage1:
            failure_cases.append({
                "window": wid,
                "stage": "Stage 1 (Evidence Selection)",
                "failure_type": "needed_unit_excluded_from_10_exposed_cards",
                "details": missed_needed_in_stage1,
            })

        stage1_results[wid] = {
            "episode_id": c_info["episode_id"],
            "full_pool_size": full_pool["candidate_count"],
            "labeled_pool_size": len(gains_by_uid),
            "unlabeled_pool_size": full_pool["candidate_count"] - len(gains_by_uid),
            "gold_needed_count": s1_eval["gold_needed_count"],
            "gold_useful_count": s1_eval["gold_useful_count"],
            "gold_not_needed_count": s1_eval["gold_not_needed_count"],
            "stage1_full_pool": s1_eval["stage1_full_pool"],
            "stage1_within_labeled_pool": s1_eval["stage1_within_labeled_pool"],
            "exposed_10_cards_labeled": exposed_card_details,
            "missed_needed_units_at_stage1": missed_needed_in_stage1,
        }

        stage2_non_llm[wid] = stage2_non_llm_baselines_on_10_cards(
            prepared["exposed_timeline"], prepared["timeline"], gains_by_uid, seeds=50,
        )

        win_dir = out_dir / wid
        win_dir.mkdir(exist_ok=True)
        (win_dir / "stage1_evaluation.json").write_text(
            json.dumps(stage1_results[wid], indent=2, ensure_ascii=False, default=str), encoding="utf-8",
        )
        (win_dir / "stage2_non_llm_baselines.json").write_text(
            json.dumps(stage2_non_llm[wid], indent=2, ensure_ascii=False, default=str), encoding="utf-8",
        )

        consistency_summary[wid] = {}
        exposed_uid_set = {canonical_unit_id(c) for c in prepared["exposed_timeline"]}

        for model_name in models:
            model_slug = model_name.split(":")[0].replace(".", "_")
            llm = OllamaClient(model_name, endpoint=endpoint)
            consistency_summary[wid][model_name] = {}

            for level in levels:
                runs_by_mode = {}
                for mode in PERMUTATIONS:
                    run_dir = win_dir / model_slug / f"{level}_{mode}"
                    rec = run_single_permutation(
                        db, llm, prepared, mode, level=level, shuffle_seed=42,
                        num_predict=512, num_ctx=8192, seed=1, out_dir=run_dir,
                    )
                    runs_by_mode[mode] = rec

                    s2 = stage2_selection(
                        prepared["exposed_timeline"], prepared["timeline"], prepared["relations"],
                        rec["canonical_claims"], rec["verification"], k=6,
                    )
                    direct_uids = s2["model_direct_unit_ids"]
                    direct_tids = s2["model_selected_fact_ids"]
                    k_actual = max(len(direct_uids), 1)
                    dist = label_distribution(direct_uids, gains_by_uid)

                    ranking_in_10 = score_ranking(
                        direct_uids, gains_by_uid, ks=(k_actual, 3, 5), ideal_pool_ids=exposed_uid_set,
                    )
                    ranking_in_22 = score_ranking(
                        direct_uids, gains_by_uid, ks=(k_actual, 3, 5),
                    )
                    per_item_scores = [
                        {
                            "timeline_id": tid,
                            "blind_unit_id": records_by_tid[tid]["blind_unit_id"],
                            "entity": records_by_tid[tid]["entity"],
                            "role": records_by_tid[tid]["role"],
                            "modality": records_by_tid[tid]["modality"],
                            "author_label": records_by_tid[tid]["necessity"],
                            "author_score": gains_by_tid[tid],
                        }
                        for tid in direct_tids if tid in records_by_tid
                    ]
                    (run_dir / "item_scores.json").write_text(
                        json.dumps(per_item_scores, indent=2, ensure_ascii=False), encoding="utf-8",
                    )

                    # Record failure cases if any claim was rejected or if model picked not_needed / missed all needed
                    if rec["verification"]["rejected"]:
                        failure_cases.append({
                            "window": wid,
                            "model": model_name,
                            "level": level,
                            "mode": mode,
                            "stage": "Stage 2 (LLM Claim / Relation Verification)",
                            "failure_type": "rejected_model_claim",
                            "rejected_claims": [
                                {
                                    "claim_type": c.get("claim_type"),
                                    "fact_id": c.get("fact_id"),
                                    "edge_id": c.get("edge_id"),
                                    "claim_level": c.get("claim_level"),
                                    "canonical_claim_level": c.get("canonical_claim_level"),
                                    "reasons": c.get("reasons"),
                                }
                                for c in rec["verification"]["rejected"]
                            ],
                        })
                    if dist["not_needed"] > 0:
                        failure_cases.append({
                            "window": wid,
                            "model": model_name,
                            "level": level,
                            "mode": mode,
                            "stage": "Stage 2 (LLM Fact Selection)",
                            "failure_type": "selected_not_needed_unit",
                            "selected_items": [it for it in per_item_scores if it["author_score"] == 0],
                        })

                    row = {
                        "window": wid,
                        "model": model_name,
                        "level": level,
                        "mode": mode,
                        "done_reason": rec["done_reason"],
                        "partial_output": rec["partial_output"],
                        "abstained": s2["abstained"],
                        "model_selected_fact_ids": direct_tids,
                        "raw_shown_fact_ids": rec["metrics"]["raw_shown_fact_ids"],
                        "model_selected_edge_ids": s2["model_selected_edge_ids"],
                        "system_resolved_evidence_id_count": s2["system_resolved_evidence_id_count"],
                        "original_positions_1based": rec["metrics"]["original_positions_1based"],
                        "display_positions_1based": rec["metrics"]["display_positions_1based"],
                        "chose_display_pos_1": rec["metrics"]["chose_display_pos_1"],
                        "direct_modality": rec["metrics"]["direct_modality"],
                        "label_distribution": dist,
                        "selected_items": per_item_scores,
                        "P@K_actual": ranking_in_10[f"P@{k_actual}"] if direct_uids else 0.0,
                        "P_needed@K_actual": ranking_in_10[f"P_needed@{k_actual}"] if direct_uids else 0.0,
                        "nDCG_within_10@K_actual": ranking_in_10[f"nDCG@{k_actual}"] if direct_uids else 0.0,
                        "P@3": ranking_in_10["P@3"],
                        "P_needed@3": ranking_in_10["P_needed@3"],
                        "R_needed_within_10@3": ranking_in_10["R_needed@3"],
                        "nDCG_within_10@3": ranking_in_10["nDCG@3"],
                        "R_needed_within_22@3": ranking_in_22["R_needed@3"],
                        "nDCG_within_22@3": ranking_in_22["nDCG@3"],
                        "total_claims": s2["total_claims"],
                        "verified_claims": s2["verified_claims"],
                        "rejected_claims": s2["rejected_claims"],
                        "faithfulness_rate": s2["faithfulness_rate"],
                        "relation_claim_count": s2["relation_claim_count"],
                        "unsupported_relation_count": s2["unsupported_relation_count"],
                        "unsupported_relation_rate": s2["unsupported_relation_rate"],
                        "prompt_tokens": rec["prompt_tokens"],
                        "completion_tokens": rec["completion_tokens"],
                    }
                    stage2_llm_rows.append(row)
                    print(
                        json.dumps({
                            "window": wid, "model": model_slug, "level": level, "mode": mode,
                            "facts": direct_tids, "edges": s2["model_selected_edge_ids"],
                            "needed/useful/not": f"{dist['needed']}/{dist['useful']}/{dist['not_needed']}",
                            "P_needed@K": row["P_needed@K_actual"],
                            "nDCG_10@3": row["nDCG_within_10@3"],
                            "faith": row["faithfulness_rate"],
                            "unsupp_rel": row["unsupported_relation_rate"],
                        }, ensure_ascii=False),
                        flush=True,
                    )
                consistency_summary[wid][model_name][level] = summarize_consistency(runs_by_mode)
        conn.close()

    (out_dir / "failure_cases.json").write_text(
        json.dumps(failure_cases, indent=2, ensure_ascii=False, default=str), encoding="utf-8",
    )
    summary = {
        "evaluation": "T3 Pilot Evaluation with Author-Validated Reference Labels",
        "independence_warning": (
            "PILOT-W01 (ev_3e4d36008b29595ef246, 60.19s) and PILOT-W02 (immediate 15.0s post-window) "
            "come from the same episode and adjacent time ranges. They are NOT independent events and "
            "cannot be used for statistical significance testing."
        ),
        "code_sha256": manifest_record["code_sha256"] if manifest_record else None,
        "reference_label_summary": {
            wid: {
                "unit_count": w["unit_count"],
                "label_distribution": w["label_distribution"],
                "modality_label_breakdown": w["modality_label_breakdown"],
                "annotator_pack_permutation_invariant": w["annotator_pack_permutation_invariant"],
            }
            for wid, w in ref_labels["windows"].items()
        },
        "stage1_evidence_selection": stage1_results,
        "stage2_non_llm_baselines_on_10_cards": stage2_non_llm,
        "stage2_llm_fact_selection_rows": stage2_llm_rows,
        "stage2_cross_permutation_consistency": consistency_summary,
        "failure_case_count": len(failure_cases),
    }
    (out_dir / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8",
    )
    return summary
