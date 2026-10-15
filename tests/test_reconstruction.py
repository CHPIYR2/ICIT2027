"""Unit and counterexample tests for the Reliability-Hardened Incident Reconstruction Engine."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from mirage_ot.etgi.agent.ollama import LLMTurn
import struct
from mirage_ot.etgi.evidence import iec104, iec104_raw
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence
from mirage_ot.etgi.reconstruction.consistency import check_quality_consistency
from mirage_ot.etgi.reconstruction.engine import reconstruct_incident
from mirage_ot.etgi.reconstruction.event_graph import build_temporal_event_graph
from mirage_ot.etgi.reconstruction.storyline import reconstruct_storylines
from mirage_ot.etgi.reconstruction.transactions import (
    evaluate_command_effect_inference,
    reconstruct_transactions,
)


GOOD_QDS = {"iv": False, "nt": False, "sb": False, "bl": False, "ov": False}


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


def _sgen6_chain_rows(*, pre=None, cmd=None, ack=None, post=None):
    """Decoded sgen.6 setpoint chain; keyword payloads override single packets."""
    return [
        _row("EV-premeas000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1", "quality_invalid": False, "quality_flags": GOOD_QDS, "cot_test": False,
                      **(pre or {})}),
        _row("EV-setcmd0000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6", "cot_negative": False, "cot_test": False, **(cmd or {})}),
        _row("EV-setack0000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7", "cot_negative": False, "cot_test": False, **(ack or {})}),
        _row("EV-postmeas00000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20001.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1", "quality_invalid": False, "quality_flags": GOOD_QDS, "cot_test": False,
                      **(post or {})}),
        _row("EV-ipalpost00000000", 1005.5, "electrical", "sgen.6:active_power", "electrical_update", 20001.0,
             ca_ioa="111.10080", update_status="new"),
        _row("EV-line7el000000000", 1006.0, "electrical", "line.7:active_power_from", "electrical_update", 318000.0,
             ca_ioa="106.10090", update_status="new"),
    ]


def test_p0_storyline_contiguous_path_invariant_and_source_deduplication(tmp_path: Path):
    """P0-4 & P1-6: Every storyline spine must be a contiguous path; pre-baseline stays in supporting_evidence_edges."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = _sgen6_chain_rows()
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


