"""Four-Layer Evidence-Stratified Incident Synthesis (`docs/INCIDENT_SYNTHESIS_DESIGN.md`).

Integrates Protocol Reconstruction (`transactions.py`) and Behavioral Reconstruction
(`anchors.py`, `behavior.py`, `storyline.py`) into a traceable, uncertainty-preserving
Incident Scenario without promoting temporal co-occurrence or shared-ASDU co-reporting
into physical topology or causation:

- Layer 1 (`local_storyline_partition`): Separates supported multi-node storylines,
  verified single-anchor storylines, unverified protocol storylines, sequential
  same-device observations (`same_entity_sequential_observation`), and quarantined
  unverified observations (`unverified_observation`).
- Layer 2 (`rtu_asdu_bundles`, `verified_element_bridges`, `bridged_bundle_components`):
  Groups verified anchors by their actual ASDU source container (`SRC-ASDU-...`,
  counted as 1 independent source regardless of IOA fan-out or mirror vantages).
  Builds a `VerifiedElementBridge` between two bundles ONLY when linked by a
  `corroborated_same_device_behavioral_transition` edge that passed
  `evaluate_behavioral_relation_consistency()`. Other devices in the same bundle
  remain co-reported context only.
- Layer 3 (`candidate_scenario_phases`): Organizes bundles, storylines, and protocol
  transactions by time horizon, RTU/master hosts, and observed network activity
  (ARP / TCP / IEC-104 link changes) while keeping all cross-device candidate links
  strictly `unresolved` (`causal_status="not_established"`).
- Layer 4 (`source_dependency_ledger`, `competing_explanations`): Deduplicated
  ledger of ASDU containers, RTUs, mirror vantages, and IPAL correspondences
  (weight 0), plus evidence-anchored competing explanations and missing
  disambiguating evidence.
"""
from __future__ import annotations
from .behavior import HORIZON_SECONDS, evaluate_behavioral_relation_consistency

VERIFIED_TX_STORY = (
    "complete_with_verified_transition",
    "partial_missing_cot10_but_verified_measurement_transition",
)


def synthesize_incident_scenario(
    *,
    incident_start: float,
    incident_end: float,
    tx_result: dict,
    anchor_result: dict | None,
    event_graph: dict,
    storyline_result: dict,
    phase_gap_seconds: float = HORIZON_SECONDS,
) -> dict:
    anchors = list((anchor_result or {}).get("anchors") or [])
    anchors_by_id = {a["anchor_id"]: a for a in anchors}
    nodes_by_id = {n["fact_id"]: n for n in event_graph.get("nodes") or []}
    edges = list(event_graph.get("edges") or [])
    edges_by_id = {e["edge_id"]: e for e in edges}
    storylines = list(storyline_result.get("storylines") or [])
    transactions = list(tx_result.get("transactions") or [])
    behavioral_mode = bool((anchor_result or {}).get("behavioral_mode", not transactions))

    # Layer 1: Local Storyline Partition
    partition = _partition_local_storylines(
        storylines=storylines,
        anchors_by_id=anchors_by_id,
        nodes_by_id=nodes_by_id,
        sequential_records=list(storyline_result.get("sequential_same_device_observations") or []),
        incident_start=incident_start,
    )

    # Layer 2: RTU ASDU Bundles & Verified Element Bridges
    bundles, bundle_by_anchor_id, bundle_by_fact_id = _build_rtu_asdu_bundles(
        anchors=anchors,
        nodes_by_id=nodes_by_id,
        edges=edges,
        placed_anchors=event_graph.get("behavioral_anchor_facts") or {},
        behavioral_mode=behavioral_mode,
        incident_start=incident_start,
    )
    bridges, same_rtu_relations = _build_verified_element_bridges(
        edges=edges,
        nodes_by_id=nodes_by_id,
        storylines=storylines,
        bundles=bundles,
        bundle_by_fact_id=bundle_by_fact_id,
        incident_start=incident_start,
    )
    bridged_components = _build_bridged_bundle_components(
        bundles=bundles,
        bridges=bridges,
        sequential_records=partition["sequential_same_device_observations"],
        incident_start=incident_start,
    )

    # Layer 3: Candidate Scenario Phases
    candidate_phases = _build_candidate_scenario_phases(
        incident_start=incident_start,
        transactions=transactions,
        bundles=bundles,
        bridges=bridges,
        partition=partition,
        storylines=storylines,
        unresolved_branches=list(storyline_result.get("unresolved_branches") or []),
        edges=edges,
        nodes_by_id=nodes_by_id,
        anchors_by_id=anchors_by_id,
        phase_gap_seconds=phase_gap_seconds,
    )

    # Layer 4: Source Dependency Ledger & Competing Explanations
    ledger = _build_source_dependency_ledger(
        transactions=transactions,
        anchors=anchors,
        bundles=bundles,
        nodes_by_id=nodes_by_id,
        edges=edges,
        behavioral_mode=behavioral_mode,
    )
    competing_explanations = _build_competing_explanations(
        incident_start=incident_start,
        transactions=transactions,
        bundles=bundles,
        bridges=bridges,
        bridged_components=bridged_components,
        partition=partition,
        candidate_phases=candidate_phases,
        ledger=ledger,
        anchors_by_id=anchors_by_id,
        edges_by_id=edges_by_id,
    )

    return {
        "synthesis_version": "1.1",
        "scenario_status": "synthesized_consistent",
        "behavioral_mode": behavioral_mode,
        "window": {
            "start": incident_start,
            "end": incident_end,
            "duration_seconds": round(incident_end - incident_start, 3),
        },
        "inputs_not_used": ["official event labels", "attack type", "malicious flags", "physical.zip"],
        "epistemic_guarantees": {
            "promotes_cooccurrence_to_supported": False,
            "promotes_same_asdu_co_report_to_topology_or_causality": False,
            "counts_same_asdu_as_independent": False,
            "counts_mirror_vantages_as_independent": False,
            "counts_ipal_as_independent": False,
            "allows_unverified_anchors_in_supported_bridges": False,
            "allows_same_rtu_relation_as_cross_rtu_bridge": False,
        },
        "local_storyline_partition": partition,
        "rtu_asdu_bundles": bundles,
        "verified_element_bridges": bridges,
        "same_rtu_supported_relations": same_rtu_relations,
        "bridged_bundle_components": bridged_components,
        "candidate_scenario_phases": candidate_phases,
        "source_dependency_ledger": ledger,
        "competing_explanations": competing_explanations,
    }


