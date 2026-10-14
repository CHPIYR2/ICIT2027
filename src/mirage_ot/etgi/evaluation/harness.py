"""Questions, graph checks, baselines, and ablations.

Question gold comes from the evidence database. A method is scored by whether
the evidence it actually retrieved is sufficient to reproduce that gold.
There is no Sherlock relation-graph gold, so this module does not report
edge precision, edge recall, or causal accuracy.
"""
from __future__ import annotations
import json
from pathlib import Path
from ..agent.controller import Flags, investigate
from ..evidence.queries import EvidenceDB
from ..reporting.generator import write_report
from ..verification.assess import verify_edge


def build_questions(db: EvidenceDB, start: float, end: float) -> list[dict]:
    conn = db.conn
    controls = conn.execute(
        """SELECT evidence_id, ca_ioa FROM evidence
           WHERE kind = 'iec104_asdu' AND protocol_class = 'control'
             AND timestamp >= ? AND timestamp < ? AND ca_ioa IS NOT NULL
           ORDER BY ca_ioa, evidence_id""",
        (start, end),
    ).fetchall()
    control_ids = [row["ca_ioa"] for row in controls]
    updates = conn.execute(
        """SELECT evidence_id, entity FROM evidence
           WHERE kind = 'electrical_update' AND timestamp >= ? AND timestamp < ?
           ORDER BY entity, evidence_id""",
        (start, end),
    ).fetchall()
    frames = conn.execute(
        """SELECT fingerprint FROM evidence
           WHERE modality = 'network' AND fingerprint IS NOT NULL
             AND timestamp >= ? AND timestamp < ?
           GROUP BY fingerprint HAVING COUNT(DISTINCT vantage) > 1""",
        (start, end),
    ).fetchall()
    sample = conn.execute(
        """SELECT evidence_id, entity, value FROM evidence
           WHERE kind = 'electrical_update' AND value_present = 1
             AND timestamp >= ? AND timestamp < ?
           ORDER BY evidence_id LIMIT 1""",
        (start, end),
    ).fetchone()
    replies = []
    for row in conn.execute(
        """SELECT evidence_id, ca_ioa, timestamp, src_ip, dst_ip, src_port, dst_port
           FROM evidence WHERE kind = 'iec104_asdu' AND protocol_class = 'control'
             AND timestamp >= ? AND timestamp < ? AND ca_ioa IS NOT NULL""",
        (start, end),
    ):
        later = conn.execute(
            """SELECT evidence_id FROM evidence
               WHERE kind = 'iec104_asdu' AND ca_ioa = ? AND timestamp > ? AND timestamp < ?
                 AND src_ip = ? AND dst_ip = ? AND src_port = ? AND dst_port = ?
               LIMIT 1""",
            (row["ca_ioa"], row["timestamp"], row["timestamp"] + 5,
             row["dst_ip"], row["src_ip"], row["dst_port"], row["src_port"]),
        ).fetchone()
        replies.append({"ca_ioa": row["ca_ioa"], "control_evidence_id": row["evidence_id"],
                        "reply_observed": later is not None,
                        "reply_evidence_id": None if later is None else later["evidence_id"]})
    questions = [
        {
            "id": "control_ca_ioa",
            "question": "Which CA/IOA values have an IEC-104 control-direction type id in the incident window?",
            "answer": sorted(set(control_ids)),
            "evidence_ids": [row["evidence_id"] for row in controls],
        },
        {
            "id": "new_electrical_entities",
            "question": "Which electrical entities have a new reported value in the incident window?",
            "answer": sorted(set(row["entity"] for row in updates)),
            "evidence_ids": [row["evidence_id"] for row in updates],
        },
        {
            "id": "shared_frame_count",
            "question": "How many Ethernet frame hashes were captured at more than one vantage?",
            "answer": len(frames),
            "evidence_ids": [],
        },
        {
            "id": "control_reply",
            "question": "For each control-direction CA/IOA, is there a later ASDU on the reversed socket within 5 seconds?",
            "answer": [{"ca_ioa": item["ca_ioa"], "reply_observed": item["reply_observed"]} for item in replies],
            "evidence_ids": [item["control_evidence_id"] for item in replies if item["control_evidence_id"]]
            + [item["reply_evidence_id"] for item in replies if item["reply_evidence_id"]],
        },
    ]
    if sample is not None:
        questions.append({
            "id": "measurement_value",
            "question": f"What new reported value is stored for {sample['entity']} in {sample['evidence_id']}?",
            "answer": {"evidence_id": sample["evidence_id"], "entity": sample["entity"], "value": sample["value"]},
            "evidence_ids": [sample["evidence_id"]],
        })
    return questions


