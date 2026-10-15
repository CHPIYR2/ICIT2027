"""Phase 3: Evidence-Constrained Storyline Reconstruction (Reliability-Hardened).

Key guarantees:
1. Strict contiguous directed path invariant on every storyline spine:
   - For every storyline, `len(spine_fact_ids) == len(confirmed_and_supported_steps) + 1`,
     and for every step `i`, `step[i].source_fact_id == spine_fact_ids[i]` and
     `step[i].target_fact_id == spine_fact_ids[i + 1]`.
   - Pre-command baseline observations (`pre_command_measurement`) and their
     comparison edges (`pre_to_post_measurement_transition`) are stored separately
     in `context_observations` and `supporting_evidence_edges` rather than prepended
     into the linear spine.
2. Vantage-invariant source accounting:
   - Separately reports `vantage_capture_count` (raw mirror-port captures),
     `logical_observation_count` (spine nodes), `independent_source_container_count`
     (unique canonical sources on the spine, unaffected by mirror port count or
     derived IPAL rows), and `independent_support_edge_count`.
3. Honest completeness & verification status:
   - Transactions whose `COT=3` state report has an undecoded value or lacks a
     pre-command baseline are labeled
     `completeness_status = "partial_state_report_observed_transition_unverified"`,
     never `"verified_state_transition"`.
"""
from __future__ import annotations

SPINE_CATEGORIES = {
    "direct_protocol_relation",
    "measurement_state_transition",
    "inference_hypothesis",
    "shared_source",
}

