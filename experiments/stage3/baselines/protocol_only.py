"""Baseline B2: Protocol-Only Reconstruction.

Fairness design:
- Uses the exact same Phase 1 IEC-104 Protocol Transaction Reconstruction
  (`reconstruct_transactions`: COT=6 activation, COT=7 confirmation with P/N bit
  check, COT=10 termination, TCP sequence retransmission deduplication, cross-vantage
  conflict detection, and pre/post command effect consistency gate).
- Does NOT use Behavioral Event Anchor Discovery (`discover_event_anchors`),
  Behavioral Storyline Search, or Four-Layer Incident Synthesis.
- Explicitly distinguishes applicability scope: when a window contains zero IEC-104
  control commands (`iec104_control_objects_in_window == 0`), B2 records
  `applicability_status = "NOT_APPLICABLE_NO_CONTROL_COMMANDS"` rather than treating
  the absence of output as a false negative or software error.
"""
from __future__ import annotations


def run_protocol_only_baseline(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
) -> dict:
    txs = list(tx_result.get("transactions") or [])
    inv = anchor_result.get("observation_inventory") or {}
    ctrl_objs = int(inv.get("iec104_control_objects_in_window") or 0)
    has_commands = bool(txs or ctrl_objs > 0)

    verified_tx = [
        tx for tx in txs
        if tx.get("device_state_change_status") in ("verified_state_transition", "verified_measurement_transition")
    ]
    unverified_sp_tx = [
        tx for tx in txs
        if str(tx.get("device_state_change_status") or "").startswith("state_report_observed")
        or tx.get("device_state_change_status") == "measurement_observed_transition_unverified"
    ]
    no_change_tx = [
        tx for tx in txs
        if tx.get("device_state_change_status") == "no_state_change_observed"
    ]

    # Build protocol-only transaction storylines
    protocol_storylines = []
    for idx, tx in enumerate(txs, start=1):
        stages = ["command_activation"]
        if tx.get("activation_confirmation") is not None:
            stages.append("command_confirmation")
        if tx.get("protocol_state_feedback"):
            stages.append("protocol_state_feedback")
        if tx.get("measurement_transition"):
            stages.append("post_command_measurement")
        if tx.get("activation_termination") is not None:
            stages.append("activation_termination")
        protocol_storylines.append({
            "storyline_id": f"PSL-{idx:03d}",
            "transaction_id": tx["transaction_id"],
            "entity": tx["entity"],
            "rtu_ip": tx.get("rtu_ip"),
            "stages": stages,
            "command_acceptance_status": tx.get("command_acceptance_status"),
            "device_state_change_status": tx.get("device_state_change_status"),
            "evidence_ids": list(tx.get("all_evidence_ids") or [])[:6],
        })

    # Quantify behavioral & network observations missed when Behavioral Reconstruction + Synthesis are absent
    anchors = list(anchor_result.get("anchors") or [])
    verified_anchors = [a for a in anchors if a.get("verification_status") == "verified_observation"]
    non_tx_verified_anchors = [a for a in verified_anchors if not a.get("covered_by_transaction")]

    missed_by_type = {}
    for a in non_tx_verified_anchors:
        t = a["anchor_type"]
        missed_by_type[t] = missed_by_type.get(t, 0) + 1

    mirage_beh_supported_chains = [
        s for s in (mirage_storylines.get("storylines") or [])
        if s.get("storyline_kind") == "behavioral"
        and s.get("completeness_status") == "behavioral_chain_with_supported_relations"
    ]
    mirage_bridges = list(mirage_synthesis.get("verified_element_bridges") or [])
    mirage_bundles = list(mirage_synthesis.get("rtu_asdu_bundles") or [])

    return {
        "baseline_id": "B2_protocol_only",
        "method_description": (
            "Protocol-Only Reconstruction using IEC-104 control commands (COT=6), confirmations "
            "(COT=7), terminations (COT=10), and direct same-device feedback, with full protocol "
            "and quality checks, but without Behavioral Anchor Discovery or Incident Synthesis."
        ),
        "observations_used": [
            "IEC-104 control commands (types 45-69, COT=6/7/8/9/10)",
            "Direct post-command same-device state reports (COT=3) and controlled setpoint measurements",
        ],
        "information_removed": [
            "Behavioral Event Anchor Discovery (`spontaneous_state_report` without command, `measurement_step`, `communication_change`, `arp_activity_increase`)",
            "Behavioral Storyline Search (`corroborated_same_device_behavioral_transition`)",
            "Four-Layer Incident Synthesis (`rtu_asdu_bundles`, `verified_element_bridges`, `candidate_scenario_phases`)",
        ],
        "allowed_claims": [
            "protocol_control_transaction",
            "verified_command_effect_transition (when pre/post consistency gate passes)",
        ],
        "applicability_status": (
            "APPLICABLE_CONTROL_COMMAND_WINDOW" if has_commands else "NOT_APPLICABLE_NO_CONTROL_COMMANDS"
        ),
        "is_applicable_to_window": has_commands,
        "transaction_count_total": len(txs),
        "transaction_count_accepted": tx_result.get("accepted_count", 0),
        "transaction_count_verified_transition": len(verified_tx),
        "transaction_count_unverified_state_report": len(unverified_sp_tx),
        "transaction_count_no_state_change": len(no_change_tx),
        "protocol_storyline_count": len(protocol_storylines),
        "retained_investigation_info_in_no_command_window": 0 if not has_commands else len(protocol_storylines),
        "omitted_compared_to_full_mirage": {
            "omitted_verified_non_command_anchor_count": len(non_tx_verified_anchors),
            "omitted_verified_anchors_by_type": missed_by_type,
            "omitted_supported_behavioral_transition_chain_count": len(mirage_beh_supported_chains),
            "omitted_cross_rtu_verified_element_bridge_count": len(mirage_bridges),
            "omitted_rtu_asdu_bundle_count": len(mirage_bundles),
            "unexpressible_network_anomalies_count": (
                missed_by_type.get("arp_activity_increase", 0)
                + missed_by_type.get("communication_change", 0)
            ),
        },
        "protocol_storylines": protocol_storylines[:30],
    }