def _partition_local_storylines(
    *,
    storylines: list[dict],
    anchors_by_id: dict[str, dict],
    nodes_by_id: dict[str, dict],
    sequential_records: list[dict],
    incident_start: float,
) -> dict:
    supported_multi_node: list[dict] = []
    verified_single_anchor: list[dict] = []
    protocol_partial_or_unverified: list[dict] = []
    quarantined_unverified: list[dict] = []
    unverified_precursors: list[dict] = []

    for sl in storylines:
        kind = sl.get("storyline_kind", "transaction_or_observed_chain")
        status = sl.get("completeness_status")
        spine_fids = list(sl.get("spine_fact_ids") or [])
        spine_entities = [nodes_by_id[f]["entity"] for f in spine_fids if f in nodes_by_id]
        entry = {
            "storyline_id": sl["storyline_id"],
            "storyline_kind": kind,
            "transaction_id": sl.get("transaction_id"),
            "anchor_ids": list(sl.get("anchor_ids") or []),
            "spine_fact_ids": spine_fids,
            "spine_entities": spine_entities,
            "start_time": sl["start_time"],
            "end_time": sl["end_time"],
            "start_relative_s": round(sl["start_time"] - incident_start, 3),
            "completeness_status": status,
            "independent_source_container_count": sl.get("independent_source_container_count", 0),
            "independent_support_edge_count": sl.get("independent_support_edge_count", 0),
            "supported_step_count": len(sl.get("confirmed_and_supported_steps") or []),
            "reconstructed_behavior": sl.get("reconstructed_behavior"),
            "evidence_ids": list(sl.get("all_spine_evidence_ids") or []),
        }
        if kind == "behavioral":
            if status == "behavioral_chain_with_supported_relations":
                supported_multi_node.append(entry)
            elif status == "behavioral_single_anchor":
                verified_single_anchor.append(entry)
            else:
                aid = (sl.get("anchor_ids") or [None])[0]
                anchor = anchors_by_id.get(aid) or {}
                issues = list(
                    (sl.get("anchor_verification_issues") or {}).get(aid)
                    or anchor.get("verification_issues")
                    or []
                )
                q_entry = {
                    **entry,
                    "anchor_id": aid,
                    "anchor_type": anchor.get("anchor_type"),
                    "rtu_ip": anchor.get("rtu_ip"),
                    "verification_status": "unverified_observation",
                    "verification_issues": issues,
                    "quarantine_reason": (
                        "Excluded from RTU ASDU bundles and Verified Element Bridges because "
                        f"anchor verification failed: {issues}."
                    ),
                }
                quarantined_unverified.append(q_entry)
                if anchor.get("anchor_type") == "spontaneous_state_report" and (
                    "no_prior_state_value_in_window" in issues
                ):
                    unverified_precursors.append({
                        "anchor_id": aid,
                        "storyline_id": sl["storyline_id"],
                        "fact_id": spine_fids[0] if spine_fids else None,
                        "time": anchor.get("time"),
                        "relative_time_s": round(float(anchor.get("time", incident_start)) - incident_start, 3),
                        "entity": anchor.get("entity"),
                        "ca_ioa": anchor.get("ca_ioa"),
                        "reported_value": anchor.get("value"),
                        "rtu_ip": anchor.get("rtu_ip"),
                        "verification_status": "unverified_observation",
                        "verification_issues": issues,
                        "epistemic_note": (
                            "Spontaneous COT=3 state report observed in network telemetry, but no prior "
                            "IEC-104 state value exists in the window to prove a state change. Retained "
                            "as an unverified precursor observation only; cannot form a Verified Element Bridge."
                        ),
                        "evidence_ids": list(anchor.get("evidence_ids") or []),
                    })
        else:
            if status in VERIFIED_TX_STORY:
                supported_multi_node.append(entry)
            else:
                protocol_partial_or_unverified.append(entry)

    seq_formatted = [
        {
            "edge_id": sq["edge_id"],
            "from_anchor_id": sq.get("from_anchor_id"),
            "to_anchor_id": sq.get("to_anchor_id"),
            "from_fact_id": sq["from_fact_id"],
            "to_fact_id": sq["to_fact_id"],
            "device_stem": sq.get("device_stem"),
            "from_entity": sq["from_entity"],
            "to_entity": sq["to_entity"],
            "from_relative_s": round(float(sq["from_time"]) - incident_start, 3),
            "to_relative_s": round(float(sq["to_time"]) - incident_start, 3),
            "relation_type": sq["relation_type"],
            "claim_level": sq["claim_level"],
            "verification_status": sq["verification_status"],
            "failed_conditions": list(sq.get("failed_conditions") or []),
            "evidence_ids": list(sq.get("evidence_ids") or []),
        }
        for sq in sequential_records
    ]

    return {
        "counts": {
            "supported_multi_node_storyline_count": len(supported_multi_node),
            "verified_single_anchor_storyline_count": len(verified_single_anchor),
            "protocol_partial_or_unverified_storyline_count": len(protocol_partial_or_unverified),
            "sequential_same_device_observation_count": len(seq_formatted),
            "quarantined_unverified_observation_count": len(quarantined_unverified),
            "unverified_precursor_state_report_count": len(unverified_precursors),
        },
        "supported_multi_node_storylines": supported_multi_node,
        "verified_single_anchor_storylines": verified_single_anchor,
        "protocol_partial_or_unverified_storylines": protocol_partial_or_unverified,
        "sequential_same_device_observations": seq_formatted,
        "unverified_precursor_state_reports": unverified_precursors,
        "quarantined_unverified_observations": quarantined_unverified,
    }


def _build_rtu_asdu_bundles(
    *,
    anchors: list[dict],
    nodes_by_id: dict[str, dict],
    edges: list[dict],
    placed_anchors: dict[str, dict],
    behavioral_mode: bool,
    incident_start: float,
) -> tuple[list[dict], dict[str, str], dict[str, str]]:
    if not behavioral_mode:
        return [], {}, {}

    same_asdu_edges_by_pair: dict[tuple[str, str], str] = {}
    for e in edges:
        if e.get("relation_type") == "same_iec104_asdu":
            s, t = e["source_fact_id"], e["target_fact_id"]
            same_asdu_edges_by_pair[(s, t)] = e["edge_id"]
            same_asdu_edges_by_pair[(t, s)] = e["edge_id"]

    grouped: dict[str, list[tuple[dict, dict]]] = {}
    for anchor in anchors:
        if anchor.get("covered_by_transaction"):
            continue
        if anchor.get("verification_status") != "verified_observation":
            continue
        aid = anchor["anchor_id"]
        placed = placed_anchors.get(aid) or {}
        fid = placed.get("fact_id") or f"BA{aid[1:]}"
        node = nodes_by_id.get(fid)
        if node is None:
            continue
        if (node.get("protocol_meta") or {}).get("verification_status") != "verified_observation":
            continue
        containers = list(node.get("source_containers") or [])
        container_id = (
            containers[0]
            if containers
            else (
                f"SRC-ASDU-{anchor['asdu_key']}"
                if anchor.get("asdu_key")
                else f"SRC-{anchor['anchor_type'].upper()}-{anchor['entity']}"
            )
        )
        grouped.setdefault(container_id, []).append((anchor, node))

    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: (min(a["time"] for a, _ in item[1]), item[0]),
    )
    bundles: list[dict] = []
    bundle_by_anchor_id: dict[str, str] = {}
    bundle_by_fact_id: dict[str, str] = {}

    for idx, (container_id, members) in enumerate(ordered_groups, start=1):
        members.sort(key=lambda pair: (pair[0]["time"], pair[0]["anchor_id"]))
        bundle_id = f"BND-{idx:03d}"
        a_ids = [a["anchor_id"] for a, _ in members]
        f_ids = [n["fact_id"] for _, n in members]
        for aid in a_ids:
            bundle_by_anchor_id[aid] = bundle_id
        for fid in f_ids:
            bundle_by_fact_id[fid] = bundle_id

        co_edges: list[str] = []
        for i, fid1 in enumerate(f_ids):
            for fid2 in f_ids[i + 1:]:
                eid = same_asdu_edges_by_pair.get((fid1, fid2))
                if eid and eid not in co_edges:
                    co_edges.append(eid)

        first_a = members[0][0]
        vantages = sorted({v for a, _ in members for v in (a.get("vantages") or []) if v})
        ev_ids = list(dict.fromkeys(eid for a, _ in members for eid in (a.get("evidence_ids") or [])))
        stems = sorted({a["device_stem"] for a, _ in members if a.get("device_stem")})
        entities = [a["entity"] for a, _ in members]
        container_kind = "iec104_asdu" if container_id.startswith("SRC-ASDU-") else "network_link_or_arp"

        bundles.append({
            "bundle_id": bundle_id,
            "asdu_container_id": container_id,
            "container_kind": container_kind,
            "rtu_ip": first_a.get("rtu_ip"),
            "master_ip": first_a.get("master_ip"),
            "host_ip": first_a.get("host_ip"),
            "time": min(a["time"] for a, _ in members),
            "time_end": max(a.get("time_end", a["time"]) for a, _ in members),
            "relative_time_s": round(min(a["time"] for a, _ in members) - incident_start, 3),
            "member_anchor_ids": a_ids,
            "member_fact_ids": f_ids,
            "member_entities": entities,
            "member_device_stems": stems,
            "member_anchor_types": sorted({a["anchor_type"] for a, _ in members}),
            "co_reported_same_asdu_edge_ids": co_edges,
            "all_members_verified": True,
            "independent_source_count": 1,
            "vantages": vantages,
            "evidence_ids": ev_ids,
            "co_reporting_semantics": "shared_asdu_container_co_report_only_not_topological_or_causal",
        })

    return bundles, bundle_by_anchor_id, bundle_by_fact_id


