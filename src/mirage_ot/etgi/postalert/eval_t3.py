"""Two-stage evaluation for T3:

Stage 1 (Evidence Selection):
  - Full candidate pool (627 / 612 atomic units) -> 10 Fact Cards: reports
    `labeled_coverage_at_k` and `unlabeled_undetermined_count_at_k`, and marks
    full-pool Recall (and Precision when unlabeled items appear in top-K) as
    `NOT_ESTIMABLE` rather than treating unlabeled candidates as Not Needed (0).
  - Labeled candidate pool (the 22 author-validated units per window) -> 10 Fact
    Cards: computes exact P@K, P_needed@K, R@K, R_needed@K, and graded nDCG@K.

Stage 2 (LLM Fact Selection):
  - Same 10 Fact Cards -> model's directly selected Fact IDs (`model_selected_fact_ids`)
    and Edge IDs (`model_selected_edge_ids`), strictly separated from
    `system_resolved_evidence_ids`.
"""
from __future__ import annotations
import math
import random
from .explain import expose_timeline
from .select import _exclude_reason, _groups, _load, _observed_span, _score
from .timeline import build_timeline_with_lineage

GAIN_MAP = {
    "needed": 2,
    "useful": 1,
    "not_needed": 0,
    "cannot_judge": 0,
}


def build_full_candidate_pool(db, start: float, end: float, *,
                              background_start: float | None = None,
                              background_end: float | None = None) -> dict:
    """Build all non-hold atomic candidate units in the window without a top-24 cutoff."""
    background_end = start if background_end is None else background_end
    background_start = background_end if background_start is None else background_start
    incident_seconds = max(end - start, 1.0)
    background = _load(db, background_start, background_end) if background_start < background_end else []
    background_seconds = _observed_span(background, background_start, background_end)
    incident = _load(db, start, end)
    kept_rows = [row for row in incident if _exclude_reason(row) is None]
    groups = _groups(kept_rows)
    background_groups = _groups([row for row in background if _exclude_reason(row) is None])
    ranked = []
    for key, group in groups.items():
        score, detail = _score(
            key, group, background_groups.get(key),
            incident_seconds=incident_seconds, background_seconds=background_seconds,
        )
        ranked.append({"key": key, "group": group, "score": score, "score_detail": detail})
    ranked.sort(key=lambda item: (-item["score"], item["group"]["time"]))
    pseudo_selection = {"selected": ranked}
    events, lineage = build_timeline_with_lineage(pseudo_selection)
    for event in events:
        uid = canonical_unit_id(event)
        event["unit_id"] = uid
    unit_lineage = {event["unit_id"]: lineage[event["timeline_id"]] for event in events}
    return {
        "incident_start": start,
        "incident_end": end,
        "background_start": background_start,
        "background_end": background_end,
        "candidate_count": len(events),
        "candidates": events,
        "unit_lineage": unit_lineage,
    }


def canonical_unit_id(event: dict) -> str:
    """Deterministic unit key independent of timeline numbering."""
    kind = (event.get("source") or {}).get("kind") or event.get("kind") or "unknown"
    entity = str(event.get("entity") or "")
    ca_ioa = str(event.get("ca_ioa") or "")
    return f"{kind}|{entity}|{ca_ioa}" if ca_ioa else f"{kind}|{entity}"


def precision_at_k(selected_ids: list[str], gold_gains: dict[str, int], k: int, *, min_gain: int = 1) -> float:
    if k <= 0:
        return 0.0
    top_k = list(dict.fromkeys(selected_ids))[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for uid in top_k if gold_gains.get(uid, 0) >= min_gain)
    return hits / len(top_k)


def recall_at_k(selected_ids: list[str], gold_gains: dict[str, int], k: int, *, min_gain: int = 1) -> float:
    relevant = {uid for uid, gain in gold_gains.items() if gain >= min_gain}
    if not relevant or k <= 0:
        return 0.0
    top_k = list(dict.fromkeys(selected_ids))[:k]
    hits = sum(1 for uid in top_k if uid in relevant)
    return hits / len(relevant)


