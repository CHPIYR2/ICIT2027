"""Rule proposer and deterministic baselines. Every method emits one row per candidate."""
from __future__ import annotations

from ebrl.ontology import Ontology
from ebrl.policy import blank_flags, decide
from ebrl.verifier import verify_row

METHODS = ("B0", "B1", "B2", "B3", "P0", "P1", "A_BINARY", "A_NO_CEILING", "A_UNTYPED", "A_ACK_OVERCLAIM")


def _base_row(candidate: dict, method: str, contract: dict) -> dict:
    return {
        "event_id": candidate["event_id"],
        "candidate_id": candidate["candidate_id"],
        "command_episode_id": candidate["command_episode_id"],
        "process_episode_id": candidate["process_episode_id"],
        "method": method,
        "contract_id": contract["contract_id"],
        "confidence": None,
    }


def _finish(raw: dict, candidate: dict, command: dict, process: dict, bundle: dict, contract: dict, ontology: Ontology, method: str, apply_verifier: bool) -> dict:
    row = _base_row(candidate, method, contract)
    row.update({
        "raw_disposition": raw["disposition"],
        "raw_level": raw["level"],
        "raw_flags": raw["flags"],
        "network_evidence_ids": raw["network_evidence_ids"],
        "process_evidence_ids": raw["process_evidence_ids"],
        "mapping_evidence_ids": raw["mapping_evidence_ids"],
        "support_evidence_ids": raw["support_evidence_ids"],
        "reason_code": raw["reason_code"],
        "row_valid": True,
    })
    if apply_verifier:
        checked = verify_row(row, candidate, command, process, bundle, contract, ontology)
        row.update(checked)
    else:
        row.update({
            "published_disposition": raw["disposition"],
            "published_level": raw["level"],
            "published_flags": raw["flags"],
            "verifier_action": "not_applied",
            "verifier_findings": [],
        })
    return row


def propose_event(bundle: dict, episodes: dict, manifest: dict, contract: dict, ontology: Ontology, method: str) -> list[dict]:
    if method not in METHODS:
        raise ValueError(f"Unknown method {method}")
    bundle = dict(bundle)
    bundle["_command_episodes"] = episodes["command_episodes"]
    commands = {item["episode_id"]: item for item in episodes["command_episodes"]}
    processes = {item["episode_id"]: item for item in episodes["process_episodes"]}
    nearest = _nearest_after(episodes, contract) if method == "B1" else set()
    rows = []
    for candidate in manifest["candidates"]:
        command = commands[candidate["command_episode_id"]]
        process = processes[candidate["process_episode_id"]]
        if method == "B0":
            raw = _abstain(command, process)
        elif method == "B1":
            raw = _nearest_row(candidate, command, process, nearest)
        elif method == "B2":
            raw = _asset_time(candidate, command, process, contract)
        elif method == "B3":
            raw = _asset_time_semantic(candidate, command, process, contract, ontology)
        else:
            raw = decide(candidate, command, process, bundle, contract, ontology)
            raw = _ablate(raw, command, method)
        rows.append(_finish(
            raw, candidate, command, process, bundle, contract, ontology, method, apply_verifier=(method == "P1"),
        ))
    return rows


def _abstain(command: dict, process: dict) -> dict:
    return {
        "disposition": "U",
        "level": "R0",
        "flags": blank_flags(),
        "reason_code": "ABSTAIN_ALL",
        "network_evidence_ids": [],
        "process_evidence_ids": [],
        "mapping_evidence_ids": [],
        "support_evidence_ids": [],
    }


def _nearest_after(episodes: dict, contract: dict) -> set[tuple[str, str]]:
    tau = float(contract["tau_max_s"])
    chosen = set()
    for command in episodes["command_episodes"]:
        best = None
        for process in episodes["process_episodes"]:
            delta = process["t_start"] - command["t_command"]
            if delta <= 0 or delta > tau:
                continue
            rank = (delta, process["episode_id"])
            if best is None or rank < best[0]:
                best = (rank, process["episode_id"])
        if best is not None:
            chosen.add((command["episode_id"], best[1]))
    return chosen


def _nearest_row(candidate, command, process, nearest: set[tuple[str, str]]) -> dict:
    linked = (command["episode_id"], process["episode_id"]) in nearest
    return {
        "disposition": "L" if linked else "U",
        "level": "R1" if linked else "R0",
        "flags": blank_flags(),
        "reason_code": "NEAREST_AFTER" if linked else "NOT_NEAREST_AFTER",
        "network_evidence_ids": command["evidence_ids"] if linked else [],
        "process_evidence_ids": process["evidence_ids"] if linked else [],
        "mapping_evidence_ids": [],
        "support_evidence_ids": [],
    }


