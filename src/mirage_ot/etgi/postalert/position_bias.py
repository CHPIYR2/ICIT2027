"""Position and ID-number bias diagnostic over a fixed 10-Fact-Card set.

Given a prepared window, the 10 exposed Fact Cards and 8 exposed candidate
relations are held strictly constant in content. Four permutations are tested:

1. `original`: original order and canonical IDs (`TL...`, `R...`).
2. `reversed`: reversed list order, canonical IDs preserved.
3. `seeded_shuffle`: deterministic shuffle (`seed=42`) of list order, canonical IDs preserved.
4. `remapped_ids`: reversible bijective ID remapping (`TL... <-> TL101..TL110`,
   `R... <-> R0101..R0108`) where electrical and later cards receive the lowest
   ID numbers (`TL101`, `TL102`, ...), while preserving all card content and
   applying the exact same verifier after inverse mapping back to canonical IDs.
"""
from __future__ import annotations
import copy
import json
import random
from pathlib import Path
from .explain import CLAIM_FORMAT_TYPED, SYSTEM_TYPED_REFS, _object
from .verify import verify_claims

PERMUTATIONS = ("original", "reversed", "seeded_shuffle", "remapped_ids")


def permute_exposed(exposed_cards: list[dict], exposed_relations: list[dict],
                    mode: str, *, shuffle_seed: int = 42) -> tuple[list[dict], list[dict], dict]:
    """Return (cards, relations, mapping_record) for one permutation mode."""
    if mode not in PERMUTATIONS:
        raise ValueError(f"Unknown permutation mode: {mode}")
    cards = copy.deepcopy(exposed_cards)
    relations = copy.deepcopy(exposed_relations)
    orig_card_order = [card["timeline_id"] for card in cards]
    orig_edge_order = [rel["edge_id"] for rel in relations]

    forward_fact = {tid: tid for tid in orig_card_order}
    inverse_fact = {tid: tid for tid in orig_card_order}
    forward_edge = {eid: eid for eid in orig_edge_order}
    inverse_edge = {eid: eid for eid in orig_edge_order}

    if mode == "original":
        pass
    elif mode == "reversed":
        cards.reverse()
        relations.reverse()
    elif mode == "seeded_shuffle":
        rng = random.Random(shuffle_seed)
        rng.shuffle(cards)
        rng.shuffle(relations)
    elif mode == "remapped_ids":
        # Assign lowest remapped IDs (TL101, TL102, ...) to electrical cards first, then reverse order of remaining
        electrical_first = sorted(
            cards,
            key=lambda c: (0 if c.get("modality") == "electrical" else 1, -orig_card_order.index(c["timeline_id"])),
        )
        forward_fact = {}
        inverse_fact = {}
        for idx, card in enumerate(electrical_first, start=1):
            canon_id = card["timeline_id"]
            remap_id = f"TL{100 + idx:03d}"
            forward_fact[canon_id] = remap_id
            inverse_fact[remap_id] = canon_id
        forward_edge = {}
        inverse_edge = {}
        for idx, rel in enumerate(reversed(relations), start=1):
            canon_eid = rel["edge_id"]
            remap_eid = f"R{100 + idx:04d}"
            forward_edge[canon_eid] = remap_eid
            inverse_edge[remap_eid] = canon_eid
        for card in cards:
            card["timeline_id"] = forward_fact[card["timeline_id"]]
        for rel in relations:
            rel["edge_id"] = forward_edge[rel["edge_id"]]
            if rel.get("source_fact_id") in forward_fact:
                rel["source_fact_id"] = forward_fact[rel["source_fact_id"]]
            if rel.get("target_fact_id") in forward_fact:
                rel["target_fact_id"] = forward_fact[rel["target_fact_id"]]

    display_card_order_canonical = [inverse_fact[card["timeline_id"]] for card in cards]
    display_edge_order_canonical = [inverse_edge[rel["edge_id"]] for rel in relations]
    mapping = {
        "mode": mode,
        "shuffle_seed": shuffle_seed,
        "original_card_order_canonical": orig_card_order,
        "display_card_order_canonical": display_card_order_canonical,
        "display_card_order_shown": [card["timeline_id"] for card in cards],
        "original_edge_order_canonical": orig_edge_order,
        "display_edge_order_canonical": display_edge_order_canonical,
        "display_edge_order_shown": [rel["edge_id"] for rel in relations],
        "forward_fact_map": forward_fact,
        "inverse_fact_map": inverse_fact,
        "forward_edge_map": forward_edge,
        "inverse_edge_map": inverse_edge,
    }
    return cards, relations, mapping


