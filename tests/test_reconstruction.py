"""Unit and counterexample tests for the Reliability-Hardened Incident Reconstruction Engine."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from mirage_ot.etgi.agent.ollama import LLMTurn
from mirage_ot.etgi.evidence import iec104
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence
from mirage_ot.etgi.reconstruction.engine import reconstruct_incident
from mirage_ot.etgi.reconstruction.event_graph import build_temporal_event_graph
from mirage_ot.etgi.reconstruction.storyline import reconstruct_storylines
from mirage_ot.etgi.reconstruction.transactions import (
    evaluate_command_effect_inference,
    reconstruct_transactions,
)


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


def test_iec104_decoder_parses_boolean_spi_sco_and_cot_negative_flags():
    """P0-1 & P0-3: Verify tshark boolean fields (siq.spi, sco.on, nega, sco.se, tx/rx) decode properly."""
    cmd_row = {
        "frame.time_epoch": "1742961051.261847",
        "ip.src": "172.16.3.5",
        "ip.dst": "172.16.1.2",
        "tcp.srcport": "2404",
        "tcp.dstport": "58630",
        "iec60870_104.type": "0x00000000",
        "iec60870_104.tx": "645",
        "iec60870_104.rx": "4",
        "iec60870_asdu.typeid": "45",
        "iec60870_asdu.addr": "110",
        "iec60870_asdu.causetx": "7",
        "iec60870_asdu.nega": "True",
        "iec60870_asdu.test": "False",
        "iec60870_asdu.sq": "False",
        "iec60870_asdu.ioa": "10130",
        "iec60870_asdu.sco.on": "True",
        "iec60870_asdu.sco.se": "False",
    }
    objs = iec104.split_fields(cmd_row)
    assert len(objs) == 1
    obj = objs[0]
    assert obj["value_present"] is True
    assert obj["value"] == 1.0
    assert obj["alignment"] == "sco"
    assert obj["cot_negative"] is True
    assert obj["select_execute"] == "execute"
    assert obj["apci_tx"] == 645
    assert obj["apci_rx"] == 4

    sp_row = {
        "frame.time_epoch": "1742961051.462021",
        "ip.src": "172.16.3.5",
        "ip.dst": "172.16.1.2",
        "tcp.srcport": "2404",
        "tcp.dstport": "58630",
        "iec60870_asdu.typeid": "1",
        "iec60870_asdu.addr": "110",
        "iec60870_asdu.causetx": "3",
        "iec60870_asdu.nega": "False",
        "iec60870_asdu.ioa": "10140",
        "iec60870_asdu.siq.spi": "False",
        "iec60870_asdu.siq.iv": "False",
    }
    sp_obj = iec104.split_fields(sp_row)[0]
    assert sp_obj["value_present"] is True
    assert sp_obj["value"] == 0.0
    assert sp_obj["alignment"] == "spi"
    assert sp_obj["quality_invalid"] is False


def test_p0_switch_state_report_without_decoded_value_or_pre_baseline_is_not_state_change(tmp_path: Path):
    """P0-1: Mere presence of COT=3 or IPAL new row must NOT set state_change_observed."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        # Case A: COT=6 -> COT=7 -> COT=3 with value=None (unparsed_value) + IPAL new row
        _row("EV-tx1cmd0000000000", 1001.0, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.1.2", src_port=58630, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        _row("EV-tx1ack0000000000", 1001.04, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=58630,
             payload={"type_id": 45, "cause": "7"}),
        _row("EV-tx1sp00000000000", 1001.24, "network", "switch.23:is_closed", "iec104_asdu", None,
             ca_ioa="110.10140", protocol_class="monitor",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=58630,
             payload={"type_id": 1, "cause": "3", "alignment": "unparsed_value"}),
        _row("EV-tx1ipal000000000", 1001.85, "electrical", "switch.23:closed", "electrical_update", 1.0,
             ca_ioa="110.10130", update_status="new"),
        # Case B: COT=6 (value=1.0) -> COT=7 (cot_negative=False) -> COT=3 (value=1.0), but NO pre-command baseline
        _row("EV-tx2cmd0000000000", 1005.0, "network", "switch.24:closed", "iec104_asdu", 1.0,
             ca_ioa="110.10150", protocol_class="control",
             src_ip="172.16.1.2", src_port=58630, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6", "cot_negative": False}),
        _row("EV-tx2ack0000000000", 1005.04, "network", "switch.24:closed", "iec104_asdu", 1.0,
             ca_ioa="110.10150", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=58630,
             payload={"type_id": 45, "cause": "7", "cot_negative": False}),
        _row("EV-tx2sp00000000000", 1005.24, "network", "switch.24:is_closed", "iec104_asdu", 1.0,
             ca_ioa="110.10160", protocol_class="monitor",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=58630,
             payload={"type_id": 1, "cause": "3"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    tx1, tx2 = res["transactions"]
    assert tx1["command_acceptance_status"] == "confirmation_observed_acceptance_unknown"
    assert tx1["device_state_change_status"] == "state_report_observed_value_unknown"
    assert tx2["command_acceptance_status"] == "accepted_by_rtu"
    assert tx2["device_state_change_status"] == "state_report_observed_no_pre_baseline"

    eg = build_temporal_event_graph([], {}, res)
    inf_edges = [e for e in eg["edges"] if e["relation_category"] == "inference_hypothesis"]
    assert len(inf_edges) == 2
    assert all(e["claim_level"] == "unresolved" and e["verification_status"] == "unresolved" for e in inf_edges)


def test_p0_cot7_negative_confirmation_rejects_command_and_blocks_inference(tmp_path: Path):
    """P0-3: COT=7 with cot_negative=True must mark rejected_negative_confirmation and block inference."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-pre0000000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
        _row("EV-cmd0000000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6", "cot_negative": False}),
        # Negative confirmation (NACK: cot_negative=True)
        _row("EV-nack000000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7", "cot_negative": True}),
        _row("EV-post000000000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    tx = res["transactions"][0]
    assert tx["command_acceptance_status"] == "rejected_negative_confirmation"
    assert tx["device_state_change_status"] == "measurement_observed_transition_unverified"
    eg = build_temporal_event_graph([], {}, res)
    assert eg["edges_by_claim_level"].get("supported_inference", 0) == 0


def test_p0_consistency_gate_counterexamples_block_supported_inference(tmp_path: Path):
    """P0-2: Audit counterexamples (unchanged post=39999, wrong direction, no pre-baseline) must stay unresolved."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-pre0000000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40004.5312,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
        _row("EV-cmd0000000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6"}),
        _row("EV-ack0000000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7"}),
        _row("EV-post000000000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20000.6875,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)
    tx_valid = reconstruct_transactions(db, 1000.0, 1010.0)

    # Exact audit counterexample: mutate post_command_value to 39999.0 and set flags to False
    tx_mutated = copy.deepcopy(tx_valid)
    mt = tx_mutated["transactions"][0]["measurement_transition"]
    mt["post_command_value"] = 39999.0
    mt["shifted_from_pre_baseline"] = False
    mt["matches_commanded_setpoint"] = False

    eg_bad = build_temporal_event_graph([], {}, tx_mutated)
    inf_edges = [e for e in eg_bad["edges"] if e["relation_category"] == "inference_hypothesis"]
    assert len(inf_edges) == 1
    assert inf_edges[0]["claim_level"] == "unresolved"
    assert inf_edges[0]["verification_status"] == "unresolved"
    assert "matching target setpoint" not in inf_edges[0]["support_basis"]

    # Wrong direction counterexample (pre=40000, cmd=20000, post=45000)
    gate_wrong_dir = evaluate_command_effect_inference(
        command_acceptance_status="accepted_by_rtu",
        command_value_present=True,
        commanded_value=20000.0,
        pre_value_present=True,
        pre_command_value=40000.0,
        post_value_present=True,
        post_command_value=45000.0,
    )
    assert gate_wrong_dir["gate_passed"] is False
    assert "shift_direction_does_not_approach_target" in gate_wrong_dir["failed_conditions"]

    # No pre-command baseline counterexample
    gate_no_pre = evaluate_command_effect_inference(
        command_acceptance_status="accepted_by_rtu",
        command_value_present=True,
        commanded_value=20000.0,
        pre_value_present=False,
        pre_command_value=None,
        post_value_present=True,
        post_command_value=20000.0,
    )
    assert gate_no_pre["gate_passed"] is False
    assert "missing_pre_command_baseline" in gate_no_pre["failed_conditions"]


def test_p1_cross_vantage_payload_conflict_and_distinct_seq_commands(tmp_path: Path):
    """P1-5: Same tcp_seq with different values across vantages must NOT merge; different tcp_seq before ACK starts new TX."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        # Audit synthetic counterexample: same 5-tuple, tcp_seq=55, CA/IOA, type=50, COT=6, but n302=100.0 vs n318=999.0
        _row("EV-p55n302000000000", 1001.00, "network", "172.16.1.2:50000->172.16.3.6:2404/TCP", "tcp_packet", 68,
             vantage="n302", fingerprint="fp-55-a", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.6", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 55}),
        _row("EV-p55n318000000000", 1001.01, "network", "172.16.1.2:50000->172.16.3.6:2404/TCP", "tcp_packet", 68,
             vantage="n318", fingerprint="fp-55-b", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.6", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 55}),
        _row("EV-a55n302000000000", 1001.00, "network", "sgen.6:target_active_power", "iec104_asdu", 100.0,
             vantage="n302", fingerprint="fp-55-a", ca_ioa="111.10040", protocol_class="control",
             parent_evidence_id="EV-p55n302000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6"}),
        _row("EV-a55n318000000000", 1001.01, "network", "sgen.6:target_active_power", "iec104_asdu", 999.0,
             vantage="n318", fingerprint="fp-55-b", ca_ioa="111.10040", protocol_class="control",
             parent_evidence_id="EV-p55n318000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6"}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    assert res["cross_vantage_conflict_count"] == 1
    assert res["cross_vantage_conflicts"][0]["conflict_type"] == "cross_vantage_payload_conflict"
    assert res["transaction_count"] == 2
    vals = [t["commanded_value"] for t in res["transactions"]]
    assert vals == [100.0, 999.0]


def test_p0_storyline_contiguous_path_invariant_and_source_deduplication(tmp_path: Path):
    """P0-4 & P1-6: Every storyline spine must be a contiguous path; pre-baseline stays in supporting_evidence_edges."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-premeas000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
        _row("EV-setcmd0000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6", "cot_negative": False}),
        _row("EV-setack0000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7", "cot_negative": False}),
        _row("EV-postmeas00000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20001.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1"}),
        _row("EV-ipalpost00000000", 1005.5, "electrical", "sgen.6:active_power", "electrical_update", 20001.0,
             ca_ioa="111.10080", update_status="new"),
        _row("EV-line7el000000000", 1006.0, "electrical", "line.7:active_power_from", "electrical_update", 318000.0,
             ca_ioa="106.10090", update_status="new"),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1020.0)

    out_dir = tmp_path / "recon_out"
    res = reconstruct_incident(db, 1000.0, 1020.0, background_start=985.0, background_end=1000.0,
                               llm=None, out_dir=out_dir)

    sl = res["storylines"]["storylines"][0]
    assert sl["spine_is_contiguous_directed_path"] is True
    spine_nodes = sl["spine_fact_ids"]
    steps = sl["confirmed_and_supported_steps"]
    assert len(spine_nodes) == 4
    assert len(steps) == 3
    for i, step in enumerate(steps):
        assert step["source_fact_id"] == spine_nodes[i]
        assert step["target_fact_id"] == spine_nodes[i + 1]
        assert step["source_evidence_ids"]
        assert step["target_evidence_ids"]

    # Pre-command baseline is in context_observations + supporting_evidence_edges
    assert len(sl["context_observations"]) == 1
    assert sl["context_observations"][0]["role"] == "pre_command_measurement"
    assert len(sl["supporting_evidence_edges"]) == 1
    assert sl["supporting_evidence_edges"][0]["relation_type"] == "pre_to_post_measurement_transition"

    # Independent source container count on the 4-node spine is 3 (CMD, ACK, POST; IPAL shares POST's source)
    assert sl["independent_source_container_count"] == 3
    assert sl["total_independent_source_containers_with_supporting"] == 4
    assert sl["independent_support_edge_count"] == 2


