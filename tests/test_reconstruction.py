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
    assert len(spine_nodes) == 3
    assert len(steps) == 2
    assert all(st["relation_category"] != "temporal_correspondence" for st in steps)
    (corr,) = sl["temporal_correspondences"]
    assert corr["from_spine_fact_id"] == spine_nodes[-1]
    assert corr["common_source_status"] == "unconfirmed_no_lineage"
    assert corr["counts_as_independent_source"] is False
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

    # CMD, ACK and POST are independent containers; the time-aligned IPAL row is off the spine
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


MASTER = "172.16.1.2"


GOOD_SIQ = {"iv": False, "nt": False, "sb": False, "bl": False}


def _iec(
    eid, t, entity, ca_ioa, value, *, rtu, tx, obj=0, type_id=13, cause="1",
    vantage="n302", quality=True, cot_test=False, extra_payload=None,
):
    default_qflags = (
        (GOOD_SIQ if type_id in (1, 2, 3, 4, 30, 31) else GOOD_QDS)
        if quality is True else None
    )
    return _row(eid, t, "network", entity, "iec104_asdu", value, vantage=vantage, ca_ioa=ca_ioa,
                protocol_class="monitor", src_ip=rtu, src_port=2404, dst_ip=MASTER, dst_port=40000,
                payload={"type_id": type_id, "cause": cause, "apci_tx": tx, "asdu_index": 0,
                         "object_index": obj, "quality_invalid": False if quality is True else None,
                         "quality_flags": default_qflags, "quality_good": quality, "cot_test": cot_test,
                         **(extra_payload or {})})


def _tcp(eid, t, src, sport, dst, dport, flags):
    return _row(eid, t, "network", f"{src}->{dst}/TCP", "tcp_packet", None, src_ip=src, src_port=sport,
                dst_ip=dst, dst_port=dport, payload={"tcp_flags": flags})


def _behavioral_rows():
    rtu_a, rtu_b, rtu_c = "172.16.3.18", "172.16.3.16", "172.16.3.22"
    rows = []
    samples_a = [
        (990.0, 100.0, 25.0, 0.98, 1e-7, 100.0, 100.0),
        (1005.0, 0.0, 0.0, 0.0, 3e-7, 300.0, 300.0),
        (1015.0, 0.0, 0.0, 0.0, 2e-7, 100.0, 305.0),
        (1025.0, 0.0, 0.0, 0.0, 1e-7, 100.0, 298.0),
    ]
    for i, (t, p, cur, volt, noise, l7, l8) in enumerate(samples_a):
        rows += [
            _iec(f"EV-a-l3p-{i}", t, "line.3:p_to", "123.1", p, rtu=rtu_a, tx=10 + i, obj=0),
            _iec(f"EV-a-l3i-{i}", t, "line.3:i_to", "123.2", cur, rtu=rtu_a, tx=10 + i, obj=1),
            _iec(f"EV-a-b5v-{i}", t, "bus.5:voltage", "123.3", volt, rtu=rtu_a, tx=10 + i, obj=2),
            _iec(f"EV-a-noise-{i}", t, "line.9:p", "123.4", noise, rtu=rtu_a, tx=10 + i, obj=3),
            _iec(f"EV-a-l7-{i}", t, "line.7:p", "123.5", l7, rtu=rtu_a, tx=10 + i, obj=4),
            _iec(f"EV-a-l8-{i}", t, "line.8:p", "123.6", l8, rtu=rtu_a, tx=10 + i, obj=5),
        ]
    rows.append(_iec("EV-a-l3p-1-m", 1005.0002, "line.3:p_to", "123.1", 0.0, rtu=rtu_a, tx=11, obj=0, vantage="n318"))
    for i, (t, p) in enumerate([(990.0, -100.0), (1010.0, 0.0), (1020.0, 0.0), (1030.0, 0.0)]):
        rows.append(_iec(f"EV-b-l3p-{i}", t, "line.3:p_from", "121.1", p, rtu=rtu_b, tx=50 + i))
    rows += [
        _iec("EV-b-sw13", 1001.0, "switch.13:is_closed", "121.9", 0.0, rtu=rtu_b, tx=60, type_id=1, cause="3"),
        _row("EV-ipal-sw13", 1001.5, "electrical", "switch.13:closed", "electrical_update", 0.0, ca_ioa="121.8"),
        _row("EV-ipal-l3p", 1005.2, "electrical", "line.3:p_to", "electrical_update", 0.0, ca_ioa="123.1"),
        _iec("EV-b-sw14-gi", 990.0, "switch.14:is_closed", "121.7", 1.0, rtu=rtu_b, tx=61, type_id=1, cause="20"),
        _iec("EV-b-sw14", 1003.0, "switch.14:is_closed", "121.7", 0.0, rtu=rtu_b, tx=62, type_id=1, cause="3"),
        _tcp("EV-tcp-fin", 1020.0, MASTER, 40001, rtu_c, 2404, 0x11),
        _tcp("EV-tcp-syn1", 1021.0, MASTER, 40002, rtu_c, 2404, 0x02),
        _tcp("EV-tcp-syn2", 1022.0, MASTER, 40002, rtu_c, 2404, 0x02),
        _tcp("EV-tcp-syn3", 1030.0, MASTER, 40003, rtu_c, 2404, 0x02),
        _tcp("EV-tcp-synack", 1030.01, rtu_c, 2404, MASTER, 40003, 0x12),
    ]
    rows += [
        _row(f"EV-arp28-{i:02d}", 1040.0 + i, "network", "172.16.3.28/ARP", "arp_packet", None,
             src_ip="172.16.3.28", dst_ip="172.16.3.9", payload={"op": 2})
        for i in range(12)
    ]
    rows += [
        _row(f"EV-arp29-{i}", 1041.0 + i, "network", "172.16.3.29/ARP", "arp_packet", None,
             src_ip="172.16.3.29", dst_ip="172.16.3.16", payload={"op": 1})
        for i in range(2)
    ]
    return rows