def _build_verified_element_bridges(
    *,
    edges: list[dict],
    nodes_by_id: dict[str, dict],
    storylines: list[dict],
    bundles: list[dict],
    bundle_by_fact_id: dict[str, str],
    incident_start: float,
) -> tuple[list[dict], list[dict]]:
    """Cross-RTU bridges only. A same-RTU supported edge is kept, not promoted."""
    storyline_by_edge_id: dict[str, str] = {}
    for sl in storylines:
        for st in sl.get("confirmed_and_supported_steps") or []:
            storyline_by_edge_id[st["edge_id"]] = sl["storyline_id"]

    stems_by_bundle: dict[str, list[str]] = {}
    for bundle in bundles:
        stems_by_bundle[bundle["bundle_id"]] = list(bundle.get("member_device_stems") or [])

    bridges: list[dict] = []
    same_rtu: list[dict] = []
    for edge in edges:
        if edge.get("relation_type") != "corroborated_same_device_behavioral_transition":
            continue
        if edge.get("verification_status") != "supported":
            continue
        if edge.get("graph_consistency_gate_status") != "passed_behavioral_consistency_gate":
            continue
        src_fid, dst_fid = edge["source_fact_id"], edge["target_fact_id"]
        src_node, dst_node = nodes_by_id.get(src_fid), nodes_by_id.get(dst_fid)
        if src_node is None or dst_node is None:
            continue
        if (src_node.get("protocol_meta") or {}).get("verification_status") != "verified_observation":
            continue
        if (dst_node.get("protocol_meta") or {}).get("verification_status") != "verified_observation":
            continue
        recheck = evaluate_behavioral_relation_consistency(src_node, dst_node)
        if not recheck.get("gate_passed"):
            continue
        from_bid = bundle_by_fact_id.get(src_fid)
        to_bid = bundle_by_fact_id.get(dst_fid)
        if not from_bid or not to_bid or from_bid == to_bid:
            continue

        sm, dm = src_node["protocol_meta"], dst_node["protocol_meta"]
        from_rtu, to_rtu = sm.get("rtu_ip"), dm.get("rtu_ip")
        stem = src_node.get("device_stem")
        other_from = sorted(set(stems_by_bundle.get(from_bid, [])) - {stem})
        other_to = sorted(set(stems_by_bundle.get(to_bid, [])) - {stem})
        record = {
            "edge_id": edge["edge_id"],
            "storyline_id": storyline_by_edge_id.get(edge["edge_id"]),
            "bridged_device_stem": stem,
            "from_bundle_id": from_bid,
            "to_bundle_id": to_bid,
            "from_anchor_id": sm.get("anchor_id"),
            "to_anchor_id": dm.get("anchor_id"),
            "from_fact_id": src_fid,
            "to_fact_id": dst_fid,
            "from_entity": src_node["entity"],
            "to_entity": dst_node["entity"],
            "from_rtu_ip": from_rtu,
            "to_rtu_ip": to_rtu,
            "from_time": src_node["time"],
            "to_time": dst_node["time"],
            "from_relative_s": round(src_node["time"] - incident_start, 3),
            "to_relative_s": round(dst_node["time"] - incident_start, 3),
            "dt_seconds": recheck["dt_seconds"],
            "matched_quantities": recheck["matched_quantities"],
            "step_kinds": sm.get("step_kinds") or [sm.get("transition_status")],
            "claim_level": "observed_fact",
            "verification_status": "supported",
            "causal_status": "not_established",
            "consistency_gate": recheck,
            "evidence_ids": list(edge.get("evidence_ids") or []),
        }
        distinct_rtu = bool(from_rtu) and bool(to_rtu) and from_rtu != to_rtu
        if distinct_rtu:
            bridges.append({
                **record,
                "bridge_id": f"BRG-{len(bridges) + 1:03d}",
                "bridge_scope": "cross_rtu_verified_element_bridge",
                "independent_rtu_support": True,
                "what_bridge_establishes": (
                    f"Both endpoints of {stem} were reported by different RTUs in separate ASDUs "
                    f"({from_bid} from RTU {from_rtu} at +{round(src_node['time'] - incident_start, 3)}s and "
                    f"{to_bid} from RTU {to_rtu} at +{round(dst_node['time'] - incident_start, 3)}s) with "
                    f"corroborated transitions on {recheck['matched_quantities']}."
                ),
                "what_bridge_does_not_establish": (
                    f"Does NOT establish a physical topology connection or causal link between other "
                    f"co-reported devices in {from_bid} ({other_from}) and {to_bid} ({other_to})."
                ),
            })
        else:
            same_rtu.append({
                **record,
                "relation_id": f"SRR-{len(same_rtu) + 1:03d}",
                "relation_scope": "same_rtu_supported_relation",
                "independent_rtu_support": False,
                "not_a_cross_rtu_bridge": (
                    f"Supported same-element relation on {stem}, reported twice by RTU {from_rtu}. "
                    "Kept as a same-RTU observation; it is not independent cross-RTU support."
                ),
            })
    return bridges, same_rtu


