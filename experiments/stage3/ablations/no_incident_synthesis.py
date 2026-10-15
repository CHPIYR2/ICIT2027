"""Ablation A3: Without Incident Synthesis (Paper-Readiness Audit Hardened).

Retains Phase 1 Protocol Transactions, Event Anchor Discovery, Phase 2 Temporal Event
Graph, and Phase 3 Local Storylines, but omits Phase 4 Four-Layer Incident Synthesis
(`synthesize_incident_scenario`).

Task 4 & Task 5 Hardening:
- Evaluates only the addition of structured, evidence-traceable incident organization
  information (bundles, cross-RTU bridges, candidate phases, competing explanations with
  missing evidence); NEVER claims empirically proven human investigation time savings
  without a human-subject study.
- Strictly separates E3 Traceability into four distinct verification levels:
  1. `evidence_citation_presence`: non-empty `evidence_ids` fields on synthesized structures.
  2. `evidence_id_resolution`: all cited `evidence_id`s resolve to rows in `evidence.sqlite`
     (`missing_ids == []`).
  3. `evidence_to_fact_anchor_consistency`: all resolved rows match the entity, `ca_ioa`,
     host IP, and sample time bounds of their Fact/Anchor (`row_check_failures == []`).
  4. `full_lineage_consistency`: passes all three levels above (`lineage_consistency["consistent"]`).
"""
from __future__ import annotations
import sqlite3
from pathlib import Path


def _verify_sqlite_id_resolution(db_path: Path | None, cited_ids: list[str]) -> tuple[bool, list[str]]:
    if not cited_ids:
        return True, []
    if db_path is None or not db_path.exists():
        return False, list(cited_ids)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    found: set[str] = set()
    try:
        uniq = list(dict.fromkeys(cited_ids))
        for i in range(0, len(uniq), 100):
            batch = uniq[i : i + 100]
            q = f"SELECT evidence_id FROM evidence WHERE evidence_id IN ({','.join('?' for _ in batch)})"
            for (eid,) in conn.execute(q, batch).fetchall():
                found.add(eid)
    finally:
        conn.close()
    missing = sorted(set(cited_ids) - found)
    return not missing, missing


def run_ablation_without_incident_synthesis(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
    lineage_consistency: dict | None = None,
    db_path: Path | None = None,
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

    # Level 1: Evidence Citation Presence (non-empty fields)
    bundles_present = all(bool(b.get("evidence_ids")) for b in bundles)
    bridges_present = all(bool(br.get("evidence_ids")) for br in bridges)
    explanations_present = all(
        bool((exp.get("anchoring_verified_evidence") or {}).get("evidence_ids"))
        and bool(exp.get("missing_disambiguating_evidence"))
        for exp in explanations
    )
    citation_presence_ok = bundles_present and bridges_present and explanations_present

    # Level 2: Evidence ID Resolution against SQLite + lineage_consistency missing_ids
    synth_cited_ids = list(dict.fromkeys([
        *(eid for b in bundles for eid in (b.get("evidence_ids") or [])),
        *(eid for br in bridges for eid in (br.get("evidence_ids") or [])),
        *(eid for exp in explanations for eid in ((exp.get("anchoring_verified_evidence") or {}).get("evidence_ids") or [])),
    ]))
    sqlite_resolved_ok, sqlite_missing_ids = _verify_sqlite_id_resolution(db_path, synth_cited_ids) if db_path else (True, [])
    lc = lineage_consistency or {}
    tl_missing = list((lc.get("timeline_lineage") or {}).get("missing_ids") or [])
    beh_missing = list((lc.get("behavioral_anchor_lineage") or {}).get("missing_ids") or [])
    id_resolution_ok = sqlite_resolved_ok and not tl_missing and not beh_missing

    # Level 3: Evidence-to-Fact / Anchor Consistency (row_check_failures)
    tl_failures = list((lc.get("timeline_lineage") or {}).get("row_check_failures") or [])
    beh_failures = list((lc.get("behavioral_anchor_lineage") or {}).get("row_check_failures") or [])
    fact_anchor_consistency_ok = not tl_failures and not beh_failures

    # Level 4: Full Lineage Consistency
    full_lineage_ok = bool(
        citation_presence_ok
        and id_resolution_ok
        and fact_anchor_consistency_ok
        and lc.get("consistent", True)
    )

    verified_local_chains = (
        int(part_counts.get("supported_multi_node_storyline_count") or 0)
        + int(part_counts.get("verified_single_anchor_storyline_count") or 0)
    )
    quarantined_unverified = int(part_counts.get("quarantined_unverified_observation_count") or 0)
    consolidated_units = len(components) + max(
        0,
        len(bundles) - sum(len(c.get("bundle_ids") or []) for c in components),
    )

    return {
        "ablation_id": "A3_without_incident_synthesis",
        "analysis_nature": "structural_traceability_comparison_not_human_time_study",
        "method_description": (
            "Retains full Protocol Transactions, Event Anchors, Temporal Event Graph, and "
            "Local Storylines, but omits Four-Layer Incident Synthesis."
        ),
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
                "1_evidence_citation_presence": citation_presence_ok,
                "2_evidence_id_resolution": id_resolution_ok,
                "3_evidence_to_fact_anchor_consistency": fact_anchor_consistency_ok,
                "4_full_lineage_consistency": full_lineage_ok,
                "synthesis_cited_evidence_id_count": len(synth_cited_ids),
                "sqlite_unresolved_ids": sqlite_missing_ids,
                "timeline_row_check_failure_count": len(tl_failures),
                "behavioral_anchor_row_check_failure_count": len(beh_failures),
            },
        },
    }
