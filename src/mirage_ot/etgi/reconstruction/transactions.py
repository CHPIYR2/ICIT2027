"""Phase 1: IEC-104 Protocol Transaction Reconstruction.

Pairs IEC-104 control commands with their protocol-level confirmations,
terminations, and subsequent device state/measurement feedback using strict
protocol invariants rather than time proximity or CA/IOA alone.

Invariants enforced:
1. Multi-vantage deduplication: identical Ethernet frames (`fingerprint`) seen
   at multiple mirror ports (`n302`, `n318`) are collapsed into one logical
   protocol message while retaining all vantages and parent packet lineage.
2. Strict session & ASDU pairing: `COT=7` (Activation Confirmation) and `COT=10`
   (Activation Termination) must match the reverse TCP 5-tuple
   (`rtu_ip:2404 -> master_ip:ephemeral_port`), the exact ASDU `type_id`, the
   exact `CA/IOA` and `entity`, and (when present) the commanded numeric value.
   Time proximity + same `CA/IOA` on a different TCP session is rejected.
3. Duplicate commands vs repeated operations: a second `COT=6` on the same
   5-tuple and `CA/IOA` with a distinct frame fingerprint before confirmation
   within `retransmit_window_sec` (0.5s) is recorded as a duplicate/retransmitted
   command on the same transaction; a `COT=6` after confirmation or outside the
   retransmit window starts a new transaction.
4. Separation of command acceptance (`command_acceptance_status`) from actual
   device state change (`device_state_change_status`).
"""
from __future__ import annotations
import json
from ..evidence.store import public_row

TYPE_NAMES = {
    1: "M_SP_NA_1 (Single-point information)",
    13: "M_ME_NC_1 (Short floating-point measurement)",
    45: "C_SC_NA_1 (Single command)",
    46: "C_DC_NA_1 (Double command)",
    50: "C_SE_NC_1 (Setpoint command, short float)",
}

COT_NAMES = {
    1: "periodic_cyclic",
    3: "spontaneous",
    6: "activation",
    7: "activation_confirmation",
    8: "deactivation",
    9: "deactivation_confirmation",
    10: "activation_termination",
}


def reconstruct_transactions(
    db,
    start: float,
    end: float,
    *,
    pre_context_sec: float = 15.0,
    post_feedback_sec: float = 15.0,
    confirm_window_sec: float = 5.0,
    termination_window_sec: float = 10.0,
    retransmit_window_sec: float = 0.5,
) -> dict:
    raw_rows = _load_window_rows(db, start - pre_context_sec, end + post_feedback_sec)
    tcp_seq_by_id = _extract_tcp_seq_map(raw_rows)
    incident_iec = [
        r for r in raw_rows
        if r["kind"] == "iec104_asdu" and start <= r["timestamp"] < end + post_feedback_sec
    ]
    logical_msgs = collapse_multi_vantage_messages(incident_iec, tcp_seq_by_id=tcp_seq_by_id)

    control_msgs = [
        m for m in logical_msgs
        if m["protocol_class"] == "control" and start <= m["timestamp"] < end
    ]
    monitor_msgs = [
        m for m in logical_msgs
        if m["protocol_class"] == "monitor"
    ]
    all_iec_with_pre = collapse_multi_vantage_messages(
        [r for r in raw_rows if r["kind"] == "iec104_asdu"],
        tcp_seq_by_id=tcp_seq_by_id,
    )
    electrical_updates = [
        r for r in raw_rows
        if r["kind"] == "electrical_update" and r.get("update_status") == "new"
    ]

    transactions: list[dict] = []
    unpaired_messages: list[dict] = []

    for msg in control_msgs:
        cot = msg["cot"]
        if cot == 6:
            # Check if this is an unconfirmed retransmission of an open transaction
            retrans_tx = _find_retransmit_target(transactions, msg, retransmit_window_sec)
            if retrans_tx is not None:
                retrans_tx["duplicate_command_messages"].append(msg)
                retrans_tx["all_evidence_ids"] = list(dict.fromkeys([
                    *retrans_tx["all_evidence_ids"], *msg["evidence_ids"], *msg["parent_evidence_ids"],
                ]))
                continue
            tx_id = f"TX{len(transactions) + 1:03d}"
            transactions.append(_new_transaction(tx_id, msg))
        elif cot in (7, 8, 9, 10):
            matched_tx, reject_reasons = _match_control_reply(
                transactions, msg,
                confirm_window_sec=confirm_window_sec,
                termination_window_sec=termination_window_sec,
            )
            if matched_tx is None:
                unpaired_messages.append({
                    "message": msg,
                    "reason": "no_matching_open_command",
                    "candidate_rejection_reasons": reject_reasons,
                })
            else:
                _attach_control_reply(matched_tx, msg, cot)
        else:
            unpaired_messages.append({
                "message": msg,
                "reason": f"unsupported_control_cot_{cot}",
                "candidate_rejection_reasons": [],
            })

    # Attach post-command protocol feedback (COT=3 / monitor shift) and IPAL state updates
    for index, tx in enumerate(transactions):
        next_same_device_cmd_time = _next_command_time_for_device(transactions, index)
        _finalize_transaction(
            tx,
            monitor_msgs=monitor_msgs,
            all_iec_with_pre=all_iec_with_pre,
            electrical_updates=electrical_updates,
            window_end=min(end + post_feedback_sec, next_same_device_cmd_time),
        )

    return {
        "incident_start": start,
        "incident_end": end,
        "transaction_count": len(transactions),
        "accepted_count": sum(1 for t in transactions if t["command_acceptance_status"] == "accepted_by_rtu"),
        "unconfirmed_count": sum(1 for t in transactions if t["command_acceptance_status"] != "accepted_by_rtu"),
        "state_change_observed_count": sum(
            1 for t in transactions if t["device_state_change_status"] == "state_change_observed"
        ),
        "no_state_change_count": sum(
            1 for t in transactions if t["device_state_change_status"] == "no_state_change_observed"
        ),
        "unpaired_control_message_count": len(unpaired_messages),
        "transactions": transactions,
        "unpaired_protocol_messages": unpaired_messages,
    }