def dcg_at_k(selected_ids: list[str], gold_gains: dict[str, int], k: int) -> float:
    top_k = list(dict.fromkeys(selected_ids))[:k]
    total = 0.0
    for idx, uid in enumerate(top_k):
        gain = gold_gains.get(uid, 0)
        if gain > 0:
            total += (2**gain - 1) / math.log2(idx + 2)
    return total


def ndcg_at_k(selected_ids: list[str], gold_gains: dict[str, int], k: int, *,
              ideal_pool_ids: set[str] | None = None) -> float:
    if k <= 0:
        return 0.0
    pool_gains = [
        gain for uid, gain in gold_gains.items()
        if gain > 0 and (ideal_pool_ids is None or uid in ideal_pool_ids)
    ]
    ideal_gains = sorted(pool_gains, reverse=True)[:k]
    if not ideal_gains:
        return 0.0
    idcg = sum((2**gain - 1) / math.log2(idx + 2) for idx, gain in enumerate(ideal_gains))
    if idcg <= 0:
        return 0.0
    return dcg_at_k(selected_ids, gold_gains, k) / idcg


def label_distribution(selected_ids: list[str], gold_gains: dict[str, int], k: int | None = None) -> dict:
    top_k = list(dict.fromkeys(selected_ids))
    if k is not None:
        top_k = top_k[:k]
    needed = sum(1 for uid in top_k if gold_gains.get(uid) == 2)
    useful = sum(1 for uid in top_k if gold_gains.get(uid) == 1)
    not_needed = sum(1 for uid in top_k if uid in gold_gains and gold_gains.get(uid) == 0)
    unlabeled = sum(1 for uid in top_k if uid not in gold_gains)
    return {
        "selected_count": len(top_k),
        "needed": needed,
        "useful": useful,
        "not_needed": not_needed,
        "unlabeled": unlabeled,
        "labeled_count": len(top_k) - unlabeled,
        "labeled_coverage": round((len(top_k) - unlabeled) / len(top_k), 4) if top_k else 0.0,
    }


def score_ranking(selected_ids: list[str], gold_gains: dict[str, int], *,
                  ks: tuple[int, ...] = (5, 10), ideal_pool_ids: set[str] | None = None) -> dict:
    out = {}
    for k in ks:
        out[f"P@{k}"] = round(precision_at_k(selected_ids, gold_gains, k, min_gain=1), 4)
        out[f"R@{k}"] = round(recall_at_k(selected_ids, gold_gains, k, min_gain=1), 4)
        out[f"P_needed@{k}"] = round(precision_at_k(selected_ids, gold_gains, k, min_gain=2), 4)
        out[f"R_needed@{k}"] = round(recall_at_k(selected_ids, gold_gains, k, min_gain=2), 4)
        out[f"nDCG@{k}"] = round(ndcg_at_k(selected_ids, gold_gains, k, ideal_pool_ids=ideal_pool_ids), 4)
    return out


