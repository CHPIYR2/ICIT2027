"""Prepare a window, ask for an explanation, and publish only verified claims."""
from __future__ import annotations
import json
from pathlib import Path
from ..graph.export import write_graph
from .explain import explain
from .relations import discover_relations
from .select import select_evidence
from .timeline import build_timeline
from .verify import verify_claims


def prepare(db, start: float, end: float, *, background_start: float | None = None,
            background_end: float | None = None, limit: int = 24) -> dict:
    selection = select_evidence(
        db, start, end, background_start=background_start, background_end=background_end, limit=limit,
    )
    timeline = build_timeline(selection)
    discovered = discover_relations(timeline)
    earliest = []
    for event in timeline[:8]:
        earliest.append({
            "time": event["time"], "entity": event["entity"], "role": event["role"],
            "evidence_ids": event["evidence_ids"][:2], "observation": event["observation"],
        })
    return {
        "incident_start": start,
        "incident_end": end,
        "selection": {key: value for key, value in selection.items() if key != "selected"},
        "timeline": timeline,
        "relations": discovered["relations"],
        "graph": discovered["graph"],
        "fixed_summary": {
            "timeline_events": len(timeline),
            "excluded_by_reason": selection["excluded_by_reason"],
            "earliest_events": earliest,
        },
    }


def run_explanation(db, llm, prepared: dict, *, level: str = "B4", num_predict: int = 512,
                    num_ctx: int = 8192, seed: int = 1) -> dict:
    model = explain(llm, prepared, level=level, num_predict=num_predict, num_ctx=num_ctx, seed=seed)
    checked = verify_claims(db, model["claims"], prepared["relations"]) if level == "B4" else {
        "verified": [], "rejected": [],
    }
    if level != "B4":
        checked = {"verified": [], "rejected": [], "unverified_model_claims": model["claims"]}
    published = checked["verified"] if level == "B4" else model["claims"]
    inferred = [claim for claim in published if claim.get("claim_level") in ("supported_inference", "observed_fact")]
    minimum = level == "B4" and not inferred
    report = _report(prepared, model, checked, published, minimum=minimum, level=level)
    return {"model": model, "verification": checked, "published_claims": published, "report": report, "minimum": minimum}


def write_run(db, llm, prepared: dict, out: Path, *, level: str = "B4", num_predict: int = 512,
              num_ctx: int = 8192, seed: int = 1) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    result = run_explanation(
        db, llm, prepared, level=level, num_predict=num_predict, num_ctx=num_ctx, seed=seed,
    )
    (out / "selection.json").write_text(json.dumps(prepared["selection"], indent=2, default=str), encoding="utf-8")
    write_graph(prepared["graph"], out)
    (out / "timeline.json").write_text(json.dumps(prepared["timeline"], indent=2, default=str), encoding="utf-8")
    (out / "relations.json").write_text(json.dumps(prepared["relations"], indent=2, default=str), encoding="utf-8")
    (out / "verification.json").write_text(json.dumps(result["verification"], indent=2, default=str), encoding="utf-8")
    (out / "model.json").write_text(json.dumps(result["model"], indent=2, default=str), encoding="utf-8")
    (out / "report.json").write_text(json.dumps(result["report"], indent=2, default=str), encoding="utf-8")
    (out / "report.md").write_text(_markdown(result["report"]), encoding="utf-8")
    trace = {
        "level": level,
        "model": result["model"].get("model"),
        "prompt_tokens": result["model"].get("prompt_tokens"),
        "completion_tokens": result["model"].get("completion_tokens"),
        "done_reason": result["model"].get("done_reason"),
        "context_limited": result["model"].get("context_limited"),
        "abstain": result["model"].get("abstain"),
        "claims": len(result["model"].get("claims") or []),
        "verified": len(result["verification"].get("verified") or []),
        "rejected": len(result["verification"].get("rejected") or []),
    }
    (out / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return {**result, "trace": trace}


def _report(prepared, model, checked, published, *, minimum: bool, level: str) -> dict:
    observations = [{
        "time": event["time"], "entity": event["entity"], "role": event["role"],
        "record_class": event["record_class"], "observation": event["observation"],
        "evidence_ids": event["evidence_ids"][:4],
    } for event in prepared["timeline"]]
    confirmed = [relation for relation in prepared["relations"] if relation.get("claim_level") == "observed_fact"]
    text = _minimum_text(observations, confirmed) if minimum or not published else _claim_text(published)
    return {
        "level": level,
        "incident_start": prepared["incident_start"],
        "incident_end": prepared["incident_end"],
        "observations": observations,
        "confirmed_record_links": confirmed,
        "published_claims": published,
        "rejected_claims": checked.get("rejected") or [],
        "model_abstained": model.get("abstain"),
        "minimum_report": minimum or not published,
        "text": text,
        "no_confirmed_inferred_relation": not any(
            claim.get("claim_level") == "supported_inference" for claim in published
        ),
    }


def _minimum_text(observations, confirmed) -> str:
    lines = ["Verified observations:"]
    if not observations:
        lines.append("No non-hold observation was selected in this window.")
    for event in observations[:12]:
        lines.append(f"- {event['time']} {event['entity']} {event['observation']} ({', '.join(event['evidence_ids'][:2])})")
    if confirmed:
        lines.append("Record links restated from those observations:")
        for relation in confirmed[:8]:
            lines.append(
                f"- {relation['relation_type']} {relation['source_entity']} — {relation['target_entity']} "
                f"({', '.join(relation['evidence_ids'][:2])}). Not a cause."
            )
    else:
        lines.append("No confirmed inferred relation.")
    return "\n".join(lines)


def _claim_text(claims: list[dict]) -> str:
    lines = []
    for claim in claims:
        ids = ", ".join(str(item) for item in (claim.get("evidence_ids") or [])[:4])
        lines.append(f"- {claim.get('statement')} ({ids}).")
    return "\n".join(lines)


def _markdown(report: dict) -> str:
    parts = [
        f"# Post-alert report ({report['level']})",
        "",
        f"Window {report['incident_start']} to {report['incident_end']}.",
        "",
        "## Timeline",
    ]
    for event in report["observations"][:16]:
        parts.append(f"- {event['time']} {event['role']} {event['entity']} ({', '.join(event['evidence_ids'][:2])})")
    parts.extend(["", report["text"], ""])
    if report["rejected_claims"]:
        parts.append("## Rejected claims")
        for claim in report["rejected_claims"]:
            parts.append(f"- {claim.get('statement')} — {', '.join(claim.get('reasons') or [])}")
    if report["no_confirmed_inferred_relation"]:
        parts.append("")
        parts.append("No confirmed inferred relation.")
    return "\n".join(parts) + "\n"