def _extract_tcp_seq_map(rows: list[dict]) -> dict[str, int]:
    seq_map: dict[str, int] = {}
    for row in rows:
        if row["kind"] == "tcp_packet":
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            seq = _int_or_none(payload.get("tcp_seq"))
            if seq is not None:
                seq_map[row["evidence_id"]] = seq
    return seq_map


def collapse_multi_vantage_messages(
    rows: list[dict],
    *,
    tcp_seq_by_id: dict[str, int] | None = None,
    cross_vantage_transit_sec: float = 0.05,
) -> list[dict]:
    """Collapse captures of the same TCP segment / Ethernet frame and (entity, CA/IOA) across vantages.

    When a packet traverses a routed hop between mirror ports `n302` and `n318`,
    its L2 frame hash (`fingerprint`) changes due to MAC/TTL rewrite while its
    TCP 5-tuple and `tcp_seq` remain identical. We group by:
      1. Exact `(5-tuple, tcp_seq, entity, ca_ioa, type_id, cot)` when parent `tcp_seq` is known, or
      2. Exact `(fingerprint, entity, ca_ioa)`, or
      3. Distinct-vantage capture within `cross_vantage_transit_sec` (50ms) sharing
         `(5-tuple, entity, ca_ioa, type_id, cot, value)`.
    Same-vantage repeats with different `fingerprint`/`tcp_seq` are NEVER collapsed
    here; they remain separate messages so duplicate commands are detected.
    """
    seq_lookup = tcp_seq_by_id or {}
    sorted_rows = sorted(rows, key=lambda r: (r["timestamp"], r["evidence_id"]))
    buckets: list[list[dict]] = []

    for row in sorted_rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        type_id = _int_or_none(payload.get("type_id"))
        cot = _int_or_none(payload.get("cause"))
        parent_id = row.get("parent_evidence_id")
        tcp_seq = seq_lookup.get(parent_id) if parent_id else None
        fp = row.get("fingerprint") or row["evidence_id"]
        vantage = row.get("vantage")

        matched_bucket = None
        for bucket in reversed(buckets):
            first = bucket[0]
            if row["timestamp"] - first["timestamp"] > 0.25:
                break
            if (first.get("entity"), first.get("ca_ioa")) != (row.get("entity"), row.get("ca_ioa")):
                continue
            f_payload = first.get("payload") if isinstance(first.get("payload"), dict) else {}
            if (_int_or_none(f_payload.get("type_id")), _int_or_none(f_payload.get("cause"))) != (type_id, cot):
                continue
            if (first.get("src_ip"), first.get("src_port"), first.get("dst_ip"), first.get("dst_port")) != (
                row.get("src_ip"), row.get("src_port"), row.get("dst_ip"), row.get("dst_port")
            ):
                continue
            f_fp = first.get("fingerprint") or first["evidence_id"]
            f_parent = first.get("parent_evidence_id")
            f_seq = seq_lookup.get(f_parent) if f_parent else None
            bucket_vantages = {r.get("vantage") for r in bucket if r.get("vantage")}

            same_l2_frame = (fp == f_fp)
            same_tcp_seq_diff_vantage = (
                tcp_seq is not None and f_seq is not None and tcp_seq == f_seq and vantage not in bucket_vantages
            )
            transit_diff_vantage = (
                tcp_seq is None and f_seq is None
                and vantage is not None and vantage not in bucket_vantages
                and abs(row["timestamp"] - first["timestamp"]) <= cross_vantage_transit_sec
                and _same_val(first.get("value") if first.get("value_present") else None,
                              row.get("value") if row.get("value_present") else None)
            )
            if same_l2_frame or same_tcp_seq_diff_vantage or transit_diff_vantage:
                matched_bucket = bucket
                break

        if matched_bucket is not None:
            matched_bucket.append(row)
        else:
            buckets.append([row])

    messages = []
    for members in buckets:
        members.sort(key=lambda r: (r["timestamp"], r["evidence_id"]))
        first = members[0]
        payload = first.get("payload") if isinstance(first.get("payload"), dict) else {}
        type_id = _int_or_none(payload.get("type_id"))
        cot = _int_or_none(payload.get("cause"))
        ca_ioa = first.get("ca_ioa")
        ca, ioa = _split_ca_ioa(ca_ioa)
        vantages = list(dict.fromkeys(r.get("vantage") for r in members if r.get("vantage")))
        ev_ids = list(dict.fromkeys(r["evidence_id"] for r in members))
        parent_ids = list(dict.fromkeys(r["parent_evidence_id"] for r in members if r.get("parent_evidence_id")))
        fps = list(dict.fromkeys(r.get("fingerprint") or r["evidence_id"] for r in members))
        tcp_seq = next((seq_lookup[p] for p in parent_ids if p in seq_lookup), None)
        direction = _direction(first)
        messages.append({
            "message_id": f"MSG-{ev_ids[0][3:11]}",
            "timestamp": first["timestamp"],
            "timestamp_end": members[-1]["timestamp"],
            "entity": first.get("entity"),
            "device_stem": _device_stem(first.get("entity")),
            "attribute": _attribute_name(first.get("entity")),
            "ca_ioa": ca_ioa,
            "ca": ca,
            "ioa": ioa,
            "protocol_class": first.get("protocol_class"),
            "type_id": type_id,
            "type_name": TYPE_NAMES.get(type_id, f"type_{type_id}"),
            "cot": cot,
            "cot_name": COT_NAMES.get(cot, f"cot_{cot}"),
            "direction": direction,
            "src_ip": first.get("src_ip"),
            "src_port": first.get("src_port"),
            "dst_ip": first.get("dst_ip"),
            "dst_port": first.get("dst_port"),
            "tcp_seq": tcp_seq,
            "value_present": bool(first.get("value_present")),
            "value": first.get("value") if first.get("value_present") else None,
            "fingerprint": fps[0],
            "all_fingerprints": fps,
            "vantages": vantages,
            "vantage_capture_count": len(members),
            "evidence_ids": ev_ids,
            "parent_evidence_ids": parent_ids,
        })
    messages.sort(key=lambda m: (m["timestamp"], m["message_id"]))
    return messages


