"""Run the synthetic EBRL suite and write table-ready artifacts.

The numbers are synthetic challenge results. They are not Sherlock scores.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ebrl.baselines import propose_event
from ebrl.canonical import sha256_obj
from ebrl.candidates import enumerate_candidates
from ebrl.contract import load_contract, load_ontology
from ebrl.normalize import normalize
from ebrl.ontology import Ontology
from ebrl.pipeline import investigate
from ebrl.reference import overlay_independent_labels, policy_reference
from ebrl.scorer import align_event, paired_bootstrap, score_events
from ebrl.suite import build_suite
from ebrl.verifier import verify_row

RUN_METHODS = ("B0", "B1", "B2", "B3", "P0", "P1", "A_BINARY", "A_NO_CEILING", "A_UNTYPED", "A_ACK_OVERCLAIM")


def _match(artifact: dict, network_id: str, process_id: str) -> str | None:
    commands = {item["episode_id"]: item for item in artifact["episodes"]["command_episodes"]}
    processes = {item["episode_id"]: item for item in artifact["episodes"]["process_episodes"]}
    for candidate in artifact["candidate_manifest"]["candidates"]:
        command = commands[candidate["command_episode_id"]]
        process = processes[candidate["process_episode_id"]]
        if network_id in command["evidence_ids"] and process_id in process["evidence_ids"]:
            return candidate["candidate_id"]
    return None


def _representable(artifact: dict, network_id: str, process_id: str) -> bool:
    commands = artifact["episodes"]["command_episodes"]
    processes = artifact["episodes"]["process_episodes"]
    return any(network_id in item["evidence_ids"] for item in commands) and any(
        process_id in item["evidence_ids"] for item in processes
    )


def main() -> None:
    contract = load_contract()
    ontology_doc = load_ontology()
    cases = build_suite()
    out = ROOT / "results" / "ebrl-synthetic-v1"
    out.mkdir(parents=True, exist_ok=True)
    events_by_method = {method: [] for method in RUN_METHODS}
    verified_ack = []
    replay = []
    enumeration = {"representable": 0, "enumerated": 0}
    previews = []
    for case in cases:
        bundle = case["bundle"]
        artifact = investigate(bundle, contract, ontology_doc, method="P1")
        ontology = Ontology(ontology_doc, bundle.get("ontology_scopes"))
        episodes = artifact["episodes"]
        manifest = artifact["candidate_manifest"]
        reference = policy_reference(bundle, episodes, manifest, contract, ontology)
        labels = {}
        for label in case.get("labels", []):
            candidate_id = _match(artifact, label["network_evidence_id"], label["process_evidence_id"])
            if candidate_id:
                labels[candidate_id] = label
        reference = overlay_independent_labels(reference, labels)
        for item in case.get("labels", []) + case.get("universe_only", []):
            if _representable(artifact, item["network_evidence_id"], item["process_evidence_id"]):
                enumeration["representable"] += 1
                if _match(artifact, item["network_evidence_id"], item["process_evidence_id"]):
                    enumeration["enumerated"] += 1
        p0_rows = propose_event(bundle, episodes, manifest, contract, ontology, "P0")
        agree = 0
        for row, pair in zip(p0_rows, reference["pairs"]):
            if row["published_disposition"] == pair["v_star"] and row["published_level"] == pair["lambda_vis"]:
                agree += 1
        replay.append({"event_id": bundle["event_id"], "agreement": agree, "candidates": len(p0_rows)})
        for method in RUN_METHODS:
            rows = artifact["ledger"] if method == "P1" else propose_event(bundle, episodes, manifest, contract, ontology, method)
            events_by_method[method].append({
                "event_id": bundle["event_id"],
                "pairs": align_event(manifest["candidates"], rows, reference["pairs"], bundle),
            })
        ack_rows = propose_event(bundle, episodes, manifest, contract, ontology, "A_ACK_OVERCLAIM")
        bundle_for_verifier = dict(bundle)
        bundle_for_verifier["_command_episodes"] = episodes["command_episodes"]
        commands = {item["episode_id"]: item for item in episodes["command_episodes"]}
        processes = {item["episode_id"]: item for item in episodes["process_episodes"]}
        checked = []
        for row, candidate in zip(ack_rows, manifest["candidates"]):
            checked.append(verify_row(
                row,
                candidate,
                commands[candidate["command_episode_id"]],
                processes[candidate["process_episode_id"]],
                bundle_for_verifier,
                contract,
                ontology,
            ))
        verified_ack.append({
            "event_id": bundle["event_id"],
            "pairs": align_event(manifest["candidates"], [
                {**raw, **checked_row} for raw, checked_row in zip(ack_rows, checked)
            ], reference["pairs"], bundle),
        })
        primary = artifact["ledger"][0] if artifact["ledger"] else None
        previews.append({
            "event_id": bundle["event_id"],
            "candidate_count": manifest["candidate_count"],
            "published": None if primary is None else {
                "disposition": primary["published_disposition"],
                "level": primary["published_level"],
                "reason": primary["reason_code"],
                "flags": primary["published_flags"],
                "verifier_action": primary["verifier_action"],
            },
            "report": None if not artifact["report"]["statements"] else artifact["report"]["statements"][0]["text"],
            "artifact_sha256": artifact["artifact_sha256"],
        })
        (out / "cases").mkdir(exist_ok=True)
        (out / "cases" / f"{bundle['event_id']}.json").write_text(
            json.dumps({"ledger": artifact["ledger"], "report": artifact["report"], "freeze_sha256": manifest["freeze_sha256"]}, indent=2),
            encoding="utf-8",
        )
    scores = {method: score_events(events) for method, events in events_by_method.items()}
    scores["A_ACK_VERIFIED"] = score_events(verified_ack)
    contrasts = []
    for metric in ("UOLR", "EAP", "SOR", "NLR"):
        for left, right in (("P1", "B1"), ("P1", "B3"), ("P1", "P0")):
            contrasts.append(paired_bootstrap(
                events_by_method, left, right, metric,
                resamples=contract["bootstrap"]["resamples"],
                seed=contract["bootstrap"]["seed"],
            ))
    enumeration["recall"] = None if enumeration["representable"] == 0 else enumeration["enumerated"] / enumeration["representable"]
    replay_rate = sum(item["agreement"] for item in replay) / sum(item["candidates"] for item in replay)
    payload = {
        "kind": "synthetic_challenge_not_sherlock",
        "contract_sha256": contract["contract_sha256"],
        "ontology_sha256": contract["ontology_sha256"],
        "scores": scores,
        "contrasts": contrasts,
        "policy_replay_p0_agreement": replay_rate,
        "policy_replay_note": "P0 uses the same visible predicates as the policy reference. Agreement is a replay diagnostic, not factual accuracy.",
        "candidate_enumeration": enumeration,
        "previews": previews,
        "b4_status": "NOT_APPLICABLE",
        "b4_reason": "No independently labeled development pairs are available. Training on the policy rules would be circular.",
        "b5_b6_status": "BLOCKED_NOT_RUN",
        "llm_status": "BLOCKED_NOT_RUN",
    }
    payload["payload_sha256"] = sha256_obj({k: v for k, v in payload.items() if k != "payload_sha256"})
    (out / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "out": str(out / "summary.json"),
        "sha256": payload["payload_sha256"],
        "enumeration_recall": enumeration["recall"],
        "p0_replay_agreement": replay_rate,
        "P1_OLP": scores["P1"]["metrics"]["OLP"],
        "P1_UOLR": scores["P1"]["metrics"]["UOLR"],
        "B1_UOLR": scores["B1"]["metrics"]["UOLR"],
        "B3_UOLR": scores["B3"]["metrics"]["UOLR"],
        "P1_EAP": scores["P1"]["metrics"]["EAP"],
    }, indent=2))


if __name__ == "__main__":
    main()
