"""Phase 3: Evidence-Constrained Storyline Reconstruction via Bounded Beam Search.

Searches over the Phase 2 Event-Level Temporal Graph to build verifiable
incident storylines while enforcing:
1. Source-deduplicated evidence counting: IEC-104 points and their derived IPAL
   state updates (`shared_source_ipal_transcription`), or sibling objects in the
   same Ethernet frame (`same_iec104_frame`), share a source container and are
   never double-counted as independent support.
2. Strict separation of confirmed/supported spine steps (`observed_fact` and
   same-device `supported_inference`) from unresolved cross-entity candidate
   branches (`temporal_cooccurrence`).
3. Explicit preservation of incomplete storylines, missing protocol stages
   (`evidence_gaps`), competing hypotheses (`competing_hypotheses`), and
   unconnected observations.
"""
from __future__ import annotations

SPINE_CATEGORIES = {
    "direct_protocol_relation",
    "measurement_state_transition",
    "inference_hypothesis",
    "shared_source",
}

EDGE_WEIGHT = {
    "direct_protocol_relation": 3.0,
    "measurement_state_transition": 2.5,
    "inference_hypothesis": 2.5,
    "shared_source": 0.5,
}


def reconstruct_storylines(
    event_graph: dict,
    tx_result: dict,
    *,
    beam_width: int = 4,
    max_depth: int = 6,
) -> dict:
    nodes_by_id = {n["fact_id"]: n for n in event_graph["nodes"]}
    adj_spine: dict[str, list[dict]] = {}
    adj_cooc: dict[str, list[dict]] = {}
    for edge in event_graph["edges"]:
        src = edge["source_fact_id"]
        if edge["relation_category"] in SPINE_CATEGORIES:
            adj_spine.setdefault(src, []).append(edge)
        elif edge["relation_category"] == "temporal_cooccurrence":
            adj_cooc.setdefault(src, []).append(edge)

    storylines: list[dict] = []
    used_spine_fids: set[str] = set()

    # 1. Build transaction-anchored storylines via bounded beam search
    tx_by_id = {tx["transaction_id"]: tx for tx in (tx_result.get("transactions") or [])}
    cmd_anchors = [
        n for n in event_graph["nodes"]
        if n["role"] == "command_activation"
    ]
    for idx, anchor in enumerate(cmd_anchors, start=1):
        sl_id = f"SL{idx:03d}"
        tx = tx_by_id.get(anchor.get("transaction_id"))
        best_path, alt_paths = _beam_search_spine(
            anchor["fact_id"], nodes_by_id, adj_spine,
            beam_width=beam_width, max_depth=max_depth,
        )
        # Also include any pre_command_measurement linked into the post_command_measurement on this transaction
        pre_step = _find_pre_measurement_step(best_path["node_ids"], nodes_by_id, event_graph["edges"])
        if pre_step is not None:
            best_path["node_ids"] = [pre_step["source_fact_id"], *best_path["node_ids"]]
            best_path["edges"] = [pre_step, *best_path["edges"]]
            best_path["containers"] |= _informative_containers(nodes_by_id[pre_step["source_fact_id"]])
            best_path["independent_edge_count"] += 1
            best_path["score"] = round(best_path["score"] + EDGE_WEIGHT["measurement_state_transition"], 4)

        used_spine_fids.update(best_path["node_ids"])
        cooc_branches = _collect_competing_cooccurrence_branches(
            best_path["node_ids"], nodes_by_id, adj_cooc,
        )
        storylines.append(
            _format_storyline(
                sl_id, anchor, best_path, alt_paths, cooc_branches,
                nodes_by_id=nodes_by_id, tx=tx,
            )
        )

    # 2. If the window has no control transactions (or has major connected state transitions outside transactions),
    #    run bounded beam search from top-scoring non-command transition roots.
    non_tx_roots = [
        n for n in event_graph["nodes"]
        if n["fact_id"] not in used_spine_fids
        and n["fact_id"] in adj_spine
        and n["role"] in ("electrical_report", "electrical_change", "communication")
    ]
    non_tx_roots.sort(
        key=lambda n: (-float((n.get("protocol_meta") or {}).get("score") or 0.0), n["time"])
    )
    for root in non_tx_roots:
        if root["fact_id"] in used_spine_fids or len(storylines) >= 6:
            continue
        best_path, alt_paths = _beam_search_spine(
            root["fact_id"], nodes_by_id, adj_spine,
            beam_width=beam_width, max_depth=max_depth,
        )
        if len(best_path["node_ids"]) < 2:
            continue
        used_spine_fids.update(best_path["node_ids"])
        sl_id = f"SL{len(storylines) + 1:03d}"
        cooc_branches = _collect_competing_cooccurrence_branches(
            best_path["node_ids"], nodes_by_id, adj_cooc,
        )
        storylines.append(
            _format_storyline(
                sl_id, root, best_path, alt_paths, cooc_branches,
                nodes_by_id=nodes_by_id, tx=None,
            )
        )

    # 3. Collect all observations that were not included in any storyline spine
    all_spine_fids = {fid for sl in storylines for fid in sl["spine_fact_ids"]}
    unattached = [
        {
            "fact_id": n["fact_id"],
            "time": n["time"],
            "entity": n["entity"],
            "ca_ioa": n.get("ca_ioa"),
            "modality": n["modality"],
            "role": n["role"],
            "observation": n["observation"],
            "evidence_ids": n["evidence_ids"],
            "reason": (
                "isolated_no_graph_edge"
                if n["fact_id"] in {u["fact_id"] for u in event_graph["unconnected_observations"]}
                else "not_on_confirmed_storyline_spine"
            ),
        }
        for n in event_graph["nodes"]
        if n["fact_id"] not in all_spine_fids
    ]

    return {
        "search_method": "source_deduplicated_bounded_beam_search",
        "beam_width": beam_width,
        "max_depth": max_depth,
        "storyline_count": len(storylines),
        "complete_storyline_count": sum(
            1 for s in storylines if s["completeness_status"] == "complete_with_state_transition"
        ),
        "partial_or_incomplete_storyline_count": sum(
            1 for s in storylines if s["completeness_status"] != "complete_with_state_transition"
        ),
        "storylines": storylines,
        "unattached_observations": unattached,
    }


