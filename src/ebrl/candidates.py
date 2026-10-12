"""Permissive command–telemetry candidate enumeration over episodes."""
from __future__ import annotations

from ebrl.canonical import sha256_obj, short_id

STRATUM_PRIORITY = (
    "reverse_time",
    "near_time_wrong_asset",
    "competing_command",
    "mapped_incompatible",
    "mapped_compatible",
    "indirect_or_unmapped",
)


def _asset_relation(command: dict, process: dict, neighborhood: set[frozenset[str]]) -> str:
    left, right = command.get("asset_id"), process.get("asset_id")
    if not left or not right:
        return "unmapped"
    if left == right:
        return "same"
    if frozenset((left, right)) in neighborhood:
        return "neighborhood"
    return "explicit_different"


def _stratum(relation: str, delta: float, skew: float, tau: float, compatible: str, competing: bool) -> str:
    if delta < -skew and abs(delta) <= tau:
        return "reverse_time"
    if relation == "explicit_different" and abs(delta) <= tau:
        return "near_time_wrong_asset"
    if competing:
        return "competing_command"
    if relation == "same" and compatible == "incompatible":
        return "mapped_incompatible"
    if relation == "same" and compatible == "compatible":
        return "mapped_compatible"
    return "indirect_or_unmapped"


def enumerate_candidates(bundle: dict, episodes: dict, contract: dict, ontology) -> dict:
    neighborhood = {
        frozenset(pair)
        for pair in bundle.get("asset_neighborhood", [])
        if len(pair) == 2
    }
    commands = episodes["command_episodes"]
    processes = episodes["process_episodes"]
    asset_counts: dict[str, int] = {}
    for command in commands:
        if command.get("asset_id"):
            asset_counts[command["asset_id"]] = asset_counts.get(command["asset_id"], 0) + 1
    skew = float(contract["clock_skew_s"])
    tau = float(contract["tau_max_s"])
    rows = []
    for command in commands:
        for process in processes:
            delta = process["t_start"] - command["t_command"]
            relation = _asset_relation(command, process, neighborhood)
            time_near = abs(delta) <= tau
            if not time_near and relation not in {"same", "neighborhood"}:
                continue
            compatible = ontology.relation(command.get("command_semantics"), process.get("variable"))
            competing = relation == "same" and asset_counts.get(command.get("asset_id"), 0) > 1
            stratum = _stratum(relation, delta, skew, tau, compatible, competing)
            identity = {
                "event_id": bundle["event_id"],
                "command_episode_id": command["episode_id"],
                "process_episode_id": process["episode_id"],
            }
            rows.append({
                "candidate_id": short_id("c", identity),
                "event_id": bundle["event_id"],
                "command_episode_id": command["episode_id"],
                "process_episode_id": process["episode_id"],
                "delta_t_s": delta,
                "asset_relation": relation,
                "stratum": stratum,
                "sampling_hash": sha256_obj({
                    "seed": contract["sampling_seed"],
                    **identity,
                    "stratum": stratum,
                }),
            })
    rows.sort(key=lambda item: item["candidate_id"])
    cap = int(contract.get("candidate_cap") or 0)
    capped = False
    if cap and len(rows) > cap:
        capped = True
        quotas = contract.get("stratum_quotas") or {}
        kept = []
        for stratum in STRATUM_PRIORITY:
            group = [row for row in rows if row["stratum"] == stratum]
            group.sort(key=lambda item: item["sampling_hash"])
            quota = int(quotas.get(stratum, 0))
            kept.extend(group[:quota] if quota else group)
        kept = kept[:cap]
        rows = sorted(kept, key=lambda item: item["candidate_id"])
    manifest = {
        "event_id": bundle["event_id"],
        "contract_id": contract["contract_id"],
        "candidate_count": len(rows),
        "capped": capped,
        "candidates": rows,
    }
    manifest["freeze_sha256"] = sha256_obj(manifest)
    return manifest
