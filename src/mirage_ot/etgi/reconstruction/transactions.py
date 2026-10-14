"""Phase 1: IEC-104 Protocol Transaction Reconstruction (Reliability-Hardened).

Invariants enforced:
1. Multi-vantage deduplication with payload-conflict detection:
   - Captures at different mirror ports (`n302`, `n318`) sharing `(5-tuple, tcp_seq,
     entity, ca_ioa, type_id, cot)` are merged into one logical message ONLY IF
     their decoded values and control flags (`value_present`, `value`, `cot_negative`,
     `select_execute`) agree.
   - If two vantages report conflicting values/flags on the same `tcp_seq`, they are
     NEVER silently merged; both observations are preserved and flagged in
     `cross_vantage_conflicts` (`cross_vantage_payload_conflict`).
   - Each logical message receives a single `canonical_source_id` (`SRC-MSG-...`)
     so multi-vantage mirror captures never inflate independent source counts.
2. Strict TCP retransmission vs. new application command:
   - An unconfirmed `COT=6` on the same 5-tuple and `CA/IOA` is attached as a
     `tcp_retransmission` ONLY when `tcp_seq` is present and identical to the open
     command (and `apci_tx` agrees when present) with the same value.
   - If `tcp_seq` or `apci_tx` differs, it is a distinct application-layer command
     and starts a new transaction even within 0.5s.
3. Explicit `COT=7` P/N bit (positive vs. negative confirmation) semantics:
   - `cot_negative is False` -> `command_acceptance_status = "accepted_by_rtu"`
   - `cot_negative is True`  -> `command_acceptance_status = "rejected_negative_confirmation"`
   - `cot_negative is None`  -> `command_acceptance_status = "confirmation_observed_acceptance_unknown"`
     (never claims `accepted_by_rtu` when the P/N bit was not decoded).
4. Strict separation of `state_report_observed` vs. `verified_state_transition`:
   - Mere presence of a `COT=3` (`M_SP_NA_1`) message or an IPAL `new` row NEVER
     sets `state_change_observed`.
   - When `COT=3` has `value_present=False` (`unparsed_value`), status is
     `"state_report_observed_value_unknown"`.
   - When `COT=3` has a decoded value but lacks a pre-command IEC-104 baseline
     proving $v_{\\text{pre}} \\neq v_{\\text{post}}$, status is
     `"state_report_observed_no_pre_baseline"`.
   - Only when a valid pre-command baseline and post-command observation both exist,
     shift in the commanded direction, and match the commanded target does the
     transaction reach `"verified_state_transition"` / `"verified_measurement_transition"`.
"""
from __future__ import annotations
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
    logical_msgs, conflicts = collapse_multi_vantage_messages(
        incident_iec, tcp_seq_by_id=tcp_seq_by_id, return_conflicts=True,
    )

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
            retrans_tx = _find_retransmit_target(transactions, msg, retransmit_window_sec)
            if retrans_tx is not None:
                retrans_tx["duplicate_command_messages"].append({
                    **msg,
                    "duplicate_classification": "tcp_retransmission",
                })
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
        "confirmation_unknown_acceptance_count": sum(
            1 for t in transactions if t["command_acceptance_status"] == "confirmation_observed_acceptance_unknown"
        ),
        "rejected_negative_ack_count": sum(
            1 for t in transactions if t["command_acceptance_status"] == "rejected_negative_confirmation"
        ),
        "unconfirmed_count": sum(
            1 for t in transactions if t["command_acceptance_status"] == "unconfirmed_missing_cot7"
        ),
        "verified_state_or_measurement_transition_count": sum(
            1 for t in transactions
            if t["device_state_change_status"] in ("verified_state_transition", "verified_measurement_transition")
        ),
        "state_report_observed_unverified_count": sum(
            1 for t in transactions
            if t["device_state_change_status"] in (
                "state_report_observed_value_unknown",
                "state_report_observed_no_pre_baseline",
                "state_report_observed_target_mismatch",
                "measurement_observed_transition_unverified",
            )
        ),
        "no_state_change_count": sum(
            1 for t in transactions if t["device_state_change_status"] == "no_state_change_observed"
        ),
        "unpaired_control_message_count": len(unpaired_messages),
        "cross_vantage_conflict_count": len(conflicts),
        "cross_vantage_conflicts": conflicts,
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
    return_conflicts: bool = False,
) -> list[dict] | tuple[list[dict], list[dict]]:
    """Collapse multi-vantage mirror captures while refusing to merge conflicting payloads."""
    seq_lookup = tcp_seq_by_id or {}
    sorted_rows = sorted(rows, key=lambda r: (r["timestamp"], r["evidence_id"]))
    buckets: list[list[dict]] = []
    conflicts: list[dict] = []
    conflicted_row_ids: set[str] = set()

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
            )
            if same_l2_frame or same_tcp_seq_diff_vantage or transit_diff_vantage:
                if _rows_payload_consistent(first, row):
                    matched_bucket = bucket
                else:
                    conflicts.append({
                        "conflict_type": "cross_vantage_payload_conflict",
                        "entity": row.get("entity"),
                        "ca_ioa": row.get("ca_ioa"),
                        "tcp_seq": tcp_seq,
                        "first_evidence_id": first["evidence_id"],
                        "first_vantage": first.get("vantage"),
                        "first_value": first.get("value") if first.get("value_present") else None,
                        "second_evidence_id": row["evidence_id"],
                        "second_vantage": vantage,
                        "second_value": row.get("value") if row.get("value_present") else None,
                    })
                    conflicted_row_ids.add(first["evidence_id"])
                    conflicted_row_ids.add(row["evidence_id"])
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
        msg_id = f"MSG-{ev_ids[0][3:11]}"
        cot_neg = payload.get("cot_negative") if isinstance(payload.get("cot_negative"), bool) else None
        cot_tst = payload.get("cot_test") if isinstance(payload.get("cot_test"), bool) else None
        se_mode = payload.get("select_execute")
        q_inv = payload.get("quality_invalid") if isinstance(payload.get("quality_invalid"), bool) else None
        apci_tx = _int_or_none(payload.get("apci_tx"))
        apci_rx = _int_or_none(payload.get("apci_rx"))

        messages.append({
            "message_id": msg_id,
            "canonical_source_id": f"SRC-{msg_id}",
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
            "cot_negative": cot_neg,
            "cot_test": cot_tst,
            "select_execute": se_mode,
            "quality_invalid": q_inv,
            "apci_tx": apci_tx,
            "apci_rx": apci_rx,
            "direction": _direction(first),
            "src_ip": first.get("src_ip"),
            "src_port": first.get("src_port"),
            "dst_ip": first.get("dst_ip"),
            "dst_port": first.get("dst_port"),
            "tcp_seq": tcp_seq,
            "value_present": bool(first.get("value_present")),
            "value": first.get("value") if first.get("value_present") else None,
            "alignment": payload.get("alignment"),
            "fingerprint": fps[0],
            "all_fingerprints": fps,
            "vantages": vantages,
            "vantage_capture_count": len(members),
            "cross_vantage_conflict": any(eid in conflicted_row_ids for eid in ev_ids),
            "evidence_ids": ev_ids,
            "parent_evidence_ids": parent_ids,
        })
    messages.sort(key=lambda m: (m["timestamp"], m["message_id"]))
    if return_conflicts:
        return messages, conflicts
    return messages


