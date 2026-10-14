"""Write the investigation report and the graph artifacts."""
from __future__ import annotations
import json
import re
from pathlib import Path
from ..agent.controller import NARRATIVE_SYSTEM
from ..graph.export import write_graph

_EVIDENCE = re.compile(r"EV-[0-9a-f]{16}")


def write_report(result: dict, db, out: Path, *, llm=None) -> dict:
    state = result["state"]
    graph = result["graph"]
    flags = result["flags"]
    limitations = list(result.get("limitations") or [])
    findings = _findings(state, graph, limitations)
    claims = verified_claims(graph, db)
    narrative, rejected, reason = _narrative(llm, state, flags, findings, claims)
    state.narrative = narrative
    state.narrative_rejected = rejected
    state.completion = _completion(state, graph, flags)
    body = {
        "method": flags.method,
        "model": state.model,
        "completion": state.completion,
        "incident_overview": {
            "start": state.incident_start,
            "end": state.incident_end,
            "modality_filter": db.modality,
            "tool_calls": state.tool_calls,
            "llm_calls": state.llm_calls,
            "gap_fallbacks": state.gap_fallbacks,
            "prompt_tokens": state.prompt_tokens,
            "completion_tokens": state.completion_tokens,
            "limitations": limitations,
        },
        "observed_events": findings["observed_events"],
        "relations": findings["relations"],
        "removed_relations": findings["removed_relations"],
        "alternative_explanations": findings["alternatives"],
        "contradictions": findings["contradictions"],
        "missing_evidence": findings["missing_evidence"],
        "uncertainty": findings["uncertainty"],
        "verified_claims": [claim for claim in claims if claim.get("verified")],
        "rejected_claims": [claim for claim in claims if not claim.get("verified")],
        "necessity": state.necessity,
        "narrative": narrative,
        "narrative_rejected": rejected,
        "narrative_rejection_reason": reason,
        "conclusion": _conclusion(state, findings),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "investigation_report.json").write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    (out / "investigation_report.md").write_text(_markdown(body), encoding="utf-8")
    write_graph(graph, out)
    _refresh_state(out, state, graph, flags)
    return body


def verified_claims(graph, db) -> list[dict]:
    """Check entity, time, field, value, and evidence ids before any prose is written."""
    claims = []
    seen = set()
    for edge in list(graph.edges.values()) + list(graph.removed.values()):
        for evidence_id in (edge.get("supporting_evidence") or edge.get("evidence_ids") or [])[:8]:
            if evidence_id in seen:
                continue
            seen.add(evidence_id)
            loaded = db.get([evidence_id])["rows"]
            if not loaded:
                claims.append({"claim_id": f"C-{evidence_id}", "verified": False, "evidence_ids": [evidence_id],
                               "reason": "evidence id is not in the database"})
                continue
            row = loaded[0]
            claims.append({
                "claim_id": f"C-{evidence_id}",
                "kind": "observation",
                "entity": row["entity"],
                "time": row["timestamp"],
                "field": row["kind"],
                "value": row["value"],
                "value_present": row["value_present"],
                "evidence_ids": [evidence_id],
                "causal": False,
                "verified": True,
            })
        if edge.get("claim_level") == "supported_inference" and edge["edge_id"] not in seen:
            claims.append({
                "claim_id": f"C-{edge['edge_id']}",
                "kind": "inference",
                "entity": f"{edge.get('source_entity')} ~ {edge.get('target_entity')}",
                "time": None,
                "field": edge.get("relation_type"),
                "value": None,
                "evidence_ids": list(edge.get("evidence_ids") or []),
                "causal": False,
                "verified": True,
                "text": "Temporal association inside the stated gap. Not a demonstrated cause.",
            })
    return claims


def _narrative(llm, state, flags, findings, claims: list[dict]) -> tuple[str, bool, str]:
    verified = [claim for claim in claims if claim.get("verified")]
    explanation = _render_claims(verified)
    if llm is None or state.llm_calls >= flags.max_llm_calls:
        return explanation, False, ""
    turn = llm.chat(
        [{"role": "system", "content": NARRATIVE_SYSTEM},
         {"role": "user", "content": json.dumps({"verified_claims": verified}, default=str)[:14000]}],
        tools=None, temperature=0.0, seed=flags.seed, num_predict=min(500, flags.num_predict),
    )
    state.llm_calls += 1
    state.prompt_tokens += turn.prompt_tokens
    state.completion_tokens += turn.completion_tokens
    allowed = {evidence_id for claim in verified for evidence_id in claim["evidence_ids"]}
    cited = set(_EVIDENCE.findall(turn.content or ""))
    unknown = sorted(cited - allowed)
    if unknown or not cited and not verified:
        reason = "Narrative cited evidence that was not in the verified claims."
        if unknown:
            reason += " Unknown ids: " + ", ".join(unknown[:8])
        return explanation, True, reason
    return (turn.content or "").strip() or explanation, False, ""