def _beam_search_spine(
    start_fid: str,
    nodes_by_id: dict[str, dict],
    adj_spine: dict[str, list[dict]],
    *,
    beam_width: int,
    max_depth: int,
) -> tuple[dict, list[dict]]:
    start_node = nodes_by_id[start_fid]
    initial = {
        "node_ids": [start_fid],
        "edges": [],
        "containers": set(_informative_containers(start_node)),
        "independent_edge_count": 0,
        "score": 0.0,
    }
    beam = [initial]
    completed = [initial]

    for _depth in range(max_depth):
        candidates = []
        for state in beam:
            last_fid = state["node_ids"][-1]
            last_time = nodes_by_id[last_fid]["time"]
            for edge in adj_spine.get(last_fid, []):
                nxt_fid = edge["target_fact_id"]
                if nxt_fid in state["node_ids"]:
                    continue
                nxt_node = nodes_by_id[nxt_fid]
                if nxt_node["time"] + 1.5 < last_time:
                    continue
                # If the anchor belongs to a transaction, keep spine steps on the same transaction or its derived IPAL state
                anchor_tx = start_node.get("transaction_id")
                if anchor_tx and nxt_node.get("transaction_id") not in (anchor_tx, None):
                    continue
                if anchor_tx and nxt_node.get("transaction_id") is None and nxt_node.get("device_stem") != start_node.get("device_stem"):
                    continue

                nxt_containers = _informative_containers(nxt_node)
                new_containers = nxt_containers - state["containers"]
                is_indep = bool(edge.get("independent_support")) and bool(new_containers)
                gain = EDGE_WEIGHT.get(edge["relation_category"], 1.0) if is_indep else 0.15
                candidates.append({
                    "node_ids": [*state["node_ids"], nxt_fid],
                    "edges": [*state["edges"], edge],
                    "containers": state["containers"] | nxt_containers,
                    "independent_edge_count": state["independent_edge_count"] + (1 if is_indep else 0),
                    "score": round(state["score"] + gain, 4),
                })
        if not candidates:
            break
        candidates.sort(
            key=lambda c: (-c["score"], -c["independent_edge_count"], -len(c["node_ids"]))
        )
        beam = candidates[:beam_width]
        completed.extend(beam)

    completed.sort(
        key=lambda c: (-c["score"], -c["independent_edge_count"], -len(c["node_ids"]))
    )
    best = completed[0]
    alternatives = [
        c for c in completed[1:]
        if c["node_ids"] != best["node_ids"] and len(c["node_ids"]) >= 2
    ][:3]
    return best, alternatives


def _find_pre_measurement_step(
    spine_fids: list[str],
    nodes_by_id: dict[str, dict],
    all_edges: list[dict],
) -> dict | None:
    spine_set = set(spine_fids)
    for edge in all_edges:
        if (
            edge["relation_type"] == "pre_to_post_measurement_transition"
            and edge["target_fact_id"] in spine_set
            and edge["source_fact_id"] not in spine_set
        ):
            return edge
    return None


def _collect_competing_cooccurrence_branches(
    spine_fids: list[str],
    nodes_by_id: dict[str, dict],
    adj_cooc: dict[str, list[dict]],
) -> list[dict]:
    branches = []
    seen_targets = set()
    for fid in spine_fids:
        for edge in adj_cooc.get(fid, []):
            tgt = edge["target_fact_id"]
            if tgt in seen_targets or tgt in spine_fids:
                continue
            seen_targets.add(tgt)
            tnode = nodes_by_id[tgt]
            branches.append({
                "edge_id": edge["edge_id"],
                "from_spine_fact_id": fid,
                "candidate_fact_id": tgt,
                "candidate_entity": tnode["entity"],
                "candidate_modality": tnode["modality"],
                "candidate_role": tnode["role"],
                "candidate_time": tnode["time"],
                "claim_level": edge["claim_level"],
                "verification_status": edge["verification_status"],
                "causal_status": "not_established",
                "temporal_condition": edge["temporal_condition"],
                "support_basis": edge["support_basis"],
                "evidence_ids": edge["evidence_ids"],
            })
    return branches