BEHAVIORAL_SPINE_CATEGORIES = {"direct_protocol_relation", "measurement_state_transition"}

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
    adj_corr: dict[str, list[dict]] = {}
    for edge in event_graph["edges"]:
        src = edge["source_fact_id"]
        if edge["relation_category"] == "temporal_correspondence":
            adj_corr.setdefault(src, []).append(edge)
            continue
        # Only verified/supported edges may form the contiguous spine; unresolved candidates stay off-spine
        if edge["relation_category"] in SPINE_CATEGORIES and edge.get("verification_status") == "supported":
            adj_spine.setdefault(src, []).append(edge)
        elif edge["relation_category"] == "temporal_cooccurrence" or edge.get("verification_status") == "unresolved":
            adj_cooc.setdefault(src, []).append(edge)

    storylines: list[dict] = []
    used_fids: set[str] = set()

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
        # Keep pre-command baseline in `context_observations` & `supporting_evidence_edges`
        # so the spine stays a strictly contiguous directed path (`node[i] -> node[i+1]`).
        supporting_edges = _find_supporting_pre_edges(best_path["node_ids"], event_graph["edges"])
        context_nodes = [
            nodes_by_id[e["source_fact_id"]]
            for e in supporting_edges
            if e["source_fact_id"] in nodes_by_id
        ]

        used_fids.update(best_path["node_ids"])
        used_fids.update(n["fact_id"] for n in context_nodes)
        cooc_branches = _collect_competing_cooccurrence_branches(
            best_path["node_ids"], nodes_by_id, adj_cooc,
        )
        storylines.append(
            _format_storyline(
                sl_id, anchor, best_path, alt_paths, cooc_branches,
                context_nodes=context_nodes,
                supporting_edges=supporting_edges,
                nodes_by_id=nodes_by_id,
                tx=tx,
                correspondences=_collect_temporal_correspondences(best_path["node_ids"], nodes_by_id, adj_corr),
            )
        )

    behavioral = _behavioral_storylines(
        event_graph, nodes_by_id, adj_cooc, adj_corr, used_fids,
        first_index=len(storylines) + 1, beam_width=beam_width, max_depth=max_depth,
    )
    storylines.extend(behavioral)

    non_tx_roots = [
        n for n in event_graph["nodes"]
        if n["fact_id"] not in used_fids
        and n["fact_id"] in adj_spine
        and n["role"] in ("electrical_report", "electrical_change", "communication")
    ]
    non_tx_roots.sort(
        key=lambda n: (-float((n.get("protocol_meta") or {}).get("score") or 0.0), n["time"])
    )
    for root in non_tx_roots:
        if root["fact_id"] in used_fids or len(storylines) >= 6:
            continue
        best_path, alt_paths = _beam_search_spine(
            root["fact_id"], nodes_by_id, adj_spine,
            beam_width=beam_width, max_depth=max_depth,
        )
        if len(best_path["node_ids"]) < 2:
            continue
        used_fids.update(best_path["node_ids"])
        sl_id = f"SL{len(storylines) + 1:03d}"
        cooc_branches = _collect_competing_cooccurrence_branches(
            best_path["node_ids"], nodes_by_id, adj_cooc,
        )
        storylines.append(
            _format_storyline(
                sl_id, root, best_path, alt_paths, cooc_branches,
                context_nodes=[],
                supporting_edges=[],
                nodes_by_id=nodes_by_id,
                tx=None,
                correspondences=_collect_temporal_correspondences(best_path["node_ids"], nodes_by_id, adj_corr),
            )
        )

    all_covered_fids = {
        fid
        for sl in storylines
        for fid in (*sl["spine_fact_ids"], *(c["fact_id"] for c in sl["context_observations"]))
    }
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
        if n["fact_id"] not in all_covered_fids
    ]

    candidate_edges = [e for e in event_graph["edges"] if e["relation_type"] == "cross_device_temporal_candidate"]
    sequential_edges = [e for e in event_graph["edges"] if e["relation_type"] == "same_entity_sequential_observation"]
    if any(_anchor_id(n) for n in event_graph["nodes"]):
        policy = {
            "status": "behavioral_anchor_search",
            "behavior": (
                "Storylines start at event anchors (state reports, measurement steps, link activity, ARP "
                "activity). A spine step requires a verified observation on both endpoints and a passed "
                "behavioral relation consistency gate (`corroborated_same_device_behavioral_transition`). "
                "Same-device observations that fail the gate stay `same_entity_sequential_observation` off "
                "the spine; unverified anchors stay single-node `behavioral_unverified_observation` records. "
                "Facts carried by one ASDU are listed as co-reported; cross-device time proximity stays an "
                "unresolved branch."
            ),
        }
    else:
        policy = {
            "status": "limited_existing_search",
            "behavior": (
                "Without a control-command anchor, storylines are formed only from supported "
                "edges already in the graph, such as same-device attribute couplings. "
                "Cross-entity time proximity stays unresolved and is not promoted into a spine."
            ),
            "deferred": "No event anchors were supplied; isolated observations remain unattached.",
        }
    return {
        "search_method": "source_deduplicated_bounded_beam_search",
        "no_control_command_policy": policy,
        "path_invariant_enforced": "contiguous_directed_spine_with_separate_supporting_evidence",
        "beam_width": beam_width,
        "max_depth": max_depth,
        "storyline_count": len(storylines),
        "verified_transition_storyline_count": sum(
            1 for s in storylines
            if s["completeness_status"] in (
                "complete_with_verified_transition",
                "partial_missing_cot10_but_verified_measurement_transition",
            )
        ),
        "partial_or_unverified_storyline_count": sum(
            1 for s in storylines
            if s["completeness_status"] not in (
                "complete_with_verified_transition",
                "partial_missing_cot10_but_verified_measurement_transition",
            )
        ),
        "behavioral_storyline_count": len(behavioral),
        "supported_behavioral_storyline_count": sum(
            1 for s in behavioral if s["completeness_status"] == "behavioral_chain_with_supported_relations"
        ),
        "verified_single_anchor_storyline_count": sum(
            1 for s in behavioral if s["completeness_status"] == "behavioral_single_anchor"
        ),
        "unverified_behavioral_observation_count": sum(
            1 for s in behavioral if s["completeness_status"] == "behavioral_unverified_observation"
        ),
        "storylines": storylines,
        "sequential_same_device_observations": [_sequential_record(e, nodes_by_id) for e in sequential_edges],
        "unresolved_branches": [_branch_record(e, nodes_by_id) for e in candidate_edges],
        "unattached_observations": unattached,
    }


def _anchor_id(node: dict) -> str | None:
    if node.get("role") == "ipal_correspondence":
        return None
    return (node.get("protocol_meta") or {}).get("anchor_id")


def _anchor_verified(node: dict) -> bool:
    return (node.get("protocol_meta") or {}).get("verification_status") == "verified_observation"