def _new_transaction(tx_id: str, cmd: dict) -> dict:
    return {
        "transaction_id": tx_id,
        "entity": cmd["entity"],
        "device_stem": cmd["device_stem"],
        "ca_ioa": cmd["ca_ioa"],
        "ca": cmd["ca"],
        "ioa": cmd["ioa"],
        "type_id": cmd["type_id"],
        "type_name": cmd["type_name"],
        "commanded_value": cmd["value"],
        "value_present": cmd["value_present"],
        "master_ip": cmd["src_ip"],
        "master_port": cmd["src_port"],
        "rtu_ip": cmd["dst_ip"],
        "rtu_port": cmd["dst_port"],
        "start_time": cmd["timestamp"],
        "end_time": cmd["timestamp_end"],
        "command_activation": cmd,
        "duplicate_command_messages": [],
        "activation_confirmation": None,
        "activation_termination": None,
        "deactivation_messages": [],
        "protocol_state_feedback": [],
        "measurement_transition": None,
        "ipal_state_updates": [],
        "command_acceptance_status": "unconfirmed_missing_cot7",
        "device_state_change_status": "no_state_change_observed",
        "transaction_completeness": "incomplete",
        "missing_stages": [],
        "all_evidence_ids": list(dict.fromkeys([*cmd["evidence_ids"], *cmd["parent_evidence_ids"]])),
        "independent_source_containers": [cmd["fingerprint"]],
        "notes": [],
    }