def _format_storyline(
    sl_id: str,
    anchor: dict,
    best_path: dict,
    alt_paths: list[dict],
    cooc_branches: list[dict],
    *,
    nodes_by_id: dict[str, dict],
    tx: dict | None,
) -> dict:
    spine_nodes = [nodes_by_id[fid] for fid in best_path["node_ids"]]
    spine_edges = best_path["edges"]
    all_ev_ids = list(dict.fromkeys(
        ev_id for n in spine_nodes for ev_id in n["evidence_ids"]
    ))

    # Determine completeness & evidence gaps
    gaps = list(tx.get("missing_stages") or []) if tx else []
    if tx is not None:
        if tx["device_state_change_status"] == "state_change_observed":
            comp_status = (
                "complete_with_state_transition"
                if tx.get("activation_termination") is not None
                else "partial_missing_cot10_but_verified_state_transition"
            )
        elif tx["command_acceptance_status"] == "accepted_by_rtu":
            comp_status = "incomplete_command_accepted_without_state_change"
        else:
            comp_status = "incomplete_unconfirmed_command"
    else:
        comp_status = "observed_state_or_session_chain"

    # Build explicit competing hypotheses when multiple cross-entity co-occurrences exist
    competing = []
    if len(cooc_branches) >= 2:
        entities = [b["candidate_entity"] for b in cooc_branches[:4]]
        competing.append({
            "hypothesis_type": "competing_cross_entity_cooccurrences",
            "status": "unresolved",
            "causal_status": "not_established",
            "candidate_entities": entities,
            "explanation": (
                f"Multiple distinct grid measurements ({', '.join(entities)}) changed within the "
                f"time horizon after {anchor['entity']}. Without an independent physical topology/power-flow "
                "model in the loop, these remain competing unresolved temporal co-occurrences rather than "
                "confirmed causal effects."
            ),
        })
    if tx and tx["device_state_change_status"] == "no_state_change_observed":
        competing.append({
            "hypothesis_type": "accepted_command_without_state_change",
            "status": "unresolved",
            "causal_status": "not_established",
            "candidate_entities": [tx["entity"]],
            "explanation": (
                f"RTU {tx['rtu_ip']} accepted command {tx['entity']} (COT=7), but no subsequent "
                "COT=3 state change report or IPAL new state update occurred. Alternative explanations: "
                "(a) the switch/point was already in the commanded state (idempotent command), or "
                "(b) physical actuation did not occur or was not reported within the window."
            ),
        })

    return {
        "storyline_id": sl_id,
        "transaction_id": tx["transaction_id"] if tx else None,
        "anchor_fact_id": anchor["fact_id"],
        "anchor_entity": anchor["entity"],
        "start_time": min(n["time"] for n in spine_nodes),
        "end_time": max(n["time_end"] for n in spine_nodes),
        "completeness_status": comp_status,
        "command_acceptance_status": tx["command_acceptance_status"] if tx else None,
        "device_state_change_status": tx["device_state_change_status"] if tx else None,
        "spine_node_count": len(spine_nodes),
        "spine_edge_count": len(spine_edges),
        "independent_source_container_count": len(best_path["containers"]),
        "independent_support_edge_count": best_path["independent_edge_count"],
        "source_deduplicated_score": best_path["score"],
        "spine_fact_ids": best_path["node_ids"],
        "spine_edge_ids": [e["edge_id"] for e in spine_edges],
        "confirmed_and_supported_steps": [
            {
                "step_index": i + 1,
                "edge_id": e["edge_id"],
                "source_fact_id": e["source_fact_id"],
                "target_fact_id": e["target_fact_id"],
                "source_entity": e["source_entity"],
                "target_entity": e["target_entity"],
                "modality_pair": e["modality_pair"],
                "relation_category": e["relation_category"],
                "relation_type": e["relation_type"],
                "claim_level": e["claim_level"],
                "verification_status": e["verification_status"],
                "independent_support": e["independent_support"],
                "temporal_condition": e["temporal_condition"],
                "support_basis": e["support_basis"],
                "evidence_ids": e["evidence_ids"],
            }
            for i, e in enumerate(spine_edges)
        ],
        "unresolved_cooccurrence_branches": cooc_branches,
        "competing_hypotheses": competing,
        "evidence_gaps": gaps,
        "all_spine_evidence_ids": all_ev_ids,
        "alternative_spine_paths": [
            {"fact_ids": alt["node_ids"], "edge_ids": [e["edge_id"] for e in alt["edges"]], "score": alt["score"]}
            for alt in alt_paths
        ],
    }


def _informative_containers(node: dict) -> set[str]:
    """Return physical/packet source container keys for deduplicating evidence support."""
    containers = [
        c for c in (node.get("source_containers") or [])
        if not str(c).startswith("point:")
    ]
    if containers:
        return set(containers)
    return set(node.get("source_containers") or node.get("evidence_ids")[:1])