def score_full_pool_with_partial_labels(selected_ids: list[str], gold_gains: dict[str, int],
                                        total_pool_size: int, *, ks: tuple[int, ...] = (5, 10)) -> dict:
    """Evaluate a ranking drawn from a partially labeled full pool without treating unlabeled items as 0."""
    unlabeled_total = max(total_pool_size - len(gold_gains), 0)
    out = {
        "total_pool_size": total_pool_size,
        "labeled_pool_size": len(gold_gains),
        "unlabeled_pool_size": unlabeled_total,
    }
    for k in ks:
        top_k = list(dict.fromkeys(selected_ids))[:k]
        dist = label_distribution(top_k, gold_gains, k=k)
        labeled_in_top_k = [uid for uid in top_k if uid in gold_gains]
        out[f"labeled_coverage@{k}"] = dist["labeled_coverage"]
        out[f"labeled_count@{k}"] = dist["labeled_count"]
        out[f"unlabeled_undetermined_count@{k}"] = dist["unlabeled"]
        out[f"distribution@{k}"] = dist
        out[f"full_pool_R@{k}"] = "NOT_ESTIMABLE" if unlabeled_total > 0 else round(
            recall_at_k(top_k, gold_gains, k, min_gain=1), 4
        )
        out[f"full_pool_R_needed@{k}"] = "NOT_ESTIMABLE" if unlabeled_total > 0 else round(
            recall_at_k(top_k, gold_gains, k, min_gain=2), 4
        )
        if dist["unlabeled"] == 0:
            out[f"P@{k}"] = round(precision_at_k(top_k, gold_gains, k, min_gain=1), 4)
            out[f"P_needed@{k}"] = round(precision_at_k(top_k, gold_gains, k, min_gain=2), 4)
            out[f"nDCG_within_labeled@{k}"] = round(ndcg_at_k(top_k, gold_gains, k), 4)
        else:
            out[f"P@{k}"] = "NOT_ESTIMABLE"
            out[f"P_needed@{k}"] = "NOT_ESTIMABLE"
            out[f"nDCG_within_labeled@{k}"] = "NOT_ESTIMABLE"
            out[f"P_among_labeled_subset@{k}"] = (
                round(sum(1 for uid in labeled_in_top_k if gold_gains[uid] >= 1) / len(labeled_in_top_k), 4)
                if labeled_in_top_k else None
            )
            out[f"P_needed_among_labeled_subset@{k}"] = (
                round(sum(1 for uid in labeled_in_top_k if gold_gains[uid] >= 2) / len(labeled_in_top_k), 4)
                if labeled_in_top_k else None
            )
    return out


def stage1_baselines(pool: dict, prepared_exposed: list[dict], *,
                     prepared_timeline: list[dict] | None = None,
                     k: int = 10, seeds: int = 50) -> dict:
    """Stage 1 baselines on both the full pool and the 22-unit labeled timeline pool."""
    candidates = pool["candidates"]
    all_uids = [item["unit_id"] for item in candidates]
    by_score_full = sorted(candidates, key=lambda item: (-float(item.get("score") or 0.0), item["time"]))
    stat_global_full = [item["unit_id"] for item in by_score_full[:k]]
    quota_cards = expose_timeline(candidates, limit=k)
    uid_by_tid = {item["timeline_id"]: item["unit_id"] for item in candidates}
    stat_quota_full = [uid_by_tid[card["timeline_id"]] for card in quota_cards if card["timeline_id"] in uid_by_tid]
    pipeline_exposed = [canonical_unit_id(card) for card in prepared_exposed[:k]]

    random_full_samples = []
    for s in range(seeds):
        rng = random.Random(1000 + s)
        shuffled = list(all_uids)
        rng.shuffle(shuffled)
        random_full_samples.append(shuffled[:k])

    labeled_pool_events = prepared_timeline if prepared_timeline is not None else []
    labeled_uids = [canonical_unit_id(e) for e in labeled_pool_events]
    by_score_labeled = sorted(labeled_pool_events, key=lambda item: (-float(item.get("score") or 0.0), item["time"]))
    stat_global_labeled = [canonical_unit_id(item) for item in by_score_labeled[:k]]
    random_labeled_samples = []
    if labeled_uids:
        for s in range(seeds):
            rng = random.Random(2000 + s)
            shuffled = list(labeled_uids)
            rng.shuffle(shuffled)
            random_labeled_samples.append(shuffled[:k])

    return {
        "candidate_pool_size": len(all_uids),
        "labeled_pool_size": len(labeled_uids),
        "k": k,
        "statistical_role_quota_ids": pipeline_exposed if pipeline_exposed else stat_quota_full,
        "statistical_global_score_full_pool_ids": stat_global_full,
        "statistical_global_score_labeled_pool_ids": stat_global_labeled,
        "pipeline_exposed_ids": pipeline_exposed,
        "random_sample_count": seeds,
        "random_samples": random_full_samples,
        "random_labeled_pool_samples": random_labeled_samples,
    }


