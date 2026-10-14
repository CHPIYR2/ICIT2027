"""ETGI checks that do not need a live model or the Sherlock ZIP."""
import json
from pathlib import Path
from mirage_ot.etgi.agent.controller import Flags, investigate
from mirage_ot.etgi.agent.ollama import LLMTurn
from mirage_ot.etgi.evidence.iec104 import split_fields
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, expand_blocked, insert_evidence
from mirage_ot.etgi.evaluation.harness import answer_from_retrieval, build_questions, score_graph, score_questions
from mirage_ot.etgi.graph.temporal import TemporalEvidenceGraph
from mirage_ot.etgi.reporting.generator import write_report
from mirage_ot.etgi.verification.assess import verify_edge
from mirage_ot.etgi.verification.necessity import run_necessity


class Scripted:
    model_name = "scripted"

    def __init__(self, turns):
        self.turns = list(turns)

    def chat(self, messages, **kwargs):
        item = self.turns.pop(0)
        return LLMTurn(item.get("content", ""), item.get("tool_calls") or [], 11, 7, {}, self.model_name)


def _db(tmp_path: Path) -> EvidenceDB:
    path = tmp_path / "evidence.sqlite"
    conn = connect(path)
    create(conn)
    rows = [
        _row("EV-aaaaaaaaaaaaaaaa", 1001, "network", "10.0.0.1:2404->10.0.0.2:50000/TCP", "tcp_packet",
             60, fingerprint="frame-a", vantage="n302", src="10.0.0.1", dst="10.0.0.2", sport=2404, dport=50000),
        _row("EV-bbbbbbbbbbbbbbbb", 1002, "network", "10.0.0.2:50000->10.0.0.1:2404/TCP", "tcp_packet",
             60, fingerprint="frame-b", vantage="n302", src="10.0.0.2", dst="10.0.0.1", sport=50000, dport=2404),
        _row("EV-cccccccccccccccc", 1001, "network", "10.0.0.1:2404->10.0.0.2:50000/TCP", "tcp_packet",
             60, fingerprint="frame-a", vantage="n318", src="10.0.0.1", dst="10.0.0.2", sport=2404, dport=50000),
        _row("EV-dddddddddddddddd", 1003.1, "network", "bus.0:voltage", "iec104_asdu", 1.0,
             fingerprint="frame-c", vantage="n302", ca_ioa="101.10010", protocol_class="monitor",
             src="10.0.0.2", dst="10.0.0.1", sport=2404, dport=50000),
        _row("EV-eeeeeeeeeeeeeeee", 1003.2, "electrical", "bus.0:voltage", "electrical_update", 1.0,
             ca_ioa="101.10010", update_status="new", trust="network-reported-not-simulator-truth"),
        _row("EV-ffffffffffffffff", 1004, "electrical", "sgen.0:active_power", "electrical_update", 5,
             update_status="new"),
        _row("EV-1111111111111111", 1005, "electrical", "sgen.0:active_power", "electrical_hold_summary", 5,
             update_status="hold"),
        _row("EV-2222222222222222", 1006, "electrical", "switch.1:closed", "electrical_update", 0,
             update_status="new"),
        _row("EV-3333333333333333", 1007, "electrical", "switch.2:closed", "electrical_update", None,
             value_present=False, update_status="new"),
    ]
    for row in rows:
        insert_evidence(conn, row)
    child = _row("EV-4444444444444444", 1003.1, "network", "bus.0:voltage", "iec104_asdu", 1.0,
                 fingerprint="frame-c", parent="EV-dddddddddddddddd", ca_ioa="101.10010")
    insert_evidence(conn, child)
    conn.commit()
    return EvidenceDB(conn, incident_start=1000, incident_end=1010)


def _row(evidence_id, timestamp, modality, entity, kind, value, **extra):
    present = extra.pop("value_present", value is not None)
    return {
        "evidence_id": evidence_id, "timestamp": timestamp, "modality": modality, "entity": entity,
        "kind": kind, "value": 0 if value is None else value, "value_present": present,
        "source_ref": evidence_id, "update_status": extra.pop("update_status", "packet"),
        "trust": extra.pop("trust", "test"), "payload": {"note": "telemetry"}, **extra,
    }