def test_r3_invalid_or_missing_quality_cannot_be_upgraded_by_event_graph(tmp_path: Path):
    """Transaction quality rejection stays unresolved when the graph recomputes the gate."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-qpre000000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1", "quality_invalid": False}),
        _row("EV-qcmd000000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6", "cot_negative": False}),
        _row("EV-qack000000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7", "cot_negative": False}),
        _row("EV-qpost00000000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20000.5,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1", "quality_invalid": True}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)
    tx_res = reconstruct_transactions(db, 1000.0, 1010.0)
    tx = tx_res["transactions"][0]
    assert tx["device_state_change_status"] == "measurement_observed_transition_unverified"
    assert "post_value_quality_invalid" in tx["measurement_transition"]["consistency_gate"]["failed_conditions"]

    eg = build_temporal_event_graph([], {}, tx_res)
    inf = [e for e in eg["edges"] if e["relation_category"] == "inference_hypothesis"]
    assert inf
    assert all(e["claim_level"] == "unresolved" for e in inf)
    assert all(e["verification_status"] == "unresolved" for e in inf)

    stripped = copy.deepcopy(tx_res)
    mt = stripped["transactions"][0]["measurement_transition"]
    mt["post_quality_invalid"] = None
    mt["pre_quality_invalid"] = False
    mt["consistency_gate"]["gate_passed"] = False
    eg_stripped = build_temporal_event_graph([], {}, stripped)
    inf2 = [e for e in eg_stripped["edges"] if e["relation_category"] == "inference_hypothesis"]
    assert all(e["claim_level"] == "unresolved" for e in inf2)

    missing = evaluate_command_effect_inference(
        command_acceptance_status="accepted_by_rtu",
        command_value_present=True, commanded_value=20000.0,
        pre_value_present=True, pre_command_value=40000.0, pre_quality_invalid=None,
        post_value_present=True, post_command_value=20000.0, post_quality_invalid=None,
    )
    assert missing["gate_passed"] is False
    assert "pre_quality_unknown" in missing["failed_conditions"]
    assert "post_quality_unknown" in missing["failed_conditions"]
    assert missing["quality_uncertainty"]

    pre_bad = evaluate_command_effect_inference(
        command_acceptance_status="accepted_by_rtu",
        command_value_present=True, commanded_value=20000.0,
        pre_value_present=True, pre_command_value=40000.0, pre_quality_invalid=True,
        post_value_present=True, post_command_value=20000.0, post_quality_invalid=False,
    )
    assert pre_bad["gate_passed"] is False
    assert "pre_value_quality_invalid" in pre_bad["failed_conditions"]


def test_r3_ipal_source_follows_lineage_not_last_fact(tmp_path: Path):
    """Multiple IEC-104 points and IPAL rows: only a parent hit shares a canonical source."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-a-pre00000000000", 995.0, "network", "sgen.6:active_power", "iec104_asdu", 40000.0,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1", "quality_invalid": False}),
        _row("EV-b-cmd00000000000", 1001.0, "network", "sgen.10:target_active_power", "iec104_asdu", 900.0,
             ca_ioa="112.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=42000, dst_ip="172.16.3.7", dst_port=2404,
             payload={"type_id": 50, "cause": "6", "cot_negative": False}),
        _row("EV-b-post0000000000", 1004.0, "network", "sgen.10:active_power", "iec104_asdu", 1000.0,
             ca_ioa="112.10080", protocol_class="monitor",
             src_ip="172.16.3.7", src_port=2404, dst_ip="172.16.1.2", dst_port=42000,
             payload={"type_id": 13, "cause": "1", "quality_invalid": False}),
        _row("EV-a-cmd00000000000", 1002.0, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.1.2", src_port=41978, dst_ip="172.16.3.6", dst_port=2404,
             payload={"type_id": 50, "cause": "6", "cot_negative": False}),
        _row("EV-a-ack00000000000", 1002.04, "network", "sgen.6:target_active_power", "iec104_asdu", 20000.0,
             ca_ioa="111.10040", protocol_class="control",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 50, "cause": "7", "cot_negative": False}),
        _row("EV-a-post0000000000", 1005.0, "network", "sgen.6:active_power", "iec104_asdu", 20000.5,
             ca_ioa="111.10080", protocol_class="monitor",
             src_ip="172.16.3.6", src_port=2404, dst_ip="172.16.1.2", dst_port=41978,
             payload={"type_id": 13, "cause": "1", "quality_invalid": False}),
        _row("EV-ipal-a0000000000", 1005.2, "electrical", "sgen.6:active_power", "electrical_update", 20000.5,
             ca_ioa="111.10080", update_status="new", parent_evidence_id="EV-a-post0000000000"),
        _row("EV-ipal-b0000000000", 1005.3, "electrical", "sgen.10:active_power", "electrical_update", 1000.0,
             ca_ioa="112.10080", update_status="new"),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)
    tx_res = reconstruct_transactions(db, 1000.0, 1010.0)
    eg = build_temporal_event_graph([], {}, tx_res)
    ipal = [n for n in eg["nodes"] if n["kind"] == "electrical_update"]
    by_entity = {n["entity"]: n for n in ipal}
    post = next(n for n in eg["nodes"] if n["role"] == "post_command_measurement" and n["entity"] == "sgen.6:active_power")
    post10 = next(n for n in eg["nodes"] if n["role"] == "post_command_measurement" and n["entity"] == "sgen.10:active_power")
    assert by_entity["sgen.6:active_power"]["source_containers"] == post["source_containers"]
    assert by_entity["sgen.6:active_power"]["protocol_meta"]["source_binding"] == "lineage_parent"
    assert by_entity["sgen.6:active_power"]["counts_as_independent_source"] is False
    assert by_entity["sgen.10:active_power"]["source_containers"] != post["source_containers"]
    assert by_entity["sgen.10:active_power"]["source_containers"] != post10["source_containers"]
    assert by_entity["sgen.10:active_power"]["protocol_meta"]["source_binding"] == "unconfirmed_temporal_correspondence"
    deriv = [e for e in eg["edges"] if e["relation_type"] == "same_network_data_stream_ipal_derivation"]
    assert len(deriv) == 1
    assert deriv[0]["independent_support"] is False
    assert deriv[0]["target_entity"] == "sgen.6:active_power"
    temporal = [e for e in eg["edges"] if e["relation_type"] == "temporally_aligned_same_point_stream"]
    assert all(e["independent_support"] is False for e in temporal)
    assert all("same original packet" in e["support_basis"] for e in temporal)
    sl = reconstruct_storylines(eg, tx_res)
    for story in sl["storylines"]:
        containers = []
        for fid in story["spine_fact_ids"]:
            node = next(n for n in eg["nodes"] if n["fact_id"] == fid)
            if node.get("counts_as_independent_source") is not False:
                containers.extend(node["source_containers"])
        assert story["independent_source_container_count"] == len(set(containers))


