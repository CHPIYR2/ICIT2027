"""Live Ollama check that a tool result is visible before the next decision.

Skipped only when the local server is not running. This is not a prompt search.
"""
import json
from pathlib import Path
import pytest
from mirage_ot.etgi.agent.controller import Flags, investigate
from mirage_ot.etgi.agent.ollama import OllamaClient
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import connect, create, insert_evidence


def _db(tmp_path: Path) -> EvidenceDB:
    path = tmp_path / "evidence.sqlite"
    conn = connect(path)
    create(conn)
    rows = [
        ("EV-aaaaaaaaaaaaaaaa", 1000.1, "10.0.0.1:2404->10.0.0.2:40000/TCP", "10.0.0.1", "10.0.0.2", 2404, 40000),
        ("EV-bbbbbbbbbbbbbbbb", 1000.4, "10.0.0.2:40000->10.0.0.1:2404/TCP", "10.0.0.2", "10.0.0.1", 40000, 2404),
    ]
    for evidence_id, timestamp, entity, src, dst, sport, dport in rows:
        insert_evidence(conn, {
            "evidence_id": evidence_id, "timestamp": timestamp, "modality": "network",
            "entity": entity, "kind": "tcp_packet", "value": 60, "value_present": True,
            "source_ref": evidence_id, "update_status": "packet", "trust": "test",
            "src_ip": src, "dst_ip": dst, "src_port": sport, "dst_port": dport,
            "payload": {},
        })
    conn.commit()
    return EvidenceDB(conn, incident_start=1000, incident_end=1002)


def test_live_json_action_takes_two_queries_then_cites_evidence(tmp_path):
    try:
        client = OllamaClient("qwen3.5:9b-q4_K_M", timeout=180)
        probe = client.probe_tool_choice()
    except Exception as exc:
        pytest.skip(f"Ollama is not available: {exc}")
    flags = Flags(action_interface="json_action", allow_gap_fallback=False, evidence_necessity=False,
                  temporal_graph=False, max_tool_calls=3, max_llm_calls=4, num_predict=400,
                  method="json-known-answer")
    investigate(_db(tmp_path), client, incident_start=1000, incident_end=1002,
                out=tmp_path / "json", flags=flags, limitations=["synthetic known-answer case"])
    events = [json.loads(line) for line in (tmp_path / "json" / "investigation_trace.jsonl").read_text().splitlines()]
    tools = [item for item in events if item.get("type") == "tool" and item.get("origin") == "llm"]
    assert len(tools) >= 2, "the model did not choose two queries"
    assert tools[0]["name"] != tools[1]["name"] or tools[0].get("arguments") != tools[1].get("arguments")
    proposed = [item for item in events if item.get("type") == "propose_relations" and item.get("created")]
    assert proposed, "the model did not propose a relation with a stored evidence id"
    cited = set(proposed[0].get("evidence_ids") or [])
    assert cited & {"EV-aaaaaaaaaaaaaaaa", "EV-bbbbbbbbbbbbbbbb"}


def test_live_model_queries_then_uses_the_result(tmp_path):
    try:
        client = OllamaClient("qwen3.5:9b-q4_K_M", timeout=120)
        probe = client.probe_tool_choice()
    except Exception as exc:
        pytest.skip(f"Ollama is not available: {exc}")
    if not probe.get("server_accepts_tool_choice"):
        pytest.skip(f"This Ollama does not accept tool_choice: {probe}")
    flags = Flags(evidence_necessity=False, temporal_graph=False, contradiction_search=True,
                  source_dependency=True, graph_revision=True, allow_gap_fallback=False,
                  max_tool_calls=2, max_llm_calls=4, num_predict=512, method="known-answer")
    investigate(_db(tmp_path), client, incident_start=1000, incident_end=1002,
                out=tmp_path / "run", flags=flags, limitations=["synthetic known-answer case"])
    events = [json.loads(line) for line in (tmp_path / "run" / "investigation_trace.jsonl").read_text().splitlines()]
    tools = [item for item in events if item.get("type") == "tool" and item.get("origin") == "llm"]
    assert tools, "the model did not choose a tool"
    proposed = [item for item in events if item.get("type") == "propose_relations" and item.get("created")]
    assert proposed, "the model did not keep a relation that cites stored evidence"
    cited = set(proposed[0].get("evidence_ids") or [])
    assert cited & set(tools[0].get("evidence_ids") or [])