def test_protocol_pairing_rejects_same_ca_ioa_on_mismatched_session_or_type(tmp_path: Path):
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-cmd0000000000001", 1001.0, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6"}),
        _row("EV-badack0000000001", 1001.05, "network", "switch.23:closed", "iec104_asdu", None,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=59999,
             payload={"type_id": 45, "cause": "7"}),
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
    assert res["transactions"][0]["command_acceptance_status"] == "unconfirmed_missing_cot7"
    assert res["unpaired_control_message_count"] == 2


def test_tcp_retransmit_same_seq_vs_new_application_command_different_seq(tmp_path: Path):
    """P1-5: Same tcp_seq at same vantage before ACK is tcp_retransmission; different tcp_seq/apci_tx starts a new TX."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-p100a00000000000", 1001.00, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             vantage="n302", fingerprint="fp-100a", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 100}),
        _row("EV-a100a00000000000", 1001.00, "network", "switch.23:closed", "iec104_asdu", 1.0,
             vantage="n302", fingerprint="fp-100a", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-p100a00000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6", "apci_tx": 1}),
        # True TCP retransmission at same vantage 0.1s later (same tcp_seq=100, apci_tx=1, different capture fingerprint)
        _row("EV-p100b00000000000", 1001.10, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             vantage="n302", fingerprint="fp-100b", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 100}),
        _row("EV-a100b00000000000", 1001.10, "network", "switch.23:closed", "iec104_asdu", 1.0,
             vantage="n302", fingerprint="fp-100b", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-p100b00000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6", "apci_tx": 1}),
        # Distinct application command 0.2s later BEFORE ACK (different tcp_seq=116, apci_tx=2) -> must NOT be swallowed
        _row("EV-p116a00000000000", 1001.20, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             vantage="n302", fingerprint="fp-116a", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 116}),
        _row("EV-a116a00000000000", 1001.20, "network", "switch.23:closed", "iec104_asdu", 1.0,
             vantage="n302", fingerprint="fp-116a", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-p116a00000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6", "apci_tx": 2}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)

    res = reconstruct_transactions(db, 1000.0, 1010.0)
    assert res["transaction_count"] == 2
    tx1, tx2 = res["transactions"]
    assert len(tx1["duplicate_command_messages"]) == 1
    assert tx1["duplicate_command_messages"][0]["duplicate_classification"] == "tcp_retransmission"
    assert tx2["transaction_id"] == "TX002"
    assert tx2["command_activation"]["tcp_seq"] == 116