def _render_claims(claims: list[dict]) -> str:
    if not claims:
        return ""
    lines = []
    for claim in claims:
        if claim["kind"] == "observation":
            value = "missing" if not claim.get("value_present") else claim.get("value")
            lines.append(
                f"{claim['entity']} {claim['field']} at {claim['time']} is {value} ({', '.join(claim['evidence_ids'])})."
            )
        else:
            lines.append(f"Inference, not a cause: {claim['entity']} ({', '.join(claim['evidence_ids'])}).")
    return " ".join(lines)


def _completion(state, graph, flags) -> str:
    if state.budget_hit:
        return "INCOMPLETE_BUDGET_EXHAUSTED"
    problems = []
    for edge in graph.edges.values():
        if edge["status"] not in ("supported", "associated", "disputed", "unresolved"):
            problems.append(edge["edge_id"])
        if flags.contradiction_search and not edge.get("contradiction_searched"):
            problems.append(edge["edge_id"] + ":contradiction")
    inferred = [edge for edge in graph.edges.values() if edge.get("origin") == "inferred" and edge.get("evidence_ids")]
    if flags.evidence_necessity and inferred and not state.necessity and not state.budget_hit:
        problems.append("necessity")
    state.errors.extend(problems)
    return "COMPLETE" if not problems else "INCOMPLETE_CHECKS"


def _findings(state, graph, limitations) -> dict:
    observed = [{
        "node_id": node["node_id"], "modality": node["modality"], "entity": node["entity_id"],
        "event_type": node["event_type"], "start_time": node["start_time"], "end_time": node["end_time"],
        "evidence_ids": node["evidence_ids"], "description": node["description"],
    } for node in graph.nodes.values()]
    relations = [_relation(edge) for edge in graph.edges.values()]
    removed = [_relation(edge) for edge in graph.removed.values()]
    alternatives = [item for edge in graph.edges.values() for item in edge.get("alternatives") or []]
    contradictions = [{
        "edge_id": edge["edge_id"], "evidence_ids": edge.get("contradicting_evidence") or [],
        "notes": edge.get("uncertainty_notes") or [],
    } for edge in graph.edges.values() if edge.get("contradicting_evidence") or edge["status"] == "disputed"]
    missing = list(limitations)
    missing.extend(state.unresolved_questions)
    if not missing:
        missing.append("No additional missing-evidence note was recorded.")
    uncertainty = [{
        "edge_id": edge["edge_id"], "status": edge["status"], "relation_type": edge["relation_type"],
        "origin": edge["origin"], "notes": edge.get("uncertainty_notes") or [],
    } for edge in list(graph.edges.values()) + list(graph.removed.values())]
    return {
        "observed_events": observed, "relations": relations, "removed_relations": removed,
        "alternatives": alternatives, "contradictions": contradictions, "missing_evidence": missing,
        "uncertainty": uncertainty,
    }


def _relation(edge: dict) -> dict:
    pair = _pair(edge)
    return {
        "edge_id": edge["edge_id"], "pair": pair, "relation_type": edge["relation_type"],
        "origin": edge["origin"], "status": edge["status"], "time_order": edge.get("time_order"),
        "directed": edge.get("directed"), "source_entity": edge.get("source_entity"),
        "target_entity": edge.get("target_entity"), "evidence_ids": edge.get("evidence_ids") or [],
        "supporting_evidence": edge.get("supporting_evidence") or [],
        "contradicting_evidence": edge.get("contradicting_evidence") or [],
        "source_dependencies": edge.get("source_dependencies") or [],
        "rationale": edge.get("rationale") or "",
        "alternatives": edge.get("alternatives") or [],
        "uncertainty_notes": edge.get("uncertainty_notes") or [],
        "claim_level": edge.get("claim_level"),
        "causal_status": edge.get("causal_status", "not_established"),
        "inference_status": edge.get("inference_status"),
        "built_by": edge.get("built_by"),
        "history_operations": [item.get("operation") for item in edge.get("history") or []],
    }