def _behavioral_db(tmp_path: Path):
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    for r in _behavioral_rows():
        insert_evidence(conn, r)
    conn.commit()
    return EvidenceDB(conn, incident_start=1000.0, incident_end=1060.0)


def test_behavioral_anchor_discovery_on_synthetic_rows(tmp_path: Path):
    from mirage_ot.etgi.reconstruction.anchors import discover_event_anchors

    res = discover_event_anchors(_behavioral_db(tmp_path), 1000.0, 1060.0, background_start=985.0)
    by_entity = {a["entity"]: a for a in res["anchors"]}
    assert res["observation_inventory"]["iec104_control_objects_in_window"] == 0

    sw13 = by_entity["switch.13:is_closed"]
    assert sw13["transition_status"] == "state_report_no_prior_value_in_window"
    assert sw13["verification_status"] == "unverified_observation"
    assert "no_prior_state_value_in_window" in sw13["verification_issues"]
    assert [r["evidence_id"] for r in sw13["ipal_rows"]] == ["EV-ipal-sw13"]
    sw14 = by_entity["switch.14:is_closed"]
    assert sw14["transition_status"] == "state_change_observed"
    assert sw14["verification_status"] == "verified_observation"
    assert sw14["verification_issues"] == []
    assert sw14["prior_evidence_ids"] == ["EV-b-sw14-gi"]

    line3_a = by_entity["line.3:i_to,p_to"]
    assert line3_a["step_kinds"] == ["to_zero"] and line3_a["sustained_in_later_samples"] is True
    assert line3_a["verification_status"] == "verified_observation"
    assert sorted(line3_a["evidence_ids"]) == ["EV-a-l3i-1", "EV-a-l3p-1", "EV-a-l3p-1-m"]
    assert line3_a["vantages"] == ["n302", "n318"]
    assert by_entity["bus.5:voltage"]["asdu_key"] == line3_a["asdu_key"]
    assert "line.3:p_from" in by_entity

    assert not any(e.startswith("line.9") for e in by_entity), "values below the magnitude floor are noise"
    assert not any(e.startswith("line.7") for e in by_entity), "a level shift that reverts is not an anchor"
    assert by_entity["line.8:p"]["step_kinds"] == ["level_shift"]
    assert by_entity["line.8:p"]["verification_status"] == "verified_observation"

    link = by_entity[f"{MASTER}<->172.16.3.22:2404/IEC104"]
    assert link["event_kinds"] == ["connection_attempt_unanswered", "connection_established", "tcp_fin"]
    unanswered = next(e for e in link["events"] if e["event"] == "connection_attempt_unanswered")
    assert unanswered["syn_count"] == 2
    assert link["time_end"] == 1030.01

    assert by_entity["172.16.3.28/ARP"]["packet_count"] == 12
    assert "172.16.3.29/ARP" not in by_entity
    assert [a["anchor_id"] for a in res["anchors"]] == [f"A{i:03d}" for i in range(1, len(res["anchors"]) + 1)]


def test_behavioral_graph_keeps_cross_device_relations_unresolved(tmp_path: Path):
    from mirage_ot.etgi.reconstruction.anchors import discover_event_anchors
    from mirage_ot.etgi.reconstruction.behavior import audit_anchor_lineage

    db = _behavioral_db(tmp_path)
    anchors = discover_event_anchors(db, 1000.0, 1060.0, background_start=985.0)["anchors"]
    eg = build_temporal_event_graph([], {}, {"transactions": []}, behavioral_anchors=anchors)
    nodes = {n["fact_id"]: n for n in eg["nodes"]}

    def edges(rel):
        return [e for e in eg["edges"] if e["relation_type"] == rel]

    (same,) = edges("corroborated_same_device_behavioral_transition")
    assert (nodes[same["source_fact_id"]]["entity"], nodes[same["target_fact_id"]]["entity"]) == ("line.3:i_to,p_to", "line.3:p_from")
    assert same["verification_status"] == "supported" and same["independent_support"] is True
    assert same["graph_consistency_gate_status"] == "passed_behavioral_consistency_gate"
    assert same["consistency_gate"]["gate_passed"] is True
    assert same["consistency_gate"]["matched_quantities"] == ["p"]

    asdu = edges("same_iec104_asdu")
    assert asdu and all(e["relation_category"] == "shared_source" and e["independent_support"] is False for e in asdu)
    assert {"bus.5:voltage", "line.3:i_to,p_to"} <= {nodes[e[k]]["entity"] for e in asdu for k in ("source_fact_id", "target_fact_id")}

    candidates = edges("cross_device_temporal_candidate")
    assert candidates and all(e["verification_status"] == "unresolved" and e["causal_status"] == "not_established" for e in candidates)
    assert any(nodes[e["source_fact_id"]]["entity"] == "switch.13:is_closed"
               and nodes[e["target_fact_id"]]["entity"] == "line.3:i_to,p_to" for e in candidates)
    for e in eg["edges"]:
        s, t = nodes[e["source_fact_id"]], nodes[e["target_fact_id"]]
        if e["verification_status"] == "supported" and e["relation_category"] != "shared_source":
            assert s["device_stem"] == t["device_stem"], e

    ipal = [e for e in eg["edges"] if e["relation_category"] == "temporal_correspondence"]
    assert {e["relation_type"] for e in ipal} == {"temporally_aligned_same_point_stream", "temporally_aligned_same_device_ipal_row"}
    assert all(e["verification_status"] == "common_source_unconfirmed" for e in ipal)
    assert all(nodes[e["target_fact_id"]]["counts_as_independent_source"] is False for e in ipal)

    audit = audit_anchor_lineage(db, anchors, eg["behavioral_anchor_facts"])
    assert audit["missing_ids"] == [] and audit["row_check_failures"] == []
    assert audit["checked_anchor_count"] == len(anchors)

    sl = reconstruct_storylines(eg, {"transactions": []})
    assert sl["no_control_command_policy"]["status"] == "behavioral_anchor_search"
    stories = [s for s in sl["storylines"] if s["storyline_kind"] == "behavioral"]
    assert sl["behavioral_storyline_count"] == len(stories)
    covered = [a for s in stories for a in s["anchor_ids"]]
    assert sorted(covered) == sorted(a["anchor_id"] for a in anchors), "each anchor sits on exactly one storyline"
    (chain,) = [s for s in stories if s["confirmed_and_supported_steps"]]
    assert [nodes[f]["entity"] for f in chain["spine_fact_ids"]] == ["line.3:i_to,p_to", "line.3:p_from"]
    assert chain["completeness_status"] == "behavioral_chain_with_supported_relations"
    assert "bus.5:voltage" in {c["entity"] for c in chain["co_reported_in_same_asdu"]}
    assert chain["temporal_correspondences"][0]["common_source_status"] == "unconfirmed_no_lineage"
    sw13 = next(s for s in stories if nodes[s["spine_fact_ids"][0]]["entity"] == "switch.13:is_closed")
    assert sw13["completeness_status"] == "behavioral_unverified_observation"
    assert sw13["unresolved_cooccurrence_branches"]
    assert all(b["verification_status"] == "unresolved" for b in sl["unresolved_branches"])


