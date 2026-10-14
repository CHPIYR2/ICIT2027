"""Post-alert selection, timeline, relations, and claim checks. No live model."""
import json
from pathlib import Path
from mirage_ot.etgi.agent.ollama import LLMTurn
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence
from mirage_ot.etgi.postalert.pipeline import export_lineage_bundle, prepare, run_explanation, write_run
from mirage_ot.etgi.postalert.verify import verify_claims


class Scripted:
    model_name = "scripted"

    def __init__(self, content, *, done_reason="stop"):
        self.content = content
        self.done_reason = done_reason

    def chat(self, messages, **kwargs):
        return LLMTurn(self.content, [], 20, 10, {}, self.model_name, done_reason=self.done_reason)


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
        {"claim_type": "measurement_claim", "statement": "The voltage was 9.", "evidence_ids": ["EV-eeeeeeeeeeeeeeee"],
         "entity": "bus.0:voltage", "time": 1003.2, "value": 9, "claim_level": "observed_fact"},
        {"claim_type": "relation_claim", "statement": "This caused the change.",
         "evidence_ids": ["EV-9999999999999999"], "claim_level": "supported_inference"},
    ]})
    result = run_explanation(db, Scripted(bad), prepared, level="B4", claim_mode="free_form")
    reasons = [reason for claim in result["verification"]["rejected"] for reason in claim["reasons"]]
    assert "value_does_not_match_cited_rows" in reasons
    assert any(reason.startswith("evidence_id_not_in_database") for reason in reasons)
    assert result["published_claims"] == []
    assert result["minimum"] is True
    assert "bus.0:voltage" in result["report"]["text"]
    assert result["report"]["no_confirmed_inferred_relation"]
    out = tmp_path / "run"
    write_run(db, Scripted(bad), prepared, out, level="B4", claim_mode="free_form")
    assert (out / "timeline.json").exists()
    assert (out / "relations.json").exists()
    saved = json.loads((out / "verification.json").read_text())
    assert saved["rejected"]


def test_a_truncated_claim_list_keeps_the_closed_claims():
    from mirage_ot.etgi.postalert.explain import _object
    text = """{"abstain": false, "claims": [
        {"statement": "A TCP flow was observed.", "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"], "claim_level": "observed_fact"},
        {"statement": "cut off", "evidence_ids": ["EV-"""
    parsed = _object(text, allow_salvage=True)
    assert len(parsed["claims"]) == 1
    assert parsed["claims"][0]["evidence_ids"] == ["EV-aaaaaaaaaaaaaaaa"]


