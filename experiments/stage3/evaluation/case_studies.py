"""Task 5: Representative Real Sherlock Case Studies (C1-C7) & Synthetic Known-Answer Counterexamples.

All 7 real Sherlock case categories are selected by explicit, pre-defined rules from the
frozen 103-window dataset, with full `evidence_id` citations and epistemic boundaries.
Synthetic known-answer counterexamples (S-KA1, S-KA2, S-KA3) are executed in isolated
temporary SQLite databases and reported strictly separately from the 103 real windows.
"""
from __future__ import annotations
import tempfile
from pathlib import Path

from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence
from mirage_ot.etgi.reconstruction.engine import reconstruct_incident
from ..baselines.temporal_only import run_temporal_only_baseline
from ..baselines.protocol_only import run_protocol_only_baseline
from ..ablations.no_behavioral_gate import run_ablation_without_behavioral_gate
from ..ablations.no_provenance_dedup import run_ablation_without_provenance_dedup
from ..ablations.no_incident_synthesis import run_ablation_without_incident_synthesis


REPRESENTATIVE_CASE_SPECS = [
    {
        "case_id": "C1_command_passed_consistency_gate",
        "category": "IEC-104 control command passing pre/post transition consistency gate",
        "selection_rule": (
            "Select `01-Basic` window `ev_0961f1c2da8a257e3ebc` (setpoint command on `sgen.6`) and "
            "`02-Semiurban` window `ev_229f54b33cd3bfeb8f67` (binary command on `switch.335:closed`), "
            "where `COT=6 -> COT=7 (P/N=0)` is followed by a decoded pre-to-post shift matching the target."
        ),
        "episodes": [
            ("01-Basic", "ev_0961f1c2da8a257e3ebc"),
            ("02-Semiurban", "ev_229f54b33cd3bfeb8f67"),
        ],
    },
    {
        "case_id": "C2_command_without_pre_post_measurement_evidence",
        "category": "IEC-104 control command without sufficient pre/post state or measurement evidence",
        "selection_rule": (
            "Select `01-Basic` window `ev_3e4d36008b29595ef246`, which contains 3 accepted switch commands "
            "(`TX001` `switch.23`, `TX002` `switch.24`, `TX003` `switch.30`) where `TX001`/`TX002` lack a "
            "prior IEC-104 state baseline in `[start-15s, cmd_time)` and `TX003` has no post-command state report."
        ),
        "episodes": [
            ("01-Basic", "ev_3e4d36008b29595ef246"),
        ],
    },
    {
        "case_id": "C3_no_command_cross_rtu_verified_bridge",
        "category": "No control command, corroborated Cross-RTU Verified Element Bridges",
        "selection_rule": (
            "Select one no-command `S2` window from each scenario (`01-Basic` `ev_564bebaa45f0686cf98d`, "
            "`02-Semiurban` `ev_d3c46672f9814dcdc40c`, `03-Rural` `ev_0d966f97d1922adb09bb`) where "
            "`verified_element_bridges > 0`."
        ),
        "episodes": [
            ("01-Basic", "ev_564bebaa45f0686cf98d"),
            ("02-Semiurban", "ev_d3c46672f9814dcdc40c"),
            ("03-Rural", "ev_0d966f97d1922adb09bb"),
        ],
    },
    {
        "case_id": "C4_arp_and_iec104_link_disruption_uncertain_causality",
        "category": "ARP burst and IEC-104 link disruptions with per-target precedence filtering and uncertain causality",
        "selection_rule": (
            "Select `01-Basic` window `ev_cbe1e5bef23346604396`, where ARP traffic from `172.16.3.28` "
            "precedes link loss on RTUs `172.16.3.10` and `172.16.3.9` within 15s, while first ARP to "
            "`172.16.3.20` occurs 37.7s after its link change."
        ),
        "episodes": [
            ("01-Basic", "ev_cbe1e5bef23346604396"),
        ],
    },
    {
        "case_id": "C5_multi_vantage_payload_conflict",
        "category": "Multi-vantage mirror payload conflicts quarantined from supported spines",
        "selection_rule": (
            "Select `01-Basic` window `ev_52f5eee28f8b95e702fd`, which exhibits 240 `post_cross_vantage_payload_conflict` "
            "and 236 `pre_cross_vantage_payload_conflict` anchor issues across mirror vantages."
        ),
        "episodes": [
            ("01-Basic", "ev_52f5eee28f8b95e702fd"),
        ],
    },
    {
        "case_id": "C6_lineage_consistency_failure_diagnostic_downgrade",
        "category": "Lineage consistency failure automatically downgrading final report to Diagnostic Only",
        "selection_rule": (
            "Select `02-Semiurban` window `ev_5dd0102bf58bf2ce9487`, the single window in the 103-window "
            "suite where `lineage_consistency.json` flags `time_outside_cited_sample` on `A007` (`EV-6e9e7ece8bf456f0`)."
        ),
        "episodes": [
            ("02-Semiurban", "ev_5dd0102bf58bf2ce9487"),
        ],
    },
    {
        "case_id": "C7_low_information_honest_abstention",
        "category": "Honest abstention in low-information periodic-measurement-only windows",
        "selection_rule": (
            "Select `01-Basic` window `ev_d58f418ff4f085ccc0a7` and `02-Semiurban` window `ev_8e3ee44aec0a0f81c99a`, "
            "where only periodic `M_ME_NC_1 (COT=1)` telemetry and transient oscillations occur."
        ),
        "episodes": [
            ("01-Basic", "ev_d58f418ff4f085ccc0a7"),
            ("02-Semiurban", "ev_8e3ee44aec0a0f81c99a"),
        ],
    },
]


