"""Independent scorer.

Factual ratios use only g=1 labels. Policy ratios use the visible contract.
A policy match is not counted as operational truth.
"""
from __future__ import annotations

import random

from ebrl.policy import FLAGS

LEVEL_RANK = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}


def _ratio(numerator: int, denominator: int) -> dict:
    value = None if denominator == 0 else numerator / denominator
    return {"numerator": numerator, "denominator": denominator, "value": value}


def _flags_within(predicted: dict, allowed: dict) -> bool:
    return all(not predicted.get(name) or allowed.get(name) for name in FLAGS)


def path_ok(row: dict, bundle: dict) -> bool:
    if not row.get("row_valid"):
        return False
    roles = {}
    for record in bundle.get("network_records", []):
        roles[record["evidence_id"]] = "network"
    for record in bundle.get("process_records", []):
        roles[record["evidence_id"]] = "process"
    for record in bundle.get("mappings", []):
        roles[record["evidence_id"]] = "mapping"
    for record in bundle.get("execution_records", []):
        roles[record["evidence_id"]] = record.get("role")
    for record in bundle.get("action_effect_records", []):
        roles[record["evidence_id"]] = record.get("role")
    groups = {
        "network": row.get("network_evidence_ids") or [],
        "process": row.get("process_evidence_ids") or [],
        "mapping": row.get("mapping_evidence_ids") or [],
    }
    for role, identifiers in groups.items():
        for evidence_id in identifiers:
            if roles.get(evidence_id) != role:
                return False
    support = row.get("support_evidence_ids") or []
    for evidence_id in support:
        if roles.get(evidence_id) not in {"operational_response", "action_effect", "security_attribution"}:
            return False
    level = row.get("published_level")
    if level == "R1":
        return bool(groups["network"] and groups["process"])
    if level == "R2":
        return bool(groups["network"] and groups["process"] and groups["mapping"])
    if level == "R3":
        return bool(groups["network"] and groups["process"] and groups["mapping"] and any(
            roles.get(evidence_id) == "operational_response" for evidence_id in support
        ))
    if level == "R4":
        return bool(groups["network"] and groups["process"] and groups["mapping"] and any(
            roles.get(evidence_id) == "action_effect" for evidence_id in support
        ))
    return False


def _pair_view(row: dict, reference: dict, bundle: dict) -> dict:
    valid = bool(row and row.get("row_valid"))
    disposition = row.get("published_disposition") if valid else None
    level = row.get("published_level") if valid else None
    flags = row.get("published_flags") or {}
    linked = valid and disposition == "L"
    ceiling_ok = linked and reference is not None and LEVEL_RANK[level] <= LEVEL_RANK[reference["lambda_vis"]]
    flags_ok = linked and reference is not None and _flags_within(flags, reference["z_vis"])
    path = path_ok(row, bundle) if linked else False
    admissible = bool(
        linked
        and reference
        and reference["v_star"] == "L"
        and ceiling_ok
        and flags_ok
        and path
    )
    overpromoted = bool(
        linked
        and reference
        and reference["v_star"] == "L"
        and (not ceiling_ok or not flags_ok)
    )
    return {
        "valid": valid,
        "disposition": disposition,
        "linked": linked,
        "admissible": admissible,
        "overpromoted": overpromoted,
        "path": path,
        "g": 0 if reference is None else int(reference["g"]),
        "o_star": None if reference is None else reference["o_star"],
        "v_star": None if reference is None else reference["v_star"],
    }


def align_event(candidates: list[dict], rows: list[dict], reference_pairs: list[dict], bundle: dict) -> list[dict]:
    by_id = {}
    for row in rows:
        by_id.setdefault(row["candidate_id"], []).append(row)
    references = {item["candidate_id"]: item for item in reference_pairs}
    aligned = []
    for candidate in candidates:
        found = by_id.get(candidate["candidate_id"], [])
        if len(found) != 1:
            row = {"row_valid": False, "published_disposition": None, "published_level": None, "published_flags": {}}
        else:
            row = found[0]
        aligned.append(_pair_view(row, references.get(candidate["candidate_id"]), bundle))
    return aligned


def score_events(events: list[dict]) -> dict:
    factual_g = any(pair["g"] == 1 for event in events for pair in event["pairs"])
    num = {name: 0 for name in (
        "olp_hit", "olp_pred", "olr_hit", "olr_true", "uolr_hit", "uolr_true",
        "eap_hit", "eap_pred", "vwlr_hit", "vwlr_true", "nlr_hit", "nlr_true",
        "iar_hit", "iar_true", "sor_hit", "sor_true", "epc_hit", "epc_pred",
        "asserted", "valid_rows", "candidates", "hallucinated",
    )}
    false_events = 0
    policy_violation_events = 0
    for event in events:
        false_event = False
        policy_violation = False
        for pair in event["pairs"]:
            num["candidates"] += 1
            if pair["valid"]:
                num["valid_rows"] += 1
            else:
                num["hallucinated"] += 1
            if pair["valid"] and pair["disposition"] in {"L", "N"}:
                num["asserted"] += 1
            if pair["linked"]:
                num["eap_pred"] += 1
                num["epc_pred"] += 1
                if pair["admissible"]:
                    num["eap_hit"] += 1
                    num["vwlr_hit"] += 1
                if pair["path"]:
                    num["epc_hit"] += 1
                if pair["g"] == 1:
                    num["olp_pred"] += 1
                    if pair["o_star"] == "L":
                        num["olp_hit"] += 1
                        num["olr_hit"] += 1
                    if pair["o_star"] == "N":
                        num["uolr_hit"] += 1
                        false_event = True
            if pair["v_star"] == "L":
                num["vwlr_true"] += 1
                if pair["linked"]:
                    num["sor_true"] += 1
                    if pair["overpromoted"]:
                        num["sor_hit"] += 1
                        policy_violation = True
            if pair["v_star"] == "N":
                num["nlr_true"] += 1
                if pair["valid"] and pair["disposition"] == "N":
                    num["nlr_hit"] += 1
            if pair["v_star"] == "U":
                num["iar_true"] += 1
                if pair["valid"] and pair["disposition"] == "U":
                    num["iar_hit"] += 1
            if pair["g"] == 1 and pair["o_star"] == "L":
                num["olr_true"] += 1
            if pair["g"] == 1 and pair["o_star"] == "N":
                num["uolr_true"] += 1
            if pair["linked"] and not pair["admissible"]:
                policy_violation = True
        if false_event:
            false_events += 1
        if policy_violation:
            policy_violation_events += 1
    event_count = len(events)
    metrics = {
        "OLP": _ratio(num["olp_hit"], num["olp_pred"]) if factual_g else _ratio(0, 0),
        "OLR": _ratio(num["olr_hit"], num["olr_true"]) if factual_g else _ratio(0, 0),
        "UOLR": _ratio(num["uolr_hit"], num["uolr_true"]) if factual_g else _ratio(0, 0),
        "EFRI": _ratio(false_events, event_count) if factual_g else _ratio(0, 0),
        "EAP": _ratio(num["eap_hit"], num["eap_pred"]),
        "V-WLR": _ratio(num["vwlr_hit"], num["vwlr_true"]),
        "NLR": _ratio(num["nlr_hit"], num["nlr_true"]),
        "IAR": _ratio(num["iar_hit"], num["iar_true"]),
        "SOR": _ratio(num["sor_hit"], num["sor_true"]),
        "EPC": _ratio(num["epc_hit"], num["epc_pred"]),
        "assertion_coverage": _ratio(num["asserted"], num["candidates"]),
        "valid_row_coverage": _ratio(num["valid_rows"], num["candidates"]),
        "invalid_row_rate": _ratio(num["hallucinated"], num["candidates"]),
        "event_policy_violation_incidence": _ratio(policy_violation_events, event_count),
    }
    return {
        "factual_status": "synthetic_or_independent" if factual_g else "NA_NO_INDEPENDENT_LABELS",
        "policy_status": "policy_consistency_not_operational_truth",
        "event_count": event_count,
        "metrics": metrics,
    }


def paired_bootstrap(events_by_method: dict[str, list[dict]], left: str, right: str, metric: str, resamples: int, seed: int) -> dict:
    left_events = events_by_method[left]
    right_events = events_by_method[right]
    if len(left_events) != len(right_events) or len(left_events) < 2:
        return {"metric": metric, "contrast": f"{left}-{right}", "value": None, "status": "NA_TOO_FEW_EVENTS"}
    observed = _contrast(left_events, right_events, metric)
    if observed is None:
        return {"metric": metric, "contrast": f"{left}-{right}", "value": None, "status": "NA_UNDEFINED_METRIC"}
    rng = random.Random(seed)
    draws = []
    size = len(left_events)
    for _ in range(resamples):
        indexes = [rng.randrange(size) for _ in range(size)]
        sample_left = [left_events[index] for index in indexes]
        sample_right = [right_events[index] for index in indexes]
        value = _contrast(sample_left, sample_right, metric)
        if value is not None:
            draws.append(value)
    if len(draws) < resamples * 0.8:
        return {"metric": metric, "contrast": f"{left}-{right}", "value": observed, "status": "NA_UNSTABLE_DENOMINATOR", "defined_resamples": len(draws)}
    draws.sort()
    lo = draws[int(0.025 * (len(draws) - 1))]
    hi = draws[int(0.975 * (len(draws) - 1))]
    return {
        "metric": metric,
        "contrast": f"{left}-{right}",
        "value": observed,
        "ci95": [lo, hi],
        "resamples": resamples,
        "defined_resamples": len(draws),
        "seed": seed,
        "status": "computed",
        "unit": "event",
    }


def _contrast(left_events: list[dict], right_events: list[dict], metric: str):
    left = score_events(left_events)["metrics"][metric]["value"]
    right = score_events(right_events)["metrics"][metric]["value"]
    if left is None or right is None:
        return None
    return left - right
