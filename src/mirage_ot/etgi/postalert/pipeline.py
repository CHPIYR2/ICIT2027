"""Prepare a window, ask for an explanation, and publish only verified claims.

Rejected claims stay in `verification.json` and `rejected_claims.json` for
audit. They are never rendered into `report.md` as public report prose.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from ..graph.export import write_graph
from .explain import explain, expose_relations, expose_timeline
from .relations import discover_relations
from .select import select_evidence
from .timeline import build_timeline_with_lineage
from .verify import verify_claims


def prepare(db, start: float, end: float, *, background_start: float | None = None,
            background_end: float | None = None, limit: int = 24) -> dict:
    selection = select_evidence(
        db, start, end, background_start=background_start, background_end=background_end, limit=limit,
    )
    timeline, lineage = build_timeline_with_lineage(selection)
    discovered = discover_relations(timeline)
    exposed_timeline = expose_timeline(timeline, limit=10)
    exposed_relations = expose_relations(discovered["relations"], exposed_timeline, limit=8)
    earliest = []
    for event in exposed_timeline[:8]:
        earliest.append({
            "timeline_id": event["timeline_id"],
            "time": event["time"],
            "entity": event["entity"],
            "role": event["role"],
            "modality": event.get("modality"),
            "evidence_ids": event["evidence_ids"][:2],
        })
    return {
        "incident_start": start,
        "incident_end": end,
        "selection": {key: value for key, value in selection.items() if key != "selected"},
        "timeline": timeline,
        "lineage": lineage,
        "relations": discovered["relations"],
        "graph": discovered["graph"],
        "exposed_timeline": exposed_timeline,
        "exposed_relations": exposed_relations,
        "coverage": _coverage_summary(selection, timeline, exposed_timeline, []),
        "fixed_summary": {
            "timeline_events": len(timeline),
            "excluded_by_reason": selection["excluded_by_reason"],
            "earliest_events": earliest,
        },
    }


def run_explanation(db, llm, prepared: dict, *, level: str = "B4", claim_mode: str = "typed_refs",
                    allow_salvage: bool = False, num_predict: int = 512,
                    num_ctx: int = 8192, seed: int = 1) -> dict:
    model = explain(
        llm, prepared, level=level, claim_mode=claim_mode,
        allow_salvage=allow_salvage, num_predict=num_predict, num_ctx=num_ctx, seed=seed,
    )
    if level == "B4":
        checked = verify_claims(db, model["claims"], prepared["relations"], prepared["timeline"])
    else:
        checked = {"verified": [], "rejected": [], "unverified_model_claims": model["claims"]}
    published = checked["verified"] if level == "B4" else model["claims"]
    coverage = _coverage_summary(prepared["selection"], prepared["timeline"], prepared["exposed_timeline"], published)
    inferred = [claim for claim in published if claim.get("claim_level") in ("supported_inference", "observed_fact")]
    minimum = level == "B4" and not inferred
    report = _report(prepared, model, checked, published, coverage=coverage, minimum=minimum, level=level)
    return {
        "model": model,
        "verification": checked,
        "published_claims": published,
        "coverage": coverage,
        "report": report,
        "minimum": minimum,
    }


def write_run(db, llm, prepared: dict, out: Path, *, level: str = "B4", claim_mode: str = "typed_refs",
              allow_salvage: bool = False, num_predict: int = 512,
              num_ctx: int = 8192, seed: int = 1) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    result = run_explanation(
        db, llm, prepared, level=level, claim_mode=claim_mode,
        allow_salvage=allow_salvage, num_predict=num_predict, num_ctx=num_ctx, seed=seed,
    )
    manifest = run_manifest(
        db, level=level, claim_mode=claim_mode, allow_salvage=allow_salvage,
        num_predict=num_predict, num_ctx=num_ctx, seed=seed,
    )
    (out / "selection.json").write_text(json.dumps(prepared["selection"], indent=2, default=str), encoding="utf-8")
    write_graph(prepared["graph"], out)
    (out / "timeline.json").write_text(json.dumps(prepared["timeline"], indent=2, default=str), encoding="utf-8")
    (out / "lineage.json").write_text(json.dumps(prepared.get("lineage") or {}, indent=2, default=str), encoding="utf-8")
    (out / "relations.json").write_text(json.dumps(prepared["relations"], indent=2, default=str), encoding="utf-8")
    (out / "verification.json").write_text(json.dumps(result["verification"], indent=2, default=str), encoding="utf-8")
    (out / "rejected_claims.json").write_text(
        json.dumps(result["verification"].get("rejected") or [], indent=2, default=str),
        encoding="utf-8",
    )
    (out / "coverage.json").write_text(json.dumps(result["coverage"], indent=2, default=str), encoding="utf-8")
    (out / "model.json").write_text(json.dumps(result["model"], indent=2, default=str), encoding="utf-8")
    (out / "report.json").write_text(json.dumps(result["report"], indent=2, default=str), encoding="utf-8")
    (out / "report.md").write_text(_markdown(result["report"]), encoding="utf-8")
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    trace = {
        "level": level,
        "claim_mode": claim_mode,
        "model": result["model"].get("model"),
        "prompt_tokens": result["model"].get("prompt_tokens"),
        "completion_tokens": result["model"].get("completion_tokens"),
        "done_reason": result["model"].get("done_reason"),
        "partial_output": result["model"].get("partial_output"),
        "salvaged_claim_count": result["model"].get("salvaged_claim_count"),
        "context_limited": result["model"].get("context_limited"),
        "abstain": result["model"].get("abstain"),
        "claims": len(result["model"].get("claims") or []),
        "verified": len(result["verification"].get("verified") or []),
        "rejected": len(result["verification"].get("rejected") or []),
        "code_sha256": manifest["code_sha256"],
    }
    (out / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return {**result, "trace": trace, "manifest": manifest}


def run_manifest(db, **config) -> dict:
    package_dir = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    file_hashes = {}
    for path in sorted(package_dir.glob("*.py")):
        data = path.read_bytes()
        file_hashes[path.name] = hashlib.sha256(data).hexdigest()
        digest.update(path.name.encode("utf-8"))
        digest.update(data)
    db_info = _db_fingerprint(db)
    git_commit, dirty_sha = _git_state(package_dir)
    config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "git_commit": git_commit,
        "git_dirty_diff_sha256": dirty_sha,
        "code_sha256": digest.hexdigest(),
        "module_hashes": file_hashes,
        "config": config,
        "config_sha256": config_sha,
        "db_fingerprint": db_info,
    }


def _db_fingerprint(db) -> dict:
    row = db.conn.execute(
        "SELECT COUNT(*) AS n, MIN(timestamp) AS t0, MAX(timestamp) AS t1 FROM evidence"
    ).fetchone()
    meta = {
        item["key"]: item["value"]
        for item in db.conn.execute("SELECT key, value FROM meta ORDER BY key").fetchall()
    }
    meta_sha = hashlib.sha256(json.dumps(meta, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "evidence_rows": row["n"],
        "min_timestamp": row["t0"],
        "max_timestamp": row["t1"],
        "meta_sha256": meta_sha,
    }


def _git_state(cwd: Path) -> tuple[str, str]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
        diff = subprocess.check_output(
            ["git", "diff", "HEAD", "--", "src/mirage_ot/etgi/postalert"],
            cwd=cwd.parents[3],
            stderr=subprocess.DEVNULL,
        )
        return commit, hashlib.sha256(diff).hexdigest()
    except Exception:
        return "unknown", "unknown"


def _coverage_summary(selection: dict, timeline: list[dict], exposed: list[dict], published: list[dict]) -> dict:
    selected_mod = _count_event_modalities(timeline)
    selected_roles = _count_event_roles(timeline)
    exposed_mod = _count_card_modalities(exposed)
    exposed_roles = _count_event_roles(exposed)
    timeline_by_ev = {}
    for event in timeline:
        for ev_id in event.get("evidence_ids") or []:
            timeline_by_ev[ev_id] = (event.get("source") or {}).get("modality") or event.get("modality")
    cited_mod: dict[str, int] = {}
    for claim in published:
        for ev_id in claim.get("evidence_ids") or []:
            mod = timeline_by_ev.get(ev_id, "unknown")
            cited_mod[mod] = cited_mod.get(mod, 0) + 1
    return {
        "available_by_modality": selection.get("available_by_modality") or {},
        "available_by_kind": selection.get("available_by_kind") or {},
        "selected_by_modality": selected_mod,
        "selected_by_role": selected_roles,
        "exposed_by_modality": exposed_mod,
        "exposed_by_role": exposed_roles,
        "cited_by_modality": cited_mod,
    }


def _count_event_modalities(events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        mod = (event.get("source") or {}).get("modality") or event.get("modality") or "unknown"
        counts[mod] = counts.get(mod, 0) + 1
    return counts


def _count_card_modalities(cards: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        mod = card.get("modality") or (card.get("source") or {}).get("modality") or "unknown"
        counts[mod] = counts.get(mod, 0) + 1
    return counts


def _count_event_roles(events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        role = str(event.get("role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return counts


def _report(prepared, model, checked, published, *, coverage: dict, minimum: bool, level: str) -> dict:
    observations = [{
        "timeline_id": event["timeline_id"],
        "time": event["time"],
        "entity": event["entity"],
        "role": event["role"],
        "record_class": event["record_class"],
        "observation": event["observation"],
        "evidence_ids": event["evidence_ids"][:4],
        "lineage_ref": event.get("lineage_ref"),
    } for event in prepared["timeline"]]
    confirmed = [
        relation for relation in prepared["relations"]
        if relation.get("claim_level") == "observed_fact" and relation.get("verification_status") == "supported"
    ]
    text = _minimum_text(observations, confirmed) if minimum or not published else _claim_text(published)
    return {
        "level": level,
        "claim_mode": model.get("claim_mode"),
        "incident_start": prepared["incident_start"],
        "incident_end": prepared["incident_end"],
        "observations": observations,
        "confirmed_record_links": confirmed,
        "published_claims": published,
        "rejected_claim_count": len(checked.get("rejected") or []),
        "rejected_claims_audit_file": "rejected_claims.json",
        "model_abstained": model.get("abstain"),
        "partial_output": bool(model.get("partial_output")),
        "minimum_report": minimum or not published,
        "coverage": coverage,
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
    lines = ["Verified claims:"]
    for claim in claims:
        rendered = claim.get("rendered_text") or claim.get("verified_prose")
        if rendered:
            lines.append(f"- {rendered}")
        else:
            ids = ", ".join(str(item) for item in (claim.get("evidence_ids") or [])[:4])
            lines.append(f"- [unverified] {claim.get('statement')} ({ids}).")
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
        parts.append(
            f"- {event['timeline_id']} {event['time']} {event['role']} {event['entity']} "
            f"({', '.join(event['evidence_ids'][:2])})"
        )
    parts.extend(["", report["text"], ""])
    if report.get("rejected_claim_count"):
        parts.append(
            f"Audit note: {report['rejected_claim_count']} unverified model claim(s) were withheld and logged to "
            f"`{report['rejected_claims_audit_file']}`."
        )
    if report["no_confirmed_inferred_relation"]:
        parts.append("")
        parts.append("No confirmed inferred relation.")
    return "\n".join(parts) + "\n"