def test_behavioral_engine_writes_anchor_storyline_and_branch_artifacts(tmp_path: Path):
    db = _behavioral_db(tmp_path)
    out = tmp_path / "out"
    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=out)
    assert res["event_anchors"]["behavioral_mode"] is True
    for name in (
        "event_anchors.json", "behavioral_storylines.json", "unresolved_branches.json",
        "quality_consistency.json", "lineage_consistency.json", "investigation_report.md",
    ):
        assert (out / name).exists(), name
    assert res["lineage_bundle_summary"]["row_check_failures"] == []
    assert res["lineage_bundle_summary"]["behavioral_anchor_lineage"]["row_check_failures"] == []
    assert res["quality_consistency"]["consistent"] is True
    assert res["quality_consistency"]["check_scope"] == "quality_and_behavioral_consistency"
    assert res["lineage_consistency"]["consistent"] is True
    assert res["lineage_consistency"]["check_scope"] == "evidence_lineage_only"
    md = (out / "investigation_report.md").read_text()
    assert "## 2A. Behavioral Incident Reconstruction (No Control Command)" in md
    assert "Candidate relations (unresolved, time proximity only" in md
    assert "corroborated_same_device_behavioral_transition" in md


def test_behavioral_anchor_reliability_counterexamples_stay_unverified(tmp_path: Path):
    """Task 2 counterexamples: invalid quality, QDS flags, test bits, stale pre-gap, or low persistence stay unverified."""
    from mirage_ot.etgi.reconstruction.anchors import discover_event_anchors

    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rtu_a, rtu_b = "172.16.3.18", "172.16.3.16"
    rows = []
    for i, (t, val) in enumerate([(990.0, 100.0), (1005.0, 0.0), (1015.0, 0.0), (1025.0, 0.0)]):
        # 1) post_quality_invalid on bus.1:voltage at step sample (i == 1)
        rows.append(_iec(
            f"EV-qinv-{i}", t, "bus.1:voltage", "123.10", val, rtu=rtu_a, tx=100 + i,
            quality=(i != 1), extra_payload={"quality_invalid": (i == 1)},
        ))
        # 2) post_quality_flags_set:nt on bus.2:voltage at step sample (i == 1)
        rows.append(_iec(
            f"EV-qnt-{i}", t, "bus.2:voltage", "123.20", val, rtu=rtu_a, tx=200 + i,
            quality=(i != 1),
            extra_payload={"quality_invalid": False, "quality_flags": {"iv": False, "ov": False, "bl": False, "sb": False, "nt": (i == 1)}},
        ))
        # 3) post_test_bit_set on bus.3:voltage at step sample (i == 1)
        rows.append(_iec(
            f"EV-tbit-{i}", t, "bus.3:voltage", "123.30", val, rtu=rtu_a, tx=300 + i,
            cot_test=(i == 1),
        ))
    # 4) pre_sample_gap_exceeded (> 30s gap before step) on line.5:p_from
    for i, (t, val) in enumerate([(950.0, 200.0), (1005.0, 0.0), (1015.0, 0.0), (1025.0, 0.0)]):
        rows.append(_iec(f"EV-gap-{i}", t, "line.5:p_from", "121.10", val, rtu=rtu_b, tx=400 + i))
    # 5) insufficient_post_samples (only 1 post sample before window end) on line.6:p_from
    for i, (t, val) in enumerate([(1040.0, 200.0), (1050.0, 0.0), (1058.0, 0.0)]):
        rows.append(_iec(f"EV-1post-{i}", t, "line.6:p_from", "121.20", val, rtu=rtu_b, tx=500 + i))
    # 6) not_sustained_in_later_samples (holds for 1 sample then bounces away: 1/4 = 0.25 < 0.8) on line.14:current_from
    for i, (t, val) in enumerate([(990.0, -0.08), (1005.0, 0.20), (1015.0, 0.195), (1025.0, -0.07), (1035.0, 0.09), (1045.0, 0.55)]):
        rows.append(_iec(f"EV-bounce-{i}", t, "line.14:current_from", "121.30", val, rtu=rtu_b, tx=600 + i))

    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1060.0)

    anchor_res = discover_event_anchors(db, 1000.0, 1060.0, background_start=940.0)
    by_entity = {a["entity"]: a for a in anchor_res["anchors"]}
    assert anchor_res["verified_anchor_count"] == 0
    assert anchor_res["unverified_anchor_count"] == 6
    assert "post_quality_invalid" in by_entity["bus.1:voltage"]["verification_issues"]
    assert "post_quality_flags_set:nt" in by_entity["bus.2:voltage"]["verification_issues"]
    assert "post_test_bit_set" in by_entity["bus.3:voltage"]["verification_issues"]
    assert "pre_sample_gap_exceeded" in by_entity["line.5:p_from"]["verification_issues"]
    assert "insufficient_post_samples" in by_entity["line.6:p_from"]["verification_issues"]
    assert "not_sustained_in_later_samples" in by_entity["line.14:current_from"]["verification_issues"]

    eg = build_temporal_event_graph([], {}, {"transactions": []}, behavioral_anchors=anchor_res["anchors"])
    sl = reconstruct_storylines(eg, {"transactions": []})
    assert sl["supported_behavioral_storyline_count"] == 0
    assert sl["verified_single_anchor_storyline_count"] == 0
    assert sl["unverified_behavioral_observation_count"] == 6
    assert all(s["completeness_status"] == "behavioral_unverified_observation" for s in sl["storylines"])


