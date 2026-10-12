"""Normalize visible IEC-104 transactions and telemetry into episodes.

Protocol acknowledgement is retained as confirmation lineage. It is not an
execution flag. Reported telemetry is not physical ground truth.
"""
from __future__ import annotations

import math
from typing import Any

from ebrl.canonical import short_id

ACTIVATION = 6
ACTIVATION_CONFIRMATION = 7
DEACTIVATION = 8
DEACTIVATION_CONFIRMATION = 9
ACTIVATION_TERMINATION = 10
COMMAND_TYPES = {45, 46, 47, 48, 49, 50, 51}
SETPOINT_TYPES = {48, 49, 50, 51}
CONFIRMATION_COTS = {ACTIVATION_CONFIRMATION, DEACTIVATION_CONFIRMATION, ACTIVATION_TERMINATION}

CLOSED_VARIABLES = {"closed", "is_closed"}
TAP_VARIABLES = {"tap_position"}
TARGET_VARIABLES = {
    "target_active_power": "set_target_active_power",
    "target_reactive_power": "set_target_reactive_power",
    "target_cos_phi": "set_target_cos_phi",
}


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _quality_bad(quality: list | None) -> bool:
    flags = set(quality or [])
    return bool(flags.intersection({"invalid", "nonfinite", "blocked", "substituted"}))


def decode_sco_select(record: dict) -> bool:
    if "qualifier_select" in record:
        return bool(record["qualifier_select"])
    sco = record.get("sco")
    if isinstance(sco, int):
        return bool(sco & 0x80)
    return False


def infer_command(record: dict, mapping: dict | None) -> str | None:
    if mapping and mapping.get("command_semantics"):
        return mapping["command_semantics"]
    variable = (mapping or {}).get("variable")
    type_id = record.get("type_id")
    value = record.get("value")
    if variable in CLOSED_VARIABLES and type_id in (45, 46):
        if value in (0, False, "off", "open"):
            return "open_breaker"
        if value in (1, True, "on", "close"):
            return "close_breaker"
    if variable in TAP_VARIABLES and type_id == 47 and _finite(value):
        if value > 0:
            return "raise_tap"
        if value < 0:
            return "lower_tap"
    if variable in TARGET_VARIABLES and type_id in SETPOINT_TYPES:
        return TARGET_VARIABLES[variable]
    return None


def _deadband(contract: dict, unit: str | None, before: Any) -> float | None:
    table = contract["deadband"]
    if unit not in table:
        return None
    spec = table[unit]
    absolute = float(spec["abs"])
    relative = float(spec["rel"])
    base = abs(before) if _finite(before) else 0.0
    return max(absolute, relative * base)


def _direction(before: Any, after: Any, unit: str | None, contract: dict) -> str | None:
    if isinstance(before, bool) or isinstance(after, bool):
        if before is True and after is False:
            return "to_false"
        if before is False and after is True:
            return "to_true"
        return None
    if not (_finite(before) and _finite(after)):
        return None
    floor = _deadband(contract, unit, before)
    if floor is None:
        return None
    delta = after - before
    if abs(delta) < floor:
        return None
    return "increase" if delta > 0 else "decrease"


def network_episodes(bundle: dict, contract: dict) -> list[dict]:
    mappings = {}
    for item in bundle.get("mappings", []):
        mappings[(item["ca"], item["ioa"])] = item
    groups: dict[tuple, list[dict]] = {}
    for record in bundle.get("network_records", []):
        if record.get("tcp_ack_only") or record.get("format") in {"S", "U"}:
            continue
        if record.get("type_id") not in COMMAND_TYPES:
            continue
        if record.get("cot") not in {ACTIVATION, DEACTIVATION, *CONFIRMATION_COTS}:
            continue
        key = (record.get("flow"), record.get("ca"), record.get("ioa"), record.get("type_id"))
        groups.setdefault(key, []).append(record)
    episodes = []
    gap = float(contract["transaction_gap_s"])
    for key, records in groups.items():
        records = sorted(records, key=lambda item: (item["observed_at"], item["evidence_id"]))
        bucket: list[dict] = []

        def flush(items: list[dict]) -> None:
            if not items:
                return
            episodes.append(_command_episode(bundle["event_id"], items, mappings, contract))

        for record in records:
            if record.get("is_retransmission") and bucket:
                bucket.append(record)
                continue
            if bucket and record["observed_at"] - bucket[-1]["observed_at"] > gap:
                flush(bucket)
                bucket = [record]
                continue
            if (
                bucket
                and record.get("cot") == ACTIVATION
                and not decode_sco_select(record)
                and any(item.get("cot") == ACTIVATION and not decode_sco_select(item) for item in bucket)
            ):
                flush(bucket)
                bucket = [record]
                continue
            bucket.append(record)
        flush(bucket)
    episodes.sort(key=lambda item: (item["t_command"], item["episode_id"]))
    return episodes