def answer_from_retrieval(db: EvidenceDB, questions: list[dict], retrieved: list[str]) -> list[dict]:
    """Gold queries restricted to the evidence ids the method actually received."""
    if not retrieved:
        return [{"id": question["id"], "answer": _empty(question)} for question in questions]
    allowed = set(retrieved)
    start = db.incident_start
    end = db.incident_end
    answers = []
    for question in questions:
        gold_db = _Allow(db.conn, allowed)
        answers.append({"id": question["id"], "answer": _restricted(gold_db, question, start, end)})
    return answers


class _Allow:
    def __init__(self, conn, allowed: set[str]):
        self.conn = conn
        self.allowed = allowed

    def rows(self, sql: str, params: tuple) -> list:
        return [row for row in self.conn.execute(sql, params) if row["evidence_id"] in self.allowed]


def _restricted(view, question, start, end):
    if question["id"] == "control_ca_ioa":
        rows = view.rows(
            """SELECT evidence_id, ca_ioa FROM evidence
               WHERE kind = 'iec104_asdu' AND protocol_class = 'control'
                 AND timestamp >= ? AND timestamp < ? AND ca_ioa IS NOT NULL""",
            (start, end),
        )
        return sorted({row["ca_ioa"] for row in rows})
    if question["id"] == "new_electrical_entities":
        rows = view.rows(
            """SELECT evidence_id, entity FROM evidence
               WHERE kind = 'electrical_update' AND timestamp >= ? AND timestamp < ?""",
            (start, end),
        )
        return sorted({row["entity"] for row in rows})
    if question["id"] == "shared_frame_count":
        rows = view.rows(
            """SELECT evidence_id, fingerprint, vantage FROM evidence
               WHERE modality = 'network' AND fingerprint IS NOT NULL
                 AND timestamp >= ? AND timestamp < ?""",
            (start, end),
        )
        grouped: dict[str, set] = {}
        for row in rows:
            if row["fingerprint"] and row["vantage"]:
                grouped.setdefault(row["fingerprint"], set()).add(row["vantage"])
        return sum(len(vantages) > 1 for vantages in grouped.values())
    if question["id"] == "control_reply":
        controls = view.rows(
            """SELECT evidence_id, ca_ioa, timestamp, src_ip, dst_ip, src_port, dst_port
               FROM evidence WHERE kind = 'iec104_asdu' AND protocol_class = 'control'
                 AND timestamp >= ? AND timestamp < ?""",
            (start, end),
        )
        later_rows = view.rows(
            """SELECT evidence_id, ca_ioa, timestamp, src_ip, dst_ip, src_port, dst_port
               FROM evidence WHERE kind = 'iec104_asdu'""",
            (),
        )
        answers = []
        for row in controls:
            observed = any(
                other["ca_ioa"] == row["ca_ioa"] and other["timestamp"] > row["timestamp"]
                and other["timestamp"] < row["timestamp"] + 5 and other["src_ip"] == row["dst_ip"]
                and other["dst_ip"] == row["src_ip"] and other["src_port"] == row["dst_port"]
                and other["dst_port"] == row["src_port"]
                for other in later_rows
            )
            answers.append({"ca_ioa": row["ca_ioa"], "reply_observed": observed})
        return answers
    if question["id"] == "measurement_value":
        rows = view.rows(
            "SELECT evidence_id, entity, value FROM evidence WHERE evidence_id = ?",
            (question["answer"]["evidence_id"],),
        )
        if not rows:
            return None
        row = rows[0]
        return {"evidence_id": row["evidence_id"], "entity": row["entity"], "value": row["value"]}
    return None


