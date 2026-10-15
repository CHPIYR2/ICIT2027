"""Cross-phase consistency checks for quality, behavioral transitions, and lineage.

1. `check_quality_consistency`:
   - Transaction gate, event-graph edge/node metadata, storyline status, and the
     report must agree on pre/post quality and COT test bits.
   - Behavioral anchor verification status (`verified_observation` vs
     `unverified_observation`), behavioral graph transition edges
     (`corroborated_same_device_behavioral_transition` vs
     `same_entity_sequential_observation`), behavioral storylines, and the
     report must all satisfy `evaluate_behavioral_relation_consistency()`.
   - Recorded in `quality_consistency.json`, strictly separate from evidence
     lineage checks.
2. `build_lineage_consistency_record`:
   - Summarizes timeline evidence lineage (`export_lineage_bundle`) and
     behavioral anchor point/sample lineage (`audit_anchor_lineage`) into a
     separate `lineage_consistency.json` record.
"""
from __future__ import annotations
from .behavior import evaluate_behavioral_relation_consistency

VERIFIED = ("verified_state_transition", "verified_measurement_transition")
VERIFIED_STORY = ("complete_with_verified_transition", "partial_missing_cot10_but_verified_measurement_transition")


def check_quality_consistency(
    tx_result: dict,
    event_graph: dict,
    storylines: dict,
    report: dict,
    *,
    anchor_result: dict | None = None,
    incident_synthesis: dict | None = None,
) -> dict:
    nodes = {n["fact_id"]: n for n in event_graph["nodes"]}
    edges = event_graph["edges"]
    edges_by_id = {e["edge_id"]: e for e in edges}
    stories = {s["transaction_id"]: s for s in storylines["storylines"] if s.get("transaction_id")}
    summaries = {t["transaction_id"]: t for t in report.get("transaction_summaries") or []}
    issues: list[dict] = []
    checks: list[dict] = []

    for tx in tx_result.get("transactions") or []:
        tx_id = tx["transaction_id"]
        mt = tx.get("measurement_transition")
        fb = (tx.get("protocol_state_feedback") or [None])[0]
        if mt is not None:
            gate, target_role, entity = mt.get("consistency_gate") or {}, "post_command_measurement", mt["measurement_entity"]
        elif fb is not None:
            gate, target_role, entity = fb.get("consistency_gate") or {}, "spontaneous_state_feedback", fb["entity"]
        else:
            continue
        passed = bool(gate.get("gate_passed"))
        status_verified = tx["device_state_change_status"] in VERIFIED

        target = next((n for n in nodes.values()
                       if n.get("transaction_id") == tx_id and n["role"] == target_role and n["entity"] == entity), None)
        inference_edges = [e for e in edges if e["relation_category"] == "inference_hypothesis"
                           and target is not None and e["target_fact_id"] == target["fact_id"]]
        graph_supported = any(e["claim_level"] == "supported_inference" for e in inference_edges)
        story = stories.get(tx_id)
        story_verified = bool(story and story["completeness_status"] in VERIFIED_STORY)
        story_supported_steps = bool(story and any(
            st["claim_level"] == "supported_inference" for st in story["confirmed_and_supported_steps"]))
        summary_gate = (summaries.get(tx_id) or {}).get("inference_gate") or {}

        row = {
            "transaction_id": tx_id,
            "transaction_gate_passed": passed,
            "transaction_status_verified": status_verified,
            "graph_supported_inference": graph_supported,
            "storyline_verified_status": story_verified,
            "storyline_has_supported_inference_step": story_supported_steps,
            "report_gate_passed": summary_gate.get("gate_passed"),
        }
        checks.append(row)
        if status_verified != passed:
            issues.append({"transaction_id": tx_id, "issue": "status_disagrees_with_transaction_gate"})
        if graph_supported != passed:
            issues.append({"transaction_id": tx_id, "issue": "graph_inference_disagrees_with_transaction_gate"})
        if story is not None and story_verified != passed:
            issues.append({"transaction_id": tx_id, "issue": "storyline_status_disagrees_with_transaction_gate"})
        if story_supported_steps and not passed:
            issues.append({"transaction_id": tx_id, "issue": "storyline_uses_inference_rejected_by_gate"})
        if summary_gate.get("gate_passed") != gate.get("gate_passed"):
            issues.append({"transaction_id": tx_id, "issue": "report_gate_disagrees_with_transaction_gate"})
        for key in ("pre_quality_invalid", "post_quality_invalid", "pre_quality_flags_set",
                    "post_quality_flags_set", "test_bits"):
            if summary_gate.get(key) != gate.get(key):
                issues.append({"transaction_id": tx_id, "issue": f"report_{key}_differs"})
        if target is not None:
            meta = target.get("protocol_meta") or {}
            node_iv = meta.get("quality_invalid", meta.get("post_quality_invalid"))
            if node_iv != gate.get("post_quality_invalid"):
                issues.append({"transaction_id": tx_id, "issue": "graph_node_post_quality_differs"})

    for edge in edges:
        if edge["claim_level"] == "supported_inference" and \
                edge.get("graph_consistency_gate_status") != "passed_noncausal_inference_gate":
            issues.append({"edge_id": edge["edge_id"], "issue": "supported_inference_without_passed_gate"})

    verified_in_report = len(report.get("verified_device_transitions") or [])
    verified_in_tx = sum(1 for tx in tx_result.get("transactions") or [] if tx["device_state_change_status"] in VERIFIED)
    if verified_in_report != verified_in_tx:
        issues.append({"issue": "report_verified_transition_count_differs",
                       "report": verified_in_report, "transactions": verified_in_tx})

    # Behavioral anchor, graph edge, storyline, and report consistency checks
    placed = event_graph.get("behavioral_anchor_facts") or {}
    behavioral_fids = {entry["fact_id"] for entry in placed.values() if entry.get("fact_id")}
    if not behavioral_fids:
        behavioral_fids = {
            n["fact_id"] for n in nodes.values()
            if n.get("role") != "ipal_correspondence" and (n.get("protocol_meta") or {}).get("anchor_id")
        }

    behavioral_anchor_checks: list[dict] = []
    anchors_by_id = {a["anchor_id"]: a for a in (anchor_result or {}).get("anchors") or []}
    for fid in sorted(behavioral_fids):
        node = nodes.get(fid)
        if node is None:
            continue
        meta = node.get("protocol_meta") or {}
        aid = meta.get("anchor_id")
        ver_status = meta.get("verification_status")
        q_good = meta.get("quality_good")
        sustained = meta.get("sustained_in_later_samples")
        ver_issues = list(meta.get("verification_issues") or [])
        anchor_rec = anchors_by_id.get(aid)
        matches_anchor = True
        if anchor_rec is not None:
            if (
                ver_status != anchor_rec.get("verification_status")
                or q_good != anchor_rec.get("quality_good")
                or sustained != anchor_rec.get("sustained_in_later_samples")
            ):
                matches_anchor = False
                issues.append({
                    "anchor_id": aid,
                    "fact_id": fid,
                    "issue": "graph_anchor_metadata_differs_from_anchor",
                })
        if ver_status == "verified_observation" and node.get("role") in ("spontaneous_state_report", "measurement_step"):
            if q_good is not True or sustained is not True or ver_issues:
                issues.append({
                    "anchor_id": aid,
                    "fact_id": fid,
                    "issue": "verified_anchor_fails_quality_or_persistence_requirements",
                    "quality_good": q_good,
                    "sustained_in_later_samples": sustained,
                    "verification_issues": ver_issues,
                })
        behavioral_anchor_checks.append({
            "anchor_id": aid,
            "fact_id": fid,
            "anchor_type": node.get("role"),
            "verification_status": ver_status,
            "quality_good": q_good,
            "sustained_in_later_samples": sustained,
            "verification_issues": ver_issues,
            "matches_anchor_record": matches_anchor,
        })

    behavioral_edge_checks: list[dict] = []
    rechecked_gates: dict[str, dict] = {}
    for edge in edges:
        src_fid, dst_fid = edge["source_fact_id"], edge["target_fact_id"]
        if src_fid not in behavioral_fids or dst_fid not in behavioral_fids:
            continue
        if (
            edge["relation_category"] not in ("measurement_state_transition", "sequential_observation")
            and edge["relation_type"] not in (
                "corroborated_same_device_behavioral_transition",
                "same_device_behavior_in_separate_asdu",
                "same_entity_sequential_observation",
            )
        ):
            continue
        recheck = evaluate_behavioral_relation_consistency(nodes[src_fid], nodes[dst_fid])
        rechecked_gates[edge["edge_id"]] = recheck
        stored_gate = edge.get("consistency_gate") or {}
        is_supported = (
            edge.get("verification_status") == "supported"
            or edge["relation_category"] == "measurement_state_transition"
            or edge["relation_type"] in (
                "corroborated_same_device_behavioral_transition",
                "same_device_behavior_in_separate_asdu",
            )
        )
        behavioral_edge_checks.append({
            "edge_id": edge["edge_id"],
            "source_fact_id": src_fid,
            "target_fact_id": dst_fid,
            "relation_type": edge["relation_type"],
            "relation_category": edge["relation_category"],
            "verification_status": edge.get("verification_status"),
            "graph_consistency_gate_status": edge.get("graph_consistency_gate_status"),
            "stored_gate_passed": stored_gate.get("gate_passed"),
            "recheck_gate_passed": recheck["gate_passed"],
            "recheck_failed_conditions": recheck["failed_conditions"],
        })
        if is_supported and not recheck["gate_passed"]:
            issues.append({
                "edge_id": edge["edge_id"],
                "issue": "supported_behavioral_edge_failed_consistency_gate",
                "failed_conditions": recheck["failed_conditions"],
            })
        if is_supported and edge.get("graph_consistency_gate_status") != "passed_behavioral_consistency_gate":
            issues.append({
                "edge_id": edge["edge_id"],
                "issue": "supported_behavioral_edge_missing_passed_gate_status",
            })
        if is_supported and edge["relation_type"] != "corroborated_same_device_behavioral_transition":
            issues.append({
                "edge_id": edge["edge_id"],
                "issue": "supported_behavioral_edge_wrong_relation_type",
                "relation_type": edge["relation_type"],
            })
        if not is_supported and recheck["gate_passed"]:
            issues.append({
                "edge_id": edge["edge_id"],
                "issue": "passed_behavioral_gate_not_marked_supported",
            })
        if stored_gate.get("gate_passed") != recheck["gate_passed"]:
            issues.append({
                "edge_id": edge["edge_id"],
                "issue": "behavioral_edge_stored_gate_disagrees_with_recheck",
            })

    behavioral_storyline_checks: list[dict] = []
    for sl in storylines.get("storylines") or []:
        if sl.get("storyline_kind") != "behavioral":
            continue
        spine_fids = sl["spine_fact_ids"]
        spine_nodes = [nodes[fid] for fid in spine_fids if fid in nodes]
        all_verified = all(
            (n.get("protocol_meta") or {}).get("verification_status") == "verified_observation"
            for n in spine_nodes
        )
        steps = sl.get("confirmed_and_supported_steps") or []
        steps_valid = True
        for st in steps:
            eid = st["edge_id"]
            edge = edges_by_id.get(eid)
            recheck = rechecked_gates.get(eid)
            if recheck is None and edge is not None:
                recheck = evaluate_behavioral_relation_consistency(
                    nodes[edge["source_fact_id"]], nodes[edge["target_fact_id"]],
                )
            if (
                edge is None
                or not recheck
                or not recheck["gate_passed"]
                or st.get("verification_status") != "supported"
                or st.get("relation_type") != "corroborated_same_device_behavioral_transition"
            ):
                steps_valid = False
                issues.append({
                    "storyline_id": sl["storyline_id"],
                    "edge_id": eid,
                    "issue": "behavioral_storyline_uses_unsupported_or_failed_edge",
                })
        comp_status = sl.get("completeness_status")
        if steps:
            if not all_verified:
                issues.append({
                    "storyline_id": sl["storyline_id"],
                    "issue": "unverified_anchor_in_supported_behavioral_storyline",
                })
            if comp_status != "behavioral_chain_with_supported_relations":
                issues.append({
                    "storyline_id": sl["storyline_id"],
                    "issue": "supported_behavioral_storyline_wrong_status",
                    "completeness_status": comp_status,
                })
        else:
            if not all_verified and comp_status != "behavioral_unverified_observation":
                issues.append({
                    "storyline_id": sl["storyline_id"],
                    "issue": "unverified_anchor_marked_as_verified_storyline",
                    "completeness_status": comp_status,
                })
            if all_verified and comp_status != "behavioral_single_anchor":
                issues.append({
                    "storyline_id": sl["storyline_id"],
                    "issue": "verified_single_anchor_wrong_status",
                    "completeness_status": comp_status,
                })
        behavioral_storyline_checks.append({
            "storyline_id": sl["storyline_id"],
            "anchor_ids": sl.get("anchor_ids"),
            "completeness_status": comp_status,
            "all_spine_anchors_verified": all_verified,
            "supported_step_count": len(steps),
            "all_steps_passed_behavioral_gate": steps_valid,
        })

    beh_rep = report.get("behavioral_reconstruction")
    if beh_rep and beh_rep.get("behavioral_mode") and not str(report.get("report_status", "")).startswith("diagnostic_only"):
        supported_in_sl = sum(
            1 for s in storylines.get("storylines") or []
            if s.get("storyline_kind") == "behavioral"
            and s.get("completeness_status") == "behavioral_chain_with_supported_relations"
        )
        if beh_rep.get("supported_chain_count") != supported_in_sl:
            issues.append({
                "issue": "report_supported_behavioral_chain_count_differs",
                "report": beh_rep.get("supported_chain_count"),
                "storylines": supported_in_sl,
            })

    synthesis_checks: dict = {}
    syn = incident_synthesis or report.get("incident_synthesis")
    if isinstance(syn, dict):
        unverified_aids = {
            a["anchor_id"] for a in (anchor_result or {}).get("anchors") or []
            if a.get("verification_status") != "verified_observation"
        } | {
            (nodes[fid].get("protocol_meta") or {}).get("anchor_id")
            for fid in behavioral_fids
            if fid in nodes and (nodes[fid].get("protocol_meta") or {}).get("verification_status") != "verified_observation"
        } - {None}

        bundle_unverified_hits = []
        for b in syn.get("rtu_asdu_bundles") or []:
            bad = sorted(set(b.get("member_anchor_ids") or []) & unverified_aids)
            if bad or b.get("independent_source_count") != 1:
                bundle_unverified_hits.append({"bundle_id": b.get("bundle_id"), "unverified_anchors": bad})
                issues.append({
                    "bundle_id": b.get("bundle_id"),
                    "issue": "synthesis_unverified_anchor_or_inflated_count_in_bundle",
                    "unverified_anchors": bad,
                    "independent_source_count": b.get("independent_source_count"),
                })

        bridge_violations = []
        for br in syn.get("verified_element_bridges") or []:
            eid = br.get("edge_id")
            edge = edges_by_id.get(eid)
            recheck = rechecked_gates.get(eid)
            if recheck is None and edge is not None and edge["source_fact_id"] in nodes and edge["target_fact_id"] in nodes:
                recheck = evaluate_behavioral_relation_consistency(
                    nodes[edge["source_fact_id"]], nodes[edge["target_fact_id"]],
                )
            endpoints_unverified = bool({br.get("from_anchor_id"), br.get("to_anchor_id")} & unverified_aids)
            if (
                edge is None
                or edge.get("relation_type") != "corroborated_same_device_behavioral_transition"
                or edge.get("verification_status") != "supported"
                or not recheck
                or not recheck.get("gate_passed")
                or endpoints_unverified
            ):
                bridge_violations.append(br.get("bridge_id"))
                issues.append({
                    "bridge_id": br.get("bridge_id"),
                    "edge_id": eid,
                    "issue": "synthesis_bridge_without_corroborated_behavioral_gate",
                })

        promoted_candidates = []
        for ph in syn.get("candidate_scenario_phases") or []:
            for cand in ph.get("unresolved_cross_device_candidates") or []:
                if (
                    cand.get("verification_status") != "unresolved"
                    or cand.get("causal_status") != "not_established"
                    or cand.get("claim_level") in ("observed_fact", "supported_inference")
                ):
                    promoted_candidates.append(cand.get("edge_id"))
                    issues.append({
                        "phase_id": ph.get("phase_id"),
                        "edge_id": cand.get("edge_id"),
                        "issue": "synthesis_candidate_cooccurrence_promoted",
                    })

        ledger = syn.get("source_dependency_ledger") or {}
        expected_containers = len({b["asdu_container_id"] for b in (syn.get("rtu_asdu_bundles") or [])})
        ledger_ok = True
        if syn.get("behavioral_mode") and ledger.get("independent_asdu_container_count") != expected_containers:
            ledger_ok = False
            issues.append({
                "issue": "synthesis_source_ledger_container_count_mismatch",
                "ledger": ledger.get("independent_asdu_container_count"),
                "expected": expected_containers,
            })
        if ledger.get("ipal_independent_source_weight", 0) != 0:
            ledger_ok = False
            issues.append({
                "issue": "synthesis_ipal_counted_as_independent_source",
                "ipal_independent_source_weight": ledger.get("ipal_independent_source_weight"),
            })

        synthesis_checks = {
            "synthesis_no_new_supported_edges": not bridge_violations,
            "synthesis_unverified_quarantine_intact": not bundle_unverified_hits and not bridge_violations,
            "synthesis_source_ledger_exact": ledger_ok,
            "synthesis_candidate_links_unresolved": not promoted_candidates,
        }

    return {
        "check_scope": "quality_and_behavioral_consistency",
        "lineage_check_recorded_separately_in": "lineage_consistency.json",
        "consistent": not issues,
        "checks": checks,
        "behavioral_anchor_checks": behavioral_anchor_checks,
        "behavioral_edge_checks": behavioral_edge_checks,
        "behavioral_storyline_checks": behavioral_storyline_checks,
        "synthesis_checks": synthesis_checks,
        "issues": issues,
    }


