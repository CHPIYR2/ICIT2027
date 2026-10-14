"""Unit tests for the Incident Reconstruction Engine (Phases 1-4)."""
from __future__ import annotations
import json
from pathlib import Path
from mirage_ot.etgi.agent.ollama import LLMTurn
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence
from mirage_ot.etgi.reconstruction.engine import reconstruct_incident
from mirage_ot.etgi.reconstruction.event_graph import build_temporal_event_graph
from mirage_ot.etgi.reconstruction.storyline import reconstruct_storylines
from mirage_ot.etgi.reconstruction.transactions import reconstruct_transactions


class ScriptedLLM:
    model_name = "scripted-recon"

    def __init__(self, payload: dict):
        self.content = json.dumps(payload)

    def chat(self, messages, **kwargs):
        return LLMTurn(self.content, [], 100, 40, {}, self.model_name, done_reason="stop")


def _row(
    evidence_id: str,
    timestamp: float,
    modality: str,
    entity: str,
    kind: str,
    value,
    *,
    vantage: str = "n302",
    fingerprint: str | None = None,
    ca_ioa: str | None = None,
    protocol_class: str | None = None,
    parent_evidence_id: str | None = None,
    src_ip: str | None = None,
    src_port: int | None = None,
    dst_ip: str | None = None,
    dst_port: int | None = None,
    update_status: str = "decoded",
    payload: dict | None = None,
) -> dict:
    present = value is not None
    return {
        "evidence_id": evidence_id,
        "timestamp": timestamp,
        "modality": modality,
        "entity": entity,
        "kind": kind,
        "value": 0.0 if value is None else value,
        "value_present": present,
        "vantage": vantage,
        "fingerprint": fingerprint or f"fp-{evidence_id}",
        "ca_ioa": ca_ioa,
        "protocol_class": protocol_class,
        "parent_evidence_id": parent_evidence_id,
        "src_ip": src_ip,
        "src_port": src_port,
        "dst_ip": dst_ip,
        "dst_port": dst_port,
        "source_ref": evidence_id,
        "update_status": update_status,
        "trust": "test",
        "payload": payload or {},
    }