def _find_retransmit_target(transactions: list[dict], msg: dict, retransmit_window_sec: float) -> dict | None:
    for tx in reversed(transactions):
        if tx["activation_confirmation"] is not None:
            continue
        if (tx["master_ip"], tx["master_port"], tx["rtu_ip"], tx["rtu_port"]) != (
            msg["src_ip"], msg["src_port"], msg["dst_ip"], msg["dst_port"]
        ):
            continue
        if tx["ca_ioa"] != msg["ca_ioa"] or tx["type_id"] != msg["type_id"] or tx["entity"] != msg["entity"]:
            continue
        if tx["value_present"] != msg["value_present"] or not _same_val(tx["commanded_value"], msg["value"]):
            continue
        dt = msg["timestamp"] - tx["command_activation"]["timestamp"]
        if 0.0 <= dt <= retransmit_window_sec:
            return tx
    return None


def _match_control_reply(
    transactions: list[dict],
    msg: dict,
    *,
    confirm_window_sec: float,
    termination_window_sec: float,
) -> tuple[dict | None, list[dict]]:
    cot = msg["cot"]
    max_dt = confirm_window_sec if cot == 7 else termination_window_sec
    rejections = []

    for tx in reversed(transactions):
        reasons = []
        if cot == 7 and tx["activation_confirmation"] is not None:
            reasons.append("already_confirmed")
        if cot == 10 and tx["activation_termination"] is not None:
            reasons.append("already_terminated")
        if (msg["src_ip"], msg["src_port"], msg["dst_ip"], msg["dst_port"]) != (
            tx["rtu_ip"], tx["rtu_port"], tx["master_ip"], tx["master_port"]
        ):
            reasons.append("reverse_tcp_5tuple_mismatch")
        if msg["type_id"] != tx["type_id"]:
            reasons.append("type_id_mismatch")
        if msg["ca_ioa"] != tx["ca_ioa"] or msg["entity"] != tx["entity"]:
            reasons.append("ca_ioa_or_entity_mismatch")
        if tx["value_present"] and msg["value_present"] and not _same_val(tx["commanded_value"], msg["value"]):
            reasons.append("command_value_mismatch")
        dt = msg["timestamp"] - tx["command_activation"]["timestamp"]
        if dt < -1e-6 or dt > max_dt:
            reasons.append("outside_protocol_reply_window")
        if not reasons:
            return tx, []
        if msg["ca_ioa"] == tx["ca_ioa"]:
            rejections.append({"transaction_id": tx["transaction_id"], "reasons": reasons})
    return None, rejections


def _attach_control_reply(tx: dict, msg: dict, cot: int) -> None:
    tx["end_time"] = max(tx["end_time"], msg["timestamp_end"])
    tx["all_evidence_ids"] = list(dict.fromkeys([
        *tx["all_evidence_ids"], *msg["evidence_ids"], *msg["parent_evidence_ids"],
    ]))
    if msg["fingerprint"] not in tx["independent_source_containers"]:
        tx["independent_source_containers"].append(msg["fingerprint"])
    if cot == 7:
        tx["activation_confirmation"] = msg
        tx["command_acceptance_status"] = "accepted_by_rtu"
    elif cot == 10:
        tx["activation_termination"] = msg
    else:
        tx["deactivation_messages"].append(msg)