def _pair(edge: dict) -> str:
    mods = sorted((edge.get("source_modality") or "", edge.get("target_modality") or ""))
    if mods == ["network", "network"]:
        return "N-N"
    if mods == ["electrical", "electrical"]:
        return "P-P"
    return "N-P"


def _conclusion(state, findings) -> str:
    supported = [item for item in findings["relations"] if item["status"] == "supported"]
    unresolved = [item for item in findings["relations"] if item["status"] == "unresolved"]
    return (
        f"Completion {state.completion}. {len(supported)} relations are supported by a record link. "
        f"{len(unresolved)} relations remain unresolved. Supported links are communications, shared frames, "
        "shared IEC-104 reports, or same-device attributes, not demonstrated physical causation. "
        + (state.narrative if state.narrative else "No model narrative was accepted.")
    )


def _markdown(body: dict) -> str:
    overview = body["incident_overview"]
    lines = [
        "# Incident investigation",
        "",
        f"Completion: `{body['completion']}`. Method: {body['method']}. Model: {body['model'] or 'scripted'}.",
        "",
        "## Incident overview",
        "",
        f"Window {overview['start']} to {overview['end']}. Modality filter: {overview['modality_filter']}.",
        f"Tool calls: {overview['tool_calls']}. LLM calls: {overview['llm_calls']}. "
        f"Gap fallbacks: {overview['gap_fallbacks']}.",
        f"Prompt tokens: {overview['prompt_tokens']}. Completion tokens: {overview['completion_tokens']}.",
        "",
        "Data limitations:",
    ]
    lines.extend(f"- {item}" for item in overview["limitations"] or ["None recorded."])
    lines.extend(["", "## Observed events", ""])
    if not body["observed_events"]:
        lines.append("No observation nodes were built.")
    for event in body["observed_events"]:
        ids = ", ".join(event["evidence_ids"][:8]) or "none"
        lines.append(
            f"- `{event['node_id']}` {event['modality']} `{event['entity']}` "
            f"({event['event_type']}, {event['start_time']}–{event['end_time']}). Evidence: {ids}."
        )
    lines.extend(["", "## Main event relations", ""])
    if not body["relations"]:
        lines.append("No relation remains in the graph.")
    for relation in body["relations"]:
        lines.append(
            f"- `{relation['edge_id']}` {relation['pair']} `{relation['relation_type']}` "
            f"status `{relation['status']}` origin `{relation['origin']}` "
            f"from `{relation['source_entity']}` to `{relation['target_entity']}`."
        )
        if relation["rationale"]:
            lines.append(f"  Inference: {relation['rationale']}")
        lines.append("  Evidence: " + (", ".join(relation["evidence_ids"][:12]) or "none") + ".")
    lines.extend(["", "## Alternative explanations", ""])
    lines.extend(f"- {item}" for item in body["alternative_explanations"] or ["None recorded."])
    lines.extend(["", "## Contradictions", ""])
    if not body["contradictions"]:
        lines.append("No contradicting evidence ids were recorded.")
    for item in body["contradictions"]:
        lines.append(f"- `{item['edge_id']}` evidence {', '.join(item['evidence_ids']) or 'none'}.")
    lines.extend(["", "## Missing evidence", ""])
    lines.extend(f"- {item}" for item in body["missing_evidence"])
    lines.extend(["", "## Uncertainty", ""])
    for item in body["uncertainty"]:
        lines.append(f"- `{item['edge_id']}` {item['status']} ({item['relation_type']}, {item['origin']}).")
        lines.extend(f"  {note}" for note in item["notes"])
    lines.extend(["", "## Investigation conclusion", "", body["conclusion"], ""])
    if body["narrative_rejected"]:
        lines.extend(["The model narrative was rejected.", body["narrative_rejection_reason"], ""])
    elif body["narrative"]:
        lines.extend(["## Model narrative", "", body["narrative"], ""])
    return "\n".join(lines) + "\n"


def _refresh_state(out: Path, state, graph, flags) -> None:
    path = out / "investigation_state.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    payload.update({
        "completion": state.completion,
        "narrative_rejected": state.narrative_rejected,
        "llm_calls": state.llm_calls,
        "prompt_tokens": state.prompt_tokens,
        "completion_tokens": state.completion_tokens,
        "errors": state.errors,
        "necessity": state.necessity,
        "flags": flags.as_dict(),
        "graph": graph.snapshot(),
    })
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