def _asset_time(candidate, command, process, contract) -> dict:
    delta = process["t_start"] - command["t_command"]
    skew = float(contract["clock_skew_s"])
    tau = float(contract["tau_max_s"])
    linked = candidate["asset_relation"] == "same" and -skew <= delta <= tau and command.get("phase") != "select_only"
    return {
        "disposition": "L" if linked else "U",
        "level": "R2" if linked else "R0",
        "flags": blank_flags(),
        "reason_code": "ASSET_TIME" if linked else "ASSET_TIME_MISS",
        "network_evidence_ids": command["evidence_ids"] if linked else [],
        "process_evidence_ids": process["evidence_ids"] if linked else [],
        "mapping_evidence_ids": command["mapping_ids"] if linked else [],
        "support_evidence_ids": [],
    }


def _asset_time_semantic(candidate, command, process, contract, ontology: Ontology) -> dict:
    delta = process["t_start"] - command["t_command"]
    tau = float(contract["tau_max_s"])
    relation = ontology.relation(command.get("command_semantics"), process.get("variable"))
    expected = ontology.expected(command.get("command_semantics"), process.get("variable"))
    from ebrl.policy import _direction_status
    direction = _direction_status(expected, process.get("direction"))
    ids = {
        "network_evidence_ids": command["evidence_ids"],
        "process_evidence_ids": process["evidence_ids"],
        "mapping_evidence_ids": command["mapping_ids"],
        "support_evidence_ids": [],
        "flags": blank_flags(),
    }
    if candidate["asset_relation"] == "explicit_different" and abs(delta) <= tau:
        return {"disposition": "N", "level": "R0", "reason_code": "ASSET_CONTRADICTION", **ids}
    if candidate["asset_relation"] == "same" and relation == "incompatible":
        return {"disposition": "N", "level": "R0", "reason_code": "SEMANTIC_INCOMPATIBILITY", **ids}
    if candidate["asset_relation"] == "same" and relation == "compatible" and direction == "contradictory":
        return {"disposition": "N", "level": "R0", "reason_code": "DIRECTION_CONTRADICTION", **ids}
    if candidate["asset_relation"] == "same" and relation == "compatible" and delta < 0:
        return {"disposition": "N", "level": "R0", "reason_code": "TIME_ORDER_CONTRADICTION", **ids}
    linked = (
        command.get("phase") != "select_only"
        and candidate["asset_relation"] == "same"
        and relation == "compatible"
        and direction == "consistent"
        and 0 < delta <= tau
    )
    if linked:
        return {"disposition": "L", "level": "R2", "reason_code": "ASSET_TIME_SEMANTIC", **ids}
    if candidate["asset_relation"] == "unmapped" and 0 < delta <= tau:
        return {
            "disposition": "L",
            "level": "R1",
            "reason_code": "B3_TEMPORAL_ONLY",
            "network_evidence_ids": command["evidence_ids"],
            "process_evidence_ids": process["evidence_ids"],
            "mapping_evidence_ids": [],
            "support_evidence_ids": [],
            "flags": blank_flags(),
        }
    return {
        "disposition": "U",
        "level": "R0",
        "reason_code": "B3_INSUFFICIENT",
        "network_evidence_ids": [],
        "process_evidence_ids": [],
        "mapping_evidence_ids": [],
        "support_evidence_ids": [],
        "flags": blank_flags(),
    }


def _ablate(raw: dict, command: dict, method: str) -> dict:
    raw = dict(raw)
    raw["flags"] = dict(raw["flags"])
    if method == "A_BINARY" and raw["disposition"] == "U":
        raw["disposition"] = "N"
        raw["reason_code"] = "BINARY_FORCED_NONLINK"
    elif method == "A_NO_CEILING" and raw["disposition"] == "L" and raw["level"] in {"R1", "R2"}:
        raw["level"] = "R4"
        raw["flags"]["causal"] = True
        raw["flags"]["completion"] = True
        raw["reason_code"] = "NO_CEILING_OVERCLAIM"
    elif method == "A_UNTYPED" and raw["disposition"] == "L":
        raw["network_evidence_ids"] = (
            raw["network_evidence_ids"] + raw["process_evidence_ids"] + raw["mapping_evidence_ids"]
        )
        raw["process_evidence_ids"] = []
        raw["mapping_evidence_ids"] = []
    elif method == "A_ACK_OVERCLAIM" and raw["disposition"] == "L":
        raw["level"] = "R4"
        raw["flags"]["execution"] = True
        raw["flags"]["completion"] = True
        raw["flags"]["causal"] = True
        raw["reason_code"] = "ACK_PROMOTED_TO_COMPLETION"
    return raw