def stage2_selection(exposed_cards: list[dict], timeline: list[dict], relations: list[dict],
                     model_claims: list[dict], verification: dict, *, k: int = 6) -> dict:
    """Stage 2: Same 10 exposed Fact Cards -> model's directly chosen facts & verification metrics."""
    uid_by_tid = {event["timeline_id"]: canonical_unit_id(event) for event in timeline}
    edge_by_id = {rel["edge_id"]: rel for rel in relations}
    exposed_uids = [canonical_unit_id(card) for card in exposed_cards]

    direct_fact_uids = []
    direct_fact_tids = []
    endpoint_fact_uids = []
    selected_edge_ids = []
    relation_claims = []
    for claim in model_claims:
        if not isinstance(claim, dict):
            continue
        fid = claim.get("fact_id") or claim.get("timeline_id")
        if fid in uid_by_tid:
            direct_fact_tids.append(fid)
            direct_fact_uids.append(uid_by_tid[fid])
        eid = claim.get("edge_id")
        if eid in edge_by_id:
            selected_edge_ids.append(eid)
            edge = edge_by_id[eid]
            for end_tid in (edge.get("source_fact_id"), edge.get("target_fact_id")):
                if end_tid in uid_by_tid:
                    endpoint_fact_uids.append(uid_by_tid[end_tid])
        if claim.get("claim_type") == "relation_claim" or eid is not None:
            relation_claims.append(claim)

    direct_fact_tids = list(dict.fromkeys(direct_fact_tids))[:k]
    direct_fact_uids = list(dict.fromkeys(direct_fact_uids))[:k]
    selected_edge_ids = list(dict.fromkeys(selected_edge_ids))[:k]
    combined_uids = list(dict.fromkeys([*direct_fact_uids, *endpoint_fact_uids]))[:k]

    verified = verification.get("verified") or verification.get("offline_audit_verified") or []
    rejected = verification.get("rejected") or verification.get("offline_audit_rejected") or []
    total_claims = len(model_claims)
    rejected_relations = [
        item for item in rejected
        if item.get("claim_type") == "relation_claim" or item.get("edge_id") is not None
    ]
    sys_resolved = [
        ev_id
        for item in (*verified, *rejected)
        for ev_id in (item.get("system_resolved_evidence_ids") or [])
    ]
    return {
        "exposed_count": len(exposed_uids),
        "exposed_unit_ids": exposed_uids,
        "model_selected_fact_ids": direct_fact_tids,
        "model_direct_unit_ids": direct_fact_uids,
        "model_selected_edge_ids": selected_edge_ids,
        "auxiliary_with_edge_endpoints_unit_ids": combined_uids,
        "system_resolved_evidence_id_count": len(set(sys_resolved)),
        "total_claims": total_claims,
        "verified_claims": len(verified),
        "rejected_claims": len(rejected),
        "faithfulness_rate": round(len(verified) / total_claims, 4) if total_claims else None,
        "relation_claim_count": len(relation_claims),
        "unsupported_relation_count": len(rejected_relations),
        "unsupported_relation_rate": (
            round(len(rejected_relations) / len(relation_claims), 4) if relation_claims else None
        ),
        "abstained": total_claims == 0,
    }