def test_evaluator_field_rejected(tmp_path):
    conn = connect(tmp_path / "x.sqlite")
    create(conn)
    try:
        insert_evidence(conn, {**_row("EV-5555555555555555", 1, "network", "a", "tcp_packet", 1),
                               "payload": {"malicious": True}})
    except ValueError as exc:
        assert "malicious" in str(exc)
    else:
        raise AssertionError("evaluator field was stored")


def test_zero_is_not_missing(tmp_path):
    db = _db(tmp_path)
    zero = db.get(["EV-2222222222222222"])["rows"][0]
    missing = db.get(["EV-3333333333333333"])["rows"][0]
    assert zero["value"] == 0 and zero["value_present"] is True
    assert missing["value"] is None and missing["value_present"] is False


def test_block_hides_same_frame_and_parent(tmp_path):
    db = _db(tmp_path)
    hidden = expand_blocked(db.conn, ["EV-4444444444444444"])
    assert "EV-dddddddddddddddd" in hidden
    page = db.with_block(["EV-4444444444444444"]).get(["EV-dddddddddddddddd", "EV-4444444444444444"])
    assert page["rows"] == []
    assert set(page["hidden_evidence_ids"]) == {"EV-dddddddddddddddd", "EV-4444444444444444"}


def test_pagination_and_filters(tmp_path):
    db = _db(tmp_path)
    page = db.search(modality="electrical", limit=2, offset=0)
    assert page["returned"] == 2 and page["truncated"] is True and page["next_offset"] == 2
    changes = db.search(kind="electrical_update", limit=20)
    assert "EV-1111111111111111" not in changes["evidence_ids"]
    assert db.search(modality="network").__class__ is dict


def test_coincidence_stays_unresolved_and_shared_source_is_one_source(tmp_path):
    db = _db(tmp_path)
    graph = TemporalEvidenceGraph()
    left = graph.add_node(modality="electrical", entity="bus.0:voltage", event_type="electrical_update",
                          start_time=1003.2, end_time=1003.2, description="voltage", evidence_ids=["EV-eeeeeeeeeeeeeeee"])
    right = graph.add_node(modality="electrical", entity="sgen.0:active_power", event_type="electrical_update",
                           start_time=1004, end_time=1004, description="power", evidence_ids=["EV-ffffffffffffffff"])
    edge = graph.add_edge(source=left["node_id"], target=right["node_id"], relation_type="temporal_association",
                          origin="inferred", evidence_ids=["EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff"])
    assessment = verify_edge(db, edge)
    assert assessment["status"] == "unresolved"
    assert assessment["direct_record_link"] is False
    iec = graph.add_node(modality="network", entity="bus.0:voltage", event_type="iec104_observation",
                         start_time=1003.1, end_time=1003.1, description="asdu", evidence_ids=["EV-dddddddddddddddd"])
    linked = graph.add_edge(source=iec["node_id"], target=left["node_id"], relation_type="shared_source",
                            origin="observed", evidence_ids=["EV-dddddddddddddddd", "EV-eeeeeeeeeeeeeeee"])
    checked = verify_edge(db, linked)
    assert checked["status"] == "supported"
    assert checked["independent_groups"] == 1
    claimed = graph.add_edge(source=iec["node_id"], target=left["node_id"], relation_type="temporal_association",
                             origin="inferred", evidence_ids=["EV-dddddddddddddddd", "EV-eeeeeeeeeeeeeeee"])
    reclassified = verify_edge(db, claimed)
    assert reclassified["status"] == "supported"
    assert reclassified["recommended_relation_type"] == "shared_source"


def test_communication_and_revision_history(tmp_path):
    db = _db(tmp_path)
    graph = TemporalEvidenceGraph()
    a = graph.add_node(modality="network", entity="10.0.0.1:2404->10.0.0.2:50000/TCP", event_type="tcp_flow",
                       start_time=1001, end_time=1001, description="forward", evidence_ids=["EV-aaaaaaaaaaaaaaaa"])
    b = graph.add_node(modality="network", entity="10.0.0.2:50000->10.0.0.1:2404/TCP", event_type="tcp_flow",
                       start_time=1002, end_time=1002, description="reverse", evidence_ids=["EV-bbbbbbbbbbbbbbbb"])
    edge = graph.add_edge(source=a["node_id"], target=b["node_id"], relation_type="communication", origin="observed",
                          evidence_ids=["EV-aaaaaaaaaaaaaaaa", "EV-bbbbbbbbbbbbbbbb"])
    from mirage_ot.etgi.verification.assess import apply_assessment
    status = apply_assessment(graph, edge["edge_id"], verify_edge(db, edge), revise=True)
    assert status == "supported"
    assert [item["operation"] for item in graph.edges[edge["edge_id"]]["history"]] == ["relation_proposed", "relation_revised"]
    graph.remove(edge["edge_id"], reason="test removal keeps the record")
    assert edge["edge_id"] in graph.removed
    assert graph.removed[edge["edge_id"]]["history"][-1]["operation"] == "relation_removed"