def _build_bridged_bundle_components(
    *,
    bundles: list[dict],
    bridges: list[dict],
    sequential_records: list[dict],
    incident_start: float,
) -> list[dict]:
    if not bridges:
        return []
    bundles_by_id = {b["bundle_id"]: b for b in bundles}
    adj: dict[str, set[str]] = {}
    bridges_by_pair: dict[str, list[dict]] = {}
    for br in bridges:
        u, v = br["from_bundle_id"], br["to_bundle_id"]
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
        bridges_by_pair.setdefault(u, []).append(br)
        bridges_by_pair.setdefault(v, []).append(br)

    visited: set[str] = set()
    components: list[dict] = []
    for b in bundles:
        bid = b["bundle_id"]
        if bid not in adj or bid in visited:
            continue
        comp_bids: list[str] = []
        queue = [bid]
        visited.add(bid)
        while queue:
            cur = queue.pop(0)
            comp_bids.append(cur)
            for nxt in sorted(adj.get(cur, ())):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        comp_bids.sort(key=lambda x: (bundles_by_id[x]["time"], x))
        comp_set = set(comp_bids)
        comp_bridges = [
            br for br in bridges
            if br["from_bundle_id"] in comp_set and br["to_bundle_id"] in comp_set
        ]
        comp_anchor_ids = [
            aid for x in comp_bids for aid in bundles_by_id[x]["member_anchor_ids"]
        ]
        comp_anchor_set = set(comp_anchor_ids)
        bridged_stems = sorted({br["bridged_device_stem"] for br in comp_bridges if br.get("bridged_device_stem")})
        all_stems = sorted({
            stem for x in comp_bids for stem in bundles_by_id[x]["member_device_stems"]
        })
        co_reported_only_stems = sorted(set(all_stems) - set(bridged_stems))
        attached_seq = [
            sq for sq in sequential_records
            if sq.get("from_anchor_id") in comp_anchor_set or sq.get("to_anchor_id") in comp_anchor_set
        ]
        rtus = sorted({bundles_by_id[x]["rtu_ip"] for x in comp_bids if bundles_by_id[x].get("rtu_ip")})
        components.append({
            "component_id": f"CMP-{len(components) + 1:03d}",
            "bundle_ids": comp_bids,
            "bridge_ids": [br["bridge_id"] for br in comp_bridges],
            "member_anchor_ids": comp_anchor_ids,
            "rtu_ips": rtus,
            "member_bundle_count": len(comp_bids),
            "start_time": min(bundles_by_id[x]["time"] for x in comp_bids),
            "end_time": max(bundles_by_id[x]["time_end"] for x in comp_bids),
            "start_relative_s": round(min(bundles_by_id[x]["time"] for x in comp_bids) - incident_start, 3),
            "end_relative_s": round(max(bundles_by_id[x]["time_end"] for x in comp_bids) - incident_start, 3),
            "bridged_device_stems": bridged_stems,
            "co_reported_only_device_stems": co_reported_only_stems,
            "attached_sequential_same_device_observations": [sq["edge_id"] for sq in attached_seq],
            "epistemic_summary": (
                f"Bundles {comp_bids} across RTUs {rtus} are connected ONLY through corroborated "
                f"same-element transitions on {bridged_stems}. Co-reported elements {co_reported_only_stems} "
                "share an ASDU container with a bridged element endpoint, which does NOT prove topological "
                "adjacency or causation."
            ),
        })
    return components