def extract_real_case_study(
    *,
    case_spec: dict,
    scenario: str,
    episode_id: str,
    window_eval: dict,
    tx_result: dict,
    anchor_result: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
    mirage_report: dict,
    quality_consistency: dict,
    lineage_consistency: dict,
    b1_result: dict,
    b2_result: dict,
    a1_result: dict,
    a2_result: dict,
    a3_result: dict,
) -> dict:
    txs = list(tx_result.get("transactions") or [])
    anchors = list(anchor_result.get("anchors") or [])
    ver_anchors = [a for a in anchors if a.get("verification_status") == "verified_observation"]
    bridges = list(mirage_synthesis.get("verified_element_bridges") or [])
    bundles = list(mirage_synthesis.get("rtu_asdu_bundles") or [])
    explanations = list(mirage_synthesis.get("competing_explanations") or [])

    cited_eids = list(dict.fromkeys([
        *(eid for t in txs for eid in (t.get("all_evidence_ids") or [])[:3]),
        *(eid for b in bundles[:6] for eid in (b.get("evidence_ids") or [])[:2]),
        *(eid for br in bridges for eid in (br.get("evidence_ids") or [])[:2]),
        *(eid for a in anchors[:4] for eid in (a.get("evidence_ids") or [])[:2]),
    ]))[:16]

    observable_facts = {
        "iec104_control_transactions": [
            {
                "transaction_id": t["transaction_id"],
                "entity": t["entity"],
                "commanded_value": t.get("commanded_value"),
                "acceptance_status": t.get("command_acceptance_status"),
                "state_change_status": t.get("device_state_change_status"),
                "evidence_ids": list(t.get("all_evidence_ids") or [])[:4],
            }
            for t in txs[:6]
        ],
        "verified_anchor_count": len(ver_anchors),
        "quarantined_unverified_anchor_count": int(anchor_result.get("unverified_anchor_count") or 0),
        "sample_verified_anchors": [
            {
                "anchor_id": a["anchor_id"],
                "anchor_type": a["anchor_type"],
                "entity": a["entity"],
                "rtu_ip": a.get("rtu_ip") or a.get("host_ip"),
                "evidence_ids": list(a.get("evidence_ids") or [])[:3],
            }
            for a in ver_anchors[:6]
        ],
    }

    baseline_relations = {
        "B1_temporal_only": {
            "candidate_temporal_relation_count": b1_result["candidate_temporal_relation_count"],
            "conflicting_or_unsupported_count": b1_result["total_conflicting_or_unsupported_candidate_count"],
            "cross_device_without_link_count": b1_result["lacking_device_or_session_support_count"],
            "quality_or_test_bit_conflict_count": b1_result["quality_or_test_bit_conflict_count"],
            "transient_not_sustained_count": b1_result["transient_not_sustained_conflict_count"],
            "same_device_direction_or_type_conflict_count": b1_result["same_device_direction_or_type_conflict_count"],
        },
        "B2_protocol_only": {
            "applicability_status": b2_result["applicability_status"],
            "protocol_storyline_count": b2_result["protocol_storyline_count"],
            "verified_command_transitions": b2_result["transaction_count_verified_transition"],
            "omitted_verified_non_command_anchors": b2_result["omitted_compared_to_full_mirage"]["omitted_verified_non_command_anchor_count"],
            "omitted_cross_rtu_bridges": b2_result["omitted_compared_to_full_mirage"]["omitted_cross_rtu_verified_element_bridge_count"],
        },
    }

    mirage_relations = {
        "report_status": mirage_report.get("report_status"),
        "quality_consistency_passed": quality_consistency.get("consistent"),
        "lineage_consistency_passed": lineage_consistency.get("consistent"),
        "lineage_consistency_issues": lineage_consistency.get("issues") or [],
        "verified_device_transitions": mirage_report.get("verified_device_transitions") or [],
        "rtu_asdu_bundle_count": len(bundles),
        "cross_rtu_verified_element_bridges": [
            {
                "bridge_id": br["bridge_id"],
                "edge_id": br["edge_id"],
                "bridged_device_stem": br["bridged_device_stem"],
                "from_rtu_ip": br["from_rtu_ip"],
                "to_rtu_ip": br["to_rtu_ip"],
                "matched_quantities": br["matched_quantities"],
                "evidence_ids": br["evidence_ids"],
            }
            for br in bridges
        ],
        "sequential_same_device_observations_rejected_by_gate": [
            {
                "edge_id": sq["edge_id"],
                "device_stem": sq.get("device_stem"),
                "failed_conditions": sq.get("failed_conditions"),
                "evidence_ids": sq.get("evidence_ids"),
            }
            for sq in (mirage_storylines.get("sequential_same_device_observations") or [])[:6]
        ],
        "unresolved_cross_device_branch_count": len(mirage_storylines.get("unresolved_branches") or []),
    }

    differences = {
        "vs_B1_temporal_only": (
            f"B1 emits {b1_result['candidate_temporal_relation_count']} candidate temporal links "
            f"({b1_result['total_conflicting_or_unsupported_candidate_count']} violating device/quality/persistence/direction "
            f"constraints); MIRAGE-OT restricts supported steps to {len(bridges)} cross-RTU bridges and "
            f"{len(mirage_report.get('verified_device_transitions') or [])} verified command transitions."
        ),
        "vs_B2_protocol_only": (
            f"B2 is `{b2_result['applicability_status']}` and omits "
            f"{b2_result['omitted_compared_to_full_mirage']['omitted_verified_non_command_anchor_count']} verified "
            f"behavioral anchors and {len(bridges)} cross-RTU bridges."
        ),
        "vs_A1_no_behavioral_gate": (
            f"Without the consistency gate, A1 promotes {a1_result['unsupported_promotion_total_count']} "
            f"unsupported relations ({a1_result['evidence_constraint_violation_breakdown']})."
        ),
        "vs_A2_no_provenance_dedup": (
            f"Without provenance deduplication, A2 inflates {a2_result['distinct_source_container_count']} "
            f"true source containers to {a2_result['raw_observation_count']} raw observations "
            f"(inflation factor {a2_result['source_inflation_factor']}x)."
        ),
        "vs_A3_no_incident_synthesis": (
            f"Without Incident Synthesis, A3 leaves {a3_result['without_synthesis']['local_storyline_count']} "
            f"fragmented local storylines without consolidating {len(bundles)} ASDU bundles, "
            f"{len(bridges)} cross-RTU bridges, or {len(explanations)} competing explanations."
        ),
    }

    unconfirmed_items = [
        "Physical causation across distinct grid elements (no bus-branch topology model in telemetry)",
        "Initiating actor or host process behind observed network frames",
        *(
            [exp["missing_disambiguating_evidence"] for exp in explanations[:2]]
            if explanations else []
        ),
    ]

    return {
        "case_id": case_spec["case_id"],
        "category": case_spec["category"],
        "selection_rule": case_spec["selection_rule"],
        "scenario": scenario,
        "episode_id": episode_id,
        "1_observable_facts": observable_facts,
        "2_baseline_relations": baseline_relations,
        "3_mirage_ot_relations": mirage_relations,
        "4_method_differences": differences,
        "5_cited_evidence_ids": cited_eids,
        "6_remaining_unconfirmed_items": unconfirmed_items,
    }