def _command_episode(event_id: str, records: list[dict], mappings: dict, contract: dict) -> dict:
    operates = [
        item for item in records
        if item.get("cot") in {ACTIVATION, DEACTIVATION}
        and not decode_sco_select(item)
        and not item.get("is_retransmission")
    ]
    selects = [item for item in records if item.get("cot") == ACTIVATION and decode_sco_select(item)]
    confirmations = [item for item in records if item.get("cot") in CONFIRMATION_COTS or item.get("is_retransmission")]
    primary = operates[-1] if operates else (selects[-1] if selects else records[0])
    mapping = mappings.get((primary.get("ca"), primary.get("ioa")))
    phase = "operate"
    if selects and operates:
        phase = "select_before_operate"
    elif selects and not operates:
        phase = "select_only"
    evidence_ids = [item["evidence_id"] for item in records if item not in confirmations and not item.get("is_retransmission")]
    if not evidence_ids:
        evidence_ids = [primary["evidence_id"]]
    confirmation_ids = [item["evidence_id"] for item in records if item["evidence_id"] not in evidence_ids]
    identity = {
        "event_id": event_id,
        "flow": primary.get("flow"),
        "ca": primary.get("ca"),
        "ioa": primary.get("ioa"),
        "type_id": primary.get("type_id"),
        "t": primary["observed_at"],
        "ids": [item["evidence_id"] for item in records],
        "contract": contract["contract_id"],
    }
    return {
        "episode_id": short_id("q", identity),
        "event_id": event_id,
        "evidence_ids": evidence_ids,
        "confirmation_ids": confirmation_ids,
        "parent_ids": [parent for item in records for parent in item.get("parent_ids", [])],
        "t_command": primary["observed_at"],
        "ca": primary.get("ca"),
        "ioa": primary.get("ioa"),
        "type_id": primary.get("type_id"),
        "flow": primary.get("flow"),
        "value": primary.get("value"),
        "phase": phase,
        "command_semantics": infer_command(primary, mapping),
        "asset_id": None if mapping is None else mapping.get("asset_id"),
        "variable": None if mapping is None else mapping.get("variable"),
        "context": None if mapping is None else mapping.get("context"),
        "mapping_ids": [] if mapping is None else [mapping["evidence_id"]],
        "protocol_confirmation_is_not_execution": True,
    }


def process_episodes(bundle: dict, contract: dict) -> list[dict]:
    series: dict[tuple, list[dict]] = {}
    for record in bundle.get("process_records", []):
        key = (record.get("asset_id"), record.get("variable"), record.get("context"))
        series.setdefault(key, []).append(record)
    episodes = []
    stale_gap = float(contract["stale_gap_s"])
    for key, records in series.items():
        records = sorted(records, key=lambda item: (item["observed_at"], item["evidence_id"]))
        previous = None
        for record in records:
            value = record.get("value")
            if value is None:
                continue
            if previous is None:
                previous = record
                continue
            if record.get("stale") or previous.get("stale"):
                quality_ok = False
                stale = True
            else:
                stale = record["observed_at"] - previous["observed_at"] > stale_gap
                quality_ok = not (_quality_bad(record.get("quality")) or _quality_bad(previous.get("quality")) or stale)
            direction = _direction(previous.get("value"), value, record.get("unit"), contract)
            if direction is None:
                if not record.get("stale"):
                    previous = record
                continue
            identity = {
                "event_id": bundle["event_id"],
                "asset": key[0],
                "variable": key[1],
                "context": key[2],
                "ids": [previous["evidence_id"], record["evidence_id"]],
                "contract": contract["contract_id"],
            }
            episodes.append({
                "episode_id": short_id("p", identity),
                "event_id": bundle["event_id"],
                "evidence_ids": [previous["evidence_id"], record["evidence_id"]],
                "parent_ids": list(previous.get("parent_ids", [])) + list(record.get("parent_ids", [])),
                "asset_id": key[0],
                "variable": key[1],
                "context": key[2],
                "unit": record.get("unit"),
                "t_start": record["observed_at"],
                "t_end": record["observed_at"],
                "before": previous.get("value"),
                "after": value,
                "direction": direction,
                "quality_ok": quality_ok,
                "stale": stale or bool(record.get("stale") or previous.get("stale")),
                "reported_not_physical_truth": True,
            })
            previous = record
    episodes.sort(key=lambda item: (item["t_start"], item["episode_id"]))
    return episodes


def normalize(bundle: dict, contract: dict) -> dict:
    commands = network_episodes(bundle, contract)
    process = process_episodes(bundle, contract)
    return {"command_episodes": commands, "process_episodes": process}