def build_lineage_consistency_record(lineage_bundle: dict) -> dict:
    """Build a standalone evidence lineage consistency record, separate from quality checks."""
    timeline_missing = list(lineage_bundle.get("missing_ids") or [])
    timeline_failures = list(lineage_bundle.get("row_check_failures") or [])
    beh = lineage_bundle.get("behavioral_anchor_lineage") or {}
    beh_missing = list(beh.get("missing_ids") or [])
    beh_failures = list(beh.get("row_check_failures") or [])
    issues: list[dict] = []
    if timeline_missing:
        issues.append({"scope": "timeline_lineage", "issue": "missing_evidence_ids", "ids": timeline_missing})
    if timeline_failures:
        issues.append({"scope": "timeline_lineage", "issue": "row_check_failures", "failures": timeline_failures})
    if beh_missing:
        issues.append({"scope": "behavioral_anchor_lineage", "issue": "missing_evidence_ids", "ids": beh_missing})
    if beh_failures:
        issues.append({"scope": "behavioral_anchor_lineage", "issue": "row_check_failures", "failures": beh_failures})
    return {
        "check_scope": "evidence_lineage_only",
        "quality_check_recorded_separately_in": "quality_consistency.json",
        "consistent": not issues,
        "timeline_lineage": {
            "requested_count": lineage_bundle.get("requested_count", 0),
            "expected_with_parents": lineage_bundle.get("expected_with_parents", 0),
            "exported_count": lineage_bundle.get("exported_count", 0),
            "missing_ids": timeline_missing,
            "row_check_failures": timeline_failures,
        },
        "behavioral_anchor_lineage": {
            "checked_anchor_count": beh.get("checked_anchor_count", 0),
            "checked_reference_count": beh.get("checked_reference_count", 0),
            "missing_ids": beh_missing,
            "row_check_failures": beh_failures,
        },
        "issues": issues,
    }
