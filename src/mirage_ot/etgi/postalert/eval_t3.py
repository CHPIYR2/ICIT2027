"""Two-stage evaluation for T3:

Stage 1 (Evidence Selection): full atomic candidate pool -> 10 Fact Cards.
Stage 2 (LLM Fact Selection): same 10 Fact Cards -> up to K chosen facts.

Official scores require an external human-adjudicated gold file. When no gold
file is supplied, `evaluate_with_gold()` returns `status="AWAITING_HUMAN_GOLD"`
and never substitutes selector scores or model outputs as gold.
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


def ndcg_at_k(selected_ids: list[str], gold_gains: dict[str, int], k: int) -> float:
    if k <= 0:
        return 0.0
    ideal_gains = sorted((gain for gain in gold_gains.values() if gain > 0), reverse=True)[:k]
    if not ideal_gains:
        return 0.0
    idcg = sum((2**gain - 1) / math.log2(idx + 2) for idx, gain in enumerate(ideal_gains))
    if idcg <= 0:
        return 0.0
    return dcg_at_k(selected_ids, gold_gains, k) / idcg


def score_ranking(selected_ids: list[str], gold_gains: dict[str, int], *, ks: tuple[int, ...] = (5, 10)) -> dict:
    out = {}
    for k in ks:
        out[f"P@{k}"] = round(precision_at_k(selected_ids, gold_gains, k, min_gain=1), 4)
        out[f"R@{k}"] = round(recall_at_k(selected_ids, gold_gains, k, min_gain=1), 4)
        out[f"P_needed@{k}"] = round(precision_at_k(selected_ids, gold_gains, k, min_gain=2), 4)
        out[f"R_needed@{k}"] = round(recall_at_k(selected_ids, gold_gains, k, min_gain=2), 4)
        out[f"nDCG@{k}"] = round(ndcg_at_k(selected_ids, gold_gains, k), 4)
    return out


def stage1_baselines(pool: dict, prepared_exposed: list[dict], *, k: int = 10, seeds: int = 50) -> dict:
    """Stage 1: Full candidate pool -> K Fact Cards."""
    candidates = pool["candidates"]
    all_uids = [item["unit_id"] for item in candidates]
    by_score = sorted(candidates, key=lambda item: (-float(item.get("score") or 0.0), item["time"]))
    stat_global = [item["unit_id"] for item in by_score[:k]]
    quota_cards = expose_timeline(candidates, limit=k)
    uid_by_tid = {item["timeline_id"]: item["unit_id"] for item in candidates}
    stat_quota = [uid_by_tid[card["timeline_id"]] for card in quota_cards if card["timeline_id"] in uid_by_tid]
    pipeline_exposed = [canonical_unit_id(card) for card in prepared_exposed[:k]]
    random_samples = []
    for s in range(seeds):
        rng = random.Random(1000 + s)
        shuffled = list(all_uids)
        rng.shuffle(shuffled)
        random_samples.append(shuffled[:k])
    return {
        "candidate_pool_size": len(all_uids),
        "k": k,
        "statistical_role_quota_ids": stat_quota,
        "statistical_global_score_ids": stat_global,
        "pipeline_exposed_ids": pipeline_exposed,
        "random_sample_count": seeds,
        "random_samples": random_samples,
    }


def stage2_selection(exposed_cards: list[dict], timeline: list[dict], relations: list[dict],
                     model_claims: list[dict], verification: dict, *, k: int = 5) -> dict:
    """Stage 2: Same 10 exposed Fact Cards -> model's chosen facts & verification metrics."""
    uid_by_tid = {event["timeline_id"]: canonical_unit_id(event) for event in timeline}
    edge_by_id = {rel["edge_id"]: rel for rel in relations}
    exposed_uids = [canonical_unit_id(card) for card in exposed_cards]

    direct_fact_uids = []
    endpoint_fact_uids = []
    relation_claims = []
    for claim in model_claims:
        if not isinstance(claim, dict):
            continue
        fid = claim.get("fact_id") or claim.get("timeline_id")
        if fid in uid_by_tid:
            direct_fact_uids.append(uid_by_tid[fid])
        eid = claim.get("edge_id")
        if eid in edge_by_id:
            edge = edge_by_id[eid]
            for end_tid in (edge.get("source_fact_id"), edge.get("target_fact_id")):
                if end_tid in uid_by_tid:
                    endpoint_fact_uids.append(uid_by_tid[end_tid])
        if claim.get("claim_type") == "relation_claim" or eid is not None:
            relation_claims.append(claim)

    direct_fact_uids = list(dict.fromkeys(direct_fact_uids))[:k]
    combined_uids = list(dict.fromkeys([*direct_fact_uids, *endpoint_fact_uids]))[:k]

    verified = verification.get("verified") or verification.get("offline_audit_verified") or []
    rejected = verification.get("rejected") or verification.get("offline_audit_rejected") or []
    total_claims = len(model_claims)
    rejected_relations = [
        item for item in rejected
        if item.get("claim_type") == "relation_claim" or item.get("edge_id") is not None
    ]
    return {
        "exposed_count": len(exposed_uids),
        "exposed_unit_ids": exposed_uids,
        "model_direct_unit_ids": direct_fact_uids,
        "model_with_edge_endpoints_unit_ids": combined_uids,
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


def evaluate_with_gold(stage1: dict, stage2: dict, gold_labels: dict[str, str] | None = None) -> dict:
    """Compute Stage 1 and Stage 2 ranking metrics only when human gold labels are supplied."""
    if not gold_labels:
        return {
            "status": "AWAITING_HUMAN_GOLD",
            "note": "No human-annotated gold file was supplied. Selector or LLM outputs are never used as gold.",
            "stage1_summary": {
                "candidate_pool_size": stage1["candidate_pool_size"],
                "k": stage1["k"],
                "statistical_role_quota_count": len(stage1["statistical_role_quota_ids"]),
                "statistical_global_score_count": len(stage1["statistical_global_score_ids"]),
            },
            "stage2_summary": stage2,
        }
    gains = {
        uid: GAIN_MAP.get(label, 0) if isinstance(label, str) else int(label)
        for uid, label in gold_labels.items()
    }
    k1 = stage1["k"]
    random_scores = [score_ranking(sample, gains, ks=(5, k1)) for sample in stage1["random_samples"]]
    avg_random = {
        metric: round(sum(item[metric] for item in random_scores) / len(random_scores), 4)
        for metric in random_scores[0]
    } if random_scores else {}
    return {
        "status": "SCORED_AGAINST_HUMAN_GOLD",
        "gold_unit_count": len(gains),
        "gold_positive_count": sum(1 for g in gains.values() if g >= 1),
        "gold_needed_count": sum(1 for g in gains.values() if g >= 2),
        "stage1": {
            "random_mean": avg_random,
            "statistical_role_quota": score_ranking(stage1["statistical_role_quota_ids"], gains, ks=(5, k1)),
            "statistical_global_score": score_ranking(stage1["statistical_global_score_ids"], gains, ks=(5, k1)),
            "pipeline_exposed": score_ranking(stage1["pipeline_exposed_ids"], gains, ks=(5, k1)),
        },
        "stage2": {
            **stage2,
            "direct_fact_ranking": score_ranking(stage2["model_direct_unit_ids"], gains, ks=(3, 5, 10)),
            "combined_fact_ranking": score_ranking(stage2["model_with_edge_endpoints_unit_ids"], gains, ks=(3, 5, 10)),
        },
    }