def test_hold_citation_is_disputed(tmp_path):
    db = _db(tmp_path)
    graph = TemporalEvidenceGraph()
    a = graph.add_node(modality="electrical", entity="sgen.0:active_power", event_type="electrical_update",
                       start_time=1004, end_time=1005, description="power", evidence_ids=["EV-ffffffffffffffff"])
    b = graph.add_node(modality="electrical", entity="bus.0:voltage", event_type="electrical_update",
                       start_time=1003.2, end_time=1003.2, description="voltage", evidence_ids=["EV-eeeeeeeeeeeeeeee"])
    edge = graph.add_edge(source=a["node_id"], target=b["node_id"], relation_type="temporal_association",
                          origin="inferred", evidence_ids=["EV-1111111111111111", "EV-eeeeeeeeeeeeeeee"])
    assert verify_edge(db, edge)["status"] == "disputed"


def test_necessity_blocks_reentry_and_detects_dependence(tmp_path):
    db = _db(tmp_path)
    graph = TemporalEvidenceGraph()
    a = graph.add_node(modality="electrical", entity="bus.0:voltage", event_type="candidate",
                       start_time=1003.2, end_time=1003.2, description="", evidence_ids=["EV-eeeeeeeeeeeeeeee"])
    b = graph.add_node(modality="electrical", entity="sgen.0:active_power", event_type="candidate",
                       start_time=1004, end_time=1004, description="", evidence_ids=["EV-ffffffffffffffff"])
    edge = graph.add_edge(source=a["node_id"], target=b["node_id"], relation_type="temporal_association",
                          origin="inferred", evidence_ids=["EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff"])

    class Judge(Scripted):
        def chat(self, messages, **kwargs):
            text = messages[-1]["content"]
            both = "EV-eeeeeeeeeeeeeeee" in text and "EV-ffffffffffffffff" in text
            status = "supported" if both else "unresolved"
            cites = [item for item in ("EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff") if item in text]
            return LLMTurn(json.dumps({"status": status, "cites": cites, "alternative": "", "rationale": "cards"}),
                           [], 3, 3, {}, self.model_name)

    result = run_necessity(Judge([]), db, edge, repeats=1, max_citations=2)
    assert result["full_stable"] is True
    assert set(result["judgment_sensitive_evidence_ids"]) == {"EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff"}
    hidden = db.with_block(["EV-eeeeeeeeeeeeeeee"])
    assert "EV-eeeeeeeeeeeeeeee" not in {row["evidence_id"] for row in hidden.search(limit=50)["rows"]}


def test_scripted_investigation_revises_coincidence(tmp_path):
    db = _db(tmp_path)
    llm = Scripted([
        {"tool_calls": [{"name": "query_electrical_changes", "arguments": {"limit": 10}}]},
        {"content": json.dumps({"action": "propose_relations", "relations": [{
            "source_entity": "bus.0:voltage", "source_modality": "electrical",
            "target_entity": "sgen.0:active_power", "target_modality": "electrical",
            "relation_type": "temporal_association", "time_order": "undirected",
            "evidence_ids": ["EV-eeeeeeeeeeeeeeee", "EV-ffffffffffffffff"],
            "status": "supported", "rationale": "both changed", "alternatives": ["independent setpoints"],
        }], "unresolved_questions": ["No out-of-band meter reading."]})},
        {"content": json.dumps({"action": "stop", "unresolved_questions": []})},
    ])
    flags = Flags(evidence_necessity=False, max_tool_calls=4, max_llm_calls=6, method="ETGI")
    result = investigate(db, llm, incident_start=1000, incident_end=1010, out=tmp_path / "run",
                         flags=flags, limitations=["electrical values are network-reported"])
    offered = [edge for edge in result["graph"].edges.values()
               if edge["source_entity"] == "bus.0:voltage" and edge["relation_type"] == "temporal_association"
               and edge["target_entity"] == "sgen.0:active_power"]
    assert offered and offered[0]["status"] == "unresolved"
    assert offered[0]["history"][0]["operation"] == "relation_proposed"
    report = write_report(result, db, tmp_path / "run", llm=None)
    assert report["completion"] == "COMPLETE"
    assert (tmp_path / "run" / "graph.json").exists()
    assert (tmp_path / "run" / "graph.graphml").exists()
    assert (tmp_path / "run" / "investigation_trace.jsonl").exists()
    metrics = score_graph(db, result["graph"])
    assert metrics["unsupported_relation_rate"] == 0 or metrics["published_supported"] >= 1
    assert metrics["by_pair"]["N-N"]["supported"] >= 1
    assert metrics["by_pair"]["N-P"]["supported"] >= 1


