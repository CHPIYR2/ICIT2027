"""Prepare a window, ask for an explanation, and publish only verified claims.

Rejected claims stay in `verification.json` and `rejected_claims.json` for
audit. They are never rendered into `report.md` as public report prose.
B0–B3 are unverified baselines: their raw claims are recorded in
`unverified_model_claims` and rendered under an explicit unverified heading.
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
    exposed_timeline, exposed_relations = _expose_connected(timeline, discovered["relations"], card_limit=10, relation_limit=8)
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
        "coverage": _coverage_summary(selection, timeline, exposed_timeline, [], lineage=lineage),
        "fixed_summary": {
            "timeline_events": len(timeline),
            "excluded_by_reason": selection["excluded_by_reason"],
            "earliest_events": earliest,
        },
    }


def _expose_connected(timeline: list[dict], relations: list[dict], *, card_limit: int = 10,
                      relation_limit: int = 8) -> tuple[list[dict], list[dict]]:
    cards = expose_timeline(timeline, limit=card_limit)
    rels = expose_relations(relations, cards, limit=relation_limit)
    return cards, rels


def run_explanation(db, llm, prepared: dict, *, level: str = "B4", claim_mode: str = "typed_refs",
                    allow_salvage: bool = False, num_predict: int = 512,
                    num_ctx: int = 8192, seed: int = 1) -> dict:
    model = explain(
        llm, prepared, level=level, claim_mode=claim_mode,
        allow_salvage=allow_salvage, num_predict=num_predict, num_ctx=num_ctx, seed=seed,
    )
    lineage = prepared.get("lineage") or {}
    if level == "B4":
        checked = verify_claims(db, model["claims"], prepared["relations"], prepared["timeline"], lineage=lineage)
        published = checked["verified"]
        unverified = []
    else:
        audited = verify_claims(db, model["claims"], prepared["relations"], prepared["timeline"], lineage=lineage)
        checked = {
            "verified": [],
            "rejected": [],
            "unverified_model_claims": model["claims"],
            "offline_audit_verified": audited["verified"],
            "offline_audit_rejected": audited["rejected"],
        }
        published = []
        unverified = model["claims"]
    coverage = _coverage_summary(
        prepared["selection"], prepared["timeline"], prepared["exposed_timeline"],
        published if level == "B4" else unverified, lineage=lineage,
    )
    coverage["stages"] = stage_coverage(
        prepared, chosen=model["claims"], published=published,
    )
    has_verified_claim = bool(published)
    minimum = level == "B4" and not has_verified_claim
    report = _report(
        prepared, model, checked, published, unverified=unverified,
        coverage=coverage, minimum=minimum, level=level,
    )
    return {
        "model": model,
        "verification": checked,
        "published_claims": published,
        "unverified_model_claims": unverified,
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
        "published_verified": len(result["published_claims"]),
        "unverified_raw_claims": len(result["unverified_model_claims"]),
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


def _coverage_summary(selection: dict, timeline: list[dict], exposed: list[dict],
                      claims: list[dict], *, lineage: dict[str, list[str]] | None = None) -> dict:
    selected_mod = _count_event_modalities(timeline)
    selected_roles = _count_event_roles(timeline)
    exposed_mod = _count_card_modalities(exposed)
    exposed_roles = _count_event_roles(exposed)
    ev_to_mod: dict[str, str] = {}
    ev_to_fact: dict[str, str] = {}
    for event in timeline:
        tid = event["timeline_id"]
        mod = (event.get("source") or {}).get("modality") or event.get("modality") or "unknown"
        ids = (lineage or {}).get(tid) or event.get("evidence_ids") or []
        for ev_id in ids:
            ev_to_mod[ev_id] = mod
            ev_to_fact[ev_id] = tid
    mention_mod: dict[str, int] = {}
    unique_ids_by_mod: dict[str, set[str]] = {}
    unique_facts_by_mod: dict[str, set[str]] = {}
    for claim in claims:
        for ev_id in claim.get("evidence_ids") or []:
            mod = ev_to_mod.get(ev_id, "unknown")
            mention_mod[mod] = mention_mod.get(mod, 0) + 1
            unique_ids_by_mod.setdefault(mod, set()).add(ev_id)
            if ev_id in ev_to_fact:
                unique_facts_by_mod.setdefault(mod, set()).add(ev_to_fact[ev_id])
    return {
        "available_by_modality": selection.get("available_by_modality") or {},
        "available_by_kind": selection.get("available_by_kind") or {},
        "selected_by_modality": selected_mod,
        "selected_by_role": selected_roles,
        "exposed_by_modality": exposed_mod,
        "exposed_by_role": exposed_roles,
        "cited_unique_evidence_by_modality": {k: len(v) for k, v in unique_ids_by_mod.items()},
        "cited_unique_facts_by_modality": {k: len(v) for k, v in unique_facts_by_mod.items()},
        "cited_mentions_by_modality": mention_mod,
        "cited_by_modality": {k: len(v) for k, v in unique_ids_by_mod.items()},
    }


def stage_coverage(prepared: dict, *, chosen: list[dict], published: list[dict]) -> dict:
    """Modality and role counts at available, selected, exposed, chosen, and published.

    `chosen` counts the fact and edge ids the model itself named; ids the system
    resolved from an anchor are not counted as model choices.
    """
    timeline = {event["timeline_id"]: event for event in prepared["timeline"]}
    edges = {edge["edge_id"]: edge for edge in prepared["relations"]}

    def facts_of(claims: list[dict]) -> tuple[list[str], list[str]]:
        fact_ids, edge_ids = [], []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            fact = claim.get("fact_id") or claim.get("timeline_id")
            if fact in timeline:
                fact_ids.append(fact)
            edge = claim.get("edge_id")
            if edge in edges:
                edge_ids.append(edge)
                fact_ids.extend(item for item in (edges[edge].get("source_fact_id"), edges[edge].get("target_fact_id"))
                                if item in timeline)
        return list(dict.fromkeys(fact_ids)), list(dict.fromkeys(edge_ids))

    def summarize(fact_ids: list[str], edge_ids: list[str] | None = None) -> dict:
        events = [timeline[tid] for tid in fact_ids]
        out = {
            "facts": len(events),
            "by_modality": _count_event_modalities(events),
            "by_role": _count_event_roles(events),
        }
        if edge_ids is not None:
            out["edges"] = len(edge_ids)
            out["edges_by_level"] = _count_by(edges[item].get("claim_level") for item in edge_ids)
        return out

    chosen_facts, chosen_edges = facts_of(chosen)
    published_facts, published_edges = facts_of(published)
    selection = prepared["selection"]
    return {
        "available": {
            "rows": sum((selection.get("available_by_modality") or {}).values()),
            "by_modality": selection.get("available_by_modality") or {},
            "by_kind": selection.get("available_by_kind") or {},
            "candidate_groups_by_kind": selection.get("candidate_groups_by_kind") or {},
        },
        "selected": summarize(list(timeline), list(edges)),
        "exposed": summarize(
            [card["timeline_id"] for card in prepared["exposed_timeline"] if card.get("timeline_id") in timeline],
            [edge["edge_id"] for edge in prepared["exposed_relations"] if edge.get("edge_id") in edges],
        ),
        "chosen_by_model": summarize(chosen_facts, chosen_edges),
        "published_verified": summarize(published_facts, published_edges),
    }


def export_lineage_bundle(db, timeline: list[dict], lineage: dict[str, list[str]], *, chunk: int = 100) -> dict:
    """Every lineage row plus parents, fetched in chunks below the query cap, with per-row checks."""
    requested = list(dict.fromkeys(item for ids in lineage.values() for item in ids))
    rows: dict[str, dict] = {}
    pending = list(requested)
    while pending:
        batch, pending = pending[:chunk], pending[chunk:]
        for row in db.get(batch)["rows"]:
            rows[row["evidence_id"]] = row
        parents = [row["parent_evidence_id"] for row in rows.values()
                   if row.get("parent_evidence_id") and row["parent_evidence_id"] not in rows
                   and row["parent_evidence_id"] not in pending]
        pending.extend(dict.fromkeys(parents))
    expected = set(requested) | {row["parent_evidence_id"] for row in rows.values() if row.get("parent_evidence_id")}
    missing = sorted(expected - set(rows))
    failures = []
    for event in timeline:
        tid = event["timeline_id"]
        members = [rows[item] for item in lineage.get(tid, []) if item in rows]
        parent_ids = {row["parent_evidence_id"] for row in members if row.get("parent_evidence_id")}
        kind = (event.get("source") or {}).get("kind")
        for row in members:
            if row["evidence_id"] in parent_ids and row["kind"] != kind:
                continue
            if row.get("entity") != event.get("entity"):
                failures.append({"timeline_id": tid, "evidence_id": row["evidence_id"], "reason": "entity_differs_from_fact"})
            if kind == "iec104_asdu" and row.get("ca_ioa") != event.get("ca_ioa"):
                failures.append({"timeline_id": tid, "evidence_id": row["evidence_id"], "reason": "ca_ioa_differs_from_fact"})
            if not (float(event["time"]) - 1e-9 <= row["timestamp"] <= float(event["time_end"]) + 1e-9):
                failures.append({"timeline_id": tid, "evidence_id": row["evidence_id"], "reason": "time_outside_fact_span"})
    return {
        "db_fingerprint": _db_fingerprint(db),
        "requested_count": len(requested),
        "expected_with_parents": len(expected),
        "exported_count": len(rows),
        "missing_ids": missing,
        "row_check_failures": failures,
        "rows": sorted(rows.values(), key=lambda row: (row["timestamp"], row["evidence_id"])),
    }


def _count_by(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


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


def _report(prepared, model, checked, published, *, unverified: list[dict], coverage: dict,
            minimum: bool, level: str) -> dict:
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
    confirmed_inferred = [
        claim for claim in published
        if claim.get("canonical_origin") == "inferred"
        and claim.get("canonical_claim_level") == "supported_inference"
        and claim.get("canonical_status") == "supported"
    ]
    if level == "B4":
        text = _minimum_text(observations, confirmed) if minimum or not published else _verified_claim_text(published)
    else:
        text = _unverified_claim_text(unverified) if unverified else "No model claims were emitted."
    return {
        "level": level,
        "claim_mode": model.get("claim_mode"),
        "verified_mode": level == "B4",
        "incident_start": prepared["incident_start"],
        "incident_end": prepared["incident_end"],
        "observations": observations,
        "confirmed_record_links": confirmed,
        "confirmed_inferred_relations": confirmed_inferred,
        "published_claims": published,
        "unverified_model_claims": unverified,
        "rejected_claim_count": len(checked.get("rejected") or []),
        "rejected_claims_audit_file": "rejected_claims.json",
        "model_abstained": model.get("abstain"),
        "partial_output": bool(model.get("partial_output")),
        "minimum_report": minimum,
        "coverage": coverage,
        "text": text,
        "no_confirmed_inferred_relation": len(confirmed_inferred) == 0,
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


def _verified_claim_text(claims: list[dict]) -> str:
    lines = ["Verified claims:"]
    for claim in claims:
        rendered = claim.get("rendered_text") or claim.get("verified_prose")
        if rendered:
            lines.append(f"- {rendered}")
    return "\n".join(lines)


def _unverified_claim_text(claims: list[dict]) -> str:
    lines = ["Unverified raw model claims (baseline output, not checked by verifier):"]
    for claim in claims:
        anchor = claim.get("fact_id") or claim.get("edge_id") or claim.get("statement") or claim.get("claim_type")
        ids = ", ".join(str(item) for item in (claim.get("evidence_ids") or [])[:4])
        suffix = f" ({ids})" if ids else ""
        lines.append(f"- [unverified] {anchor} level={claim.get('claim_level')}{suffix}.")
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
