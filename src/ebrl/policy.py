"""Visible-evidence relation policy.

This module decides the strongest wording supported by a model-visible bundle.
It does not read evaluator-only labels. A caller that reuses these predicates to
build a silver reference must label that reference as rule-derived policy.
"""
from __future__ import annotations

from ebrl.ontology import Ontology

FLAGS = ("execution", "completion", "causal", "security")
CONTRADICTION_REASONS = frozenset({
    "TIME_ORDER_CONTRADICTION",
    "ASSET_CONTRADICTION",
    "SEMANTIC_INCOMPATIBILITY",
    "DIRECTION_CONTRADICTION",
})


def blank_flags() -> dict:
    return {name: False for name in FLAGS}


def _time_class(delta: float, skew: float) -> str:
    if delta > skew:
        return "after"
    if delta < -skew:
        return "reverse"
    return "within_skew"


def _direction_status(expected: str | None, direction: str | None) -> str:
    if expected is None or direction is None:
        return "unknown"
    consistent = {
        ("to_false", "to_false"),
        ("to_true", "to_true"),
        ("decrease", "decrease"),
        ("increase", "increase"),
    }
    contradictory = {
        ("to_false", "to_true"),
        ("to_true", "to_false"),
        ("decrease", "increase"),
        ("increase", "decrease"),
    }
    if (expected, direction) in consistent:
        return "consistent"
    if (expected, direction) in contradictory:
        return "contradictory"
    return "unknown"


def _ids(values: list[str], visible: set[str]) -> list[str]:
    return [value for value in values if value in visible]


def _linked(records: list[dict], command: dict, process: dict, role: str) -> list[str]:
    found = []
    for record in records:
        if record.get("role") != role:
            continue
        command_ok = record.get("command_episode_id") in {None, command["episode_id"]} and (
            record.get("command_episode_id") == command["episode_id"]
            or (record.get("ca"), record.get("ioa")) == (command.get("ca"), command.get("ioa"))
        )
        process_ok = True
        if role == "action_effect":
            process_ok = record.get("process_episode_id") in {None, process["episode_id"]} and (
                record.get("process_episode_id") == process["episode_id"]
                or record.get("asset_id") == process.get("asset_id")
            )
        if command_ok and process_ok:
            found.append(record["evidence_id"])
    return found


def decide(candidate: dict, command: dict, process: dict, bundle: dict, contract: dict, ontology: Ontology) -> dict:
    visible = set()
    for key in ("network_records", "process_records", "mappings", "execution_records", "action_effect_records"):
        for record in bundle.get(key, []):
            visible.add(record["evidence_id"])
    skew = float(contract["clock_skew_s"])
    tau = float(contract["tau_max_s"])
    delta = process["t_start"] - command["t_command"]
    time_class = _time_class(delta, skew)
    relation = candidate["asset_relation"]
    semantics = ontology.relation(command.get("command_semantics"), process.get("variable"))
    expected = ontology.expected(command.get("command_semantics"), process.get("variable"))
    direction = _direction_status(expected, process.get("direction"))
    context_collision = bool(
        command.get("context")
        and process.get("context")
        and command.get("variable")
        and command.get("variable") == process.get("variable")
        and command.get("context") != process.get("context")
    )
    network_ids = _ids(command.get("evidence_ids", []), visible)
    process_ids = _ids(process.get("evidence_ids", []), visible)
    mapping_ids = _ids(command.get("mapping_ids", []), visible)
    operational_ids = _ids(
        _linked(bundle.get("execution_records", []), command, process, "operational_response"),
        visible,
    )
    effect_ids = _ids(
        _linked(bundle.get("action_effect_records", []), command, process, "action_effect"),
        visible,
    )
    flags = blank_flags()
    support_ids: list[str] = []

    def row(disposition: str, level: str, reason: str) -> dict:
        return {
            "disposition": disposition,
            "level": level,
            "flags": dict(flags),
            "reason_code": reason,
            "network_evidence_ids": network_ids,
            "process_evidence_ids": process_ids,
            "mapping_evidence_ids": mapping_ids,
            "support_evidence_ids": support_ids,
            "confidence": None,
        }

    if command.get("phase") == "select_only":
        return row("U", "R0", "SELECT_WITHOUT_OPERATE")
    if relation == "explicit_different" and abs(delta) <= tau:
        return row("N", "R0", "ASSET_CONTRADICTION")
    if context_collision and relation == "same":
        return row("U", "R0", "CONTEXT_ALIAS_COLLISION")
    if relation == "same" and semantics == "incompatible":
        return row("N", "R0", "SEMANTIC_INCOMPATIBILITY")
    if (
        relation == "same"
        and semantics == "compatible"
        and direction == "contradictory"
        and process.get("quality_ok")
        and time_class != "reverse"
    ):
        return row("N", "R0", "DIRECTION_CONTRADICTION")
    if relation == "same" and semantics == "compatible" and time_class == "reverse" and process.get("quality_ok"):
        return row("N", "R0", "TIME_ORDER_CONTRADICTION")
    if not process.get("quality_ok") or process.get("stale"):
        return row("U", "R0", "STALE_OR_BAD_QUALITY")
    if _is_competition_loser(command, process, bundle, contract, ontology, delta, skew):
        return row("U", "R0", "COMPETING_COMMAND")
    if relation == "neighborhood":
        return row("U", "R0", "INDIRECT_PROPAGATION")
    if relation == "unmapped":
        if time_class in {"after", "within_skew"} and abs(delta) <= tau:
            reason = "SUFFICIENT_TEMPORAL_LINK" if time_class == "after" else "CLOCK_COOC_ORDER_UNRESOLVED"
            return row("L", "R1", reason)
        return row("U", "R0", "INSUFFICIENT_EVIDENCE")
    if semantics == "compatible" and direction == "consistent" and time_class == "after":
        level = "R2"
        reason = "SUFFICIENT_BOUNDED_ASSOCIATION"
        if operational_ids:
            level = "R3"
            reason = "SUFFICIENT_OPERATIONAL_RESPONSE"
            flags["execution"] = True
            support_ids.extend(operational_ids)
        if effect_ids:
            level = "R4"
            reason = "SUFFICIENT_ACTION_EFFECT"
            flags["completion"] = True
            flags["causal"] = True
            support_ids.extend(effect_ids)
            if operational_ids:
                flags["execution"] = True
        return row("L", level, reason)
    if semantics == "compatible" and direction == "consistent" and time_class == "within_skew":
        return row("L", "R1", "CLOCK_COOC_ORDER_UNRESOLVED")
    if time_class in {"after", "within_skew"} and abs(delta) <= tau:
        reason = "SUFFICIENT_TEMPORAL_LINK" if time_class == "after" else "CLOCK_COOC_ORDER_UNRESOLVED"
        return row("L", "R1", reason)
    return row("U", "R0", "INSUFFICIENT_EVIDENCE")


def _is_competition_loser(command, process, bundle, contract, ontology: Ontology, delta: float, skew: float) -> bool:
    if command.get("asset_id") is None:
        return False
    if ontology.relation(command.get("command_semantics"), process.get("variable")) != "compatible":
        return False
    for other in bundle.get("_command_episodes", []):
        if other["episode_id"] == command["episode_id"]:
            continue
        if other.get("asset_id") != command.get("asset_id"):
            continue
        if other.get("phase") == "select_only":
            continue
        if ontology.relation(other.get("command_semantics"), process.get("variable")) != "compatible":
            continue
        other_delta = process["t_start"] - other["t_command"]
        if other_delta <= skew:
            continue
        if abs(other_delta) + 1e-9 < abs(delta):
            return True
    return False
