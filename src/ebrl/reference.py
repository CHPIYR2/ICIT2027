"""Evaluator-only reference construction.

Policy references replay the visible decision rules and are not operational
ground truth. Independent labels are supplied by the caller and are never
written back into the model-visible bundle.
"""
from __future__ import annotations

from ebrl.ontology import Ontology
from ebrl.policy import decide


def policy_reference(bundle: dict, episodes: dict, manifest: dict, contract: dict, ontology: Ontology) -> dict:
    visible = dict(bundle)
    visible["_command_episodes"] = episodes["command_episodes"]
    commands = {item["episode_id"]: item for item in episodes["command_episodes"]}
    processes = {item["episode_id"]: item for item in episodes["process_episodes"]}
    pairs = []
    for candidate in manifest["candidates"]:
        decision = decide(
            candidate,
            commands[candidate["command_episode_id"]],
            processes[candidate["process_episode_id"]],
            visible,
            contract,
            ontology,
        )
        pairs.append({
            "candidate_id": candidate["candidate_id"],
            "g": 0,
            "o_star": None,
            "v_star": decision["disposition"],
            "lambda_vis": decision["level"],
            "z_vis": decision["flags"],
            "source": "rule_derived_policy",
            "policy_reason": decision["reason_code"],
        })
    return {
        "event_id": bundle["event_id"],
        "reference_kind": "policy_silver",
        "factual_metrics": "NA",
        "pairs": pairs,
    }


def overlay_independent_labels(reference: dict, labels_by_candidate: dict[str, dict]) -> dict:
    updated = dict(reference)
    updated["pairs"] = []
    for pair in reference["pairs"]:
        item = dict(pair)
        label = labels_by_candidate.get(pair["candidate_id"])
        if label:
            item["g"] = int(label["g"])
            item["o_star"] = label["o_star"]
            item["source"] = label.get("source", "synthetic_independent")
        updated["pairs"].append(item)
    if any(pair["g"] == 1 for pair in updated["pairs"]):
        updated["reference_kind"] = "mixed_policy_and_synthetic_independent"
        updated["factual_metrics"] = "synthetic_independent_only"
    return updated