def evaluate_with_gold(stage1: dict, stage2: dict, gold_labels: dict[str, str | int] | None = None) -> dict:
    """Compute Stage 1 and Stage 2 ranking metrics only when human/author gold labels are supplied."""
    if not gold_labels:
        return {
            "status": "AWAITING_HUMAN_GOLD",
            "note": "No human-annotated gold file was supplied. Selector or LLM outputs are never used as gold.",
            "stage1_summary": {
                "candidate_pool_size": stage1["candidate_pool_size"],
                "k": stage1["k"],
                "statistical_role_quota_count": len(stage1["statistical_role_quota_ids"]),
                "statistical_global_score_count": len(stage1.get("statistical_global_score_full_pool_ids") or []),
            },
            "stage2_summary": stage2,
        }
    gains = {
        uid: GAIN_MAP.get(label.lower(), 0) if isinstance(label, str) else int(label)
        for uid, label in gold_labels.items()
    }
    k1 = stage1["k"]
    total_pool = stage1["candidate_pool_size"]

    # 1. Full-pool evaluation (strictly marks NOT_ESTIMABLE where unlabeled items prevent valid estimation)
    full_quota = score_full_pool_with_partial_labels(
        stage1["statistical_role_quota_ids"], gains, total_pool, ks=(5, k1),
    )
    full_global = score_full_pool_with_partial_labels(
        stage1.get("statistical_global_score_full_pool_ids") or [], gains, total_pool, ks=(5, k1),
    )
    rand_full_cov5 = [
        label_distribution(sample, gains, k=5)["labeled_coverage"] for sample in stage1["random_samples"]
    ]
    rand_full_cov10 = [
        label_distribution(sample, gains, k=k1)["labeled_coverage"] for sample in stage1["random_samples"]
    ]
    full_random_summary = {
        "total_pool_size": total_pool,
        "labeled_pool_size": len(gains),
        "unlabeled_pool_size": max(total_pool - len(gains), 0),
        "mean_labeled_coverage@5": round(sum(rand_full_cov5) / len(rand_full_cov5), 4) if rand_full_cov5 else 0.0,
        f"mean_labeled_coverage@{k1}": round(sum(rand_full_cov10) / len(rand_full_cov10), 4) if rand_full_cov10 else 0.0,
        f"mean_unlabeled_undetermined_count@{k1}": round(
            sum(label_distribution(sample, gains, k=k1)["unlabeled"] for sample in stage1["random_samples"])
            / len(stage1["random_samples"]), 4
        ) if stage1["random_samples"] else 0.0,
        "P@5": "NOT_ESTIMABLE",
        f"P@{k1}": "NOT_ESTIMABLE",
        "full_pool_R@5": "NOT_ESTIMABLE",
        f"full_pool_R@{k1}": "NOT_ESTIMABLE",
        f"nDCG@{k1}": "NOT_ESTIMABLE",
    }

    # 2. Within-labeled-pool evaluation (exact P@K, R@K, nDCG@K over the 22 author-validated units)
    labeled_random_samples = stage1.get("random_labeled_pool_samples") or []
    labeled_random_scores = [score_ranking(sample, gains, ks=(5, k1)) for sample in labeled_random_samples]
    avg_labeled_random = {
        metric: round(sum(item[metric] for item in labeled_random_scores) / len(labeled_random_scores), 4)
        for metric in labeled_random_scores[0]
    } if labeled_random_scores else {}

    global_labeled_ids = stage1.get("statistical_global_score_labeled_pool_ids") or []
    quota_ids = stage1["statistical_role_quota_ids"]

    exposed_set = set(stage2["exposed_unit_ids"])
    direct_uids = stage2["model_direct_unit_ids"]
    k_sel = max(len(direct_uids), 1)
    return {
        "status": "SCORED_AGAINST_HUMAN_GOLD",
        "gold_unit_count": len(gains),
        "gold_positive_count": sum(1 for g in gains.values() if g >= 1),
        "gold_needed_count": sum(1 for g in gains.values() if g >= 2),
        "gold_useful_count": sum(1 for g in gains.values() if g == 1),
        "gold_not_needed_count": sum(1 for g in gains.values() if g == 0),
        "stage1_full_pool": {
            "random_50_seeds": full_random_summary,
            "statistical_global_score": full_global,
            "statistical_role_quota": full_quota,
        },
        "stage1_within_labeled_pool": {
            "random_50_seeds_mean": avg_labeled_random,
            "statistical_global_score": score_ranking(global_labeled_ids, gains, ks=(5, k1)) if global_labeled_ids else {},
            "statistical_global_score_distribution@10": label_distribution(global_labeled_ids, gains, k=k1),
            "statistical_role_quota": score_ranking(quota_ids, gains, ks=(5, k1)),
            "statistical_role_quota_distribution@10": label_distribution(quota_ids, gains, k=k1),
        },
        "stage2": {
            **stage2,
            "direct_fact_distribution": label_distribution(direct_uids, gains),
            "direct_fact_ranking_within_exposed_10": score_ranking(
                direct_uids, gains, ks=(k_sel, 3, 5), ideal_pool_ids=exposed_set,
            ),
            "direct_fact_ranking_within_labeled_22": score_ranking(
                direct_uids, gains, ks=(k_sel, 3, 5),
            ),
            "auxiliary_with_edge_endpoints_distribution": label_distribution(
                stage2["auxiliary_with_edge_endpoints_unit_ids"], gains,
            ),
        },
    }