def score_questions(questions: list[dict], predicted: list[dict]) -> dict:
    by_id = {item["id"]: item["answer"] for item in predicted}
    details = []
    for question in questions:
        match = by_id.get(question["id"]) == question["answer"]
        details.append({"id": question["id"], "match": match})
    return {
        "exact_match": sum(item["match"] for item in details) / len(details) if details else None,
        "details": details,
    }


def score_graph(db: EvidenceDB, graph) -> dict:
    published = list(graph.edges.values())
    offered = [edge for edge in published if edge.get("origin") == "inferred"]
    classes = {"N-N": [], "P-P": [], "N-P": []}
    unsupported = temporal_errors = citation_errors = citations = dependency_errors = 0
    for edge in published:
        classes[_pair(edge)].append(edge["status"])
        oracle = verify_edge(db, edge, contradiction_search=True, source_dependency=True)
        if edge["status"] == "supported" and oracle["status"] != "supported":
            unsupported += 1
        if edge.get("time_order") in ("source_before_target", "target_before_source"):
            if any(item.get("reason") == "temporal_order" for item in oracle["contradiction_details"]):
                temporal_errors += 1
        for evidence_id in edge.get("evidence_ids") or []:
            citations += 1
            loaded = db.get([evidence_id])
            row = loaded["rows"][0] if loaded["rows"] else None
            if row is None or not (_matches_endpoint(row, edge)):
                citation_errors += 1
        if _dependency_error(edge, oracle):
            dependency_errors += 1
    supported = [edge for edge in published if edge["status"] == "supported"]
    return {
        "published_edges": len(published),
        "removed_edges": len(graph.removed),
        "offered_inferred_edges": len(offered),
        "published_supported": len(supported),
        "unsupported_relation_rate": (unsupported / len(supported)) if supported else None,
        "temporal_order_errors": temporal_errors,
        "citation_validity": ((citations - citation_errors) / citations) if citations else None,
        "source_dependency_errors": dependency_errors,
        "by_pair": {key: _status_counts(value) for key, value in classes.items()},
        "note": "unsupported_relation_rate is not edge precision. Sherlock has no relation-graph gold.",
    }


def score_necessity(state) -> dict:
    tests = state.necessity or []
    sensitive = 0
    stable = 0
    compared = 0
    for item in tests:
        if not item.get("applicable"):
            continue
        if item.get("full_stable"):
            stable += 1
        for ablation in item.get("ablations") or []:
            compared += 1
            sensitive += int(bool(ablation.get("judgment_changed")))
    return {
        "relations_tested": len(tests),
        "stable_full_judgments": stable,
        "citations_compared": compared,
        "judgment_sensitive_citations": sensitive,
        "sensitivity": (sensitive / compared) if compared else None,
        "note": "Sensitivity is model dependence, not causal necessity and not relation correctness.",
    }


