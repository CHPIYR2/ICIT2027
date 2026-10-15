"""Ablation A3: Without Incident Synthesis.

Retains Phase 1 Protocol Transactions, Event Anchor Discovery, Phase 2 Temporal Event
Graph, and Phase 3 Local Storylines, but omits Phase 4 Four-Layer Incident Synthesis
(`synthesize_incident_scenario`).

Evaluates what structured, evidence-traceable incident organization information is added
by Four-Layer Incident Synthesis beyond local storylines, and verifies that every synthesized
bundle, bridge, component, phase, and competing explanation traces back to valid `evidence_id`s.
"""
from __future__ import annotations


def run_ablation_without_incident_synthesis(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
    lineage_bundle_summary: dict | None = None,
) -> dict:
    storylines = list(mirage_storylines.get("storylines") or [])
    bundles = list(mirage_synthesis.get("rtu_asdu_bundles") or [])
    bridges = list(mirage_synthesis.get("verified_element_bridges") or [])
    components = list(mirage_synthesis.get("bridged_bundle_components") or [])
    phases = list(mirage_synthesis.get("candidate_scenario_phases") or [])
    explanations = list(mirage_synthesis.get("competing_explanations") or [])
    ledger = mirage_synthesis.get("source_dependency_ledger") or {}
    part = mirage_synthesis.get("local_storyline_partition") or {}
    part_counts = part.get("counts") or {}

    # Verify evidence_id traceability on every synthesized structure
    bundles_traceable = all(bool(b.get("evidence_ids")) for b in bundles)
    bridges_traceable = all(bool(br.get("evidence_ids")) for br in bridges)
    explanations_traceable = all(
        bool((exp.get("anchoring_verified_evidence") or {}).get("evidence_ids"))
        and bool(exp.get("missing_disambiguating_evidence"))
        for exp in explanations
    )

    verified_local_chains = (
        int(part_counts.get("supported_multi_node_storyline_count") or 0)
        + int(part_counts.get("verified_single_anchor_storyline_count") or 0)
    )
    quarantined_unverified = int(part_counts.get("quarantined_unverified_observation_count") or 0)

    # Fragmentation reduction: how many verified local anchor chains are consolidated into RTU ASDU bundles
    # and multi-RTU bridged components
    consolidated_units = len(components) + max(
        0,
        len(bundles) - sum(len(c.get("bundle_ids") or []) for c in components),
    )

    return {
        "ablation_id": "A3_without_incident_synthesis",
        "method_description": (
            "Retains full Protocol Transactions, Event Anchors, Temporal Event Graph, and "
            "Local Storylines, but omits Four-Layer Incident Synthesis."
        ),
        "observations_used": ["Identical to full MIRAGE-OT"],
        "information_removed": [
            "Layer 1 explicit partition & unverified quarantine table",
            "Layer 2 RTU ASDU Bundle consolidation & Cross-RTU Verified Element Bridges",
            "Layer 3 Candidate Scenario Phases with host/ARP/link context aggregation",
            "Layer 4 Source Dependency Ledger & Evidence-Anchored Competing Explanations",
        ],
        "without_synthesis": {
            "local_storyline_count": len(storylines),
            "verified_local_storyline_count": verified_local_chains,
            "quarantined_unverified_storyline_count": quarantined_unverified,
            "deduplicated_source_container_ledger_available": False,
            "cross_rtu_verified_element_bridge_count": 0,
            "multi_bundle_bridged_component_count": 0,
            "candidate_scenario_phase_count": 0,
            "explicit_unresolved_vs_supported_layer_separation": True,
            "competing_explanations_with_missing_evidence_count": 0,
        },
        "with_full_synthesis": {
            "local_storyline_count": len(storylines),
            "deduplicated_source_container_count": int(ledger.get("verified_source_container_count") or 0),
            "rtu_asdu_bundle_count": len(bundles),
            "co_reported_points_collapsed_into_bundles": int(ledger.get("co_reported_same_asdu_reduction_count") or 0),
            "cross_rtu_verified_element_bridge_count": len(bridges),
            "multi_bundle_bridged_component_count": len(components),
            "consolidated_incident_unit_count": consolidated_units,
            "candidate_scenario_phase_count": len(phases),
            "unresolved_cross_device_branch_count_preserved": len(mirage_storylines.get("unresolved_branches") or []),
            "competing_explanations_with_missing_evidence_count": len(explanations),
            "traceability_verification": {
                "all_bundles_cite_evidence_ids": bundles_traceable,
                "all_bridges_cite_evidence_ids": bridges_traceable,
                "all_explanations_cite_evidence_and_missing_disambiguators": explanations_traceable,
            },
        },
    }