def test_behavioral_relation_consistency_separates_sequential_observations_from_corroborated_transitions(tmp_path: Path):
    """Task 1 counterexamples: same_device + different_asdu + dt<=15s is NOT enough without compatible verified transitions."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rtu_a, rtu_b = "172.16.3.14", "172.16.3.16"
    rows = []
    # Case 1 (line.2): from-side has level_shift on Q_from (+375000 -> -11680) and P_from (890000 -> 0.026),
    # while to-side has to_zero on Q_to (-385000 -> 0.0) and P_to (-889000 -> 0.0) -> change_type_mismatch
    for i, (t, pf, qf) in enumerate([
        (990.0, 890000.0, 375000.0), (1006.0, 0.026, -11680.0), (1016.0, 0.026, -11679.0), (1026.0, 0.026, -11678.0),
    ]):
        rows.append(_iec(f"EV-l2pf-{i}", t, "line.2:active_power_from", "114.1", pf, rtu=rtu_a, tx=10 + i, obj=0))
        rows.append(_iec(f"EV-l2qf-{i}", t, "line.2:reactive_power_from", "114.2", qf, rtu=rtu_a, tx=10 + i, obj=1))
    for i, (t, pt, qt) in enumerate([
        (990.0, -889000.0, -385000.0), (1010.0, 0.0, 0.0), (1020.0, 0.0, 0.0), (1030.0, 0.0, 0.0),
    ]):
        rows.append(_iec(f"EV-l2pt-{i}", t, "line.2:active_power_to", "116.1", pt, rtu=rtu_b, tx=20 + i, obj=0))
        rows.append(_iec(f"EV-l2qt-{i}", t, "line.2:reactive_power_to", "116.2", qt, rtu=rtu_b, tx=20 + i, obj=1))

    # Case 2 (line.14): |current_from| increases (0.10 -> 0.30) while |current_to| decreases (0.40 -> 0.15) -> magnitude_direction_mismatch
    for i, (t, cf) in enumerate([(990.0, 0.10), (1005.0, 0.30), (1015.0, 0.30), (1025.0, 0.30)]):
        rows.append(_iec(f"EV-l14cf-{i}", t, "line.14:current_from", "114.3", cf, rtu=rtu_a, tx=30 + i))
    for i, (t, ct) in enumerate([(990.0, 0.40), (1008.0, 0.15), (1018.0, 0.15), (1028.0, 0.15)]):
        rows.append(_iec(f"EV-l14ct-{i}", t, "line.14:current_to", "116.3", ct, rtu=rtu_b, tx=40 + i))

    # Case 3 (sgen.0): COT=3 is_connected=0 WITHOUT prior baseline followed by active_power 20000 -> 0 -> sequential_observation
    rows.append(_iec("EV-sgen0-st", 1001.0, "sgen.0:is_connected", "115.1", 0.0, rtu="172.16.3.15", tx=50, type_id=1, cause="3"))
    for i, (t, p) in enumerate([(990.0, 20000.0), (1010.0, 0.0), (1020.0, 0.0), (1030.0, 0.0)]):
        rows.append(_iec(f"EV-sgen0-p-{i}", t, "sgen.0:active_power", "115.2", p, rtu="172.16.3.15", tx=60 + i))

    # Case 4 (sgen.1, positive control): COT=20 prior is_connected=1.0 then COT=3 is_connected=0.0 then active_power 30000 -> 0 -> supported!
    rows.append(_iec("EV-sgen1-pre", 990.0, "sgen.1:is_connected", "117.1", 1.0, rtu="172.16.3.17", tx=70, type_id=1, cause="20"))
    rows.append(_iec("EV-sgen1-st", 1002.0, "sgen.1:is_connected", "117.1", 0.0, rtu="172.16.3.17", tx=71, type_id=1, cause="3"))
    for i, (t, p) in enumerate([(990.0, 30000.0), (1008.0, 0.0), (1018.0, 0.0), (1028.0, 0.0)]):
        rows.append(_iec(f"EV-sgen1-p-{i}", t, "sgen.1:active_power", "117.2", p, rtu="172.16.3.17", tx=80 + i))

    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1060.0)

    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out")
    assert res["quality_consistency"]["consistent"] is True
    assert res["lineage_consistency"]["consistent"] is True

    seq_by_stem = {s["device_stem"]: s for s in res["storylines"]["sequential_same_device_observations"]}
    assert set(seq_by_stem) == {"line.2", "line.14", "sgen.0"}
    assert "change_type_mismatch" in seq_by_stem["line.2"]["failed_conditions"]
    assert "magnitude_direction_mismatch:current" in seq_by_stem["line.14"]["failed_conditions"]
    assert "left_anchor_unverified" in seq_by_stem["sgen.0"]["failed_conditions"]

    supported = [
        s for s in res["storylines"]["storylines"]
        if s.get("storyline_kind") == "behavioral" and s["confirmed_and_supported_steps"]
    ]
    assert len(supported) == 1
    assert supported[0]["confirmed_and_supported_steps"][0]["source_entity"] == "sgen.1:is_connected"
    assert supported[0]["confirmed_and_supported_steps"][0]["target_entity"] == "sgen.1:active_power"
    assert supported[0]["confirmed_and_supported_steps"][0]["relation_type"] == "corroborated_same_device_behavioral_transition"


def test_behavioral_consistency_checker_catches_tampered_edge_or_storyline(tmp_path: Path):
    """Task 3: check_quality_consistency rejects a sequential edge promoted to supported or an unverified anchor on a spine."""
    from mirage_ot.etgi.reconstruction.report import apply_quality_consistency

    db = _behavioral_db(tmp_path)
    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out")
    assert res["quality_consistency"]["consistent"] is True

    # Tamper 1: force an unverified anchor (switch.13) to look like a verified single-anchor storyline
    tampered_sl = copy.deepcopy(res["storylines"])
    for s in tampered_sl["storylines"]:
        if s.get("anchor_ids") == ["A001"]:
            s["completeness_status"] = "behavioral_single_anchor"
    check1 = check_quality_consistency(
        res["transactions"], res["event_graph"], tampered_sl, res["report"], anchor_result=res["event_anchors"],
    )
    assert check1["consistent"] is False
    assert any(i["issue"] == "unverified_anchor_marked_as_verified_storyline" for i in check1["issues"])

    # Tamper 2: corrupt the right endpoint of the supported line.3 edge to be unverified in the graph
    tampered_eg = copy.deepcopy(res["event_graph"])
    for n in tampered_eg["nodes"]:
        if n["entity"] == "line.3:p_from":
            n["protocol_meta"]["verification_status"] = "unverified_observation"
            n["protocol_meta"]["sustained_in_later_samples"] = False
    check2 = check_quality_consistency(
        res["transactions"], tampered_eg, res["storylines"], res["report"], anchor_result=res["event_anchors"],
    )
    issues2 = {i["issue"] for i in check2["issues"]}
    assert check2["consistent"] is False
    assert "supported_behavioral_edge_failed_consistency_gate" in issues2
    assert "unverified_anchor_in_supported_behavioral_storyline" in issues2

    diag_report = apply_quality_consistency(copy.deepcopy(res["report"]), check2, res["lineage_consistency"])
    assert diag_report["report_status"] == "diagnostic_only_quality_inconsistent"
    assert diag_report["behavioral_reconstruction"]["supported_chain_count"] == 0
    assert diag_report["behavioral_reconstruction"]["withheld_supported_chain_count"] == 1


def test_quality_inconsistent_report_is_diagnostic_only(tmp_path: Path, monkeypatch):
    from mirage_ot.etgi.reconstruction import engine

    issue = {"issue": "synthetic_disagreement", "transaction_id": "TX001"}
    monkeypatch.setattr(engine, "check_quality_consistency", lambda *a, **k: {"consistent": False, "issues": [issue]})
    res = _reconstruct(tmp_path, _sgen6_chain_rows())
    report = res["report"]
    assert report["report_status"] == "diagnostic_only_quality_inconsistent"
    assert report["verified_device_transitions"] == []
    assert report["withheld_verified_device_transitions"], "the verified transition is withheld, not lost"
    assert report["quality_consistency_issues"] == [issue]
    md = (tmp_path / "out" / "investigation_report.md").read_text()
    assert md.startswith("# Evidence-Grounded Incident Reconstruction Report — DIAGNOSTIC ONLY, NOT VERIFIED")
    assert "WITHHELD: quality inconsistent" in md
    for name in ("transactions.json", "event_graph.json", "storylines.json", "quality_consistency.json"):
        assert (tmp_path / "out" / name).exists(), name
    saved = json.loads((tmp_path / "out" / "investigation_report.json").read_text())
    assert saved["report_status"] == "diagnostic_only_quality_inconsistent"


def test_obs_quality_fields_and_merge_iec_vantages_reject_incomplete_bits_and_bad_merges():
    """Pre-synthesis fixes 1 & 2: incomplete quality bits stay unknown; same-vantage or conflicting packets never merge."""
    from mirage_ot.etgi.reconstruction.anchors import _merge_iec_vantages, _obs_quality_fields

    # Fix 2: incomplete quality bits must never be assumed good, even if quality_invalid=False or quality_good=True
    q_no_flags = _obs_quality_fields({"type_id": 13, "quality_invalid": False, "quality_good": True})
    assert q_no_flags["quality_good"] is None and q_no_flags["quality_flags_unknown"] is True

    q_missing_ov = _obs_quality_fields({
        "type_id": 13,
        "quality_invalid": False,
        "quality_good": True,
        "quality_flags": {"iv": False, "nt": False, "sb": False, "bl": False},
    })
    assert q_missing_ov["quality_good"] is None and q_missing_ov["quality_flags_unknown"] is True

    q_missing_bl_state = _obs_quality_fields({
        "type_id": 1,
        "quality_invalid": False,
        "quality_good": True,
        "quality_flags": {"iv": False, "nt": False, "sb": False},
    })
    assert q_missing_bl_state["quality_good"] is None and q_missing_bl_state["quality_flags_unknown"] is True

    q_complete = _obs_quality_fields({
        "type_id": 13,
        "quality_invalid": False,
        "quality_flags": {"iv": False, "nt": False, "sb": False, "bl": False, "ov": False},
    })
    assert q_complete["quality_good"] is True and q_complete["quality_flags_unknown"] is False

    # Fix 1a: two independent packets on the SAME vantage (n302) within 0.5s must NOT merge and get distinct asdu_keys
    same_vantage_rows = [
        _iec("EV-sv1", 1005.0, "line.3:p_to", "123.1", 0.0, rtu="172.16.3.18", tx=11, obj=0, vantage="n302"),
        _iec("EV-sv2", 1005.1, "line.3:p_to", "123.1", 0.0, rtu="172.16.3.18", tx=11, obj=0, vantage="n302"),
    ]
    merged_sv = _merge_iec_vantages(same_vantage_rows)
    assert len(merged_sv) == 2
    assert merged_sv[0]["asdu_key"] != merged_sv[1]["asdu_key"]

    # Fix 1b: two packets on DIFFERENT vantages (n302 vs n318) with conflicting values or flags must NOT merge
    conflicting_vantage_rows = [
        _iec("EV-cv1", 1005.0, "line.3:p_to", "123.1", 0.0, rtu="172.16.3.18", tx=12, obj=0, vantage="n302"),
        _iec("EV-cv2", 1005.0002, "line.3:p_to", "123.1", 99.0, rtu="172.16.3.18", tx=12, obj=0, vantage="n318"),
    ]
    merged_cv = _merge_iec_vantages(conflicting_vantage_rows)
    assert len(merged_cv) == 2
    assert all(o["cross_vantage_conflict"] is True for o in merged_cv)
    assert merged_cv[0]["asdu_key"] != merged_cv[1]["asdu_key"]


def test_incident_synthesis_enforces_four_layers_and_counterexamples(tmp_path: Path, monkeypatch):
    """Verify Layer 1-4 synthesis invariants and counterexamples:
    - Unverified anchors never form a bundle or Verified Element Bridge.
    - Same-ASDU multi-IOA anchors are collapsed to 1 independent source container.
    - Cross-device temporal candidates stay unresolved in candidate_scenario_phases.
    - Missing/failed lineage downgrades the Final Report to diagnostic_only_lineage_inconsistent.
    """
    from mirage_ot.etgi.reconstruction import engine
    from mirage_ot.etgi.reconstruction.report import apply_quality_consistency

    db = _behavioral_db(tmp_path)
    out = tmp_path / "out"
    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=out)
    assert (out / "incident_synthesis.json").exists()

    syn = res["incident_synthesis"]
    assert syn["scenario_status"] == "synthesized_consistent"
    assert res["quality_consistency"]["consistent"] is True
    assert res["quality_consistency"]["synthesis_checks"] == {
        "synthesis_no_new_supported_edges": True,
        "synthesis_unverified_quarantine_intact": True,
        "synthesis_source_ledger_exact": True,
        "synthesis_candidate_links_unresolved": True,
    }

    # 1) Unverified anchor A001 (switch.13:is_closed, no prior baseline) is quarantined and excluded from bundles/bridges
    part = syn["local_storyline_partition"]
    assert [q["anchor_id"] for q in part["quarantined_unverified_observations"]] == ["A001"]
    assert [p["anchor_id"] for p in part["unverified_precursor_state_reports"]] == ["A001"]
    bundle_anchor_ids = {aid for b in syn["rtu_asdu_bundles"] for aid in b["member_anchor_ids"]}
    assert "A001" not in bundle_anchor_ids
    bridge_anchor_ids = {
        aid for br in syn["verified_element_bridges"] for aid in (br["from_anchor_id"], br["to_anchor_id"])
    }
    assert "A001" not in bridge_anchor_ids

    # 2) Same-ASDU anchors (bus.5:voltage [A003], line.3:i_to,p_to [A004], line.8:p [A005]) share ONE RTU ASDU bundle
    # with independent_source_count == 1 and reduce the container count by 2
    shared_bundle = next(b for b in syn["rtu_asdu_bundles"] if "A004" in b["member_anchor_ids"])
    assert shared_bundle["member_anchor_ids"] == ["A003", "A004", "A005"]
    assert shared_bundle["independent_source_count"] == 1
    ledger = syn["source_dependency_ledger"]
    assert ledger["verified_anchor_count"] == 7
    assert ledger["iec104_asdu_container_count"] == 3
    assert ledger["tcp_link_container_count"] == 1
    assert ledger["arp_container_count"] == 1
    assert ledger["verified_source_container_count"] == 5
    assert ledger["co_reported_same_asdu_reduction_count"] == 2
    assert ledger["ipal_independent_source_weight"] == 0

    # 3) Verified Element Bridge on line.3 links BND-002 (RTU .18) -> BND-003 (RTU .16) without promoting bus.5 or line.8
    (bridge,) = syn["verified_element_bridges"]
    assert bridge["bridged_device_stem"] == "line.3"
    assert "Does NOT establish a physical topology connection" in bridge["what_bridge_does_not_establish"]

    # 4) All cross-device candidates in candidate_scenario_phases stay strictly unresolved
    for ph in syn["candidate_scenario_phases"]:
        for cand in ph["unresolved_cross_device_candidates"]:
            assert cand["verification_status"] == "unresolved"
            assert cand["causal_status"] == "not_established"

    # 5) Counterexample: tampering synthesis to put unverified A001 into a bridge or promote a candidate fails consistency
    tampered_syn = copy.deepcopy(syn)
    tampered_syn["verified_element_bridges"][0]["from_anchor_id"] = "A001"
    tampered_syn["candidate_scenario_phases"][0]["unresolved_cross_device_candidates"][0]["verification_status"] = "supported"
    tampered_syn["source_dependency_ledger"]["ipal_independent_source_weight"] = 1
    bad_qc = check_quality_consistency(
        res["transactions"], res["event_graph"], res["storylines"], res["report"],
        anchor_result=res["event_anchors"], incident_synthesis=tampered_syn,
    )
    bad_issues = {i["issue"] for i in bad_qc["issues"]}
    assert bad_qc["consistent"] is False
    assert "synthesis_bridge_without_corroborated_behavioral_gate" in bad_issues
    assert "synthesis_candidate_cooccurrence_promoted" in bad_issues
    assert "synthesis_ipal_counted_as_independent_source" in bad_issues

    # 6) Fix 3 counterexample: when quality_consistency is True but lineage_consistency fails, Final Report is downgraded
    failed_lineage = {
        "check_scope": "evidence_lineage_only",
        "consistent": False,
        "issues": [{"scope": "behavioral_anchor_lineage", "issue": "missing_evidence_ids", "ids": ["EV-missing"]}],
    }
    downgraded = apply_quality_consistency(copy.deepcopy(res["report"]), res["quality_consistency"], failed_lineage)
    assert downgraded["report_status"] == "diagnostic_only_lineage_inconsistent"
    assert downgraded["quality_consistency_status"] == "consistent"
    assert downgraded["lineage_consistency_status"] == "inconsistent"
    assert downgraded["behavioral_reconstruction"]["supported_chain_count"] == 0
    assert downgraded["incident_synthesis"]["scenario_status"] == "diagnostic_only_withheld"
    assert downgraded["incident_synthesis"]["verified_element_bridges"] == []
    assert len(downgraded["incident_synthesis"]["withheld_verified_element_bridges"]) == 1
    assert downgraded["markdown"].startswith("# Evidence-Grounded Incident Reconstruction Report — DIAGNOSTIC ONLY, NOT VERIFIED")
    assert "Lineage Issue:" in downgraded["markdown"]

    # 7) End-to-end engine check: when export_lineage_bundle reports a missing ID, the written report is diagnostic_only
    monkeypatch.setattr(
        engine,
        "export_lineage_bundle",
        lambda *a, **k: {
            "db_fingerprint": "test",
            "requested_count": 1,
            "expected_with_parents": 1,
            "exported_count": 0,
            "missing_ids": ["EV-missing-from-db"],
            "row_check_failures": [],
            "rows": [],
        },
    )
    out_bad_lin = tmp_path / "out_bad_lineage"
    res_bad_lin = reconstruct_incident(
        db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=out_bad_lin,
    )
    assert res_bad_lin["quality_consistency"]["consistent"] is True
    assert res_bad_lin["lineage_consistency"]["consistent"] is False
    assert res_bad_lin["report"]["report_status"] == "diagnostic_only_lineage_inconsistent"
    assert res_bad_lin["report"]["incident_synthesis"]["verified_element_bridges"] == []


def test_incident_synthesis_without_bridges_builds_arp_and_link_candidate_scenario(tmp_path: Path):
    """When there are 0 Verified Element Bridges but ARP + IEC-104 link disruptions exist, Layer 3 & 4 still build a candidate scenario."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row(f"EV-arp-{i:02d}", 1001.0 + i * 0.5, "network", "172.16.3.28/ARP", "arp_packet", None,
             src_ip="172.16.3.28", dst_ip="172.16.3.10" if i % 2 == 0 else "172.16.3.9", payload={"op": 2})
        for i in range(14)
    ] + [
        _tcp("EV-fin-10", 1007.0, MASTER, 56094, "172.16.3.10", 2404, 0x11),
        _tcp("EV-syn-10a", 1008.0, MASTER, 56736, "172.16.3.10", 2404, 0x02),
        _tcp("EV-syn-10b", 1009.0, MASTER, 56736, "172.16.3.10", 2404, 0x02),
        _tcp("EV-fin-9", 1012.0, MASTER, 54426, "172.16.3.9", 2404, 0x11),
        _tcp("EV-syn-9a", 1013.0, MASTER, 58512, "172.16.3.9", 2404, 0x02),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1040.0)

    res = reconstruct_incident(db, 1000.0, 1040.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out")
    syn = res["incident_synthesis"]
    assert syn["verified_element_bridges"] == []
    assert syn["bridged_bundle_components"] == []
    assert len(syn["rtu_asdu_bundles"]) == 3
    (phase,) = syn["candidate_scenario_phases"]
    assert phase["phase_profile"] == "arp_burst_and_multi_rtu_iec104_link_disruptions"
    assert phase["observed_host_and_link_context"]["arp_activity"][0]["arp_target_overlap_rtu_ips"] == [
        "172.16.3.10", "172.16.3.9",
    ]
    assert phase["unresolved_cross_device_candidate_count"] >= 2
    assert all(c["verification_status"] == "unresolved" for c in phase["unresolved_cross_device_candidates"])
    classes = [e["hypothesis_class"] for e in syn["competing_explanations"]]
    assert "arp_address_interference_preceding_iec104_session_loss_hypothesis" in classes
    assert "concurrent_l2_link_disturbance_and_arp_re_resolution_hypothesis" in classes
    precedence = next(e for e in syn["competing_explanations"] if e["hypothesis_class"].startswith("arp_address"))
    assert precedence["eligibility_gate"] == "passed_per_target_arp_overlap_and_temporal_order"
    assert precedence["eligible_arp_link_pairs"]
    assert all(p["timestamp_basis"] == "per_target_first_arp_packet" for p in precedence["eligible_arp_link_pairs"])


def test_cross_rtu_bridge_rejects_same_rtu_and_inconsistent_endpoints(tmp_path: Path):
    """A supported same-RTU relation is kept but is not a cross-RTU bridge. Tampered endpoints fail the checker."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rtu = "172.16.3.17"
    rows = [
        _iec("EV-sgen1-pre", 990.0, "sgen.1:is_connected", "117.1", 1.0, rtu=rtu, tx=70, type_id=1, cause="20"),
        _iec("EV-sgen1-st", 1002.0, "sgen.1:is_connected", "117.1", 0.0, rtu=rtu, tx=71, type_id=1, cause="3"),
    ]
    for i, (t, p) in enumerate([(990.0, 30000.0), (1008.0, 0.0), (1018.0, 0.0), (1028.0, 0.0)]):
        rows.append(_iec(f"EV-sgen1-p-{i}", t, "sgen.1:active_power", "117.2", p, rtu=rtu, tx=80 + i))
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1060.0)
    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out")
    syn = res["incident_synthesis"]
    assert syn["verified_element_bridges"] == []
    (same,) = syn["same_rtu_supported_relations"]
    assert same["from_rtu_ip"] == same["to_rtu_ip"] == rtu
    assert same["independent_rtu_support"] is False
    assert res["quality_consistency"]["consistent"] is True

    base = _behavioral_db(tmp_path / "cross")
    cross = reconstruct_incident(base, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "cross-out")
    original = cross["incident_synthesis"]
    (bridge,) = original["verified_element_bridges"]
    assert bridge["from_rtu_ip"] != bridge["to_rtu_ip"]

    def issues_for(mutator):
        tampered = copy.deepcopy(original)
        mutator(tampered["verified_element_bridges"][0])
        checked = check_quality_consistency(
            cross["transactions"], cross["event_graph"], cross["storylines"], cross["report"],
            anchor_result=cross["event_anchors"], incident_synthesis=tampered,
        )
        return {i["issue"] for i in checked["issues"]}

    other_bundle = next(b["bundle_id"] for b in original["rtu_asdu_bundles"] if b["bundle_id"] != bridge["from_bundle_id"])
    assert "synthesis_bridge_bundle_endpoint_mismatch" in issues_for(lambda br: br.update(from_bundle_id=other_bundle))
    assert "synthesis_bridge_not_cross_rtu" in issues_for(lambda br: br.update(from_rtu_ip=br["to_rtu_ip"]))
    # Distinct RTU IP that does NOT match the underlying graph node / bundle RTU IP must also be rejected
    assert "synthesis_bridge_rtu_ip_mismatch" in issues_for(lambda br: br.update(from_rtu_ip="172.16.3.99"))
    assert "synthesis_bridge_rtu_ip_mismatch" in issues_for(lambda br: br.update(to_rtu_ip="172.16.3.98"))
    other_anchor = next(
        aid for b in original["rtu_asdu_bundles"] for aid in b["member_anchor_ids"] if aid != bridge["from_anchor_id"]
    )
    assert "synthesis_bridge_anchor_or_fact_mismatch" in issues_for(lambda br: br.update(from_anchor_id=other_anchor))


def test_arp_precedence_hypothesis_requires_overlap_and_order(tmp_path: Path):
    """ARP that does not address the disrupted RTU, or that starts after the link change, claims no precedence."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row(f"EV-arp-{i:02d}", 1030.0 + i, "network", "172.16.3.28/ARP", "arp_packet", None,
             src_ip="172.16.3.28", dst_ip="172.16.3.99", payload={"op": 2})
        for i in range(12)
    ] + [
        _tcp("EV-fin-10", 1005.0, MASTER, 56094, "172.16.3.10", 2404, 0x11),
        _tcp("EV-syn-10", 1006.0, MASTER, 56736, "172.16.3.10", 2404, 0x02),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1060.0)
    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out")
    classes = [e["hypothesis_class"] for e in res["incident_synthesis"]["competing_explanations"]]
    assert "arp_address_interference_preceding_iec104_session_loss_hypothesis" not in classes
    general = next(e for e in res["incident_synthesis"]["competing_explanations"] if e["eligibility_gate"] == "failed_target_overlap_or_temporal_order")
    assert "No precedence" in general["explanation_summary"]
    ledger = res["incident_synthesis"]["source_dependency_ledger"]
    assert ledger["arp_container_count"] == 1
    assert ledger["tcp_link_container_count"] == 1
    assert ledger["iec104_asdu_container_count"] == 0


