"""Event investigation entry point. Evaluator references are not an input."""
from __future__ import annotations

import time

from ebrl.baselines import propose_event
from ebrl.canonical import sha256_obj
from ebrl.candidates import enumerate_candidates
from ebrl.contract import assert_bundle_visible
from ebrl.normalize import normalize
from ebrl.ontology import Ontology
from ebrl.report import render_report


def investigate(bundle: dict, contract: dict, ontology_doc: dict, method: str = "P1") -> dict:
    assert_bundle_visible(bundle)
    started = time.perf_counter()
    ontology = Ontology(ontology_doc, bundle.get("ontology_scopes"))
    episodes = normalize(bundle, contract)
    manifest = enumerate_candidates(bundle, episodes, contract, ontology)
    rows = propose_event(bundle, episodes, manifest, contract, ontology, method)
    if len(rows) != len(manifest["candidates"]):
        raise RuntimeError("Ledger does not contain exactly one row per candidate")
    report = render_report(bundle, rows)
    elapsed = time.perf_counter() - started
    artifact = {
        "event_id": bundle["event_id"],
        "method": method,
        "contract_id": contract["contract_id"],
        "contract_sha256": contract.get("contract_sha256"),
        "episodes": episodes,
        "candidate_manifest": manifest,
        "ledger": rows,
        "report": report,
        "runtime_seconds": elapsed,
        "llm_used": False,
    }
    artifact["artifact_sha256"] = sha256_obj({
        "ledger": rows,
        "freeze_sha256": manifest["freeze_sha256"],
        "method": method,
    })
    return artifact