def _sequential_record(edge: dict, nodes_by_id: dict[str, dict]) -> dict:
    src, dst = nodes_by_id[edge["source_fact_id"]], nodes_by_id[edge["target_fact_id"]]
    gate = edge.get("consistency_gate") or {}
    return {
        "edge_id": edge["edge_id"],
        "from_fact_id": src["fact_id"],
        "from_anchor_id": _anchor_id(src),
        "from_entity": src["entity"],
        "from_time": src["time"],
        "to_fact_id": dst["fact_id"],
        "to_anchor_id": _anchor_id(dst),
        "to_entity": dst["entity"],
        "to_time": dst["time"],
        "device_stem": src.get("device_stem"),
        "relation_type": edge["relation_type"],
        "claim_level": edge["claim_level"],
        "verification_status": edge["verification_status"],
        "graph_consistency_gate_status": edge.get("graph_consistency_gate_status"),
        "failed_conditions": list(gate.get("failed_conditions") or []),
        "consistency_gate": gate,
        "temporal_condition": edge["temporal_condition"],
        "support_basis": edge["support_basis"],
        "evidence_ids": edge["evidence_ids"],
    }


def _branch_record(edge: dict, nodes_by_id: dict[str, dict]) -> dict:
    src, dst = nodes_by_id[edge["source_fact_id"]], nodes_by_id[edge["target_fact_id"]]
    return {
        "edge_id": edge["edge_id"],
        "from_fact_id": src["fact_id"],
        "from_anchor_id": _anchor_id(src),
        "from_entity": src["entity"],
        "from_time": src["time"],
        "to_fact_id": dst["fact_id"],
        "to_anchor_id": _anchor_id(dst),
        "to_entity": dst["entity"],
        "to_time": dst["time"],
        "relation_type": edge["relation_type"],
        "claim_level": edge["claim_level"],
        "verification_status": edge["verification_status"],
        "causal_status": "not_established",
        "temporal_condition": edge["temporal_condition"],
        "support_basis": edge["support_basis"],
        "evidence_ids": edge["evidence_ids"],
    }