def test_arp_precedence_uses_per_target_first_packet_and_degrades_when_missing(tmp_path: Path):
    """Per-target first ARP time filters out late-targeted RTUs; missing per-target times degrade to weak co-occurrence."""
    from mirage_ot.etgi.reconstruction.synthesis import synthesize_incident_scenario

    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    # ARP anchor starts at 1001.0 targeting .10 (10 packets), and only targets .20 at 1045.0 (2 packets),
    # while .10 link changes at 1007.0 and .20 link changes at 1008.0.
    rows = [
        _row(f"EV-arp10-{i:02d}", 1001.0 + i * 0.2, "network", "172.16.3.28/ARP", "arp_packet", None,
             src_ip="172.16.3.28", dst_ip="172.16.3.10", payload={"op": 2})
        for i in range(10)
    ] + [
        _row(f"EV-arp20-{i:02d}", 1045.0 + i * 0.2, "network", "172.16.3.28/ARP", "arp_packet", None,
             src_ip="172.16.3.28", dst_ip="172.16.3.20", payload={"op": 2})
        for i in range(2)
    ] + [
        _tcp("EV-fin-10", 1007.0, MASTER, 56094, "172.16.3.10", 2404, 0x11),
        _tcp("EV-syn-10", 1008.0, MASTER, 56736, "172.16.3.10", 2404, 0x02),
        _tcp("EV-fin-20", 1008.0, MASTER, 51454, "172.16.3.20", 2404, 0x11),
        _tcp("EV-syn-20", 1009.0, MASTER, 51456, "172.16.3.20", 2404, 0x02),
    ]
    for r in rows:
        insert_evidence(conn, r)
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000.0, incident_end=1060.0)
    res = reconstruct_incident(db, 1000.0, 1060.0, background_start=985.0, background_end=1000.0, llm=None, out_dir=tmp_path / "out")
    syn = res["incident_synthesis"]
    prec = next(
        e for e in syn["competing_explanations"]
        if e["hypothesis_class"] == "arp_address_interference_preceding_iec104_session_loss_hypothesis"
    )
    # Only .10 passes per-target precedence; .20 (first ARP at 1045.0 > link change at 1008.0) is excluded!
    assert prec["anchoring_verified_evidence"]["overlapping_target_rtu_ips"] == ["172.16.3.10"]
    assert [p["rtu_ip"] for p in prec["eligible_arp_link_pairs"]] == ["172.16.3.10"]
    assert [p["rtu_ip"] for p in prec["ineligible_arp_link_pairs"]] == ["172.16.3.20"]
    assert prec["ineligible_arp_link_pairs"][0]["arp_before_link"] is False

    # When per-target ARP timestamps are absent on the anchor, only the weaker co-occurrence claim is emitted
    stripped_anchors = copy.deepcopy(res["event_anchors"])
    for a in stripped_anchors["anchors"]:
        a.pop("target_first_seen", None)
        a.pop("target_first_evidence_ids", None)
    degraded_syn = synthesize_incident_scenario(
        incident_start=1000.0,
        incident_end=1060.0,
        tx_result=res["transactions"],
        anchor_result=stripped_anchors,
        event_graph=res["event_graph"],
        storyline_result=res["storylines"],
    )
    deg_classes = [e["hypothesis_class"] for e in degraded_syn["competing_explanations"]]
    assert "arp_address_interference_preceding_iec104_session_loss_hypothesis" not in deg_classes
    assert "arp_and_iec104_link_temporal_cooccurrence_without_per_target_timestamp" in deg_classes
    weak_exp = next(
        e for e in degraded_syn["competing_explanations"]
        if e["hypothesis_class"] == "arp_and_iec104_link_temporal_cooccurrence_without_per_target_timestamp"
    )
    assert weak_exp["eligibility_gate"] == "degraded_missing_per_target_arp_timestamp"