def _row(eid: str, t: float, mod: str, ent: str, kind: str, val, *, vantage="n302", ca_ioa=None, src=None, sport=2404, dst="172.16.1.2", dport=40000, payload=None):
    return {
        "evidence_id": eid,
        "timestamp": t,
        "modality": mod,
        "entity": ent,
        "kind": kind,
        "value": 0.0 if val is None else val,
        "value_present": val is not None,
        "vantage": vantage,
        "fingerprint": f"fp-{eid}",
        "ca_ioa": ca_ioa,
        "protocol_class": "monitor",
        "parent_evidence_id": None,
        "src_ip": src,
        "src_port": sport,
        "dst_ip": dst,
        "dst_port": dport,
        "source_ref": eid,
        "update_status": "decoded",
        "trust": "synthetic_known_answer",
        "payload": payload or {},
    }


def run_synthetic_known_answer_counterexamples() -> list[dict]:
    """Run 3 synthetic known-answer counterexamples in isolated temporary DBs (reported separately from Sherlock)."""
    good_qds = {"iv": False, "nt": False, "sb": False, "bl": False, "ov": False}
    cases = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # S-KA1: Quality & Test-Bit Conflict + Opposing Direction on Same Line
        db1_path = tmp_path / "ska1.sqlite"
        conn1 = connect(db1_path)
        create(conn1)
        rows1 = []
        for i, (t, pf, pt) in enumerate([(990.0, 100.0, -100.0), (1005.0, 300.0, -40.0), (1015.0, 300.0, -40.0), (1025.0, 300.0, -40.0)]):
            # line.1 from-side increases 100 -> 300 with good quality; to-side decreases |-100| -> |-40| AND has test bit set at step i==1
            rows1.append(_row(
                f"EV-ska1-f-{i}", t, "network", "line.1:active_power_from", "iec104_asdu", pf,
                ca_ioa="110.1", src="172.16.3.11",
                payload={"type_id": 13, "cause": "1", "apci_tx": 10 + i, "asdu_index": 0, "object_index": 0,
                         "quality_invalid": False, "quality_flags": good_qds, "quality_good": True, "cot_test": False},
            ))
            rows1.append(_row(
                f"EV-ska1-t-{i}", t + 1.0, "network", "line.1:active_power_to", "iec104_asdu", pt,
                ca_ioa="112.1", src="172.16.3.12",
                payload={"type_id": 13, "cause": "1", "apci_tx": 20 + i, "asdu_index": 0, "object_index": 0,
                         "quality_invalid": False, "quality_flags": good_qds, "quality_good": True, "cot_test": (i == 1)},
            ))
        for r in rows1:
            insert_evidence(conn1, r)
        conn1.commit()
        res1 = reconstruct_incident(
            EvidenceDB(conn1, incident_start=1000.0, incident_end=1040.0),
            1000.0, 1040.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out1",
        )
        conn1.close()
        b1_1 = run_temporal_only_baseline(
            tx_result=res1["transactions"], anchor_result=res1["event_anchors"],
            mirage_event_graph=res1["event_graph"], mirage_storylines=res1["storylines"],
            mirage_synthesis=res1["incident_synthesis"],
        )
        a1_1 = run_ablation_without_behavioral_gate(
            tx_result=res1["transactions"], anchor_result=res1["event_anchors"],
            mirage_event_graph=res1["event_graph"], mirage_storylines=res1["storylines"],
            mirage_synthesis=res1["incident_synthesis"],
        )
        cases.append({
            "synthetic_case_id": "S_KA1_test_bit_and_opposing_direction",
            "known_ground_truth": (
                "`line.1:active_power_from` (RTU .11) increases 100->300, whereas `line.1:active_power_to` (RTU .12) "
                "decreases in magnitude |-100|->|-40| and has COT test bit `T=1` at the step sample. Must NOT form a "
                "supported transition or cross-RTU bridge."
            ),
            "B1_temporal_only_candidates": b1_1["candidate_temporal_relation_count"],
            "A1_ungated_unsupported_promotions": a1_1["unsupported_promotion_total_count"],
            "MIRAGE_OT_supported_bridges": len(res1["incident_synthesis"]["verified_element_bridges"]),
            "MIRAGE_OT_sequential_rejected": len(res1["storylines"]["sequential_same_device_observations"]),
            "passed_known_answer": (
                b1_1["candidate_temporal_relation_count"] == 1
                and a1_1["unsupported_promotion_total_count"] == 1
                and len(res1["incident_synthesis"]["verified_element_bridges"]) == 0
            ),
        })

        # S-KA2: Multi-Vantage Mirror Duplication + Same-ASDU Multi-IOA + IPAL Row Inflation
        db2_path = tmp_path / "ska2.sqlite"
        conn2 = connect(db2_path)
        create(conn2)
        rows2 = []
        for i, (t, v1, v2) in enumerate([(990.0, 100.0, 50.0), (1005.0, 0.0, 0.0), (1015.0, 0.0, 0.0), (1025.0, 0.0, 0.0)]):
            for vant, dt_v in [("n302", 0.0), ("n318", 0.0002)]:
                rows2.append(_row(
                    f"EV-ska2-p-{i}-{vant}", t + dt_v, "network", "bus.5:active_power", "iec104_asdu", v1,
                    vantage=vant, ca_ioa="123.1", src="172.16.3.18",
                    payload={"type_id": 13, "cause": "1", "apci_tx": 30 + i, "asdu_index": 0, "object_index": 0,
                             "quality_invalid": False, "quality_flags": good_qds, "quality_good": True, "cot_test": False},
                ))
                rows2.append(_row(
                    f"EV-ska2-l-{i}-{vant}", t + dt_v, "network", "load.3:active_power", "iec104_asdu", v2,
                    vantage=vant, ca_ioa="123.2", src="172.16.3.18",
                    payload={"type_id": 13, "cause": "1", "apci_tx": 30 + i, "asdu_index": 0, "object_index": 1,
                             "quality_invalid": False, "quality_flags": good_qds, "quality_good": True, "cot_test": False},
                ))
        rows2.append(_row("EV-ska2-ipal1", 1005.2, "electrical", "bus.5:active_power", "electrical_update", 0.0, vantage="ipal_state", ca_ioa="123.1"))
        rows2.append(_row("EV-ska2-ipal2", 1005.2, "electrical", "load.3:active_power", "electrical_update", 0.0, vantage="ipal_state", ca_ioa="123.2"))
        for r in rows2:
            insert_evidence(conn2, r)
        conn2.commit()
        res2 = reconstruct_incident(
            EvidenceDB(conn2, incident_start=1000.0, incident_end=1040.0),
            1000.0, 1040.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out2",
        )
        conn2.close()
        a2_2 = run_ablation_without_provenance_dedup(
            tx_result=res2["transactions"], anchor_result=res2["event_anchors"],
            mirage_event_graph=res2["event_graph"], mirage_storylines=res2["storylines"],
            mirage_synthesis=res2["incident_synthesis"],
        )
        cases.append({
            "synthetic_case_id": "S_KA2_mirror_and_same_asdu_and_ipal_duplication",
            "known_ground_truth": (
                "One ASDU (`apci_tx=31`) from RTU `172.16.3.18` carries two objects (`bus.5` and `load.3`), "
                "is mirrored at two vantages (`n302` and `n318`, 4 packet objects), and produces 2 IPAL rows "
                "(6 raw observations total). True independent source container count is exactly 1."
            ),
            "A2_naive_raw_observation_count": a2_2["raw_observation_count"],
            "A2_mirror_duplicate_count": a2_2["mirror_duplicate_count"],
            "A2_same_asdu_expansion_count": a2_2["same_asdu_multi_point_expansion_count"],
            "A2_ipal_derived_count": a2_2["ipal_derived_observation_count"],
            "MIRAGE_OT_distinct_source_container_count": a2_2["distinct_source_container_count"],
            "passed_known_answer": (
                a2_2["raw_observation_count"] == 6
                and a2_2["distinct_source_container_count"] == 1
                and a2_2["falsely_counted_independent_source_count"] == 5
            ),
        })

        # S-KA3: Cross-Device Unrelated Co-Occurrence vs True Cross-RTU Same-Line Transition
        db3_path = tmp_path / "ska3.sqlite"
        conn3 = connect(db3_path)
        create(conn3)
        rows3 = [
            _row("EV-ska3-sw", 1001.0, "network", "switch.99:is_closed", "iec104_asdu", 0.0,
                 ca_ioa="199.1", src="172.16.3.99",
                 payload={"type_id": 1, "cause": "3", "apci_tx": 1, "asdu_index": 0, "object_index": 0,
                          "quality_invalid": False, "quality_flags": {"iv": False, "nt": False, "sb": False, "bl": False},
                          "quality_good": True, "cot_test": False}),
        ]
        for i, (t, p_to, p_from) in enumerate([(990.0, -200.0, 200.0), (1005.0, 0.0, 0.0), (1015.0, 0.0, 0.0), (1025.0, 0.0, 0.0)]):
            rows3.append(_row(
                f"EV-ska3-l4to-{i}", t, "network", "line.4:active_power_to", "iec104_asdu", p_to,
                ca_ioa="118.1", src="172.16.3.18",
                payload={"type_id": 13, "cause": "1", "apci_tx": 40 + i, "asdu_index": 0, "object_index": 0,
                         "quality_invalid": False, "quality_flags": good_qds, "quality_good": True, "cot_test": False},
            ))
            rows3.append(_row(
                f"EV-ska3-l4fr-{i}", t + 2.0, "network", "line.4:active_power_from", "iec104_asdu", p_from,
                ca_ioa="122.1", src="172.16.3.22",
                payload={"type_id": 13, "cause": "1", "apci_tx": 50 + i, "asdu_index": 0, "object_index": 0,
                         "quality_invalid": False, "quality_flags": good_qds, "quality_good": True, "cot_test": False},
            ))
        for r in rows3:
            insert_evidence(conn3, r)
        conn3.commit()
        res3 = reconstruct_incident(
            EvidenceDB(conn3, incident_start=1000.0, incident_end=1040.0),
            1000.0, 1040.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out3",
        )
        conn3.close()
        b1_3 = run_temporal_only_baseline(
            tx_result=res3["transactions"], anchor_result=res3["event_anchors"],
            mirage_event_graph=res3["event_graph"], mirage_storylines=res3["storylines"],
            mirage_synthesis=res3["incident_synthesis"],
        )
        cases.append({
            "synthetic_case_id": "S_KA3_unverified_switch_vs_verified_cross_rtu_line_bridge",
            "known_ground_truth": (
                "Unverified `switch.99:is_closed=0` (no prior baseline) occurs 4s before `line.4` drops to zero "
                "at both `to` (RTU .18) and `from` (RTU .22) ends. Only `line.4` (`to` <-> `from`) is a corroborated "
                "cross-RTU bridge; `switch.99 -> line.4` must remain an unresolved candidate branch."
            ),
            "B1_temporal_only_candidates": b1_3["candidate_temporal_relation_count"],
            "B1_cross_device_unsupported_candidates": b1_3["lacking_device_or_session_support_count"],
            "MIRAGE_OT_verified_bridges": [b["bridged_device_stem"] for b in res3["incident_synthesis"]["verified_element_bridges"]],
            "MIRAGE_OT_unresolved_branches": len(res3["storylines"]["unresolved_branches"]),
            "passed_known_answer": (
                b1_3["candidate_temporal_relation_count"] == 3
                and b1_3["lacking_device_or_session_support_count"] == 2
                and [b["bridged_device_stem"] for b in res3["incident_synthesis"]["verified_element_bridges"]] == ["line.4"]
                and len(res3["storylines"]["unresolved_branches"]) == 2
            ),
        })

    return cases