def test_r3_select_and_execute_stay_distinct_transactions(tmp_path: Path):
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-sel-pkt000000000", 1001.00, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             fingerprint="fp-sel", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 10}),
        _row("EV-sel-cmd000000000", 1001.00, "network", "switch.23:closed", "iec104_asdu", 1.0,
             fingerprint="fp-sel", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-sel-pkt000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6", "select_execute": "select", "cot_negative": False}),
        _row("EV-exe-pkt000000000", 1001.40, "network", "172.16.1.2:50000->172.16.3.5:2404/TCP", "tcp_packet", 68,
             fingerprint="fp-exe", src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             update_status="packet", payload={"tcp_seq": 40}),
        _row("EV-exe-cmd000000000", 1001.40, "network", "switch.23:closed", "iec104_asdu", 1.0,
             fingerprint="fp-exe", ca_ioa="110.10130", protocol_class="control",
             parent_evidence_id="EV-exe-pkt000000000",
             src_ip="172.16.1.2", src_port=50000, dst_ip="172.16.3.5", dst_port=2404,
             payload={"type_id": 45, "cause": "6", "select_execute": "execute", "cot_negative": False}),
        _row("EV-sel-ack000000000", 1001.50, "network", "switch.23:closed", "iec104_asdu", 1.0,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=50000,
             payload={"type_id": 45, "cause": "7", "select_execute": "select", "cot_negative": False}),
        _row("EV-exe-ack000000000", 1001.80, "network", "switch.23:closed", "iec104_asdu", 1.0,
             ca_ioa="110.10130", protocol_class="control",
             src_ip="172.16.3.5", src_port=2404, dst_ip="172.16.1.2", dst_port=50000,
             payload={"type_id": 45, "cause": "7", "select_execute": "execute", "cot_negative": False}),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1010.0)
    res = reconstruct_transactions(db, 1000.0, 1010.0)
    assert res["transaction_count"] == 2
    modes = [tx["select_execute"] for tx in res["transactions"]]
    assert modes == ["select", "execute"]
    assert all(tx["command_acceptance_status"] == "accepted_by_rtu" for tx in res["transactions"])
    assert res["transactions"][0]["activation_confirmation"]["select_execute"] == "select"
    assert res["transactions"][1]["activation_confirmation"]["select_execute"] == "execute"
    assert res["unpaired_control_message_count"] == 0


def test_r3_multi_ioa_asdu_keeps_shared_header_and_does_not_shift_values():
    shared = {
        "frame.time_epoch": "1000.0",
        "ip.src": "172.16.3.6", "ip.dst": "172.16.1.2",
        "tcp.srcport": "2404", "tcp.dstport": "41978",
        "iec60870_asdu.typeid": "13",
        "iec60870_asdu.addr": "111",
        "iec60870_asdu.causetx": "1",
        "iec60870_asdu.nega": "False",
        "iec60870_asdu.sq": "False",
        "iec60870_asdu.ioa": "10080,10090",
        "iec60870_asdu.float": "1.5,2.5",
        "iec60870_asdu.qds.iv": "False,True",
    }
    objs = iec104.split_fields(shared)
    assert [(o["ioa"], o["type_id"], o["cause"], o["ca"], o["value"], o["quality_invalid"]) for o in objs] == [
        ("10080", 13, "1", "111", 1.5, False),
        ("10090", 13, "1", "111", 2.5, True),
    ]

    gapped = dict(shared)
    gapped["iec60870_asdu.ioa"] = "10080,10081,10090"
    gapped["iec60870_asdu.float"] = "1.5,,2.5"
    gapped["iec60870_asdu.qds.iv"] = "False,False,True"
    gap_objs = iec104.split_fields(gapped)
    assert [o["value"] for o in gap_objs] == [1.5, None, 2.5]
    assert gap_objs[1]["alignment"] == "identifier_without_aligned_value"
    assert gap_objs[2]["ioa"] == "10090"

    shifted = dict(shared)
    shifted["iec60870_asdu.ioa"] = "10080,10081,10090"
    shifted["iec60870_asdu.float"] = "1.5,2.5"
    shifted["iec60870_asdu.qds.iv"] = "False"
    bad = iec104.split_fields(shifted)
    assert all(o["value"] is None for o in bad)
    assert all(o["alignment"] == "value_count_mismatch_not_shifted" for o in bad)
    assert all(o["type_id"] == 13 and o["ca"] == "111" for o in bad)