def _rows_payload_consistent(r1: dict, r2: dict) -> bool:
    if bool(r1.get("value_present")) != bool(r2.get("value_present")):
        return False
    v1 = r1.get("value") if r1.get("value_present") else None
    v2 = r2.get("value") if r2.get("value_present") else None
    if not _same_val(v1, v2):
        return False
    p1 = r1.get("payload") if isinstance(r1.get("payload"), dict) else {}
    p2 = r2.get("payload") if isinstance(r2.get("payload"), dict) else {}
    for key in ("cot_negative", "cot_test", "select_execute", "quality_invalid", "apci_tx"):
        if p1.get(key) is not None and p2.get(key) is not None and p1.get(key) != p2.get(key):
            return False
    return True


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
        "select_execute": cmd.get("select_execute"),
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
        "state_verification_reason": "no_post_command_feedback_observed",
        "transaction_completeness": "incomplete",
        "missing_stages": [],
        "all_evidence_ids": list(dict.fromkeys([*cmd["evidence_ids"], *cmd["parent_evidence_ids"]])),
        "canonical_source_ids": [cmd["canonical_source_id"]],
        "notes": [],
    }


def _find_retransmit_target(transactions: list[dict], msg: dict, retransmit_window_sec: float) -> dict | None:
    """Attach as a TCP retransmission ONLY when tcp_seq (and apci_tx if present) matches an unconfirmed command."""
    for tx in reversed(transactions):
        if tx["activation_confirmation"] is not None:
            continue
        cmd = tx["command_activation"]
        if (tx["master_ip"], tx["master_port"], tx["rtu_ip"], tx["rtu_port"]) != (
            msg["src_ip"], msg["src_port"], msg["dst_ip"], msg["dst_port"]
        ):
            continue
        if tx["ca_ioa"] != msg["ca_ioa"] or tx["type_id"] != msg["type_id"] or tx["entity"] != msg["entity"]:
            continue
        if tx["value_present"] != msg["value_present"] or not _same_val(tx["commanded_value"], msg["value"]):
            continue
        if not _select_execute_compatible(tx.get("select_execute"), msg.get("select_execute")):
            continue
        # Require identical TCP sequence number to classify as a TCP retransmission
        if cmd.get("tcp_seq") is None or msg.get("tcp_seq") is None or cmd["tcp_seq"] != msg["tcp_seq"]:
            continue
        if cmd.get("apci_tx") is not None and msg.get("apci_tx") is not None and cmd["apci_tx"] != msg["apci_tx"]:
            continue
        dt = msg["timestamp"] - cmd["timestamp"]
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
        if not _select_execute_compatible(tx.get("select_execute"), msg.get("select_execute")):
            reasons.append("select_execute_mismatch")
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
    if msg["canonical_source_id"] not in tx["canonical_source_ids"]:
        tx["canonical_source_ids"].append(msg["canonical_source_id"])
    if cot == 7:
        tx["activation_confirmation"] = msg
        cot_neg = msg.get("cot_negative")
        if cot_neg is True:
            tx["command_acceptance_status"] = "rejected_negative_confirmation"
        elif cot_neg is False:
            tx["command_acceptance_status"] = "accepted_by_rtu"
        else:
            tx["command_acceptance_status"] = "confirmation_observed_acceptance_unknown"
    elif cot == 10:
        tx["activation_termination"] = msg
    else:
        tx["deactivation_messages"].append(msg)