def unmap_claims(raw_claims: list[dict], mapping: dict) -> list[dict]:
    """Map model-emitted fact_id / edge_id back to canonical IDs via inverse map."""
    inv_fact = mapping["inverse_fact_map"]
    inv_edge = mapping["inverse_edge_map"]
    canonical_claims = []
    for raw in raw_claims:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        fid = item.get("fact_id") or item.get("timeline_id")
        if fid:
            item["raw_selected_fact_id"] = fid
            item["fact_id"] = inv_fact.get(fid, fid)
        eid = item.get("edge_id")
        if eid:
            item["raw_selected_edge_id"] = eid
            item["edge_id"] = inv_edge.get(eid, eid)
        canonical_claims.append(item)
    return canonical_claims


def run_single_permutation(db, llm, prepared: dict, mode: str, *, level: str = "B4",
                           shuffle_seed: int = 42, num_predict: int = 512,
                           num_ctx: int = 8192, seed: int = 1, out_dir: Path | None = None) -> dict:
    cards, relations, mapping = permute_exposed(
        prepared["exposed_timeline"], prepared["exposed_relations"], mode, shuffle_seed=shuffle_seed,
    )
    body = {
        "incident_start": prepared["incident_start"],
        "incident_end": prepared["incident_end"],
        "timeline": cards,
    }
    if level in ("B3", "B4"):
        body["candidate_relations"] = relations
    messages = [
        {"role": "system", "content": SYSTEM_TYPED_REFS},
        {"role": "user", "content": json.dumps(body, default=str)},
    ]
    turn = llm.chat(
        messages, tools=None, temperature=0, seed=seed,
        num_predict=num_predict, num_ctx=num_ctx, response_format=CLAIM_FORMAT_TYPED,
    )
    parsed = _object(turn.content, allow_salvage=False)
    partial = bool(turn.done_reason == "length" or parsed.get("json_truncated"))
    raw_claims = [c for c in (parsed.get("claims") or []) if isinstance(c, dict)] if not partial else []
    canonical_claims = unmap_claims(raw_claims, mapping)
    checked = verify_claims(
        db, canonical_claims, prepared["relations"], prepared["timeline"], lineage=prepared["lineage"],
    )
    metrics = _measure_selection(prepared, mapping, raw_claims, canonical_claims, checked)
    record = {
        "mode": mode,
        "level": level,
        "model": getattr(turn, "model", "") or getattr(llm, "model_name", ""),
        "prompt_tokens": turn.prompt_tokens,
        "completion_tokens": turn.completion_tokens,
        "done_reason": turn.done_reason,
        "partial_output": partial,
        "abstain": bool(parsed.get("abstain")) and not partial and not raw_claims,
        "raw_claims": raw_claims,
        "canonical_claims": canonical_claims,
        "verification": checked,
        "metrics": metrics,
        "mapping": mapping,
        "prompt_messages": messages,
        "raw_output": turn.content,
    }
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "prompt.json").write_text(json.dumps(messages, indent=2, default=str), encoding="utf-8")
        (out_dir / "raw_output.txt").write_text(turn.content or "", encoding="utf-8")
        (out_dir / "id_mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
        (out_dir / "verification.json").write_text(json.dumps(checked, indent=2, default=str), encoding="utf-8")
        (out_dir / "trace.json").write_text(
            json.dumps({k: v for k, v in record.items() if k != "prompt_messages"}, indent=2, default=str),
            encoding="utf-8",
        )
    return record


def _measure_selection(prepared: dict, mapping: dict, raw_claims: list[dict],
                       canonical_claims: list[dict], checked: dict) -> dict:
    timeline_by_id = {e["timeline_id"]: e for e in prepared["timeline"]}
    edge_by_id = {r["edge_id"]: r for r in prepared["relations"]}
    orig_order = mapping["original_card_order_canonical"]
    disp_order = mapping["display_card_order_canonical"]
    shown_order = mapping["display_card_order_shown"]

    direct_canon_facts = []
    raw_shown_facts = []
    canon_edges = []
    all_referenced_facts = []
    for raw, canon in zip(raw_claims, canonical_claims):
        rf = raw.get("fact_id") or raw.get("timeline_id")
        cf = canon.get("fact_id") or canon.get("timeline_id")
        if cf in timeline_by_id:
            direct_canon_facts.append(cf)
            all_referenced_facts.append(cf)
        if rf:
            raw_shown_facts.append(rf)
        ce = canon.get("edge_id")
        if ce in edge_by_id:
            canon_edges.append(ce)
            edge = edge_by_id[ce]
            for end_tid in (edge.get("source_fact_id"), edge.get("target_fact_id")):
                if end_tid in timeline_by_id:
                    all_referenced_facts.append(end_tid)

    direct_canon_facts = list(dict.fromkeys(direct_canon_facts))
    all_referenced_facts = list(dict.fromkeys(all_referenced_facts))
    canon_edges = list(dict.fromkeys(canon_edges))

    orig_positions = [orig_order.index(fid) + 1 for fid in direct_canon_facts if fid in orig_order]
    disp_positions = [disp_order.index(fid) + 1 for fid in direct_canon_facts if fid in disp_order]

    def mod_split(fids: list[str]) -> dict:
        net = sum(1 for fid in fids if (timeline_by_id[fid].get("source") or {}).get("modality") == "network")
        elec = sum(1 for fid in fids if (timeline_by_id[fid].get("source") or {}).get("modality") == "electrical")
        total = len(fids)
        return {
            "network": net,
            "electrical": elec,
            "total": total,
            "network_ratio": round(net / total, 4) if total else None,
            "electrical_ratio": round(elec / total, 4) if total else None,
        }

    smallest_shown = min(shown_order) if shown_order else None
    return {
        "canonical_fact_ids": direct_canon_facts,
        "raw_shown_fact_ids": raw_shown_facts,
        "canonical_edge_ids": canon_edges,
        "all_referenced_canonical_fact_ids": all_referenced_facts,
        "original_positions_1based": orig_positions,
        "display_positions_1based": disp_positions,
        "chose_display_pos_1": 1 in disp_positions,
        "chose_original_pos_1": 1 in orig_positions,
        "chose_smallest_shown_id": (smallest_shown in raw_shown_facts) if smallest_shown else False,
        "direct_modality": mod_split(direct_canon_facts),
        "all_referenced_modality": mod_split(all_referenced_facts),
        "verified_count": len(checked["verified"]),
        "rejected_count": len(checked["rejected"]),
    }


def summarize_consistency(runs_by_mode: dict[str, dict]) -> dict:
    """Compute cross-permutation agreement over canonical Fact IDs and Edge IDs."""
    modes = [m for m in PERMUTATIONS if m in runs_by_mode]
    fact_sets = {m: set(runs_by_mode[m]["metrics"]["canonical_fact_ids"]) for m in modes}
    ref_sets = {m: set(runs_by_mode[m]["metrics"]["all_referenced_canonical_fact_ids"]) for m in modes}
    edge_sets = {m: set(runs_by_mode[m]["metrics"]["canonical_edge_ids"]) for m in modes}

    def pairwise_jaccard(sets_by_mode: dict[str, set[str]]) -> tuple[float, dict[str, float]]:
        pairs = {}
        for i, m1 in enumerate(modes):
            for m2 in modes[i + 1:]:
                a, b = sets_by_mode[m1], sets_by_mode[m2]
                score = 1.0 if (not a and not b) else (len(a & b) / len(a | b) if (a | b) else 0.0)
                pairs[f"{m1}__vs__{m2}"] = round(score, 4)
        mean_val = round(sum(pairs.values()) / len(pairs), 4) if pairs else 0.0
        return mean_val, pairs

    direct_mean, direct_pairs = pairwise_jaccard(fact_sets)
    ref_mean, ref_pairs = pairwise_jaccard(ref_sets)
    edge_mean, edge_pairs = pairwise_jaccard(edge_sets)
    first_set = next(iter(fact_sets.values())) if fact_sets else set()
    exact_match = all(s == first_set for s in fact_sets.values())
    return {
        "modes_compared": modes,
        "canonical_facts_by_mode": {m: sorted(fact_sets[m]) for m in modes},
        "canonical_edges_by_mode": {m: sorted(edge_sets[m]) for m in modes},
        "display_positions_by_mode": {m: runs_by_mode[m]["metrics"]["display_positions_1based"] for m in modes},
        "original_positions_by_mode": {m: runs_by_mode[m]["metrics"]["original_positions_1based"] for m in modes},
        "direct_fact_jaccard_mean": direct_mean,
        "direct_fact_jaccard_pairs": direct_pairs,
        "all_referenced_fact_jaccard_mean": ref_mean,
        "all_referenced_fact_jaccard_pairs": ref_pairs,
        "edge_jaccard_mean": edge_mean,
        "edge_jaccard_pairs": edge_pairs,
        "exact_canonical_fact_match_all_modes": exact_match,
        "display_pos_1_selection_rate": round(
            sum(1 for m in modes if runs_by_mode[m]["metrics"]["chose_display_pos_1"]) / len(modes), 4
        ) if modes else 0.0,
        "original_pos_1_selection_rate": round(
            sum(1 for m in modes if runs_by_mode[m]["metrics"]["chose_original_pos_1"]) / len(modes), 4
        ) if modes else 0.0,
        "smallest_shown_id_selection_rate": round(
            sum(1 for m in modes if runs_by_mode[m]["metrics"]["chose_smallest_shown_id"]) / len(modes), 4
        ) if modes else 0.0,
    }


def run_position_bias_suite(cases: list[dict], out_dir: Path, *,
                            model: str = "qwen3.5:9b-q4_K_M",
                            levels: tuple[str, ...] = ("B2", "B4"),
                            endpoint: str = "http://127.0.0.1:11434") -> dict:
    from ..agent.ollama import OllamaClient
    from ..evidence.index import open_indexed
    from ..evidence.queries import EvidenceDB
    from .pipeline import prepare, run_manifest
    from .runner import background, window

    if out_dir.exists():
        raise FileExistsError(f"{out_dir} exists; refusing to overwrite")
    out_dir.mkdir(parents=True)
    llm = OllamaClient(model, endpoint=endpoint)
    all_case_summaries = {}
    flat_rows = []
    manifest_sha = None

    for case in cases:
        conn, meta = open_indexed(Path(case["db"]))
        start, end = window(case, meta)
        bg_start, bg_end = background(case, meta, start, 15.0)
        db = EvidenceDB(conn, incident_start=start, incident_end=end)
        prepared = prepare(db, start, end, background_start=bg_start, background_end=bg_end, limit=24)
        if manifest_sha is None:
            manifest_sha = run_manifest(db, diagnostic="position_bias")["code_sha256"]

        case_dir = out_dir / case["name"]
        case_dir.mkdir()
        (case_dir / "canonical_exposed_timeline.json").write_text(
            json.dumps(prepared["exposed_timeline"], indent=2, default=str), encoding="utf-8",
        )
        (case_dir / "canonical_exposed_relations.json").write_text(
            json.dumps(prepared["exposed_relations"], indent=2, default=str), encoding="utf-8",
        )
        all_case_summaries[case["name"]] = {}
        for level in levels:
            runs_by_mode = {}
            for mode in PERMUTATIONS:
                sub = case_dir / f"{level}_{mode}"
                rec = run_single_permutation(
                    db, llm, prepared, mode, level=level, shuffle_seed=42, out_dir=sub,
                )
                runs_by_mode[mode] = rec
                m = rec["metrics"]
                flat_rows.append({
                    "case": case["name"],
                    "level": level,
                    "mode": mode,
                    "canonical_fact_ids": m["canonical_fact_ids"],
                    "raw_shown_fact_ids": m["raw_shown_fact_ids"],
                    "canonical_edge_ids": m["canonical_edge_ids"],
                    "original_positions_1based": m["original_positions_1based"],
                    "display_positions_1based": m["display_positions_1based"],
                    "chose_display_pos_1": m["chose_display_pos_1"],
                    "chose_original_pos_1": m["chose_original_pos_1"],
                    "chose_smallest_shown_id": m["chose_smallest_shown_id"],
                    "direct_modality": m["direct_modality"],
                    "all_referenced_modality": m["all_referenced_modality"],
                    "verified_count": m["verified_count"],
                    "rejected_count": m["rejected_count"],
                    "prompt_tokens": rec["prompt_tokens"],
                    "completion_tokens": rec["completion_tokens"],
                })
                print(json.dumps(flat_rows[-1], default=str), flush=True)
            all_case_summaries[case["name"]][level] = summarize_consistency(runs_by_mode)
        conn.close()

    summary = {
        "model": model,
        "code_sha256": manifest_sha,
        "permutations": list(PERMUTATIONS),
        "levels": list(levels),
        "consistency_by_case_and_level": all_case_summaries,
        "rows": flat_rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary

