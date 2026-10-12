"""Deterministic publication verifier.

The verifier may retain, downgrade, or suppress a proposal. It never deletes a
candidate, never turns insufficient evidence into a supported non-link, and
never reads evaluator-only labels. Matching its own rules is not factual truth.
"""
from __future__ import annotations

from ebrl.ontology import Ontology
from ebrl.policy import CONTRADICTION_REASONS, _direction_status, _is_competition_loser, blank_flags

LEVEL_RANK = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}
DISPOSITIONS = {"L", "N", "U"}


def _visible_index(bundle: dict) -> dict[str, str]:
    roles = {}
    for record in bundle.get("network_records", []):
        roles[record["evidence_id"]] = "network"
    for record in bundle.get("process_records", []):
        roles[record["evidence_id"]] = "process"
    for record in bundle.get("mappings", []):
        roles[record["evidence_id"]] = "mapping"
    for record in bundle.get("execution_records", []):
        roles[record["evidence_id"]] = record.get("role", "execution")
    for record in bundle.get("action_effect_records", []):
        roles[record["evidence_id"]] = record.get("role", "action_effect")
    return roles


def _copy_flags(flags: dict | None) -> dict:
    base = blank_flags()
    for name in base:
        base[name] = bool((flags or {}).get(name))
    return base


def verify_row(row: dict, candidate: dict, command: dict, process: dict, bundle: dict, contract: dict, ontology: Ontology) -> dict:
    published = dict(row)
    findings: list[str] = []
    roles = _visible_index(bundle)
    if not _schema_ok(row, candidate):
        return _invalid(published, ["SCHEMA_OR_CANDIDATE_MISMATCH"])
    cited = {
        "network": list(row.get("network_evidence_ids") or []),
        "process": list(row.get("process_evidence_ids") or []),
        "mapping": list(row.get("mapping_evidence_ids") or []),
        "support": list(row.get("support_evidence_ids") or []),
    }
    for role, identifiers in cited.items():
        for evidence_id in identifiers:
            actual = roles.get(evidence_id)
            if actual is None:
                return _invalid(published, ["HALLUCINATED_OR_INVISIBLE_EVIDENCE"])
            if role == "support":
                if actual not in {"operational_response", "action_effect", "security_attribution"}:
                    return _invalid(published, ["EVIDENCE_ROLE_MISMATCH"])
            elif actual != role:
                return _invalid(published, ["EVIDENCE_ROLE_MISMATCH"])
    disposition = row["raw_disposition"]
    level = row["raw_level"]
    flags = _copy_flags(row.get("raw_flags"))
    action = "retain"
    if disposition == "U":
        published.update(_published("U", "R0", blank_flags(), "retain", []))
        return published
    if disposition == "N" and row.get("reason_code") not in CONTRADICTION_REASONS:
        findings.append("NONLINK_WITHOUT_CONTRADICTION")
        published.update(_published("U", "R0", blank_flags(), "suppress", findings))
        return published
    if disposition == "N" and not _contradiction_holds(row.get("reason_code"), candidate, command, process, contract, ontology):
        findings.append("CONTRADICTION_PREDICATE_FAILED")
        published.update(_published("U", "R0", blank_flags(), "suppress", findings))
        return published
    if disposition == "N":
        published.update(_published("N", "R0", blank_flags(), "retain", findings))
        return published

    support_roles = {evidence_id: roles[evidence_id] for evidence_id in cited["support"]}
    has_operational = any(role == "operational_response" for role in support_roles.values())
    has_effect = any(role == "action_effect" for role in support_roles.values())
    has_security = any(role == "security_attribution" for role in support_roles.values())
    ack_ids = set(command.get("confirmation_ids") or [])
    cites_ack = bool(set(cited["support"]).intersection(ack_ids) or set(cited["network"]).intersection(ack_ids))
    if cites_ack and (flags["execution"] or flags["completion"] or level in {"R3", "R4"}):
        findings.append("ACK_USED_AS_EXECUTION")
    if flags["execution"] and not has_operational:
        flags["execution"] = False
        findings.append("EXECUTION_WITHOUT_OPERATIONAL_RESPONSE")
        action = "downgrade"
    if (flags["completion"] or flags["causal"]) and not has_effect:
        flags["completion"] = False
        flags["causal"] = False
        findings.append("COMPLETION_WITHOUT_ACTION_EFFECT")
        action = "downgrade"
    if flags["security"] and (not has_security or LEVEL_RANK[level] <= 2):
        flags["security"] = False
        findings.append("SECURITY_FLAG_NOT_WARRANTED")
        action = "downgrade"
    warranted = _warranted_level(
        candidate, command, process, bundle, contract, ontology, has_operational, has_effect, cited,
    )
    if warranted is None:
        findings.append("LINK_NOT_WARRANTED")
        published.update(_published("U", "R0", blank_flags(), "suppress", findings))
        return published
    if LEVEL_RANK[level] > LEVEL_RANK[warranted]:
        findings.append("LEVEL_ABOVE_VISIBLE_CEILING")
        level = warranted
        action = "downgrade"
    if level == "R4" and not has_effect:
        level = "R3" if has_operational else ("R2" if LEVEL_RANK[warranted] >= 2 else "R1")
        flags["completion"] = False
        flags["causal"] = False
        findings.append("R4_WITHOUT_ACTION_EFFECT")
        action = "downgrade"
    if level == "R3" and not has_operational:
        level = "R2" if LEVEL_RANK[warranted] >= 2 else "R1"
        flags["execution"] = False
        findings.append("R3_WITHOUT_OPERATIONAL_RESPONSE")
        action = "downgrade"
    if LEVEL_RANK[level] <= 2:
        flags["execution"] = False
        flags["completion"] = False
        flags["causal"] = False
        flags["security"] = False
    if level == "R1" and not (cited["network"] and cited["process"]):
        findings.append("R1_PATH_INCOMPLETE")
        published.update(_published("U", "R0", blank_flags(), "suppress", findings))
        return published
    published.update(_published(disposition, level, flags, action if findings else "retain", findings))
    return published


def _schema_ok(row: dict, candidate: dict) -> bool:
    required = ("candidate_id", "command_episode_id", "process_episode_id", "raw_disposition", "raw_level", "reason_code")
    if any(name not in row for name in required):
        return False
    if row["raw_disposition"] not in DISPOSITIONS or row["raw_level"] not in LEVEL_RANK:
        return False
    return (
        row["candidate_id"] == candidate["candidate_id"]
        and row["command_episode_id"] == candidate["command_episode_id"]
        and row["process_episode_id"] == candidate["process_episode_id"]
    )


def _published(disposition: str, level: str, flags: dict, action: str, findings: list[str]) -> dict:
    return {
        "row_valid": True,
        "published_disposition": disposition,
        "published_level": level,
        "published_flags": flags,
        "verifier_action": action,
        "verifier_findings": findings,
    }


def _invalid(row: dict, findings: list[str]) -> dict:
    row = dict(row)
    row.update({
        "row_valid": False,
        "published_disposition": None,
        "published_level": None,
        "published_flags": blank_flags(),
        "verifier_action": "invalid",
        "verifier_findings": findings,
    })
    return row


def _time_after(process: dict, command: dict, contract: dict) -> bool:
    return process["t_start"] - command["t_command"] > float(contract["clock_skew_s"])


def _contradiction_holds(reason: str, candidate: dict, command: dict, process: dict, contract: dict, ontology: Ontology) -> bool:
    delta = process["t_start"] - command["t_command"]
    skew = float(contract["clock_skew_s"])
    tau = float(contract["tau_max_s"])
    if reason == "ASSET_CONTRADICTION":
        return candidate["asset_relation"] == "explicit_different" and abs(delta) <= tau
    if reason == "SEMANTIC_INCOMPATIBILITY":
        return candidate["asset_relation"] == "same" and ontology.relation(
            command.get("command_semantics"), process.get("variable")
        ) == "incompatible"
    if reason == "DIRECTION_CONTRADICTION":
        return candidate["asset_relation"] == "same" and process.get("quality_ok") and delta >= -skew
    if reason == "TIME_ORDER_CONTRADICTION":
        return candidate["asset_relation"] == "same" and process.get("quality_ok") and delta < -skew
    return False


def _warranted_level(candidate, command, process, bundle, contract, ontology, has_operational, has_effect, cited) -> str | None:
    if command.get("phase") == "select_only":
        return None
    if not process.get("quality_ok") or process.get("stale"):
        return None
    delta = process["t_start"] - command["t_command"]
    skew = float(contract["clock_skew_s"])
    tau = float(contract["tau_max_s"])
    if _is_competition_loser(command, process, bundle, contract, ontology, delta, skew):
        return None
    if abs(delta) > tau and candidate["asset_relation"] not in {"same", "neighborhood"}:
        return None
    relation = ontology.relation(command.get("command_semantics"), process.get("variable"))
    expected = ontology.expected(command.get("command_semantics"), process.get("variable"))
    direction = _direction_status(expected, process.get("direction"))
    temporal = cited["network"] and cited["process"] and abs(delta) <= tau and delta >= -skew
    bounded = (
        candidate["asset_relation"] == "same"
        and relation == "compatible"
        and direction == "consistent"
        and delta > skew
        and cited["network"]
        and cited["process"]
        and cited["mapping"]
        and not (
            command.get("context")
            and process.get("context")
            and command.get("variable") == process.get("variable")
            and command.get("context") != process.get("context")
        )
    )
    if bounded and has_effect:
        return "R4"
    if bounded and has_operational:
        return "R3"
    if bounded:
        return "R2"
    if temporal:
        return "R1"
    return None
