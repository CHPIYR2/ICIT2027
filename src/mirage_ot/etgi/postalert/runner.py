"""Run fixed windows and variants from one protocol file into a new directory.

The output directory must not already exist, so a frozen run is never
overwritten. Every variant in one invocation shares the same code hash.
"""
from __future__ import annotations
import json
from pathlib import Path
from ..agent.ollama import OllamaClient
from ..evidence.index import open_indexed
from ..evidence.queries import EvidenceDB
from .evaluate import gold_facts, score_run
from .pipeline import export_lineage_bundle, prepare, write_run


def run_protocol(protocol_path: Path, out: Path, *, endpoint: str = "http://127.0.0.1:11434") -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if out.exists():
        raise FileExistsError(f"{out} exists; choose a new run directory")
    out.mkdir(parents=True)
    (out / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    llm = OllamaClient(protocol["model"], endpoint=endpoint)
    rows = []
    bundles = {}
    code_hashes = set()
    for case in protocol["cases"]:
        conn, meta = open_indexed(Path(case["db"]))
        db = EvidenceDB(conn, incident_start=float(meta["incident_start"]), incident_end=float(meta["incident_end"]))
        start, end = window(case, meta)
        background_start, background_end = background(case, meta, start, protocol["background_seconds"])
        db.incident_start, db.incident_end = start, end
        prepared = prepare(db, start, end, background_start=background_start, background_end=background_end,
                           limit=protocol.get("selection_limit", 24))
        gold = gold_facts(db, start, end, prepared)
        bundle = export_lineage_bundle(db, prepared["timeline"], prepared["lineage"])
        case_dir = out / case["name"]
        case_dir.mkdir()
        (case_dir / "evidence_audit_bundle.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
        bundles[case["name"]] = {key: bundle[key] for key in (
            "requested_count", "expected_with_parents", "exported_count", "missing_ids", "row_check_failures")}
        policy = {
            "window": [start, end],
            "background_requested_seconds": protocol["background_seconds"],
            "background_effective": [background_start, background_end],
            "clipped_to_indexed_start": background_start > start - protocol["background_seconds"],
            "background_status": prepared["selection"]["query"]["background_status"],
        }
        (case_dir / "window_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
        for variant in protocol["variants"]:
            run_id = f"{variant['level']}_{variant['claim_mode']}_{variant['num_predict']}"
            result = write_run(
                db, llm, prepared, case_dir / run_id, level=variant["level"], claim_mode=variant["claim_mode"],
                allow_salvage=False, num_predict=variant["num_predict"], num_ctx=protocol["num_ctx"],
                seed=protocol["seed"],
            )
            code_hashes.add(result["manifest"]["code_sha256"])
            scored = score_run(prepared, result, gold, db=db)
            rows.append({
                "case": case["name"], "run_id": run_id, **variant, **scored,
                "background_policy": policy,
                "stages": result["coverage"]["stages"],
                **result["trace"],
            })
            print(json.dumps({key: rows[-1][key] for key in (
                "case", "run_id", "model_claims", "published_verified_claims", "rejected_claims",
                "offline_audit_verified_claims", "confirmed_inferred_relations")}, default=str), flush=True)
        conn.close()
    summary = {
        "protocol": protocol,
        "code_sha256": sorted(code_hashes),
        "bundles": bundles,
        "rows": rows,
    }
    (out / "comparison.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def window(case: dict, meta: dict) -> tuple[float, float]:
    start = float(meta["incident_start"])
    end = float(meta["incident_end"])
    if case.get("window") == "preceding":
        return start - float(case["preceding_seconds"]), start
    return start, end


def background(case: dict, meta: dict, start: float, seconds: float) -> tuple[float, float]:
    """Fixed policy: the `seconds` before the window, clipped to the indexed range."""
    return max(start - seconds, float(meta["indexed_start"])), start