def _behavioral_storylines(
    event_graph: dict,
    nodes_by_id: dict[str, dict],
    adj_cooc: dict[str, list[dict]],
    adj_corr: dict[str, list[dict]],
    used_fids: set[str],
    *,
    first_index: int,
    beam_width: int,
    max_depth: int,
) -> list[dict]:
    """One storyline per anchor group, rooted at the earliest anchor not yet on a spine."""
    roots = sorted((n for n in event_graph["nodes"] if _anchor_id(n)), key=lambda n: (n["time"], n["fact_id"]))
    if not roots:
        return []
    anchor_fids = {n["fact_id"] for n in roots}
    adj_beh: dict[str, list[dict]] = {}
    same_asdu: dict[str, list[dict]] = {}
    same_device_seq: dict[str, list[dict]] = {}
    incoming: dict[str, list[dict]] = {}
    for edge in event_graph["edges"]:
        src, dst = edge["source_fact_id"], edge["target_fact_id"]
        if src not in anchor_fids or dst not in anchor_fids:
            continue
        if (
            edge["relation_category"] in BEHAVIORAL_SPINE_CATEGORIES
            and edge["verification_status"] == "supported"
            and edge.get("graph_consistency_gate_status") == "passed_behavioral_consistency_gate"
            and _anchor_verified(nodes_by_id[src])
            and _anchor_verified(nodes_by_id[dst])
        ):
            adj_beh.setdefault(src, []).append(edge)
        elif edge["relation_type"] == "same_entity_sequential_observation":
            same_device_seq.setdefault(src, []).append(edge)
            same_device_seq.setdefault(dst, []).append(edge)
        elif edge["relation_type"] == "same_iec104_asdu":
            same_asdu.setdefault(src, []).append(edge)
            same_asdu.setdefault(dst, []).append(edge)
        elif edge["relation_type"] == "cross_device_temporal_candidate":
            incoming.setdefault(dst, []).append(edge)

    out = []
    for root in roots:
        if root["fact_id"] in used_fids:
            continue
        root_verified = _anchor_verified(root)
        if root_verified:
            open_adj = {
                fid: [e for e in edges if e["target_fact_id"] not in used_fids]
                for fid, edges in adj_beh.items()
            }
            best_path, alt_paths = _beam_search_spine(
                root["fact_id"], nodes_by_id, open_adj, beam_width=beam_width, max_depth=max_depth,
            )
        else:
            best_path = {
                "node_ids": [root["fact_id"]],
                "edges": [],
                "containers": set(_informative_containers(root)),
                "independent_edge_count": 0,
                "score": 0.0,
            }
            alt_paths = []
        used_fids.update(best_path["node_ids"])
        spine = best_path["node_ids"]
        story = _format_storyline(
            f"SL{first_index + len(out):03d}", root, best_path, alt_paths,
            _collect_competing_cooccurrence_branches(spine, nodes_by_id, adj_cooc),
            context_nodes=[], supporting_edges=[], nodes_by_id=nodes_by_id, tx=None,
            correspondences=_collect_temporal_correspondences(spine, nodes_by_id, adj_corr),
        )
        co_reported = []
        for fid in spine:
            for edge in same_asdu.get(fid, []):
                other = edge["target_fact_id"] if edge["source_fact_id"] == fid else edge["source_fact_id"]
                if other in spine or any(c["fact_id"] == other for c in co_reported):
                    continue
                onode = nodes_by_id[other]
                co_reported.append({
                    "edge_id": edge["edge_id"], "with_spine_fact_id": fid, "fact_id": other,
                    "anchor_id": _anchor_id(onode), "entity": onode["entity"], "time": onode["time"],
                    "relation_type": "same_iec104_asdu", "independent_support": False,
                    "meaning": "carried by the same ASDU; no relation between the devices' changes is established",
                })
        sequential_obs = []
        seen_seq_edges: set[str] = set()
        for fid in spine:
            for edge in same_device_seq.get(fid, []):
                if edge["edge_id"] in seen_seq_edges:
                    continue
                seen_seq_edges.add(edge["edge_id"])
                sequential_obs.append(_sequential_record(edge, nodes_by_id))
        incoming_branches = [
            _branch_record(e, nodes_by_id)
            for fid in spine for e in incoming.get(fid, [])
            if e["source_fact_id"] not in spine
        ]
        spine_nodes = [nodes_by_id[f] for f in spine]
        if not root_verified:
            comp_status = "behavioral_unverified_observation"
        elif story["confirmed_and_supported_steps"]:
            comp_status = "behavioral_chain_with_supported_relations"
        else:
            comp_status = "behavioral_single_anchor"
        story.update({
            "storyline_kind": "behavioral",
            "anchor_ids": [_anchor_id(n) for n in spine_nodes],
            "anchor_types": sorted({n["role"] for n in spine_nodes}),
            "anchor_verification_statuses": {
                _anchor_id(n): (n.get("protocol_meta") or {}).get("verification_status", "unverified_observation")
                for n in spine_nodes
            },
            "anchor_verification_issues": {
                _anchor_id(n): list((n.get("protocol_meta") or {}).get("verification_issues") or [])
                for n in spine_nodes
                if (n.get("protocol_meta") or {}).get("verification_issues")
            },
            "completeness_status": comp_status,
            "co_reported_in_same_asdu": co_reported,
            "sequential_same_device_observations": sequential_obs,
            "incoming_unresolved_branches": incoming_branches,
            "reconstructed_behavior": _describe_behavior(
                spine_nodes, story["confirmed_and_supported_steps"], co_reported, sequential_obs,
            ),
            "not_reconstructed": (
                "Cause, the initiating actor, and any relation to devices outside this chain. Cross-device "
                "links are listed only as unresolved branches; no grid topology is available."
            ),
        })
        out.append(story)
    return out


def _describe_behavior(
    spine_nodes: list[dict],
    steps: list[dict],
    co_reported: list[dict],
    sequential_obs: list[dict] | None = None,
) -> str:
    parts = [f"[{n['protocol_meta']['anchor_id']}] {n['observation'].rstrip('.')}" for n in spine_nodes]
    text = " THEN ".join(parts)
    if steps:
        text += (
            f". {len(steps)} corroborated same-device behavioral transition(s) in separate ASDUs "
            "(passed behavioral consistency gate; element identity from the data point map; not a cause)"
        )
    if sequential_obs:
        text += (
            f". {len(sequential_obs)} same-device sequential observation(s) kept off-spine "
            f"(failed behavioral consistency gate: {[s['failed_conditions'] for s in sequential_obs]})"
        )
    if co_reported:
        text += f". Co-reported in the same ASDU: {', '.join(sorted({c['entity'] for c in co_reported}))}"
    return text + "."


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