def test_r3_no_control_command_storyline_is_limited():
    same = [
        {
            "timeline_id": "TL1", "role": "electrical_change", "entity": "sgen.6:active_power",
            "time": 10.0, "time_end": 10.0, "record_class": "transcription",
            "value": 1.0, "value_present": True, "ca_ioa": "111.10080",
            "observation": "active", "score": 2.0,
            "source": {"kind": "electrical_update", "modality": "electrical", "vantages": ["ipal_state"]},
            "evidence_ids": ["EV-a"],
        },
        {
            "timeline_id": "TL2", "role": "electrical_change", "entity": "sgen.6:reactive_power",
            "time": 11.0, "time_end": 11.0, "record_class": "transcription",
            "value": 2.0, "value_present": True, "ca_ioa": "111.10081",
            "observation": "reactive", "score": 1.0,
            "source": {"kind": "electrical_update", "modality": "electrical", "vantages": ["ipal_state"]},
            "evidence_ids": ["EV-b"],
        },
    ]
    eg = build_temporal_event_graph(same, {}, {"transactions": []})
    sl = reconstruct_storylines(eg, {"transactions": []})
    assert sl["no_control_command_policy"]["status"] == "limited_existing_search"
    assert sl["storyline_count"] == 1
    story = sl["storylines"][0]
    assert story["spine_is_contiguous_directed_path"] is True
    assert story["transaction_id"] is None
    assert all(step["claim_level"] != "supported_inference" for step in story["confirmed_and_supported_steps"])

    cross = [
        dict(same[0], timeline_id="TL3", entity="line.7:active_power_from", ca_ioa="106.10090", time=20.0, time_end=20.0),
        dict(same[1], timeline_id="TL4", entity="bus.0:voltage", ca_ioa="101.10010", time=21.0, time_end=21.0),
    ]
    eg2 = build_temporal_event_graph(cross, {}, {"transactions": []})
    sl2 = reconstruct_storylines(eg2, {"transactions": []})
    assert sl2["storyline_count"] == 0
    assert "deferred" in sl2["no_control_command_policy"]



def _gate(**overrides):
    args = dict(
        command_acceptance_status="accepted_by_rtu", command_value_present=True, commanded_value=20000.0,
        pre_value_present=True, pre_command_value=40000.0, post_value_present=True, post_command_value=20001.0,
        pre_quality_invalid=False, post_quality_invalid=False,
        pre_quality_flags_set=[], post_quality_flags_set=[],
        test_bits={"command": False, "confirmation": False, "pre": False, "post": False},
    )
    args.update(overrides)
    return evaluate_command_effect_inference(**args)


def test_r4_gate_requires_decoded_quality_flags_test_bits_and_acceptance():
    assert _gate()["gate_passed"] is True
    cases = {
        "command_acceptance_unknown": dict(command_acceptance_status="confirmation_observed_acceptance_unknown"),
        "pre_quality_flags_unknown": dict(pre_quality_flags_set=None),
        "post_value_quality_not_good:sb": dict(post_quality_flags_set=["sb"]),
        "post_value_quality_invalid": dict(post_quality_invalid=True),
        "test_bits_unknown": dict(test_bits=None),
        "command_test_bit_set": dict(test_bits={"command": True, "confirmation": False, "pre": False, "post": False}),
        "confirmation_test_bit_set": dict(test_bits={"command": False, "confirmation": True, "pre": False, "post": False}),
        "post_test_bit_set": dict(test_bits={"command": False, "confirmation": False, "pre": False, "post": True}),
        "post_test_bit_unknown": dict(test_bits={"command": False, "confirmation": False, "pre": False, "post": None}),
    }
    for expected, override in cases.items():
        gate = _gate(**override)
        assert gate["gate_passed"] is False, expected
        assert expected in gate["failed_conditions"], (expected, gate["failed_conditions"])