def test_narrative_rejects_unknown_evidence(tmp_path):
    db = _db(tmp_path)
    graph_result = {
        "state": type("S", (), {
            "incident_start": 1000, "incident_end": 1010, "tool_calls": 0, "llm_calls": 0,
            "gap_fallbacks": 0, "prompt_tokens": 0, "completion_tokens": 0, "unresolved_questions": [],
            "necessity": [], "errors": [], "narrative": "", "narrative_rejected": False, "model": "scripted",
            "budget_hit": False, "completion": "",
        })(),
        "graph": TemporalEvidenceGraph(),
        "flags": Flags(evidence_necessity=False, contradiction_search=False),
        "limitations": ["test"],
    }
    llm = Scripted([{"content": "The voltage was 9.5 according to EV-9999999999999999."}])
    body = write_report(graph_result, db, tmp_path / "report", llm=llm)
    assert body["narrative_rejected"] is True
    assert body["narrative"] == ""
    text = (tmp_path / "report" / "investigation_report.md").read_text()
    assert "The voltage was 9.5" not in text


def test_question_gold_uses_retrieved_ids_only(tmp_path):
    db = _db(tmp_path)
    questions = build_questions(db, 1000, 1010)
    by_id = {item["id"]: item for item in questions}
    assert "bus.0:voltage" in by_id["new_electrical_entities"]["answer"]
    assert by_id["measurement_value"]["answer"]["value"] in (0, 1.0, 5)
    full = answer_from_retrieval(db, questions, [row["evidence_id"] for row in db.search(limit=100)["rows"]])
    assert score_questions(questions, full)["exact_match"] == 1
    partial = answer_from_retrieval(db, questions, ["EV-ffffffffffffffff"])
    assert score_questions(questions, partial)["exact_match"] < 1


def test_iec104_split_does_not_broadcast_one_value():
    rows = split_fields({
        "frame.time_epoch": "100.5", "ip.src": "10.0.0.1", "ip.dst": "10.0.0.2",
        "tcp.srcport": "2404", "tcp.dstport": "40000", "iec60870_104.type": "0",
        "iec60870_asdu.typeid": "13", "iec60870_asdu.addr": "101", "iec60870_asdu.causetx": "3",
        "iec60870_asdu.ioa": "10010,10020", "iec60870_asdu.float": "1.25",
        "iec60870_asdu.normval": "", "iec60870_asdu.scalval": "", "iec60870_asdu.siq.spi": "",
        "iec60870_asdu.sco.on": "",
    })
    assert len(rows) == 2
    assert all(row["value_present"] is False for row in rows)
    aligned = split_fields({
        "frame.time_epoch": "100.5", "ip.src": "10.0.0.1", "ip.dst": "10.0.0.2",
        "tcp.srcport": "2404", "tcp.dstport": "40000", "iec60870_104.type": "0",
        "iec60870_asdu.typeid": "45", "iec60870_asdu.addr": "101", "iec60870_asdu.causetx": "6",
        "iec60870_asdu.ioa": "10", "iec60870_asdu.float": "", "iec60870_asdu.normval": "",
        "iec60870_asdu.scalval": "", "iec60870_asdu.siq.spi": "", "iec60870_asdu.sco.on": "1",
    })
    assert aligned[0]["protocol_class"] == "control"
    assert aligned[0]["value"] == 1
    assert aligned[0]["ca_ioa"] == "101.10"