def _find_supporting_pre_edges(
    spine_fids: list[str],
    all_edges: list[dict],
) -> list[dict]:
    spine_set = set(spine_fids)
    out = []
    for edge in all_edges:
        if (
            edge["relation_type"] in ("pre_to_post_measurement_transition", "pre_to_post_measurement_comparison")
            and edge["target_fact_id"] in spine_set
            and edge["source_fact_id"] not in spine_set
        ):
            out.append(edge)
    return out


def _collect_temporal_correspondences(
    spine_fids: list[str],
    nodes_by_id: dict[str, dict],
    adj_corr: dict[str, list[dict]],
) -> list[dict]:
    """IPAL rows aligned with a spine fact by point and time only; common source not confirmed."""
    out = []
    for fid in spine_fids:
        for edge in adj_corr.get(fid, []):
            tnode = nodes_by_id[edge["target_fact_id"]]
            out.append({
                "edge_id": edge["edge_id"],
                "from_spine_fact_id": fid,
                "fact_id": tnode["fact_id"],
                "entity": tnode["entity"],
                "time": tnode["time"],
                "value": tnode.get("value"),
                "relation_type": edge["relation_type"],
                "claim_level": edge["claim_level"],
                "common_source_status": "unconfirmed_no_lineage",
                "counts_as_independent_source": False,
                "evidence_ids": edge["evidence_ids"],
            })
    return out


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
                "relation_type": edge["relation_type"],
                "candidate_time": tnode["time"],
                "claim_level": edge["claim_level"],
                "verification_status": edge["verification_status"],
                "graph_consistency_gate_status": edge.get("graph_consistency_gate_status"),
                "causal_status": "not_established",
                "temporal_condition": edge["temporal_condition"],
                "support_basis": edge["support_basis"],
                "source_evidence_ids": edge.get("source_evidence_ids") or [],
                "target_evidence_ids": edge.get("target_evidence_ids") or [],
                "evidence_ids": edge["evidence_ids"],
            })
    return branches


def _assert_contiguous_spine_path(spine_fids: list[str], steps: list[dict]) -> None:
    if len(spine_fids) != len(steps) + 1:
        raise ValueError(
            f"Spine path invariant violated: {len(spine_fids)} nodes vs {len(steps)} edges"
        )
    for idx, step in enumerate(steps):
        if step["source_fact_id"] != spine_fids[idx] or step["target_fact_id"] != spine_fids[idx + 1]:
            raise ValueError(
                f"Spine step {idx + 1} ({step['source_fact_id']} -> {step['target_fact_id']}) "
                f"does not match contiguous nodes ({spine_fids[idx]} -> {spine_fids[idx + 1]})"
            )