def test_r4_quality_good_is_unknown_when_any_bit_is_missing():
    assert iec104.quality_good({"iv": False, "nt": False, "sb": False, "bl": False, "ov": False}) is True
    assert iec104.quality_good({"iv": False, "nt": None, "sb": False, "bl": False, "ov": False}) is None
    assert iec104.quality_good({"iv": False, "nt": None, "sb": True, "bl": False, "ov": False}) is False
    assert iec104.quality_good(None) is None


def _frame(**fields):
    base = {"frame.time_epoch": "1000.0", "frame.number": "7", "ip.src": "172.16.3.6", "ip.dst": "172.16.1.2",
            "tcp.srcport": "2404", "tcp.dstport": "41978"}
    base.update({f"iec60870_asdu.{k}" if not k.startswith(("iec60870", "frame")) else k: v for k, v in fields.items()})
    return base


def test_r4_two_asdus_in_one_frame_keep_their_own_header_and_quality():
    row = _frame(**{
        "iec60870_104.type": "0x00,0x00", "iec60870_104.tx": "4,5", "iec60870_104.rx": "9,9",
        "typeid": "13,50", "causetx": "3,6", "nega": "False,False", "test": "False,True", "sq": "False,False",
        "addr": "111,111", "numix": "1,1", "oa": "0,0", "ioa": "10080,10040", "float": "1.5,20000.0",
        "qds.iv": "True", "qds.nt": "False", "qds.sb": "False", "qds.bl": "False", "qds.ov": "False",
        "qos.se": "False",
    })
    meas, cmd = iec104.split_fields(row)
    assert (meas["type_id"], meas["cause"], meas["cot_test"], meas["value"], meas["apci_tx"]) == (13, "3", False, 1.5, 4)
    assert meas["quality_flags"] == {"iv": True, "nt": False, "sb": False, "bl": False, "ov": False}
    assert meas["quality_good"] is False and meas["select_execute"] is None
    assert (cmd["type_id"], cmd["cause"], cmd["cot_test"], cmd["value"], cmd["apci_tx"]) == (50, "6", True, 20000.0, 5)
    assert cmd["quality_flags"] is None and cmd["quality_invalid"] is None
    assert cmd["select_execute"] == "execute"


def test_r4_per_object_quality_count_mismatch_is_not_broadcast_or_shifted():
    row = _frame(**{
        "typeid": "13", "causetx": "1", "nega": "False", "test": "False", "sq": "False", "addr": "111",
        "numix": "2", "ioa": "10080,10090", "float": "1.5,2.5",
        "qds.iv": "False", "qds.nt": "False,False", "qds.sb": "False,False", "qds.bl": "False,False",
        "qds.ov": "False,False",
    })
    objs = iec104.split_fields(row)
    assert [o["value"] for o in objs] == [1.5, 2.5]
    assert all(o["quality_invalid"] is None and o["quality_good"] is None for o in objs)
    assert all(o["field_alignment"]["iec60870_asdu.qds.iv"] == "count_mismatch_not_shifted" for o in objs)
    assert all(o["quality_flags"]["nt"] is False for o in objs)


def test_r4_missing_quality_bits_stay_unknown():
    row = _frame(**{
        "typeid": "13", "causetx": "1", "nega": "False", "test": "False", "sq": "False", "addr": "111",
        "numix": "1", "ioa": "10080", "float": "1.5", "qds.iv": "False",
    })
    (obj,) = iec104.split_fields(row)
    assert obj["quality_invalid"] is False
    assert obj["quality_flags"] == {"iv": False, "nt": None, "sb": None, "bl": None, "ov": None}
    assert obj["quality_good"] is None
    assert obj["field_alignment"]["iec60870_asdu.qds.nt"] == "not_decoded_by_tshark"


def _apdu(type_id: int, cot: int, ca: int, objects: bytes, count: int, *, tx: int = 1, sq: bool = False) -> bytes:
    asdu = bytes([type_id, (0x80 if sq else 0) | count, cot, 0]) + struct.pack("<H", ca) + objects
    control = struct.pack("<HH", tx << 1, 0)
    return bytes([0x68, len(control) + len(asdu)]) + control + asdu