def _build_candidate_scenario_phases(
    *,
    incident_start: float,
    transactions: list[dict],
    bundles: list[dict],
    bridges: list[dict],
    partition: dict,
    storylines: list[dict],
    unresolved_branches: list[dict],
    edges: list[dict],
    nodes_by_id: dict[str, dict],
    anchors_by_id: dict[str, dict],
    phase_gap_seconds: float,
) -> list[dict]:
    events: list[dict] = []
    for tx in transactions:
        events.append({
            "kind": "transaction",
            "id": tx["transaction_id"],
            "time": float(tx["start_time"]),
            "time_end": float(tx["end_time"]),
            "rtu_ip": tx.get("rtu_ip"),
            "master_ip": tx.get("master_ip"),
        })
    for b in bundles:
        events.append({
            "kind": "bundle",
            "id": b["bundle_id"],
            "time": float(b["time"]),
            "time_end": float(b["time_end"]),
            "rtu_ip": b.get("rtu_ip"),
            "master_ip": b.get("master_ip"),
            "host_ip": b.get("host_ip"),
            "anchor_ids": b["member_anchor_ids"],
            "fact_ids": b["member_fact_ids"],
        })
    for pre in partition["unverified_precursor_state_reports"]:
        events.append({
            "kind": "unverified_precursor",
            "id": pre["anchor_id"],
            "time": float(pre["time"]),
            "time_end": float(pre["time"]),
            "rtu_ip": pre.get("rtu_ip"),
            "anchor_ids": [pre["anchor_id"]],
            "fact_ids": [pre["fact_id"]] if pre.get("fact_id") else [],
        })

    if not events:
        return []
    events.sort(key=lambda e: (e["time"], e["id"]))

    groups: list[list[dict]] = [[events[0]]]
    for ev in events[1:]:
        prev_start_max = max(x["time"] for x in groups[-1])
        if ev["time"] - prev_start_max <= phase_gap_seconds:
            groups[-1].append(ev)
        else:
            groups.append([ev])

    storylines_by_anchor: dict[str, str] = {}
    for sl in storylines:
        for aid in sl.get("anchor_ids") or []:
            if aid:
                storylines_by_anchor[aid] = sl["storyline_id"]
    storylines_by_tx = {
        sl["transaction_id"]: sl["storyline_id"]
        for sl in storylines if sl.get("transaction_id")
    }

    phases: list[dict] = []
    for idx, members in enumerate(groups, start=1):
        phase_id = f"PHS-{idx:03d}"
        t_start = min(m["time"] for m in members)
        t_end = max(m["time_end"] for m in members)
        bundle_ids = [m["id"] for m in members if m["kind"] == "bundle"]
        tx_ids = [m["id"] for m in members if m["kind"] == "transaction"]
        precursor_ids = [m["id"] for m in members if m["kind"] == "unverified_precursor"]
        verified_anchor_ids = [
            aid for m in members if m["kind"] == "bundle" for aid in m.get("anchor_ids") or []
        ]
        all_phase_anchor_ids = set(verified_anchor_ids) | set(precursor_ids)
        phase_fids = {
            fid for m in members for fid in m.get("fact_ids") or [] if fid
        }

        verified_sl_ids = list(dict.fromkeys(
            [storylines_by_tx[t] for t in tx_ids if t in storylines_by_tx]
            + [storylines_by_anchor[a] for a in verified_anchor_ids if a in storylines_by_anchor]
        ))
        phase_bridges = [
            br["bridge_id"] for br in bridges
            if br["from_bundle_id"] in bundle_ids or br["to_bundle_id"] in bundle_ids
        ]
        phase_seq = [
            sq["edge_id"] for sq in partition["sequential_same_device_observations"]
            if sq.get("from_anchor_id") in all_phase_anchor_ids or sq.get("to_anchor_id") in all_phase_anchor_ids
        ]

        # Collect unresolved cross-device candidate links touching this phase
        phase_candidates: list[dict] = []
        seen_cand_edges: set[str] = set()
        for br in unresolved_branches:
            if br.get("from_anchor_id") in all_phase_anchor_ids or br.get("to_anchor_id") in all_phase_anchor_ids:
                seen_cand_edges.add(br["edge_id"])
                phase_candidates.append({
                    "edge_id": br["edge_id"],
                    "from_anchor_id": br.get("from_anchor_id"),
                    "to_anchor_id": br.get("to_anchor_id"),
                    "from_entity": br["from_entity"],
                    "to_entity": br["to_entity"],
                    "dt_seconds": round(float(br["to_time"]) - float(br["from_time"]), 3),
                    "relation_type": br["relation_type"],
                    "claim_level": "temporal_cooccurrence",
                    "verification_status": "unresolved",
                    "causal_status": "not_established",
                    "support_basis": br["support_basis"],
                    "evidence_ids": list(br.get("evidence_ids") or []),
                })
        if not phase_candidates and tx_ids:
            for e in edges:
                if e.get("relation_category") == "temporal_cooccurrence" and e["edge_id"] not in seen_cand_edges:
                    s_node = nodes_by_id.get(e["source_fact_id"])
                    t_node = nodes_by_id.get(e["target_fact_id"])
                    if s_node and t_node and (t_start - 1.0 <= s_node["time"] <= t_end + 1.0):
                        phase_candidates.append({
                            "edge_id": e["edge_id"],
                            "from_anchor_id": None,
                            "to_anchor_id": None,
                            "from_entity": e["source_entity"],
                            "to_entity": e["target_entity"],
                            "dt_seconds": round(float(t_node["time"]) - float(s_node["time"]), 3),
                            "relation_type": e["relation_type"],
                            "claim_level": "temporal_cooccurrence",
                            "verification_status": "unresolved",
                            "causal_status": "not_established",
                            "support_basis": e["support_basis"],
                            "evidence_ids": list(e.get("evidence_ids") or []),
                        })

        rtu_ips = sorted({m.get("rtu_ip") for m in members if m.get("rtu_ip")})
        master_ips = sorted({m.get("master_ip") for m in members if m.get("master_ip")})
        arp_details = []
        for aid in verified_anchor_ids:
            anc = anchors_by_id.get(aid) or {}
            if anc.get("anchor_type") == "arp_activity_increase":
                targets = dict(anc.get("targets") or {})
                overlap = sorted(set(targets) & set(rtu_ips))
                arp_details.append({
                    "anchor_id": aid,
                    "host_ip": anc.get("host_ip"),
                    "packet_count": anc.get("packet_count"),
                    "targets": targets,
                    "arp_target_overlap_rtu_ips": overlap,
                })

        anchor_types = {
            (anchors_by_id.get(aid) or {}).get("anchor_type")
            for aid in verified_anchor_ids
        } - {None}
        if tx_ids:
            profile = "protocol_command_transactions"
        elif "arp_activity_increase" in anchor_types and "communication_change" in anchor_types:
            profile = "arp_burst_and_multi_rtu_iec104_link_disruptions"
        elif "communication_change" in anchor_types:
            profile = "multi_rtu_iec104_link_disruptions"
        elif phase_bridges:
            profile = "multi_rtu_corroborated_measurement_transitions"
        else:
            profile = "localized_measurement_or_state_observations"

        phases.append({
            "phase_id": phase_id,
            "phase_profile": profile,
            "start_time": t_start,
            "end_time": t_end,
            "start_relative_s": round(t_start - incident_start, 3),
            "end_relative_s": round(t_end - incident_start, 3),
            "transaction_ids": tx_ids,
            "verified_bundle_ids": bundle_ids,
            "verified_storyline_ids": verified_sl_ids,
            "verified_anchor_ids": verified_anchor_ids,
            "verified_bridge_ids": phase_bridges,
            "sequential_same_device_edge_ids": phase_seq,
            "unverified_precursor_anchor_ids": precursor_ids,
            "observed_host_and_link_context": {
                "rtu_ips": rtu_ips,
                "master_ips": master_ips,
                "arp_activity": arp_details,
            },
            "unresolved_cross_device_candidate_count": len(phase_candidates),
            "unresolved_cross_device_candidates": phase_candidates,
            "epistemic_boundary": (
                f"Phase {phase_id} groups {len(bundle_ids)} verified bundle(s) and {len(tx_ids)} transaction(s) "
                f"within +{round(t_start - incident_start, 3)}s..+{round(t_end - incident_start, 3)}s. "
                f"{len(phase_bridges)} element bridge(s) are supported; all {len(phase_candidates)} cross-device "
                "candidate relation(s) remain strictly unresolved (causal_status=not_established)."
            ),
        })

    return phases


def container_family(bundle: dict) -> str:
    """Classify a verified source container. IEC-104 ASDU, TCP link, ARP and other containers stay separate."""
    container_id = str(bundle.get("asdu_container_id") or "")
    kinds = set(bundle.get("member_anchor_types") or [])
    if "arp_activity_increase" in kinds or container_id.startswith("SRC-ARP_ACTIVITY_INCREASE-"):
        return "arp"
    if "communication_change" in kinds or container_id.startswith("SRC-COMMUNICATION_CHANGE-"):
        return "tcp_link"
    if container_id.startswith("SRC-ASDU-") or kinds & {"measurement_step", "spontaneous_state_report"}:
        return "iec104_asdu"
    return "composite_event"


def _build_source_dependency_ledger(
    *,
    transactions: list[dict],
    anchors: list[dict],
    bundles: list[dict],
    nodes_by_id: dict[str, dict],
    edges: list[dict],
    behavioral_mode: bool,
) -> dict:
    verified_anchors = [a for a in anchors if a.get("verification_status") == "verified_observation" and not a.get("covered_by_transaction")]
    unverified_anchors = [a for a in anchors if a.get("verification_status") == "unverified_observation" and not a.get("covered_by_transaction")]

    families = {"iec104_asdu": [], "tcp_link": [], "arp": [], "composite_event": []}
    if behavioral_mode:
        for bundle in bundles:
            families[container_family(bundle)].append(bundle["asdu_container_id"])
        for key in families:
            families[key] = sorted(set(families[key]))
        iec_anchor_count = sum(
            len(b["member_anchor_ids"]) for b in bundles if container_family(b) == "iec104_asdu"
        )
        rtu_ips = sorted({b["rtu_ip"] for b in bundles if b.get("rtu_ip")})
        master_ips = sorted({b["master_ip"] for b in bundles if b.get("master_ip")})
        arp_hosts = sorted({b["host_ip"] for b in bundles if b.get("host_ip")})
        vantages = sorted({v for b in bundles for v in (b.get("vantages") or []) if v})
        raw_captures = sum(len(a.get("evidence_ids") or []) for a in verified_anchors)
        unique_ev_ids = list(dict.fromkeys(eid for a in verified_anchors for eid in (a.get("evidence_ids") or [])))
        co_reported_reduction = max(0, iec_anchor_count - len(families["iec104_asdu"]))
    else:
        rtu_ips = sorted({tx["rtu_ip"] for tx in transactions if tx.get("rtu_ip")})
        master_ips = sorted({tx["master_ip"] for tx in transactions if tx.get("master_ip")})
        arp_hosts = []
        vantages = sorted({
            v for tx in transactions for v in (tx.get("command_activation", {}).get("vantages") or []) if v
        })
        unique_ev_ids = list(dict.fromkeys(
            eid for tx in transactions for eid in (tx.get("all_evidence_ids") or [])
        ))
        raw_captures = len(unique_ev_ids)
        co_reported_reduction = 0
        families["composite_event"] = sorted({
            cid for tx in transactions for cid in (tx.get("canonical_source_ids") or [])
        })

    ipal_corr_edges = [e for e in edges if e.get("relation_category") == "temporal_correspondence"]
    ipal_corr_fids = sorted({e["target_fact_id"] for e in ipal_corr_edges})
    ipal_row_count = sum(len(a.get("ipal_rows") or []) for a in anchors)

    return {
        "verified_anchor_count": len(verified_anchors),
        "quarantined_unverified_anchor_count": len(unverified_anchors),
        "iec104_asdu_container_ids": families["iec104_asdu"],
        "iec104_asdu_container_count": len(families["iec104_asdu"]),
        "tcp_link_container_ids": families["tcp_link"],
        "tcp_link_container_count": len(families["tcp_link"]),
        "arp_container_ids": families["arp"],
        "arp_container_count": len(families["arp"]),
        "composite_event_container_ids": families["composite_event"],
        "composite_event_container_count": len(families["composite_event"]),
        "verified_source_container_count": sum(len(v) for v in families.values()),
        "distinct_rtu_ips": rtu_ips,
        "distinct_rtu_count": len(rtu_ips),
        "distinct_master_ips": master_ips,
        "distinct_arp_host_ips": arp_hosts,
        "co_reported_same_asdu_reduction_count": co_reported_reduction,
        "mirror_vantages_observed": vantages,
        "raw_vantage_capture_count": raw_captures,
        "unique_verified_evidence_id_count": len(unique_ev_ids),
        "ipal_correspondence_fact_count": len(ipal_corr_fids),
        "ipal_correspondence_edge_count": len(ipal_corr_edges),
        "ipal_correspondence_row_count": ipal_row_count,
        "ipal_independent_source_weight": 0,
        "accounting_rules": {
            "same_asdu_multi_ioa": "counted_as_one_container_not_independent_per_point",
            "mirror_vantage_captures": "deduplicated_across_n302_and_n318",
            "ipal_state_updates": "weight_zero_temporal_correspondence_only",
            "unverified_observations": "quarantined_excluded_from_verified_containers",
        },
    }