def _format_storyline(
    sl_id: str,
    anchor: dict,
    best_path: dict,
    alt_paths: list[dict],
    cooc_branches: list[dict],
    *,
    context_nodes: list[dict],
    supporting_edges: list[dict],
    nodes_by_id: dict[str, dict],
    tx: dict | None,
    correspondences: list[dict] | None = None,
) -> dict:
    spine_nodes = [nodes_by_id[fid] for fid in best_path["node_ids"]]
    spine_edges = best_path["edges"]
    steps = [
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
            "graph_consistency_gate_status": e.get("graph_consistency_gate_status"),
            "consistency_gate": e.get("consistency_gate"),
            "independent_support": e["independent_support"],
            "temporal_condition": e["temporal_condition"],
            "support_basis": e["support_basis"],
            "source_evidence_ids": e.get("source_evidence_ids") or [],
            "target_evidence_ids": e.get("target_evidence_ids") or [],
            "evidence_ids": e["evidence_ids"],
        }
        for i, e in enumerate(spine_edges)
    ]
    _assert_contiguous_spine_path(best_path["node_ids"], steps)

    all_ev_ids = list(dict.fromkeys(
        ev_id
        for n in (*context_nodes, *spine_nodes)
        for ev_id in n["evidence_ids"]
    ))
    vantage_captures = sum(int(n.get("vantage_capture_count") or 1) for n in spine_nodes)
    supporting_containers = {
        c for n in context_nodes for c in _informative_containers(n)
    }

    gaps = list(tx.get("missing_stages") or []) if tx else []
    if tx is not None:
        state_status = tx["device_state_change_status"]
        if state_status in ("verified_state_transition", "verified_measurement_transition"):
            comp_status = (
                "complete_with_verified_transition"
                if tx.get("activation_termination") is not None
                else "partial_missing_cot10_but_verified_measurement_transition"
            )
        elif state_status.startswith("state_report_observed") or state_status == "measurement_observed_transition_unverified":
            comp_status = "partial_state_report_observed_transition_unverified"
        elif tx.get("activation_confirmation") is not None:
            comp_status = "incomplete_confirmation_observed_without_state_report"
        else:
            comp_status = "incomplete_unconfirmed_command"
    else:
        comp_status = "observed_state_or_session_chain"

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
            "hypothesis_type": "confirmation_without_state_report",
            "status": "unresolved",
            "causal_status": "not_established",
            "candidate_entities": [tx["entity"]],
            "explanation": (
                f"RTU {tx['rtu_ip']} sent COT=7 on {tx['entity']} "
                f"(acceptance_status={tx['command_acceptance_status']}), but no subsequent "
                "COT=3 state report or IPAL new state update occurred. Alternative explanations: "
                "(a) the switch/point was already in the target state, or "
                "(b) physical actuation did not occur or was not reported within the window."
            ),
        })
    elif tx and tx["device_state_change_status"].startswith("state_report_observed"):
        competing.append({
            "hypothesis_type": "state_report_without_verified_before_after_values",
            "status": "unresolved",
            "causal_status": "not_established",
            "candidate_entities": [tx["entity"]],
            "explanation": (
                f"A subsequent M_SP_NA_1 (COT=3) state report was observed for {tx['device_stem']}, "
                f"but {tx['device_state_change_status']} ({tx.get('state_verification_reason')}). "
                "Therefore a state transition cannot be confirmed from protocol values alone."
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
        "spine_is_contiguous_directed_path": True,
        "spine_node_count": len(spine_nodes),
        "spine_edge_count": len(spine_edges),
        "vantage_capture_count": vantage_captures,
        "logical_observation_count": len(spine_nodes),
        "independent_source_container_count": len(best_path["containers"]),
        "total_independent_source_containers_with_supporting": len(best_path["containers"] | supporting_containers),
        "independent_support_edge_count": best_path["independent_edge_count"],
        "supporting_evidence_edge_count": len(supporting_edges),
        "source_deduplicated_score": best_path["score"],
        "spine_fact_ids": best_path["node_ids"],
        "spine_edge_ids": [e["edge_id"] for e in spine_edges],
        "confirmed_and_supported_steps": steps,
        "context_observations": [
            {
                "fact_id": n["fact_id"],
                "time": n["time"],
                "entity": n["entity"],
                "ca_ioa": n.get("ca_ioa"),
                "role": n["role"],
                "value": n.get("value"),
                "evidence_ids": n["evidence_ids"],
                "observation": n["observation"],
            }
            for n in context_nodes
        ],
        "supporting_evidence_edges": [
            {
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
                "temporal_condition": e["temporal_condition"],
                "support_basis": e["support_basis"],
                "source_evidence_ids": e.get("source_evidence_ids") or [],
                "target_evidence_ids": e.get("target_evidence_ids") or [],
                "evidence_ids": e["evidence_ids"],
            }
            for e in supporting_edges
        ],
        "unresolved_cooccurrence_branches": cooc_branches,
        "temporal_correspondences": correspondences or [],
        "competing_hypotheses": competing,
        "evidence_gaps": gaps,
        "all_spine_evidence_ids": all_ev_ids,
        "alternative_spine_paths": [
            {"fact_ids": alt["node_ids"], "edge_ids": [e["edge_id"] for e in alt["edges"]], "score": alt["score"]}
            for alt in alt_paths
        ],
    }


def _informative_containers(node: dict) -> set[str]:
    if node.get("counts_as_independent_source") is False:
        return set()
    return set(node.get("source_containers") or node.get("evidence_ids")[:1])