def test_a_matching_observation_can_be_published(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    shared = next(relation for relation in prepared["relations"] if relation["relation_type"] == "shared_source")
    claim = {
        "claim_type": "relation_claim",
        "edge_id": shared["edge_id"],
        "evidence_ids": shared["evidence_ids"],
        "source_entity": shared["source_entity"],
        "target_entity": shared["target_entity"],
        "claim_level": "observed_fact",
        "relation_type": "shared_source",
    }
    checked = verify_claims(db, [claim], prepared["relations"], prepared["timeline"])
    assert checked["verified"] and not checked["rejected"]


def test_packet_existence_does_not_require_numeric_measurement(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    claim = {
        "claim_type": "observation_claim",
        "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"],
        "entity": "10.0.0.1:2404->10.0.0.2:50000/TCP",
        "time": 1001.0,
        "value": True,
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [claim], prepared["relations"], prepared["timeline"])
    assert len(checked["verified"]) == 1
    assert not checked["rejected"]
    assert "Observed tcp_packet" in checked["verified"][0]["rendered_text"]


def test_true_is_not_equal_to_numeric_one(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    claim = {
        "claim_type": "measurement_claim",
        "evidence_ids": ["EV-eeeeeeeeeeeeeeee"],
        "entity": "bus.0:voltage",
        "time": 1003.2,
        "value": True,
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [claim], prepared["relations"], prepared["timeline"])
    assert not checked["verified"]
    assert "value_must_be_numeric" in checked["rejected"][0]["reasons"]


def test_observed_single_packet_without_edge_can_pass(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    claim = {
        "claim_type": "observation_claim",
        "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"],
        "entity": "10.0.0.1:2404->10.0.0.2:50000/TCP",
        "time": 1001.0,
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [claim], [], prepared["timeline"])
    assert len(checked["verified"]) == 1


def test_unsupported_statement_cannot_pass_with_only_valid_id(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    fake = {
        "statement": "The packet carried an unauthorized firmware installation payload of 999 gigabytes.",
        "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"],
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [fake], prepared["relations"], prepared["timeline"])
    assert checked["verified"] == []
    assert "missing_observation_anchor" in checked["rejected"][0]["reasons"]


def test_relation_requires_both_endpoint_refs_and_type(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    one_side = {
        "claim_type": "relation_claim",
        "source_entity": "10.0.0.1:2404->10.0.0.2:50000/TCP",
        "target_entity": "10.0.0.2:50000->10.0.0.1:2404/TCP",
        "relation_type": "communication",
        "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"],
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [one_side], prepared["relations"], prepared["timeline"])
    assert checked["verified"] == []
    assert "relation_missing_endpoint_evidence" in checked["rejected"][0]["reasons"]


def test_entity_timestamp_and_value_match_same_fact(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    mixed = {
        "claim_type": "measurement_claim",
        "evidence_ids": ["EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff"],
        "entity": "bus.0:voltage",
        "time": 1003.2,
        "value": 5.0,
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [mixed], prepared["relations"], prepared["timeline"])
    assert checked["verified"] == []
    assert "fields_do_not_match_same_row" in checked["rejected"][0]["reasons"]


def test_time_interval_supported_with_typed_range(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    claim = {
        "claim_type": "observation_claim",
        "evidence_ids": ["EV-aaaaaaaaaaaaaaaa", "EV-bbbbbbbbbbbbbbbb"],
        "entity": "10.0.0.1:2404->10.0.0.2:50000/TCP",
        "time": {"start": 1000.5, "end": 1001.5},
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [claim], prepared["relations"], prepared["timeline"])
    assert len(checked["verified"]) == 1


def test_multimodal_input_exposes_available_electrical_changes(tmp_path):
    conn = connect(tmp_path / "mm.sqlite")
    create(conn)
    for i in range(10):
        insert_evidence(conn, _row(
            f"EV-00000000000000{i:02d}", 1000.0 + i * 0.01, "network",
            f"10.0.0.1:2404->10.0.0.{i + 2}:50000/TCP", "tcp_packet", 60,
            vantage="n302", src="10.0.0.1", dst=f"10.0.0.{i + 2}", sport=2404, dport=50000,
        ))
    insert_evidence(conn, _row(
        "EV-eeeeeeeeeeeeeeee", 1008.0, "electrical", "line.0:active_power", "electrical_update", 42.0,
        update_status="new",
    ))
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000, incident_end=1010)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    roles = [card["role"] for card in prepared["exposed_timeline"]]
    assert "electrical_change" in roles
    assert prepared["coverage"]["exposed_by_modality"].get("electrical", 0) >= 1


def test_derived_iec104_and_ipal_not_independent_sources(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    fake_edge = {
        "edge_id": "R9999",
        "source_entity": "bus.0:voltage",
        "target_entity": "bus.0:voltage",
        "relation_type": "temporal_association",
        "claim_level": "supported_inference",
        "status": "supported",
        "evidence_ids": ["EV-dddddddddddddddd", "EV-eeeeeeeeeeeeeeee"],
    }
    claim = {
        "claim_type": "relation_claim",
        "edge_id": "R9999",
        "source_entity": "bus.0:voltage",
        "target_entity": "bus.0:voltage",
        "relation_type": "temporal_association",
        "evidence_ids": ["EV-dddddddddddddddd", "EV-eeeeeeeeeeeeeeee"],
        "claim_level": "supported_inference",
    }
    checked = verify_claims(db, [claim], [*prepared["relations"], fake_edge], prepared["timeline"])
    assert checked["verified"] == []
    assert "same_source_counted_as_independent_evidence" in checked["rejected"][0]["reasons"]


def test_partial_json_is_not_complete_response(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    truncated = """{"abstain": false, "claims": [
        {"claim_type": "observation_claim", "fact_id": "TL001", "claim_level": "observed_fact"},
        {"claim_type": "observation_claim", "fact_id": "TL0"""
    result = run_explanation(
        db, Scripted(truncated, done_reason="length"), prepared,
        level="B4", claim_mode="typed_refs", allow_salvage=False,
    )
    assert result["model"]["partial_output"] is True
    assert result["model"]["abstain"] is False
    assert result["model"]["salvaged_claim_count"] == 1
    assert result["model"]["claims"] == []
    assert result["published_claims"] == []


def test_code_version_and_run_artifact_consistency(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    out = tmp_path / "artifact"
    reply = json.dumps({"abstain": True, "hypotheses": [], "claims": []})
    write_run(db, Scripted(reply), prepared, out, level="B4")
    manifest = json.loads((out / "run_manifest.json").read_text())
    saved_timeline = json.loads((out / "timeline.json").read_text())
    lineage = json.loads((out / "lineage.json").read_text())
    assert manifest["code_sha256"]
    assert manifest["db_fingerprint"]["evidence_rows"] == 6
    for event in saved_timeline:
        assert event["evidence_id_count"] == len(lineage[event["timeline_id"]])


def test_public_report_does_not_include_rejected_claim_text(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    bad = json.dumps({"abstain": False, "hypotheses": [], "claims": [{
        "claim_type": "measurement_claim",
        "statement": "HALLUCINATED_STORAGE_SOC_100",
        "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"],
        "entity": "storage.1:state_of_charge",
        "value": 100.0,
        "claim_level": "observed_fact",
    }]})
    out = tmp_path / "pub"
    write_run(db, Scripted(bad), prepared, out, level="B4", claim_mode="free_form")
    report_md = (out / "report.md").read_text()
    rejected_audit = (out / "rejected_claims.json").read_text()
    assert "HALLUCINATED_STORAGE_SOC_100" not in report_md
    assert "HALLUCINATED_STORAGE_SOC_100" in rejected_audit


def test_observed_edge_upgraded_to_supported_inference_is_rejected(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    comm = next(r for r in prepared["relations"] if r["relation_type"] == "communication")
    upgraded = json.dumps({"abstain": False, "hypotheses": [], "claims": [{
        "claim_type": "relation_claim",
        "edge_id": comm["edge_id"],
        "relation_type": "communication",
        "claim_level": "supported_inference",
    }]})
    result = run_explanation(db, Scripted(upgraded), prepared, level="B4", claim_mode="typed_refs")
    assert result["published_claims"] == []
    assert "observed_link_cannot_be_upgraded_to_inference" in result["verification"]["rejected"][0]["reasons"]
    assert result["report"]["no_confirmed_inferred_relation"] is True
    assert result["report"]["confirmed_inferred_relations"] == []


def test_canonical_fact_and_edge_binding_rejects_mismatched_fields(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    comm = next(r for r in prepared["relations"] if r["relation_type"] == "communication")
    tl_first = prepared["timeline"][0]
    tl_other = next(e for e in prepared["timeline"] if e["timeline_id"] != tl_first["timeline_id"])
    counterexamples = [
        {
            "claim_type": "relation_claim",
            "edge_id": comm["edge_id"],
            "relation_type": "firmware_installation",
            "claim_level": "observed_fact",
        },
        {
            "claim_type": "relation_claim",
            "edge_id": comm["edge_id"],
            "relation_type": "communication",
            "source_entity": "bus.0:voltage",
            "target_entity": "sgen.0:active_power",
            "evidence_ids": ["EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff"],
            "claim_level": "observed_fact",
        },
        {
            "claim_type": "observation_claim",
            "fact_id": tl_first["timeline_id"],
            "entity": tl_other["entity"],
            "time": tl_other["time"],
            "evidence_ids": tl_other["evidence_ids"],
            "claim_level": "observed_fact",
        },
    ]
    checked = verify_claims(db, counterexamples, prepared["relations"], prepared["timeline"], lineage=prepared["lineage"])
    assert checked["verified"] == []
    assert len(checked["rejected"]) == 3
    all_reasons = {r for item in checked["rejected"] for r in item["reasons"]}
    assert "edge_relation_type_mismatch" in all_reasons
    assert "edge_endpoint_mismatch" in all_reasons
    assert "fact_id_entity_mismatch" in all_reasons or "fact_id_evidence_mismatch" in all_reasons


def test_baseline_reports_do_not_label_raw_claims_as_verified(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    tl_first = prepared["timeline"][0]
    raw_claim = json.dumps({"abstain": False, "hypotheses": [], "claims": [{
        "claim_type": "observation_claim",
        "fact_id": tl_first["timeline_id"],
        "claim_level": "observed_fact",
    }]})
    b1 = run_explanation(db, Scripted(raw_claim), prepared, level="B1", claim_mode="typed_refs")
    assert b1["published_claims"] == []
    assert len(b1["unverified_model_claims"]) == 1
    assert "Verified claims:" not in b1["report"]["text"]
    assert "Unverified raw model claims" in b1["report"]["text"]


def test_absence_claim_rejects_range_outside_indexed_window(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    outside = {
        "claim_type": "absence_claim",
        "absent_kind": "arp_packet",
        "start_time": 900.0,
        "end_time": 950.0,
        "claim_level": "observed_fact",
    }
    inside = {
        "claim_type": "absence_claim",
        "absent_kind": "arp_packet",
        "start_time": 1000.0,
        "end_time": 1010.0,
        "claim_level": "observed_fact",
    }
    checked = verify_claims(db, [outside, inside], prepared["relations"], prepared["timeline"], lineage=prepared["lineage"])
    assert len(checked["verified"]) == 1
    assert len(checked["rejected"]) == 1
    assert "absence_range_outside_indexed_incident_window" in checked["rejected"][0]["reasons"]



def _multi_point_db(tmp_path: Path) -> EvidenceDB:
    """Two IEC-104 frames, each carrying two information objects, captured at two vantages."""
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    rows = []
    for frame, stamp, voltage, power in (("frame-1", 1002.0, 0.98, 33000.0), ("frame-2", 1004.0, 0.97, 31000.0)):
        for vantage in ("n302", "n318"):
            parent = f"EV-{frame[-1]}{vantage[-1]}" + "0" * 14
            rows.append(_row(parent, stamp, "network", "10.0.0.1:2404->10.0.0.2:50000/TCP", "tcp_packet", 120,
                             fingerprint=frame, vantage=vantage, src="10.0.0.1", dst="10.0.0.2",
                             sport=2404, dport=50000))
            rows.append(_row(f"EV-{frame[-1]}{vantage[-1]}v" + "0" * 13, stamp, "network", "bus.7:voltage",
                             "iec104_asdu", voltage, fingerprint=frame, vantage=vantage, ca_ioa="129.10010",
                             protocol_class="monitor", parent_evidence_id=parent))
            rows.append(_row(f"EV-{frame[-1]}{vantage[-1]}p" + "0" * 13, stamp, "network", "sgen.9:active_power",
                             "iec104_asdu", power, fingerprint=frame, vantage=vantage, ca_ioa="125.10080",
                             protocol_class="monitor", parent_evidence_id=parent))
    for row in rows:
        insert_evidence(conn, row)
    conn.commit()
    return EvidenceDB(conn, incident_start=1000, incident_end=1010)


def test_iec104_points_in_one_frame_are_separate_facts_with_shared_lineage(tmp_path):
    db = _multi_point_db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    points = {event["entity"]: event for event in prepared["timeline"] if event["source"]["kind"] == "iec104_asdu"}
    assert set(points) == {"bus.7:voltage", "sgen.9:active_power"}
    voltage, power = points["bus.7:voltage"], points["sgen.9:active_power"]
    assert (voltage["value_min"], voltage["value_max"]) == (0.97, 0.98)
    assert (power["value_min"], power["value_max"]) == (31000.0, 33000.0)
    assert voltage["sample_count"] == 2 and power["sample_count"] == 2
    assert voltage["ca_ioa"] == "129.10010" and power["ca_ioa"] == "125.10080"
    assert set(voltage["lineage"]) == set(power["lineage"])
    assert voltage["independent"] is False and power["independent"] is False
    pair = {voltage["timeline_id"], power["timeline_id"]}
    links = [r for r in prepared["relations"] if {r["source_fact_id"], r["target_fact_id"]} == pair]
    assert [(r["relation_type"], r["claim_level"]) for r in links] == [("same_frame", "observed_fact")]
    for row in export_lineage_bundle(db, prepared["timeline"], prepared["lineage"])["rows"]:
        if row["kind"] == "iec104_asdu":
            owner = voltage if row["entity"] == "bus.7:voltage" else power
            assert row["evidence_id"] in prepared["lineage"][owner["timeline_id"]]
            other = power if owner is voltage else voltage
            assert row["evidence_id"] not in prepared["lineage"][other["timeline_id"]]


def test_measurement_from_a_sibling_point_in_the_same_frame_is_rejected(tmp_path):
    db = _multi_point_db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    voltage = next(event for event in prepared["timeline"] if event["entity"] == "bus.7:voltage")
    claim = {"claim_type": "measurement_claim", "fact_id": voltage["timeline_id"], "value": 33000.0,
             "claim_level": "observed_fact"}
    checked = verify_claims(db, [claim], prepared["relations"], prepared["timeline"], lineage=prepared["lineage"])
    assert checked["verified"] == []


def test_same_flow_at_two_vantages_reports_distinct_frames(tmp_path):
    prepared = prepare(_multi_point_db(tmp_path), 1000, 1010, background_start=1000, background_end=1000)
    flow = next(event for event in prepared["timeline"] if event["role"] == "communication")
    assert flow["packet_count"] == 4
    assert flow["packet_count_by_vantage"] == {"n302": 2, "n318": 2}
    assert flow["distinct_frame_count"] == 2


def test_lineage_bundle_exports_every_id_beyond_the_query_cap(tmp_path):
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    for index in range(130):
        insert_evidence(conn, _row(f"EV-{index:016x}", 1000 + index * 0.05, "network",
                                   "10.0.0.1:2404->10.0.0.2:50000/TCP", "tcp_packet", 60,
                                   fingerprint=f"frame-{index}", vantage="n302", src="10.0.0.1", dst="10.0.0.2",
                                   sport=2404, dport=50000))
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000, incident_end=1010)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    bundle = export_lineage_bundle(db, prepared["timeline"], prepared["lineage"])
    assert bundle["requested_count"] == 130
    assert bundle["exported_count"] == 130
    assert bundle["missing_ids"] == []
    assert bundle["row_check_failures"] == []


def test_lineage_bundle_includes_parents_and_passes_row_checks(tmp_path):
    db = _multi_point_db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    bundle = export_lineage_bundle(db, prepared["timeline"], prepared["lineage"], chunk=3)
    assert bundle["missing_ids"] == []
    assert bundle["row_check_failures"] == []
    assert bundle["exported_count"] == 12


def test_edge_provenance_excludes_same_entity_at_another_time(tmp_path):
    db = _db(tmp_path)
    timeline = [
        {"timeline_id": "TL001", "entity": "10.0.0.1:2404->10.0.0.2:50000/TCP", "time": 1001, "time_end": 1001,
         "evidence_ids": ["EV-aaaaaaaaaaaaaaaa"], "role": "communication", "source": {"kind": "tcp_packet"}},
        {"timeline_id": "TL002", "entity": "10.0.0.2:50000->10.0.0.1:2404/TCP", "time": 1001.1, "time_end": 1001.1,
         "evidence_ids": ["EV-bbbbbbbbbbbbbbbb"], "role": "communication", "source": {"kind": "tcp_packet"}},
        {"timeline_id": "TL003", "entity": "10.0.0.1:2404->10.0.0.2:50000/TCP", "time": 1009, "time_end": 1009,
         "evidence_ids": ["EV-dddddddddddddddd"], "role": "communication", "source": {"kind": "tcp_packet"}},
    ]
    edge = {"edge_id": "R0001", "source_fact_id": "TL001", "target_fact_id": "TL002",
            "source_entity": timeline[0]["entity"], "target_entity": timeline[1]["entity"],
            "relation_type": "communication", "claim_level": "observed_fact",
            "verification_status": "supported", "status": "supported",
            "evidence_ids": ["EV-aaaaaaaaaaaaaaaa", "EV-bbbbbbbbbbbbbbbb"]}
    lineage = {item["timeline_id"]: item["evidence_ids"] for item in timeline}
    stray = {"claim_type": "relation_claim", "edge_id": "R0001", "claim_level": "observed_fact",
             "evidence_ids": ["EV-aaaaaaaaaaaaaaaa", "EV-dddddddddddddddd"]}
    checked = verify_claims(db, [stray], [edge], timeline, lineage=lineage)
    assert "edge_evidence_not_in_edge_provenance" in checked["rejected"][0]["reasons"]


def test_flat_or_missing_background_gives_bounded_labeled_scores(tmp_path):
    conn = connect(tmp_path / "evidence.sqlite")
    create(conn)
    for index in range(5):
        insert_evidence(conn, _row(f"EV-b{index:015x}", 990 + index, "electrical", "bus.0:voltage",
                                   "electrical_update", 1.0, update_status="new"))
    insert_evidence(conn, _row("EV-c000000000000000", 1002, "electrical", "bus.0:voltage",
                               "electrical_update", 1.0001, update_status="new"))
    conn.commit()
    db = EvidenceDB(conn, incident_start=1000, incident_end=1010)
    flat = prepare(db, 1000, 1010, background_start=985, background_end=1000)
    item = flat["timeline"][0]
    detail = flat["selection"]["query"]
    assert detail["background_status"] == "observed"
    assert 0 <= item["score"] <= 10
    none = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    assert none["selection"]["query"]["background_status"] == "none_requested"
    assert none["timeline"][0]["score"] == 0.0


def test_claim_records_model_choices_separately_from_system_resolution(tmp_path):
    db = _db(tmp_path)
    prepared = prepare(db, 1000, 1010, background_start=1000, background_end=1000)
    fact = next(event for event in prepared["timeline"] if event["role"] == "electrical_change"
                and event["entity"] == "bus.0:voltage")
    exact = {"claim_type": "measurement_claim", "fact_id": fact["timeline_id"], "value": 1.0,
             "claim_level": "observed_fact"}
    shifted = {**exact, "time": fact["time"] + 0.6}
    checked = verify_claims(db, [exact, shifted], prepared["relations"], prepared["timeline"],
                            lineage=prepared["lineage"])
    first, second = checked["verified"]
    assert first["model_selected_fact_ids"] == [fact["timeline_id"]]
    assert first["model_supplied_evidence_ids"] == []
    assert first["system_resolved_evidence_ids"]
    assert first["time_match"] == "inherited_from_anchor"
    assert second["time_match"] == "tolerance_aligned"
    assert second["time_tolerance_seconds"] == 1.0