def preset(name: str) -> Flags:
    table = {
        "B0": dict(method="B0-direct", active_retrieval=False, temporal_graph=False, contradiction_search=False,
                   evidence_necessity=False, source_dependency=False, graph_revision=False, context="earliest",
                   max_tool_calls=0, max_llm_calls=3),
        "B1": dict(method="B1-flat-retrieval", active_retrieval=False, temporal_graph=False, contradiction_search=False,
                   evidence_necessity=False, source_dependency=False, graph_revision=False, context="stratified",
                   max_tool_calls=0, max_llm_calls=3),
        "B2": dict(method="B2-observed-graph-retrieval", active_retrieval=False, temporal_graph=True,
                   contradiction_search=False, evidence_necessity=False, source_dependency=False,
                   graph_revision=False, context="graph", max_tool_calls=0, max_llm_calls=3),
        "B3": dict(method="B3-agentic-retrieval", active_retrieval=True, temporal_graph=True,
                   contradiction_search=False, evidence_necessity=False, source_dependency=False,
                   graph_revision=False, context="tools", max_tool_calls=8, max_llm_calls=10),
        "ETGI": dict(method="ETGI"),
        "wo_retrieval": dict(method="ETGI-wo-active-retrieval", active_retrieval=False, context="stratified"),
        "wo_graph": dict(method="ETGI-wo-temporal-graph", temporal_graph=False),
        "wo_contradiction": dict(method="ETGI-wo-contradiction", contradiction_search=False),
        "wo_necessity": dict(method="ETGI-wo-necessity", evidence_necessity=False),
        "wo_dependency": dict(method="ETGI-wo-source-dependency", source_dependency=False),
        "wo_revision": dict(method="ETGI-wo-revision", graph_revision=False),
    }
    if name not in table:
        raise KeyError(name)
    flags = Flags()
    for key, value in table[name].items():
        setattr(flags, key, value)
    return flags


MODALITY_PRESETS = ("both", "network", "electrical")


def run_named(db: EvidenceDB, llm, name: str, out: Path, *, limitations=None,
              full_db: EvidenceDB | None = None, questions=None) -> dict:
    flags = preset(name)
    result = investigate(
        db, llm, incident_start=db.incident_start, incident_end=db.incident_end,
        out=out, flags=flags, limitations=limitations,
    )
    report = write_report(result, db, out, llm=llm)
    oracle = full_db or db
    questions = questions or []
    predicted = answer_from_retrieval(oracle, questions, result["state"].retrieved_ids)
    summary = {
        "method": flags.method,
        "completion": result["state"].completion,
        "questions": score_questions(questions, predicted),
        "graph": score_graph(oracle, result["graph"]),
        "necessity": score_necessity(result["state"]),
        "llm_calls": result["state"].llm_calls,
        "tool_calls": result["state"].tool_calls,
        "gap_fallbacks": result["state"].gap_fallbacks,
        "prompt_tokens": result["state"].prompt_tokens,
        "completion_tokens": result["state"].completion_tokens,
        "narrative_rejected": result["state"].narrative_rejected,
        "modality_filter": db.modality,
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _empty(question: dict):
    if isinstance(question["answer"], list):
        return []
    if isinstance(question["answer"], int):
        return 0
    return None


def _pair(edge: dict) -> str:
    mods = sorted((edge.get("source_modality") or "", edge.get("target_modality") or ""))
    if mods == ["network", "network"]:
        return "N-N"
    if mods == ["electrical", "electrical"]:
        return "P-P"
    return "N-P"


def _status_counts(statuses: list[str]) -> dict:
    return {name: statuses.count(name) for name in ("supported", "disputed", "unresolved", "removed")}


def _matches_endpoint(row: dict, edge: dict) -> bool:
    entities = {edge.get("source_entity"), edge.get("target_entity")}
    if row["entity"] in entities:
        return True
    for ip in (row.get("src_ip"), row.get("dst_ip")):
        if ip and any(ip in (entity or "") for entity in entities):
            return True
    return False


def _dependency_error(edge: dict, oracle: dict) -> bool:
    if edge["status"] != "supported" or edge.get("relation_type") != "temporal_association":
        return False
    if _pair(edge) != "N-P":
        return False
    return oracle.get("recommended_relation_type") == "shared_source" or any(
        len(group.get("evidence_ids") or []) > 1 for group in oracle.get("source_dependencies") or []
    )