def test_protocol_pairing_rejects_same_ca_ioa_on_mismatched_session_or_type(tmp_path: Path):
    """Time proximity + identical CA/IOA must NOT pair if reverse 5-tuple or ASDU type_id mismatches."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        # Command COT=6 from Master 172.16.1.2:50000 -> RTU 172.16.3.5:2404
        _row("EV-cmd0000000000001", 1001.0, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        # Spoofed/unrelated COT=7 on same CA/IOA 50ms later, but from wrong TCP port (59999 instead of 50000)
        _row("EV-badack0000000001", 1001.05, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=59999,
             payload={"type_id": 45, "cause": "7"}),
        # Another COT=7 with matching 5-tuple, but mismatched ASDU type_id (50 instead of 45)
        _row("EV-badack0000000002", 1001.08, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=50000,
             payload={"type_id": 50, "cause": "7"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    assert res["transaction_count"] == 1
    tx = res["transactions"][0]
    assert tx["command_acceptance_status"] == "unconfirmed_missing_cot7"
    assert tx["activation_confirmation"] is None
    assert res["unpaired_control_message_count"] == 2
    reasons = [
        r
        for u in res["unpaired_protocol_messages"]
        for cand in u["candidate_rejection_reasons"]
        for r in cand["reasons"]
    ]
    assert "reverse_tcp_5tuple_mismatch" in reasons
    assert "type_id_mismatch" in reasons


def test_duplicate_retransmit_vs_repeated_operations_and_multi_vantage(tmp_path: Path):
    """Multi-vantage captures collapse by tcp_seq; unconfirmed retransmit attaches to same TX; post-ACK command starts new TX."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        # Parent TCP packets at n302 and n318 with identical tcp_seq=100 but different L2 fingerprints (routed hop)
        _row("EV-p1n3020000000000", 1001.00, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             vantage="n302", fingerprint="fp-l2-n302", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 100}),
        _row("EV-p1n3180000000000", 1001.02, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             vantage="n318", fingerprint="fp-l2-n318", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 100}),
        # ASDU COT=6 at both vantages
        _row("EV-a1n3020000000000", 1001.00, "network", "switch.23:closed", "iec104_asdu", None,
             vantage="n302", fingerprint="fp-l2-n302", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-p1n3020000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        _row("EV-a1n3180000000000", 1001.02, "network", "switch.23:closed", "iec104_asdu", None,
             vantage="n318", fingerprint="fp-l2-n318", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-p1n3180000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        # Retransmitted COT=6 at n302 0.2s later BEFORE any COT=7 (different frame & tcp_seq=116)
        _row("EV-p1retrans0000000", 1001.20, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             vantage="n302", fingerprint="fp-retrans", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 116}),
        _row("EV-a1retrans0000000", 1001.20, "network", "switch.23:closed", "iec104_asdu", None,
             vantage="n302", fingerprint="fp-retrans", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-p1retrans0000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        # Confirmation COT=7 for TX001
        _row("EV-ack1000000000000", 1001.25, "network", "switch.23:closed", "iec104_asdu", None,
             vantage="n302", fingerprint="fp-ack1", ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=50000,
             payload={"type_id": 45, "cause": "7"}),
        # Second independent operation on the exact same point 3 seconds later -> must start TX002
        _row("EV-a2cmd00000000000", 1004.00, "network", "switch.23:closed", "iec104_asdu", None,
             vantage="n302", fingerprint="fp-cmd2", ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        _row("EV-ack2000000000000", 1004.05, "network", "switch.23:closed", "iec104_asdu", None,
             vantage="n302", fingerprint="fp-ack2", ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=50000,
             payload={"type_id": 45, "cause": "7"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    assert res["transaction_count"] == 2
    tx1, tx2 = res["transactions"]
    assert tx1["command_activation"]["vantages"] == ["n302", "n318"]
    assert len(tx1["duplicate_command_messages"]) == 1
    assert tx1["command_acceptance_status"] == "accepted_by_rtu"
    assert tx2["transaction_id"] == "TX002"
    assert tx2["command_acceptance_status"] == "accepted_by_rtu"


def test_separation_of_command_acceptance_vs_actual_device_state_change(tmp_path: Path):
    """Distinguish accepted command without state change from accepted command with state change."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        # TX001: switch.30 accepted (COT=6 -> COT=7), but NO COT=3 or IPAL state change
        _row("EV-tx1cmd0000000000", 1001.0, "network", "switch.30:closed", "iec104_asdu", None,
             ca_ioa="116.10150", protocol_class="control",
             src_ip="172.16.1.2", src_port=40000, dst_ip="172.16.3.11", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        _row("EV-tx1ack0000000000", 1001.03, "network", "switch.30:closed", "iec104_asdu", None,
             ca_ioa="116.10150", protocol_class="control",
             src_ip="172.16.3.11", src_port=2404, dst_ip="172.16.1.2", dst_port=40000,
             payload={"type_id": 45, "cause": "7"}),
        # TX002: switch.31 accepted (COT=6 -> COT=7) AND followed by COT=3 spontaneous state report
        _row("EV-tx2cmd0000000000", 1003.0, "network", "switch.31:closed", "iec104_asdu", None,
             ca_ioa="117.10150", protocol_class="control",
             src_ip="172.16.1.2", src_port=40001, dst_ip="172.16.3.12", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        _row("EV-tx2ack0000000000", 1003.03, "network", "switch.31:closed", "iec104_asdu", None,
             ca_ioa="117.10150", protocol_class="control",
             src_ip="172.16.3.12", src_port=2404, dst_ip="172.16.1.2", dst_port=40001,
             payload={"type_id": 45, "cause": "7"}),
        _row("EV-tx2spont00000000", 1003.25, "network", "switch.31:is_closed", "iec104_asdu", None,
             ca_ioa="117.10160", protocol_class="monitor",
             src_ip="172.16.3.12", src_port=2404, dst_ip="172.16.1.2", dst_port=40001,
             payload={"type_id": 1, "cause": "3"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    tx1, tx2 = res["transactions"]
    assert tx1["command_acceptance_status"] == "accepted_by_rtu"
    assert tx1["device_state_change_status"] == "no_state_change_observed"
    assert "post_command_state_or_measurement_change" in tx1["missing_stages"]
    assert tx2["command_acceptance_status"] == "accepted_by_rtu"
    assert tx2["device_state_change_status"] == "state_change_observed"


def test_storyline_search_and_source_deduplication_prevent_double_counting(tmp_path: Path):
    """Verify N-N, P-P, N-P modeling, storyline beam search, and that IPAL transcription is not double-counted."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        # Pre-command measurement on sgen.6:active_power = 40000.0
        _row("EV-premeas000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
        # Setpoint command COT=6: sgen.6:target_active_power = 20000.0
        _row("EV-setcmd0000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6"}),
        # Setpoint confirmation COT=7
        _row("EV-setack0000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7"}),
        # Post-command measurement on sgen.6:active_power = 20001.0
        _row("EV-postmeas00000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20001.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
        # Derived IPAL state update for sgen.6:active_power = 20001.0 (same source, must not double-count)
        _row("EV-ipalpost00000000", 1005.5, "electrical", "sgen.6:active_power", "electrical_update", 20001.0,
             ca_ioa="111.10080", update_status="new"),
        # Cross-entity electrical change on line.7 within 2s (must stay temporal_cooccurrence / unresolved)
        _row("EV-line7el000000000", 1006.0, "electrical", "line.7:active_power_from", "electrical_update", 318000.0,
             ca_ioa="106.10090", update_status="new"),
        # Unconnected observation on bus.99 outside cooccurrence horizon
        _row("EV-bus99el000000000", 1019.0, "electrical", "bus.99:voltage", "electrical_update", 0.99,
             ca_ioa="199.10010", update_status="new"),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1020.0)

    out_dir = tmp_path / "recon_out"
    scripted = ScriptedLLM({
        "abstain": False,
        "selected_transaction_ids": ["TX001"],
        "selected_storyline_ids": ["SL001"],
        "claims": [
            {"claim_type": "measurement_claim", "fact_id": "EF001", "claim_level": "observed_fact"},
            # Attempt to upgrade an observed protocol edge to supported_inference -> must be rejected
            {"claim_type": "relation_claim", "edge_id": "R0001", "relation_type": "iec104_command_confirmation",
             "claim_level": "supported_inference"},
        ],
    })
    res = reconstruct_incident(db, 1000.0, 1020.0, background_start=985.0, background_end=1000.0,
                               llm=scripted, out_dir=out_dir)

    assert (out_dir / "transactions.json").exists()
    assert (out_dir / "event_graph.json").exists()
    assert (out_dir / "storylines.json").exists()
    assert (out_dir / "investigation_report.md").exists()
    assert (out_dir / "run_manifest.json").exists()
    assert res["lineage_bundle_summary"]["missing_ids"] == []
    assert res["lineage_bundle_summary"]["row_check_failures"] == []

    sl = res["storylines"]["storylines"][0]
    assert sl["spine_node_count"] == 5
    shared_steps = [s for s in sl["confirmed_and_supported_steps"] if s["relation_category"] == "shared_source"]
    assert len(shared_steps) == 1
    assert shared_steps[0]["independent_support"] is False
    # 4 spine edges total, but only 3 are independent (the 4th is shared_source IPAL transcription)
    assert sl["spine_edge_count"] == 4
    assert sl["independent_support_edge_count"] == 3

    # Cross-entity line.7 change stays temporal_cooccurrence / unresolved
    cooc = sl["unresolved_cooccurrence_branches"]
    assert len(cooc) == 1
    assert cooc[0]["candidate_entity"] == "line.7:active_power_from"
    assert cooc[0]["claim_level"] == "temporal_cooccurrence"
    assert cooc[0]["verification_status"] == "unresolved"

    # Verifier accepts EF001 measurement claim and rejects the R0001 upgrade
    assert len(res["explanation"]["verification"]["verified"]) == 1
    assert len(res["explanation"]["verification"]["rejected"]) == 1
    assert "observed_link_cannot_be_upgraded_to_inference" in res["explanation"]["verification"]["rejected"][0]["reasons"]