def _finalize_transaction(
    tx: dict,
    *,
    monitor_msgs: list[dict],
    all_iec_with_pre: list[dict],
    electrical_updates: list[dict],
    window_end: float,
) -> None:
    cmd_time = tx["command_activation"]["timestamp"]
    feedback_horizon = min(cmd_time + 15.0, window_end)

    # 1. Spontaneous single-point state feedback (e.g., switch.23:is_closed, M_SP_NA_1, COT=3)
    for m in monitor_msgs:
        if not (cmd_time <= m["timestamp"] <= feedback_horizon):
            continue
        if m["src_ip"] != tx["rtu_ip"] or m["ca"] != tx["ca"] or m["device_stem"] != tx["device_stem"]:
            continue
        if m["cot"] == 3 or m["type_id"] == 1:
            tx["protocol_state_feedback"].append(m)
            tx["end_time"] = max(tx["end_time"], m["timestamp_end"])
            tx["all_evidence_ids"] = list(dict.fromkeys([
                *tx["all_evidence_ids"], *m["evidence_ids"], *m["parent_evidence_ids"],
            ]))
            if m["fingerprint"] not in tx["independent_source_containers"]:
                tx["independent_source_containers"].append(m["fingerprint"])

    # 2. Setpoint -> actual measurement transition on the same device & RTU (e.g., sgen.6:target_active_power -> sgen.6:active_power)
    target_attr = _controlled_measurement_attribute(tx["entity"])
    if target_attr:
        meas_entity = f"{tx['device_stem']}:{target_attr}"
        pre_msgs = [
            m for m in all_iec_with_pre
            if m["entity"] == meas_entity and m["src_ip"] == tx["rtu_ip"]
            and m["value_present"] and (cmd_time - 15.0) <= m["timestamp"] < cmd_time
        ]
        post_msgs = [
            m for m in monitor_msgs
            if m["entity"] == meas_entity and m["src_ip"] == tx["rtu_ip"]
            and m["value_present"] and cmd_time < m["timestamp"] <= feedback_horizon
        ]
        if post_msgs:
            first_post = post_msgs[0]
            pre_val = pre_msgs[-1]["value"] if pre_msgs else None
            post_val = first_post["value"]
            cmd_val = tx["commanded_value"]
            shifted = (pre_val is not None and abs(float(post_val) - float(pre_val)) > max(abs(float(pre_val)) * 0.01, 1e-3))
            matches_setpoint = (
                cmd_val is not None
                and abs(float(post_val) - float(cmd_val)) <= max(abs(float(cmd_val)) * 0.02, 1.0)
            )
            tx["measurement_transition"] = {
                "measurement_entity": meas_entity,
                "ca_ioa": first_post["ca_ioa"],
                "pre_command_value": pre_val,
                "pre_command_time": pre_msgs[-1]["timestamp"] if pre_msgs else None,
                "pre_command_time_end": pre_msgs[-1]["timestamp_end"] if pre_msgs else None,
                "pre_command_evidence_ids": (
                    [*pre_msgs[-1]["evidence_ids"], *pre_msgs[-1]["parent_evidence_ids"]] if pre_msgs else []
                ),
                "post_command_value": post_val,
                "post_command_time": first_post["timestamp"],
                "post_command_time_end": first_post["timestamp_end"],
                "post_command_evidence_ids": first_post["evidence_ids"],
                "post_command_parent_evidence_ids": first_post["parent_evidence_ids"],
                "commanded_setpoint": cmd_val,
                "shifted_from_pre_baseline": bool(shifted),
                "matches_commanded_setpoint": bool(matches_setpoint),
            }
            tx["end_time"] = max(tx["end_time"], first_post["timestamp_end"])
            tx["all_evidence_ids"] = list(dict.fromkeys([
                *tx["all_evidence_ids"],
                *(pre_msgs[-1]["evidence_ids"] if pre_msgs else []),
                *first_post["evidence_ids"],
                *first_post["parent_evidence_ids"],
            ]))
            if first_post["fingerprint"] not in tx["independent_source_containers"]:
                tx["independent_source_containers"].append(first_post["fingerprint"])

    # 3. IPAL state table updates (`electrical_update`) on the same entity or controlled measurement entity
    watched_entities = {tx["entity"]}
    if target_attr:
        watched_entities.add(f"{tx['device_stem']}:{target_attr}")
    for row in electrical_updates:
        if row.get("entity") in watched_entities and cmd_time <= row["timestamp"] <= feedback_horizon:
            tx["ipal_state_updates"].append({
                "evidence_id": row["evidence_id"],
                "timestamp": row["timestamp"],
                "entity": row["entity"],
                "ca_ioa": row.get("ca_ioa"),
                "value": row.get("value") if row.get("value_present") else None,
                "shared_network_source": True,
                "note": "IPAL state update derived from network telemetry; not an independent physical sensor.",
            })
            tx["all_evidence_ids"] = list(dict.fromkeys([*tx["all_evidence_ids"], row["evidence_id"]]))

    # Determine device_state_change_status and missing stages
    has_spontaneous = len(tx["protocol_state_feedback"]) > 0
    has_meas_shift = bool(
        tx["measurement_transition"]
        and (tx["measurement_transition"]["shifted_from_pre_baseline"]
             or tx["measurement_transition"]["matches_commanded_setpoint"])
    )
    has_direct_switch_ipal = any(
        u["entity"] == tx["entity"] and tx["entity"].endswith(":closed") for u in tx["ipal_state_updates"]
    )

    if has_spontaneous or has_meas_shift or has_direct_switch_ipal:
        tx["device_state_change_status"] = "state_change_observed"
    else:
        tx["device_state_change_status"] = "no_state_change_observed"

    if tx["activation_confirmation"] is None:
        tx["missing_stages"].append("activation_confirmation_cot7")
    if tx["activation_termination"] is None:
        tx["missing_stages"].append("activation_termination_cot10")
    if tx["device_state_change_status"] == "no_state_change_observed":
        tx["missing_stages"].append("post_command_state_or_measurement_change")

    if tx["activation_confirmation"] is not None and tx["device_state_change_status"] == "state_change_observed":
        tx["transaction_completeness"] = (
            "complete_with_state_feedback"
            if tx["activation_termination"] is not None
            else "partial_no_cot10_but_state_feedback_observed"
        )
    elif tx["activation_confirmation"] is not None:
        tx["transaction_completeness"] = "command_accepted_only_no_state_change"
    else:
        tx["transaction_completeness"] = "unconfirmed_command"

    tx["notes"].append(
        "COT=7 confirms RTU reception/acceptance of the command only; "
        "actual state change is tracked separately in device_state_change_status."
    )


