"""End-to-end Incident Reconstruction Engine (Phases 1-4).

Given an indexed window DB (and optional LLM client), executes:
1. Phase 1 (`reconstruct_transactions`): IEC-104 protocol transaction reconstruction.
2. Phase 2 (`build_temporal_event_graph`): Event-level temporal graph with N-N, P-P, N-P edges.
3. Phase 3 (`reconstruct_storylines`): Source-deduplicated bounded beam search storylines.
   Without a control command, event anchors (`discover_event_anchors`) enter the graph
   and root behavioral storylines.
4. Phase 4 (`run_llm_explanation` + `build_investigation_report`): Typed-reference LLM
   explanation checked by `verify_claims` and rendered into `investigation_report.md`.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from ..graph.export import write_graph
from ..postalert.pipeline import _db_fingerprint, export_lineage_bundle, prepare
from .anchors import discover_event_anchors
from .behavior import audit_anchor_lineage
from .consistency import build_lineage_consistency_record, check_quality_consistency
from .event_graph import build_temporal_event_graph
from .report import apply_quality_consistency, build_investigation_report, run_llm_explanation
from .storyline import reconstruct_storylines
from .synthesis import synthesize_incident_scenario
from .transactions import reconstruct_transactions


def reconstruct_incident(
    db,
    start: float,
    end: float,
    *,
    background_start: float | None = None,
    background_end: float | None = None,
    llm=None,
    selection_limit: int = 24,
    num_predict: int = 512,
    num_ctx: int = 8192,
    seed: int = 1,
    out_dir: Path | None = None,
) -> dict:
    if out_dir is not None and out_dir.exists():
        raise FileExistsError(f"{out_dir} already exists; refusing to overwrite")

    bg_end = start if background_end is None else background_end
    bg_start = max(start - 15.0, 0.0) if background_start is None else background_start

    prepared = prepare(
        db, start, end, background_start=bg_start, background_end=bg_end, limit=selection_limit,
    )
    tx_result = reconstruct_transactions(db, start, end)
    anchor_result = discover_event_anchors(
        db, start, end, background_start=bg_start, transactions=tx_result.get("transactions"),
    )
    behavioral_mode = not tx_result.get("transactions")
    anchor_result["behavioral_mode"] = behavioral_mode
    eg_result = build_temporal_event_graph(
        prepared["timeline"], prepared["lineage"], tx_result,
        behavioral_anchors=anchor_result["anchors"] if behavioral_mode else None,
    )
    sl_result = reconstruct_storylines(eg_result, tx_result)
    incident_synthesis = synthesize_incident_scenario(
        incident_start=start,
        incident_end=end,
        tx_result=tx_result,
        anchor_result=anchor_result,
        event_graph=eg_result,
        storyline_result=sl_result,
    )
    explanation = run_llm_explanation(
        db,
        llm,
        incident_start=start,
        incident_end=end,
        tx_result=tx_result,
        event_graph=eg_result,
        storyline_result=sl_result,
        num_predict=num_predict,
        num_ctx=num_ctx,
        seed=seed,
    )
    report = build_investigation_report(
        incident_start=start,
        incident_end=end,
        tx_result=tx_result,
        event_graph=eg_result,
        storyline_result=sl_result,
        explanation=explanation,
        anchor_result=anchor_result,
        incident_synthesis=incident_synthesis,
    )
    placed = eg_result["behavioral_anchor_facts"]
    behavioral_fids = {fid for entry in placed.values() for fid in entry.values() if fid}
    lineage_bundle = export_lineage_bundle(
        db, [n for n in eg_result["nodes"] if n["fact_id"] not in behavioral_fids], eg_result["fact_lineage"],
    )
    lineage_bundle["behavioral_anchor_lineage"] = audit_anchor_lineage(db, anchor_result["anchors"], placed)
    lineage_consistency = build_lineage_consistency_record(lineage_bundle)
    quality_consistency = check_quality_consistency(
        tx_result, eg_result, sl_result, report,
        anchor_result=anchor_result,
        incident_synthesis=incident_synthesis,
    )
    report = apply_quality_consistency(report, quality_consistency, lineage_consistency)
    manifest = reconstruction_manifest(
        db,
        incident_start=start,
        incident_end=end,
        background_start=bg_start,
        background_end=bg_end,
        selection_limit=selection_limit,
        model=explanation.get("model"),
        num_predict=num_predict,
        num_ctx=num_ctx,
        seed=seed,
    )

    public_event_graph = {
        k: v for k, v in eg_result.items() if k not in ("graph_object", "fact_lineage")
    }

    if out_dir is not None:
        out_dir.mkdir(parents=True)
        (out_dir / "transactions.json").write_text(
            json.dumps(tx_result, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "event_graph.json").write_text(
            json.dumps(public_event_graph, indent=2, default=str), encoding="utf-8",
        )
        write_graph(eg_result["graph_object"], out_dir)
        (out_dir / "storylines.json").write_text(
            json.dumps(sl_result, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "event_anchors.json").write_text(
            json.dumps(anchor_result, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "behavioral_storylines.json").write_text(
            json.dumps(
                [s for s in sl_result["storylines"] if s.get("storyline_kind") == "behavioral"],
                indent=2, default=str,
            ),
            encoding="utf-8",
        )
        (out_dir / "unresolved_branches.json").write_text(
            json.dumps(sl_result["unresolved_branches"], indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "incident_synthesis.json").write_text(
            json.dumps(incident_synthesis, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "lineage.json").write_text(
            json.dumps(eg_result["fact_lineage"], indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "evidence_audit_bundle.json").write_text(
            json.dumps(lineage_bundle, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "llm_explanation.json").write_text(
            json.dumps(explanation, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "verification.json").write_text(
            json.dumps(explanation["verification"], indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "investigation_report.json").write_text(
            json.dumps({k: v for k, v in report.items() if k != "markdown"}, indent=2, default=str),
            encoding="utf-8",
        )
        (out_dir / "investigation_report.md").write_text(
            report["markdown"], encoding="utf-8",
        )
        (out_dir / "quality_consistency.json").write_text(
            json.dumps(quality_consistency, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "lineage_consistency.json").write_text(
            json.dumps(lineage_consistency, indent=2, default=str), encoding="utf-8",
        )
        (out_dir / "run_manifest.json").write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8",
        )

    return {
        "manifest": manifest,
        "transactions": tx_result,
        "event_anchors": anchor_result,
        "event_graph": public_event_graph,
        "storylines": sl_result,
        "incident_synthesis": incident_synthesis,
        "lineage_bundle_summary": {
            k: lineage_bundle[k]
            for k in ("requested_count", "expected_with_parents", "exported_count", "missing_ids", "row_check_failures")
        } | {"behavioral_anchor_lineage": lineage_bundle["behavioral_anchor_lineage"]},
        "explanation": explanation,
        "report": report,
        "quality_consistency": quality_consistency,
        "lineage_consistency": lineage_consistency,
    }


def reconstruction_manifest(db, **config) -> dict:
    recon_dir = Path(__file__).resolve().parent
    post_dir = recon_dir.parent / "postalert"
    digest = hashlib.sha256()
    file_hashes = {}
    for folder in (post_dir, recon_dir):
        for path in sorted(folder.glob("*.py")):
            rel = f"{folder.name}/{path.name}"
            data = path.read_bytes()
            file_hashes[rel] = hashlib.sha256(data).hexdigest()
            digest.update(rel.encode("utf-8"))
            digest.update(data)
    evidence_digest = hashlib.sha256()
    evidence_hashes = {}
    for path in sorted((recon_dir.parent / "evidence").glob("*.py")):
        rel = f"evidence/{path.name}"
        data = path.read_bytes()
        evidence_hashes[rel] = hashlib.sha256(data).hexdigest()
        evidence_digest.update(rel.encode("utf-8"))
        evidence_digest.update(data)
    git_commit, dirty_sha = _git_state(recon_dir)
    config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "git_commit": git_commit,
        "git_dirty_diff_sha256": dirty_sha,
        "code_sha256": digest.hexdigest(),
        "module_hashes": file_hashes,
        "evidence_code_sha256": evidence_digest.hexdigest(),
        "evidence_module_hashes": evidence_hashes,
        "config": config,
        "config_sha256": config_sha,
        "db_fingerprint": _db_fingerprint(db),
    }


def _git_state(cwd: Path) -> tuple[str, str]:
    try:
        repo_root = cwd.parents[3]
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        diff = subprocess.check_output(
            ["git", "diff", "HEAD", "--", "src/mirage_ot/etgi/postalert", "src/mirage_ot/etgi/reconstruction",
             "src/mirage_ot/etgi/evidence"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
        return commit, hashlib.sha256(diff).hexdigest()
    except Exception:
        return "unknown", "unknown"