def _ioa(value: int) -> bytes:
    return struct.pack("<I", value)[:3]


def test_r4_raw_decoder_reads_per_object_quality_and_cot_bits():
    meas = _apdu(13, 0x03 | 0x80, 111,
                 _ioa(10080) + struct.pack("<f", 1.5) + bytes([0x80])
                 + _ioa(10090) + struct.pack("<f", 2.5) + bytes([0x10]), 2)
    cmd = _apdu(45, 0x07 | 0x40, 110, _ioa(10130) + bytes([0x81]), 1, tx=2)
    objs, status = iec104_raw.decode_apdus(meas + cmd)
    assert status == "complete"
    m1, m2, c = objs
    assert (m1["cot_test"], m1["cot_negative"], m1["cause"], m1["value"]) == (True, False, 3, 1.5)
    assert m1["quality_flags"] == {"iv": True, "nt": False, "sb": False, "bl": False, "ov": False}
    assert m2["quality_flags"] == {"iv": False, "nt": False, "sb": False, "bl": True, "ov": False}
    assert (c["type_id"], c["cause"], c["cot_negative"], c["cot_test"]) == (45, 7, True, False)
    assert (c["value"], c["select_execute"], c["quality_flags"], c["asdu_index"]) == (1.0, "select", None, 1)


def test_r4_raw_decoder_does_not_invent_truncated_objects():
    apdu = bytearray(_apdu(13, 0x03, 111, _ioa(10080) + struct.pack("<f", 1.5) + bytes([0x00]), 2))
    objs, status = iec104_raw.decode_apdus(bytes(apdu))
    assert status == "truncated_information_object"
    assert [o["ioa"] for o in objs] == [10080]


def _reconstruct(tmp_path: Path, rows):
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1020.0)
    return reconstruct_incident(db, 1000.0, 1020.0, background_start=985.0, background_end=1000.0,
                                llm=None, out_dir=tmp_path / "out")


def test_r4_test_bit_or_flag_blocks_verification_in_every_phase(tmp_path: Path):
    variants = {
        "command_test_bit_set": dict(cmd={"cot_test": True}),
        "post_test_bit_set": dict(post={"cot_test": True}),
        "post_value_quality_not_good:nt": dict(post={"quality_flags": {**GOOD_QDS, "nt": True}}),
        "pre_quality_flags_unknown": dict(pre={"quality_flags": {**GOOD_QDS, "ov": None}}),
        "command_acceptance_unknown": dict(ack={"cot_negative": None}),
    }
    for expected, override in variants.items():
        res = _reconstruct(tmp_path / expected, _sgen6_chain_rows(**override))
        tx = res["transactions"]["transactions"][0]
        gate = tx["measurement_transition"]["consistency_gate"]
        assert gate["gate_passed"] is False and expected in gate["failed_conditions"], (expected, gate)
        assert tx["device_state_change_status"] != "verified_measurement_transition"
        assert not any(e["claim_level"] == "supported_inference" for e in res["event_graph"]["edges"]), expected
        story = res["storylines"]["storylines"][0]
        assert all(st["claim_level"] != "supported_inference" for st in story["confirmed_and_supported_steps"])
        summary = res["report"]["transaction_summaries"][0]["inference_gate"]
        assert summary["gate_passed"] is False and expected in summary["failed_conditions"]
        assert res["quality_consistency"]["consistent"] is True, res["quality_consistency"]["issues"]
        assert (tmp_path / expected / "out" / "quality_consistency.json").exists()


def test_r4_consistency_checker_flags_a_graph_that_ignores_the_gate(tmp_path: Path):
    res = _reconstruct(tmp_path, _sgen6_chain_rows(post={"cot_test": True}))
    graph = copy.deepcopy(res["event_graph"])
    for edge in graph["edges"]:
        if edge["relation_category"] == "inference_hypothesis":
            edge["claim_level"] = "supported_inference"
    check = check_quality_consistency(res["transactions"], graph, res["storylines"], res["report"])
    issues = {i["issue"] for i in check["issues"]}
    assert check["consistent"] is False
    assert "graph_inference_disagrees_with_transaction_gate" in issues
    assert "supported_inference_without_passed_gate" in issues