def evaluate_command_effect_inference(
    *,
    command_acceptance_status: str | None,
    command_value_present: bool,
    commanded_value: float | None,
    pre_value_present: bool,
    pre_command_value: float | None,
    post_value_present: bool,
    post_command_value: float | None,
    pre_quality_invalid: bool | None = None,
    post_quality_invalid: bool | None = None,
    same_rtu_and_ca: bool = True,
    same_device_stem: bool = True,
) -> dict:
    """Testable consistency gate for upgrading a command-to-state transition to `supported_inference`.

    Invalid quality on the pre-command or post-command measurement blocks the upgrade.
    Missing quality is recorded as uncertainty and also blocks the upgrade: an absent
    IV/QDS bit is not treated as a valid measurement.
    """
    failed = []
    uncertainties = []
    if not same_rtu_and_ca:
        failed.append("rtu_or_ca_mismatch")
    if not same_device_stem:
        failed.append("device_stem_mismatch")
    if command_acceptance_status == "rejected_negative_confirmation":
        failed.append("command_rejected_by_negative_confirmation")
    elif command_acceptance_status == "unconfirmed_missing_cot7":
        failed.append("command_missing_cot7_confirmation")
    if not command_value_present or commanded_value is None:
        failed.append("command_value_unknown")
    if not pre_value_present or pre_command_value is None:
        failed.append("missing_pre_command_baseline")
    elif pre_quality_invalid is True:
        failed.append("pre_value_quality_invalid")
    elif pre_quality_invalid is None:
        failed.append("pre_quality_unknown")
        uncertainties.append("pre_quality_not_decoded")
    if not post_value_present or post_command_value is None:
        failed.append("post_state_or_measurement_value_unknown")
    elif post_quality_invalid is True:
        failed.append("post_value_quality_invalid")
    elif post_quality_invalid is None:
        failed.append("post_quality_unknown")
        uncertainties.append("post_quality_not_decoded")

    shifted = False
    direction_ok = False
    matches_target = False
    if (
        pre_value_present and pre_command_value is not None
        and post_value_present and post_command_value is not None
    ):
        pre_f = float(pre_command_value)
        post_f = float(post_command_value)
        delta = post_f - pre_f
        shifted = abs(delta) > max(abs(pre_f) * 0.01, 1e-3)
        if not shifted:
            failed.append("not_shifted_from_pre_baseline")
        if command_value_present and commanded_value is not None:
            cmd_f = float(commanded_value)
            target_delta = cmd_f - pre_f
            tol = max(abs(cmd_f) * 0.02, 1.0 if abs(cmd_f) > 1.0 else 1e-3)
            matches_target = abs(post_f - cmd_f) <= tol
            if abs(target_delta) > 1e-6:
                direction_ok = (delta * target_delta > 0) and (abs(post_f - cmd_f) < abs(pre_f - cmd_f))
            else:
                direction_ok = False
            if not direction_ok:
                failed.append("shift_direction_does_not_approach_target")
            if not matches_target:
                failed.append("post_value_outside_target_tolerance")

    passed = len(failed) == 0
    return {
        "gate_passed": passed,
        "shifted_from_pre_baseline": shifted,
        "direction_matches_target": direction_ok,
        "matches_commanded_setpoint": matches_target,
        "pre_quality_invalid": pre_quality_invalid,
        "post_quality_invalid": post_quality_invalid,
        "quality_uncertainty": uncertainties,
        "failed_conditions": failed,
        "recommended_claim_level": "supported_inference" if passed else "unresolved",
        "recommended_verification_status": "supported" if passed else "unresolved",
    }


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

    # 1. Spontaneous single-point state reports (`COT == 3` only, same RTU IP, same CA, same device_stem)
    for m in monitor_msgs:
        if not (cmd_time <= m["timestamp"] <= feedback_horizon):
            continue
        if m["src_ip"] != tx["rtu_ip"] or m["ca"] != tx["ca"] or m["device_stem"] != tx["device_stem"]:
            continue
        if m["cot"] == 3:
            pre_sp = [
                pm for pm in all_iec_with_pre
                if pm["entity"] == m["entity"] and pm["src_ip"] == tx["rtu_ip"]
                and pm["value_present"] and (cmd_time - 15.0) <= pm["timestamp"] < cmd_time
            ]
            pre_val = pre_sp[-1]["value"] if pre_sp else None
            pre_quality = pre_sp[-1].get("quality_invalid") if pre_sp else None
            gate = evaluate_command_effect_inference(
                command_acceptance_status=tx["command_acceptance_status"],
                command_value_present=tx["value_present"],
                commanded_value=tx["commanded_value"],
                pre_value_present=bool(pre_sp),
                pre_command_value=pre_val,
                pre_quality_invalid=pre_quality,
                post_value_present=m["value_present"],
                post_command_value=m["value"],
                post_quality_invalid=m.get("quality_invalid"),
                same_rtu_and_ca=True,
                same_device_stem=True,
            )
            tx["protocol_state_feedback"].append({
                **m,
                "pre_state_value": pre_val,
                "pre_quality_invalid": pre_quality,
                "consistency_gate": gate,
            })
            tx["end_time"] = max(tx["end_time"], m["timestamp_end"])
            tx["all_evidence_ids"] = list(dict.fromkeys([
                *tx["all_evidence_ids"], *m["evidence_ids"], *m["parent_evidence_ids"],
            ]))
            if m["canonical_source_id"] not in tx["canonical_source_ids"]:
                tx["canonical_source_ids"].append(m["canonical_source_id"])

    # 2. Setpoint -> actual measurement transition on the same device & RTU
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
            pre_quality = pre_msgs[-1].get("quality_invalid") if pre_msgs else None
            post_val = first_post["value"]
            cmd_val = tx["commanded_value"]
            gate = evaluate_command_effect_inference(
                command_acceptance_status=tx["command_acceptance_status"],
                command_value_present=tx["value_present"],
                commanded_value=cmd_val,
                pre_value_present=bool(pre_msgs),
                pre_command_value=pre_val,
                pre_quality_invalid=pre_quality,
                post_value_present=first_post["value_present"],
                post_command_value=post_val,
                post_quality_invalid=first_post.get("quality_invalid"),
                same_rtu_and_ca=(first_post["src_ip"] == tx["rtu_ip"] and first_post["ca"] == tx["ca"]),
                same_device_stem=(first_post["device_stem"] == tx["device_stem"]),
            )
            tx["measurement_transition"] = {
                "measurement_entity": meas_entity,
                "ca_ioa": first_post["ca_ioa"],
                "pre_command_value": pre_val,
                "pre_command_time": pre_msgs[-1]["timestamp"] if pre_msgs else None,
                "pre_command_time_end": pre_msgs[-1]["timestamp_end"] if pre_msgs else None,
                "pre_quality_invalid": pre_quality,
                "post_quality_invalid": first_post.get("quality_invalid"),
                "pre_command_canonical_source_id": pre_msgs[-1]["canonical_source_id"] if pre_msgs else None,
                "pre_command_evidence_ids": (
                    [*pre_msgs[-1]["evidence_ids"], *pre_msgs[-1]["parent_evidence_ids"]] if pre_msgs else []
                ),
                "post_command_value": post_val,
                "post_command_time": first_post["timestamp"],
                "post_command_time_end": first_post["timestamp_end"],
                "post_command_canonical_source_id": first_post["canonical_source_id"],
                "post_command_evidence_ids": first_post["evidence_ids"],
                "post_command_parent_evidence_ids": first_post["parent_evidence_ids"],
                "commanded_setpoint": cmd_val,
                "shifted_from_pre_baseline": gate["shifted_from_pre_baseline"],
                "direction_matches_target": gate["direction_matches_target"],
                "matches_commanded_setpoint": gate["matches_commanded_setpoint"],
                "consistency_gate": gate,
            }
            tx["end_time"] = max(tx["end_time"], first_post["timestamp_end"])
            tx["all_evidence_ids"] = list(dict.fromkeys([
                *tx["all_evidence_ids"],
                *(tx["measurement_transition"]["pre_command_evidence_ids"]),
                *first_post["evidence_ids"],
                *first_post["parent_evidence_ids"],
            ]))
            if pre_msgs and pre_msgs[-1]["canonical_source_id"] not in tx["canonical_source_ids"]:
                tx["canonical_source_ids"].append(pre_msgs[-1]["canonical_source_id"])
            if first_post["canonical_source_id"] not in tx["canonical_source_ids"]:
                tx["canonical_source_ids"].append(first_post["canonical_source_id"])

    # 3. IPAL state table updates (`electrical_update`) on the same entity or controlled measurement entity
    watched_entities = {tx["entity"]}
    if target_attr:
        watched_entities.add(f"{tx['device_stem']}:{target_attr}")
    for row in electrical_updates:
        if row.get("entity") in watched_entities and cmd_time <= row["timestamp"] <= feedback_horizon:
            tx["ipal_state_updates"].append({
                "evidence_id": row["evidence_id"],
                "parent_evidence_id": row.get("parent_evidence_id"),
                "timestamp": row["timestamp"],
                "entity": row["entity"],
                "ca_ioa": row.get("ca_ioa"),
                "value": row.get("value") if row.get("value_present") else None,
                "shared_network_source": True,
                "note": "IPAL state update derived from network telemetry; not an independent physical sensor and cannot alone prove state transition without decoded protocol values and a pre-command baseline.",
            })
            tx["all_evidence_ids"] = list(dict.fromkeys([*tx["all_evidence_ids"], row["evidence_id"]]))

    # 4. Determine strict `device_state_change_status` (P0-1 & P0-2)
    mt = tx["measurement_transition"]
    fb_list = tx["protocol_state_feedback"]

    if mt is not None:
        mt_gate = mt["consistency_gate"]
        if mt_gate["gate_passed"]:
            tx["device_state_change_status"] = "verified_measurement_transition"
            tx["state_verification_reason"] = "pre_to_post_shift_and_setpoint_match_verified"
        else:
            tx["device_state_change_status"] = "measurement_observed_transition_unverified"
            tx["state_verification_reason"] = ",".join(mt_gate["failed_conditions"])
    elif fb_list:
        first_fb = fb_list[0]
        fb_gate = first_fb["consistency_gate"]
        if fb_gate["gate_passed"]:
            tx["device_state_change_status"] = "verified_state_transition"
            tx["state_verification_reason"] = "decoded_spontaneous_state_shift_verified"
        elif not first_fb["value_present"]:
            tx["device_state_change_status"] = "state_report_observed_value_unknown"
            tx["state_verification_reason"] = ",".join(fb_gate["failed_conditions"])
        elif first_fb.get("pre_state_value") is None:
            tx["device_state_change_status"] = "state_report_observed_no_pre_baseline"
            tx["state_verification_reason"] = ",".join(fb_gate["failed_conditions"])
        else:
            tx["device_state_change_status"] = "state_report_observed_target_mismatch"
            tx["state_verification_reason"] = ",".join(fb_gate["failed_conditions"])
    else:
        tx["device_state_change_status"] = "no_state_change_observed"
        tx["state_verification_reason"] = "no_post_command_feedback_observed"

    if tx["activation_confirmation"] is None:
        tx["missing_stages"].append("activation_confirmation_cot7")
    elif tx["command_acceptance_status"] == "confirmation_observed_acceptance_unknown":
        tx["missing_stages"].append("cot7_positive_negative_bit_undecoded")
    if tx["activation_termination"] is None:
        tx["missing_stages"].append("activation_termination_cot10")
    if tx["device_state_change_status"] == "no_state_change_observed":
        tx["missing_stages"].append("post_command_state_or_measurement_change")
    elif tx["device_state_change_status"] in (
        "state_report_observed_value_unknown",
        "state_report_observed_no_pre_baseline",
        "state_report_observed_target_mismatch",
        "measurement_observed_transition_unverified",
    ):
        tx["missing_stages"].append(f"unverified_state_transition:{tx['state_verification_reason']}")

    if tx["device_state_change_status"] in ("verified_state_transition", "verified_measurement_transition"):
        tx["transaction_completeness"] = (
            "complete_with_verified_transition"
            if tx["activation_termination"] is not None
            else "partial_no_cot10_but_verified_measurement_transition"
        )
    elif tx["device_state_change_status"].startswith("state_report_observed") or (
        tx["device_state_change_status"] == "measurement_observed_transition_unverified"
    ):
        tx["transaction_completeness"] = "partial_state_report_observed_transition_unverified"
    elif tx["activation_confirmation"] is not None:
        tx["transaction_completeness"] = "confirmation_observed_only_no_state_report"
    else:
        tx["transaction_completeness"] = "unconfirmed_command"

    tx["notes"].append(
        "COT=7 confirms RTU protocol reply only (positive acceptance requires P/N bit=0); "
        "actual state transition requires decoded values and a pre-command baseline comparison."
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


def _select_execute_compatible(command_mode, reply_mode) -> bool:
    """Select and Execute are different operations. Unknown on one side is not a match to the other."""
    if command_mode in (None, "") or reply_mode in (None, ""):
        return command_mode in (None, "") and reply_mode in (None, "") or command_mode == reply_mode
    return command_mode == reply_mode


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