def _next_command_time_for_device(transactions: list[dict], index: int) -> float:
    stem = transactions[index]["device_stem"]
    for later in transactions[index + 1:]:
        if later["device_stem"] == stem:
            return float(later["start_time"])
    return float("inf")


def _controlled_measurement_attribute(entity: str | None) -> str | None:
    attr = _attribute_name(entity)
    if attr and attr.startswith("target_"):
        return attr[len("target_"):]
    return None


def _direction(row: dict) -> str:
    if row.get("dst_port") == 2404:
        return "master_to_rtu"
    if row.get("src_port") == 2404:
        return "rtu_to_master"
    return "unknown"


def _device_stem(entity: str | None) -> str | None:
    if not entity or ":" not in entity or str(entity).endswith("/TCP"):
        return None
    return str(entity).split(":", 1)[0]


def _attribute_name(entity: str | None) -> str | None:
    if not entity or ":" not in entity or str(entity).endswith("/TCP"):
        return None
    return str(entity).split(":", 1)[1]


def _split_ca_ioa(ca_ioa: str | None) -> tuple[int | None, int | None]:
    if not ca_ioa or "." not in str(ca_ioa):
        return None, None
    left, right = str(ca_ioa).split(".", 1)
    return _int_or_none(left), _int_or_none(right)


def _int_or_none(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _same_val(a, b) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= 1e-3
    except (TypeError, ValueError):
        return str(a) == str(b)


def _load_window_rows(db, start: float, end: float) -> list[dict]:
    found = db.conn.execute(
        """SELECT * FROM evidence WHERE timestamp >= ? AND timestamp < ?
           ORDER BY timestamp, evidence_id""",
        (start, end),
    ).fetchall()
    return [public_row(row) for row in found]
