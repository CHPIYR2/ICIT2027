"""Post-alert selection, timeline, relations, and claim checks. No live model."""
import json
from pathlib import Path
from mirage_ot.etgi.agent.ollama import LLMTurn
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence
from mirage_ot.etgi.postalert.pipeline import prepare, run_explanation, write_run
from mirage_ot.etgi.postalert.verify import verify_claims


class Scripted:
    model_name = "scripted"

    def __init__(self, content):
        self.content = content

    def chat(self, messages, **kwargs):
        return LLMTurn(self.content, [], 20, 10, {}, self.model_name, done_reason="stop")


def _db(tmp_path: Path) -> EvidenceDB:
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = [
        _row("EV-aaaaaaaaaaaaaaaa", 1001, "network", "10.0.0.1:2404->10.0.0.2:50000/TCP", "tcp_packet", 60,
             fingerprint="frame-a", vantage="n302", src="10.0.0.1", dst="10.0.0.2", sport=2404, dport=50000),
        _row("EV-bbbbbbbbbbbbbbbb", 1001.1, "network", "10.0.0.2:50000->10.0.0.1:2404/TCP", "tcp_packet", 60,
             fingerprint="frame-b", vantage="n302", src="10.0.0.2", dst="10.0.0.1", sport=50000, dport=2404),
        _row("EV-dddddddddddddddd", 1003, "network", "bus.0:voltage", "iec104_asdu", 1.0,
             fingerprint="frame-c", vantage="n302", ca_ioa="101.10010", protocol_class="monitor",
             parent_evidence_id="EV-aaaaaaaaaaaaaaaa"),
        _row("EV-eeeeeeeeeeeeeeee", 1003.2, "electrical", "bus.0:voltage", "electrical_update", 1.0,
             ca_ioa="101.10010", update_status="new"),
        _row("EV-ffffffffffffffff", 1004, "electrical", "sgen.0:active_power", "electrical_update", 5,
             update_status="new"),
        _row("EV-1111111111111111", 1005, "electrical", "sgen.0:active_power", "electrical_hold_summary", 5,
             update_status="hold"),
    ]
    for row in rows:
        insert_evidence(conn, row)
    conn.commit()
    return EvidenceDB(conn, incident_start=1000, incident_end=1010)


def _row(evidence_id, timestamp, modality, entity, kind, value, **extra):
    present = extra.pop("value_present", value is not None)
    return {
        "evidence_id": evidence_id, "timestamp": timestamp, "modality": modality, "entity": entity,
        "kind": kind, "value": 0 if value is None else value, "value_present": present,
        "source_ref": evidence_id, "update_status": extra.pop("update_status", "packet"),
        "trust": "test", "payload": {"note": "telemetry"}, **extra,
    }


def test_holds_and_packet_derivatives_are_not_independent(tmp_path):
    prepared = prepare(_db(tmp_path), 1000, 1010, background_start=1000, background_end=1000)
    assert prepared["selection"]["excluded_by_reason"]["forward_filled_or_initial_state"] == 1
    assert prepared["selection"]["collapsed_by_reason"]["same_packet_derivative"] == 1
    packet = next(event for event in prepared["timeline"] if "EV-dddddddddddddddd" in event["evidence_ids"])
    assert packet["record_class"] == "transcription"
    assert packet["independent"] is False
    assert "EV-aaaaaaaaaaaaaaaa" in packet["lineage"] or "EV-aaaaaaaaaaaaaaaa" in packet["evidence_ids"]


def test_time_proximity_stays_cooccurrence_and_tcp_is_observed(tmp_path):
    prepared = prepare(_db(tmp_path), 1000, 1010, background_start=1000, background_end=1000)
    levels = {relation["relation_type"]: relation["claim_level"] for relation in prepared["relations"]}
    assert levels["communication"] == "observed_fact"
    assert "temporal_cooccurrence" in levels.values()
    assert "supported_inference" not in levels.values()
    causal = {relation["causal_status"] for relation in prepared["relations"]}
    assert causal == {"not_established"}


def test_rejected_claims_are_kept_and_a_minimum_report_remains(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    bad = json.dumps({"abstain": False, "hypotheses": [], "claims": [
        {"statement": "The voltage was 9.", "evidence_ids": ["EV-eeeeeeeeeeeeeeee"], "entity": "bus.0:voltage",
         "time": 1003.2, "value": 9, "claim_level": "observed_fact"},
        {"statement": "This caused the change.", "evidence_ids": ["EV-9999999999999999"], "claim_level": "supported_inference"},
    ]})
    result = run_explanation(db, Scripted(bad), prepared, level="B4")
    reasons = [reason for claim in result["verification"]["rejected"] for reason in claim["reasons"]]
    assert "value_does_not_match_cited_rows" in reasons
    assert any(reason.startswith("evidence_id_not_in_database") for reason in reasons)
    assert result["published_claims"] == []
    assert result["minimum"] is True
    assert "bus.0:voltage" in result["report"]["text"]
    assert result["report"]["no_confirmed_inferred_relation"]
    out = tmp_path / "run"
    write_run(db, Scripted(bad), prepared, out, level="B4")
    assert (out / "timeline.json").exists()
    assert (out / "relations.json").exists()
    saved = json.loads((out / "verification.json").read_text())
    assert saved["rejected"]


def test_a_truncated_claim_list_keeps_the_closed_claims():
    from mirage_ot.etgi.postalert.explain import _object
    text = """{"abstain": false, "claims": [
        {"statement": "A TCP flow was observed.", "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"], "claim_level": "observed_fact"},
        {"statement": "cut off", "evidence_ids": ["EV-"""
    parsed = _object(text)
    assert len(parsed["claims"]) == 1
    assert parsed["claims"][0]["evidence_ids"] == ["EV-aaaaaaaaaaaaaaaa"]


def test_a_matching_observation_can_be_published(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    shared = next(relation for relation in prepared["relations"] if relation["relation_type"] == "shared_source")
    claim = {
        "statement": "The IEC-104 point and the electrical name are the same mapped point.",
        "evidence_ids": shared["evidence_ids"],
        "entity": "bus.0:voltage",
        "time": 1003.2,
        "value": 1.0,
        "claim_level": "observed_fact",
        "relation_type": "shared_source",
    }
    checked = verify_claims(db, [claim], prepared["relations"])
    assert checked["verified"] and not checked["rejected"]