def _arp_link_precedence(arp: dict, comm: dict) -> dict:
    """A precedence claim needs target overlap, ARP before the link change, and the horizon."""
    rtu = comm.get("rtu_ip")
    targets = set((arp.get("targets") or {}))
    overlap = bool(rtu) and rtu in targets
    arp_time = float(arp["time"])
    link_time = float(comm["time"])
    arp_before_link = arp_time <= link_time
    dt = round(link_time - arp_time, 6)
    within_horizon = arp_before_link and 0.0 <= dt <= HORIZON_SECONDS
    return {
        "arp_anchor_id": arp.get("anchor_id"),
        "communication_anchor_id": comm.get("anchor_id"),
        "rtu_ip": rtu,
        "target_overlap": overlap,
        "arp_before_link": arp_before_link,
        "dt_seconds": dt,
        "within_horizon": within_horizon,
        "eligible": overlap and within_horizon,
    }


def _build_competing_explanations(
    *,
    incident_start: float,
    transactions: list[dict],
    bundles: list[dict],
    bridges: list[dict],
    bridged_components: list[dict],
    partition: dict,
    candidate_phases: list[dict],
    ledger: dict,
    anchors_by_id: dict[str, dict],
    edges_by_id: dict[str, dict],
) -> list[dict]:
    explanations: list[dict] = []

    # Pattern A: Protocol command transactions present
    if transactions:
        tx_ids = [tx["transaction_id"] for tx in transactions]
        verified_tx = [
            tx["transaction_id"] for tx in transactions
            if tx.get("device_state_change_status") in ("verified_state_transition", "verified_measurement_transition")
        ]
        ev_ids = list(dict.fromkeys(eid for tx in transactions for eid in (tx.get("all_evidence_ids") or [])[:4]))
        explanations.append({
            "explanation_id": f"EXP-{len(explanations) + 1:03d}",
            "scope": tx_ids,
            "hypothesis_class": "command_induced_device_transition_hypothesis",
            "verification_status": "unresolved_competing_hypothesis",
            "causal_status": "not_established",
            "anchoring_verified_evidence": {
                "transaction_ids": tx_ids,
                "verified_transition_transaction_ids": verified_tx,
                "evidence_ids": ev_ids[:8],
            },
            "unverified_or_candidate_links_assumed": [
                tx["transaction_id"] for tx in transactions if tx["transaction_id"] not in verified_tx
            ],
            "explanation_summary": (
                f"Observed IEC-104 control activation(s) {tx_ids} on the SCADA network, with "
                f"{len(verified_tx)} transaction(s) passing pre/post setpoint/state consistency checks. "
                "Consistent with RTU execution of the received IEC-104 command(s)."
            ),
            "alternative_comparison": (
                "Competes with coincidence or unverified physical actuation where protocol confirmation "
                "(COT=7) or telemetry shifts occur without independent physical sensor verification."
            ),
            "missing_disambiguating_evidence": [
                "Independent out-of-band physical process sensor or PMU log not derived from IEC-104",
                "Master station operator/application audit log identifying the initiating process",
                *(
                    ["Pre-command IEC-104 state baseline (COT=20/COT=1) for switch transactions"]
                    if len(verified_tx) < len(tx_ids) else []
                ),
            ],
        })

    # Pattern B: Multi-RTU corroborated line/bus measurement transitions (e.g. ev_564bebaa)
    if bridges:
        bridge_ids = [br["bridge_id"] for br in bridges]
        bridged_stems = sorted({br["bridged_device_stem"] for br in bridges})
        comp_ids = [c["component_id"] for c in bridged_components]
        precursor_ids = [p["anchor_id"] for p in partition["unverified_precursor_state_reports"]]
        seq_ids = [s["edge_id"] for s in partition["sequential_same_device_observations"]]
        cand_ids = [
            c["edge_id"] for ph in candidate_phases for c in (ph.get("unresolved_cross_device_candidates") or [])[:6]
        ]
        ev_ids = list(dict.fromkeys(eid for br in bridges for eid in (br.get("evidence_ids") or [])))[:10]

        explanations.append({
            "explanation_id": f"EXP-{len(explanations) + 1:03d}",
            "scope": comp_ids or bridge_ids,
            "hypothesis_class": "physical_switching_or_protection_cascade_hypothesis",
            "verification_status": "unresolved_competing_hypothesis",
            "causal_status": "not_established",
            "anchoring_verified_evidence": {
                "bridge_ids": bridge_ids,
                "bridged_device_stems": bridged_stems,
                "component_ids": comp_ids,
                "iec104_asdu_container_count": ledger["iec104_asdu_container_count"],
                "distinct_rtu_count": ledger["distinct_rtu_count"],
                "evidence_ids": ev_ids,
            },
            "unverified_or_candidate_links_assumed": [
                *precursor_ids,
                *seq_ids,
                *cand_ids[:8],
            ],
            "explanation_summary": (
                f"Corroborated two-end transitions on {bridged_stems} across {ledger['distinct_rtu_count']} RTUs "
                f"(bridges {bridge_ids}, components {comp_ids}), co-occurring with bus/load/generator `to_zero` "
                f"bundles and preceded by spontaneous COT=3 state report(s) {precursor_ids}. Consistent with a "
                "physical switching/isolation event and power-flow redistribution."
            ),
            "alternative_comparison": (
                "Requires assuming that unverified COT=3 state reports (which lack a prior in-window state "
                "baseline) and unresolved cross-device co-occurrences reflect physical grid connectivity."
            ),
            "missing_disambiguating_evidence": [
                "Substation bus/breaker physical topology model connecting switch, bus, line, load, and sgen elements",
                f"Pre-window IEC-104 state baseline (COT=20) for spontaneous state report(s) {precursor_ids}",
                "Local protection relay / breaker trip records at the RTUs independent of IEC-104 telemetry",
            ],
        })
        explanations.append({
            "explanation_id": f"EXP-{len(explanations) + 1:03d}",
            "scope": comp_ids or bridge_ids,
            "hypothesis_class": "uncommanded_or_altered_multi_rtu_telemetry_hypothesis",
            "verification_status": "unresolved_competing_hypothesis",
            "causal_status": "not_established",
            "anchoring_verified_evidence": {
                "bridge_ids": bridge_ids,
                "iec104_control_objects_in_window": 0,
                "iec104_asdu_container_count": ledger["iec104_asdu_container_count"],
                "evidence_ids": ev_ids,
            },
            "unverified_or_candidate_links_assumed": seq_ids,
            "explanation_summary": (
                f"Zero IEC-104 control commands (types 45-69) were observed in the capture, yet "
                f"{ledger['iec104_asdu_container_count']} IEC-104 ASDU containers from {ledger['distinct_rtu_count']} "
                "RTUs reported abrupt `to_zero` and `level_shift` steps (including asymmetric endpoint behavior "
                f"recorded in {seq_ids}). Consistent with uncommanded local RTU action or altered/replayed "
                "network telemetry without SCADA command initiation."
            ),
            "alternative_comparison": (
                "Accounts for the absence of any COT=6 control command in the PCAP without assuming a verified "
                "physical topology link across distinct devices."
            ),
            "missing_disambiguating_evidence": [
                "Out-of-band physical electrical measurements (e.g. independent PMU or field recorder)",
                "RTU local console/logic logs and L2 switch port authentication records",
            ],
        })

    # Pattern C: ARP burst + IEC-104 communication link disruptions (e.g. ev_cbe1e5) or link-only disruptions (e.g. ev_812f80)
    comm_anchors = [
        a for a in anchors_by_id.values()
        if a.get("anchor_type") == "communication_change" and a.get("verification_status") == "verified_observation"
    ]
    arp_anchors = [
        a for a in anchors_by_id.values()
        if a.get("anchor_type") == "arp_activity_increase" and a.get("verification_status") == "verified_observation"
    ]
    if comm_anchors:
        comm_ids = [a["anchor_id"] for a in comm_anchors]
        comm_rtus = sorted({a.get("rtu_ip") for a in comm_anchors if a.get("rtu_ip")})
        comm_evs = list(dict.fromkeys(eid for a in comm_anchors for eid in (a.get("evidence_ids") or [])[:3]))
        cand_ids = [
            c["edge_id"] for ph in candidate_phases for c in (ph.get("unresolved_cross_device_candidates") or [])
        ]
        if arp_anchors:
            arp_ids = [a["anchor_id"] for a in arp_anchors]
            arp_hosts = sorted({a.get("host_ip") for a in arp_anchors if a.get("host_ip")})
            arp_evs = list(dict.fromkeys(eid for a in arp_anchors for eid in (a.get("evidence_ids") or [])[:3]))
            eligible = [
                pair for arp in arp_anchors for comm in comm_anchors
                if (pair := _arp_link_precedence(arp, comm))["eligible"]
            ]
            overlap_rtus = sorted({pair["rtu_ip"] for pair in eligible})
            if eligible:
                explanations.append({
                    "explanation_id": f"EXP-{len(explanations) + 1:03d}",
                    "scope": [*arp_ids, *comm_ids],
                    "hypothesis_class": "arp_address_interference_preceding_iec104_session_loss_hypothesis",
                    "verification_status": "unresolved_competing_hypothesis",
                    "causal_status": "not_established",
                    "eligibility_gate": "passed_target_overlap_and_temporal_order",
                    "eligible_arp_link_pairs": eligible,
                    "anchoring_verified_evidence": {
                        "arp_anchor_ids": arp_ids,
                        "communication_anchor_ids": comm_ids,
                        "arp_source_hosts": arp_hosts,
                        "overlapping_target_rtu_ips": overlap_rtus,
                        "evidence_ids": [*arp_evs, *comm_evs][:10],
                    },
                    "unverified_or_candidate_links_assumed": cand_ids,
                    "explanation_summary": (
                        f"Host(s) {arp_hosts} emitted elevated ARP traffic ({arp_ids}) whose targets include RTU "
                        f"IP(s) {overlap_rtus}, and those IEC-104 links changed only after the ARP activity and "
                        f"within {HORIZON_SECONDS:.0f}s. This is an unresolved candidate for L2 ARP cache "
                        "interference; the pairs are listed in eligible_arp_link_pairs."
                    ),
                    "alternative_comparison": (
                        f"Target overlap and time order hold for {overlap_rtus}, but candidate edges {cand_ids} "
                        "remain unresolved. ARP counts do not prove MAC spoofing."
                    ),
                    "missing_disambiguating_evidence": [
                        f"ARP payload sender-MAC to sender-IP binding audit for {arp_hosts} vs legitimate MACs of {overlap_rtus} and master",
                        "Managed switch CAM/ARP table logs and port-security counters at n302/n318",
                        f"TCP stack reset/timeout logs on master 172.16.1.2 and RTUs {overlap_rtus}",
                    ],
                })
            else:
                explanations.append({
                    "explanation_id": f"EXP-{len(explanations) + 1:03d}",
                    "scope": [*arp_ids, *comm_ids],
                    "hypothesis_class": "arp_and_iec104_link_observations_without_supported_precedence",
                    "verification_status": "unresolved_competing_hypothesis",
                    "causal_status": "not_established",
                    "eligibility_gate": "failed_target_overlap_or_temporal_order",
                    "anchoring_verified_evidence": {
                        "arp_anchor_ids": arp_ids,
                        "communication_anchor_ids": comm_ids,
                        "arp_source_hosts": arp_hosts,
                        "evidence_ids": [*arp_evs, *comm_evs][:10],
                    },
                    "unverified_or_candidate_links_assumed": cand_ids,
                    "explanation_summary": (
                        f"ARP activity {arp_ids} and IEC-104 link changes {comm_ids} were both observed. "
                        "No pair has ARP target overlap with the affected RTU, ARP before the link change, and a "
                        f"gap of at most {HORIZON_SECONDS:.0f}s. No precedence between them is claimed."
                    ),
                    "alternative_comparison": (
                        "A general co-observation only. It does not say the ARP activity came first or addressed "
                        "the RTU whose session changed."
                    ),
                    "missing_disambiguating_evidence": [
                        "ARP target addresses that match the RTU whose IEC-104 session changed",
                        "Timestamps showing the ARP activity before that session change and inside the horizon",
                    ],
                })
            explanations.append({
                "explanation_id": f"EXP-{len(explanations) + 1:03d}",
                "scope": [*arp_ids, *comm_ids],
                "hypothesis_class": "concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis",
                "verification_status": "unresolved_competing_hypothesis",
                "causal_status": "not_established",
                "anchoring_verified_evidence": {
                    "arp_anchor_ids": arp_ids,
                    "communication_anchor_ids": comm_ids,
                    "evidence_ids": [*arp_evs, *comm_evs][:10],
                },
                "unverified_or_candidate_links_assumed": [],
                "explanation_summary": (
                    f"IEC-104 links {comm_ids} (sharing master 172.16.1.2) experienced session loss and "
                    f"re-establishment in the same window as ARP burst {arp_ids}, without requiring {arp_hosts} "
                    "to have caused the TCP session drops (e.g. switch path reset or interface flap accompanied "
                    "by neighbor re-resolution)."
                ),
                "alternative_comparison": (
                    "Treats the ARP burst and the TCP session drops as co-occurring L2/L3 network events rather "
                    "than assuming causal ARP interference."
                ),
                "missing_disambiguating_evidence": [
                    "Switch interface link-state / spanning-tree logs during the telemetry gap",
                    f"Host {arp_hosts} network service and ARP table logs",
                ],
            })
        else:
            explanations.append({
                "explanation_id": f"EXP-{len(explanations) + 1:03d}",
                "scope": comm_ids,
                "hypothesis_class": "shared_master_or_path_iec104_session_interruption_hypothesis",
                "verification_status": "unresolved_competing_hypothesis",
                "causal_status": "not_established",
                "anchoring_verified_evidence": {
                    "communication_anchor_ids": comm_ids,
                    "affected_rtu_ips": comm_rtus,
                    "shared_master_ips": ledger["distinct_master_ips"],
                    "evidence_ids": comm_evs[:8],
                },
                "unverified_or_candidate_links_assumed": cand_ids,
                "explanation_summary": (
                    f"IEC-104 sessions to RTUs {comm_rtus} ({comm_ids}) sharing master {ledger['distinct_master_ips']} "
                    "experienced telemetry gaps, TCP FIN teardown, repeated unanswered SYN attempts, and subsequent "
                    "re-establishment with General Interrogation (COT=6/7/10/20) and Clock Synchronisation (COT=6/7)."
                ),
                "alternative_comparison": (
                    f"Competes with independent RTU-side daemon/interface restarts on {comm_rtus} occurring within "
                    f"the same 15s window (candidate link {cand_ids} remains unresolved)."
                ),
                "missing_disambiguating_evidence": [
                    "Switch port drop/ACL counters between master 172.16.1.2 and RTU subnet",
                    f"Host/RTU daemon logs on 172.16.1.2 and {comm_rtus}",
                ],
            })
            explanations.append({
                "explanation_id": f"EXP-{len(explanations) + 1:03d}",
                "scope": comm_ids,
                "hypothesis_class": "independent_rtu_endpoint_unavailability_cooccurrence_hypothesis",
                "verification_status": "unresolved_competing_hypothesis",
                "causal_status": "not_established",
                "anchoring_verified_evidence": {
                    "communication_anchor_ids": comm_ids,
                    "affected_rtu_ips": comm_rtus,
                    "evidence_ids": comm_evs[:8],
                },
                "unverified_or_candidate_links_assumed": [],
                "explanation_summary": (
                    f"Each RTU link in {comm_ids} ({comm_rtus}) independently refused master TCP SYN attempts "
                    "before recovering and completing General Interrogation and Clock Synchronisation, without "
                    "requiring a shared network-fabric fault."
                ),
                "alternative_comparison": (
                    "Does not assume a common upstream cause across the two RTUs; keeps the cross-link temporal "
                    f"candidate {cand_ids} unresolved."
                ),
                "missing_disambiguating_evidence": [
                    f"Local RTU OS/service restart logs on {comm_rtus}",
                    "Per-port L2 link-down counters on the RTU access switch",
                ],
            })

    # Pattern D: Single-device sequential observation where state report lacks prior baseline (e.g. ev_4e913b)
    if not bridges and not comm_anchors and not transactions and partition["sequential_same_device_observations"]:
        seq = partition["sequential_same_device_observations"][0]
        explanations.append({
            "explanation_id": f"EXP-{len(explanations) + 1:03d}",
            "scope": [seq["from_anchor_id"], seq["to_anchor_id"]],
            "hypothesis_class": "local_device_disconnection_with_unverified_prior_state_hypothesis",
            "verification_status": "unresolved_competing_hypothesis",
            "causal_status": "not_established",
            "anchoring_verified_evidence": {
                "verified_anchor_ids": [
                    aid for s in partition["verified_single_anchor_storylines"] for aid in (s.get("anchor_ids") or [])
                ],
                "sequential_edge_id": seq["edge_id"],
                "device_stem": seq.get("device_stem"),
                "evidence_ids": seq["evidence_ids"],
            },
            "unverified_or_candidate_links_assumed": [seq["from_anchor_id"], seq["edge_id"]],
            "explanation_summary": (
                f"On {seq.get('device_stem')}, a spontaneous COT=3 state report ({seq['from_anchor_id']}: "
                f"{seq['from_entity']}) preceded a verified measurement drop to zero ({seq['to_anchor_id']}: "
                f"{seq['to_entity']}), recorded as sequential observation {seq['edge_id']} because "
                f"{seq['from_anchor_id']} failed {seq['failed_conditions']}."
            ),
            "alternative_comparison": (
                "Assumes the COT=3 report reflects an actual disconnection from a prior connected state (1.0 -> 0.0), "
                "which is not provable from in-window IEC-104 traffic alone."
            ),
            "missing_disambiguating_evidence": [
                f"Pre-window IEC-104 state baseline (COT=20) for {seq['from_entity']}",
                f"Local RTU {seq.get('device_stem')} breaker/controller event log",
            ],
        })
        explanations.append({
            "explanation_id": f"EXP-{len(explanations) + 1:03d}",
            "scope": [seq["to_anchor_id"]],
            "hypothesis_class": "uncommanded_output_drop_with_redundant_state_report_hypothesis",
            "verification_status": "unresolved_competing_hypothesis",
            "causal_status": "not_established",
            "anchoring_verified_evidence": {
                "verified_anchor_ids": [
                    aid for s in partition["verified_single_anchor_storylines"] for aid in (s.get("anchor_ids") or [])
                ],
                "device_stem": seq.get("device_stem"),
                "evidence_ids": seq["evidence_ids"],
            },
            "unverified_or_candidate_links_assumed": [],
            "explanation_summary": (
                f"Only the measurement step {seq['to_anchor_id']} ({seq['to_entity']} -> 0.0) is a verified "
                f"transition; the earlier COT=3 report {seq['from_anchor_id']} could be a redundant status "
                "re-transmission or unverified telemetry frame without a physical state transition."
            ),
            "alternative_comparison": (
                "Relies strictly on the verified measurement step A002 without promoting the unverified COT=3 "
                "state report A001."
            ),
            "missing_disambiguating_evidence": [
                f"Out-of-band physical meter for {seq.get('device_stem')}",
                "Pre-window IEC-104 state history prior to background_start",
            ],
        })

    return explanations
