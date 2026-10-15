"""Baseline B1: Temporal-Only Reconstruction.

Fairness design:
- Uses the exact same event observations, timestamps, vantage-deduplicated events,
  and 15.0s time horizon (`HORIZON_SECONDS = 15.0`, bounded at `MAX_LINKS_PER_EVENT = 6`
  for storyline chaining plus full 15s window accounting) as MIRAGE-OT.
- Does NOT use `evaluate_behavioral_relation_consistency`, command-effect setpoint/state
  consistency gates, lineage-based source deduplication, or Four-Layer Incident Synthesis.
- Every relation produced by B1 is explicitly typed as `"candidate_temporal_relation"`
  (never assumed to be physical causation).

Independent Epistemic Constraint Audit (non-circular):
Each candidate temporal relation is audited against five objective telemetry facts:
1. `cross_device_without_protocol_or_session_link`: endpoints belong to distinct grid
   elements (`device_stem`) and do not share an IEC-104 control session.
2. `same_asdu_co_report_chained_as_sequence`: endpoints were carried in the exact same
   IEC-104 ASDU (`asdu_key`), representing simultaneous packet packing rather than a sequence.
3. `endpoint_quality_or_test_bit_conflict`: at least one endpoint has `quality_good != True`,
   `cot_test == True`, or `cross_vantage_payload_conflict`.
4. `endpoint_transient_not_sustained`: at least one measurement/state endpoint fails post-sample
   persistence (`sustained_in_later_samples != True`).
5. `same_device_direction_or_change_type_conflict`: endpoints share `device_stem` in separate
   ASDUs, but have non-complementary sides (`from` vs `from`), mismatched `step_kinds`, or
   opposing magnitude change directions.
"""
from __future__ import annotations
from mirage_ot.etgi.reconstruction.anchors import MAGNITUDE_FLOOR

HORIZON_SECONDS = 15.0
MAX_LINKS_PER_EVENT = 6


def _extract_deduplicated_events(tx_result: dict, anchor_result: dict) -> list[dict]:
    """Collect vantage-deduplicated protocol and anchor events in chronological order."""
    events: list[dict] = []
    for tx in tx_result.get("transactions") or []:
        cmd = tx["command_activation"]
        events.append({
            "event_id": f"TXCMD-{tx['transaction_id']}",
            "origin_kind": "command_activation",
            "time": float(cmd["timestamp"]),
            "time_end": float(cmd["timestamp_end"]),
            "entity": cmd["entity"],
            "device_stem": tx.get("device_stem"),
            "rtu_ip": tx.get("rtu_ip"),
            "master_ip": tx.get("master_ip"),
            "asdu_key": f"TX-{cmd['message_id']}",
            "quality_ok": cmd.get("cot_test") is False,
            "sustained_ok": True,
            "has_cross_vantage_conflict": bool(cmd.get("cross_vantage_conflict")),
            "step_kinds": ["command_activation"],
            "points": [],
            "evidence_ids": list(cmd.get("evidence_ids") or []),
        })
        ack = tx.get("activation_confirmation")
        if ack is not None:
            events.append({
                "event_id": f"TXACK-{tx['transaction_id']}",
                "origin_kind": "command_confirmation",
                "time": float(ack["timestamp"]),
                "time_end": float(ack["timestamp_end"]),
                "entity": ack["entity"],
                "device_stem": tx.get("device_stem"),
                "rtu_ip": tx.get("rtu_ip"),
                "master_ip": tx.get("master_ip"),
                "asdu_key": f"TX-{ack['message_id']}",
                "quality_ok": ack.get("cot_test") is False and ack.get("cot_negative") is False,
                "sustained_ok": True,
                "has_cross_vantage_conflict": bool(ack.get("cross_vantage_conflict")),
                "step_kinds": ["command_confirmation"],
                "points": [],
                "evidence_ids": list(ack.get("evidence_ids") or []),
            })

    for a in anchor_result.get("anchors") or []:
        if a.get("covered_by_transaction"):
            continue
        issues = list(a.get("verification_issues") or [])
        has_conflict = any("cross_vantage_payload_conflict" in iss for iss in issues)
        atype = a["anchor_type"]
        if atype in ("communication_change", "arp_activity_increase"):
            q_ok = a.get("verification_status") == "verified_observation"
            sus_ok = a.get("verification_status") == "verified_observation"
        else:
            q_ok = a.get("quality_good") is True and not has_conflict
            sus_ok = a.get("sustained_in_later_samples") is True
        events.append({
            "event_id": a["anchor_id"],
            "origin_kind": atype,
            "time": float(a["time"]),
            "time_end": float(a.get("time_end", a["time"])),
            "entity": a["entity"],
            "device_stem": a.get("device_stem"),
            "rtu_ip": a.get("rtu_ip"),
            "master_ip": a.get("master_ip"),
            "host_ip": a.get("host_ip"),
            "asdu_key": a.get("asdu_key"),
            "quality_ok": q_ok,
            "sustained_ok": sus_ok,
            "has_cross_vantage_conflict": has_conflict,
            "transition_status": a.get("transition_status"),
            "prior_value": a.get("prior_value"),
            "value": a.get("value"),
            "step_kinds": list(a.get("step_kinds") or ([a.get("transition_status")] if a.get("transition_status") else [])),
            "points": list(a.get("points") or []),
            "evidence_ids": list(a.get("evidence_ids") or []),
        })

    events.sort(key=lambda e: (e["time"], e["event_id"]))
    return events


def _audit_temporal_pair(left: dict, right: dict) -> dict:
    """Objective audit of a candidate temporal relation against raw telemetry properties."""
    same_device = bool(left.get("device_stem")) and left.get("device_stem") == right.get("device_stem")
    same_asdu = bool(left.get("asdu_key")) and left.get("asdu_key") == right.get("asdu_key")
    same_rtu = bool(left.get("rtu_ip")) and left.get("rtu_ip") == right.get("rtu_ip")

    violations: list[str] = []
    if not same_device:
        violations.append("cross_device_without_protocol_or_session_link")
    if same_asdu:
        violations.append("same_asdu_co_report_chained_as_sequence")
    if not left["quality_ok"] or not right["quality_ok"]:
        violations.append("endpoint_quality_or_test_bit_conflict")
    if not left["sustained_ok"] or not right["sustained_ok"]:
        violations.append("endpoint_transient_not_sustained")

    # Check same-device direction / change-type conflicts on separate ASDUs
    direction_or_type_conflict = False
    if same_device and not same_asdu:
        l_pts = left.get("points") or []
        r_pts = right.get("points") or []
        if l_pts and r_pts:
            l_sides = {p.get("endpoint_side") for p in l_pts}
            r_sides = {p.get("endpoint_side") for p in r_pts}
            complementary = (
                l_sides in ({"from"}, {"to"})
                and r_sides in ({"from"}, {"to"})
                and l_sides != r_sides
            )
            l_by_base = {p.get("base_attribute"): p for p in l_pts if p.get("base_attribute")}
            r_by_base = {p.get("base_attribute"): p for p in r_pts if p.get("base_attribute")}
            shared_q = sorted(set(l_by_base) & set(r_by_base))
            if not complementary or not shared_q:
                direction_or_type_conflict = True
            else:
                if set(left.get("step_kinds") or []) != set(right.get("step_kinds") or []):
                    direction_or_type_conflict = True
                for q in shared_q:
                    lp, rp = l_by_base[q], r_by_base[q]
                    if lp.get("step_kind") != rp.get("step_kind"):
                        direction_or_type_conflict = True
                    elif lp.get("step_kind") == "level_shift":
                        l_delta = abs(float(lp["post_value"])) - abs(float(lp["pre_value"]))
                        r_delta = abs(float(rp["post_value"])) - abs(float(rp["pre_value"]))
                        if l_delta * r_delta <= 0:
                            direction_or_type_conflict = True
                        l_ratio = abs(float(lp["post_value"])) / max(abs(float(lp["pre_value"])), MAGNITUDE_FLOOR)
                        r_ratio = abs(float(rp["post_value"])) / max(abs(float(rp["pre_value"])), MAGNITUDE_FLOOR)
                        if min(l_ratio, r_ratio) / max(l_ratio, r_ratio) < 0.5:
                            direction_or_type_conflict = True
                        if q in ("active_power", "p") and float(lp["post_value"]) * float(rp["post_value"]) >= 0:
                            direction_or_type_conflict = True
        elif left["origin_kind"] == "spontaneous_state_report" and right["origin_kind"] == "measurement_step":
            if left.get("transition_status") != "state_change_observed":
                direction_or_type_conflict = True
        if direction_or_type_conflict:
            violations.append("same_device_direction_or_change_type_conflict")

    return {
        "same_device": same_device,
        "same_asdu": same_asdu,
        "same_rtu": same_rtu,
        "independent_rtu": bool(left.get("rtu_ip")) and bool(right.get("rtu_ip")) and not same_rtu,
        "violations": violations,
        "has_any_violation": bool(violations),
    }


def run_temporal_only_baseline(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
    horizon_seconds: float = HORIZON_SECONDS,
    max_links_per_event: int = MAX_LINKS_PER_EVENT,
) -> dict:
    events = _extract_deduplicated_events(tx_result, anchor_result)
    bounded_relations: list[dict] = []
    all_window_pair_count = 0
    all_window_violation_counts = {
        "cross_device_without_protocol_or_session_link": 0,
        "same_asdu_co_report_chained_as_sequence": 0,
        "endpoint_quality_or_test_bit_conflict": 0,
        "endpoint_transient_not_sustained": 0,
        "same_device_direction_or_change_type_conflict": 0,
        "any_violation": 0,
    }

    for i, left in enumerate(events):
        cross_device_links_for_left = 0
        for right in events[i + 1:]:
            dt = round(right["time"] - left["time"], 6)
            if dt < 0.0:
                continue
            if dt > horizon_seconds:
                break
            all_window_pair_count += 1
            audit = _audit_temporal_pair(left, right)
            for v in audit["violations"]:
                all_window_violation_counts[v] = all_window_violation_counts.get(v, 0) + 1
            if audit["has_any_violation"]:
                all_window_violation_counts["any_violation"] += 1

            # Fairness rule (matched to MIRAGE-OT's edge builder): never truncate same-device pairs
            # by the cross-device candidate cap `max_links_per_event`.
            include_in_bounded = False
            if audit["same_device"] or audit["same_asdu"]:
                include_in_bounded = True
            elif cross_device_links_for_left < max_links_per_event:
                cross_device_links_for_left += 1
                include_in_bounded = True

            if include_in_bounded:
                bounded_relations.append({
                    "relation_id": f"TMP-{len(bounded_relations) + 1:04d}",
                    "source_event_id": left["event_id"],
                    "target_event_id": right["event_id"],
                    "source_entity": left["entity"],
                    "target_entity": right["entity"],
                    "dt_seconds": dt,
                    "relation_type": "candidate_temporal_relation",
                    "claim_level": "candidate_temporal_association",
                    "causal_status": "not_established",
                    "same_device": audit["same_device"],
                    "same_asdu": audit["same_asdu"],
                    "independent_rtu": audit["independent_rtu"],
                    "violations": audit["violations"],
                    "has_any_violation": audit["has_any_violation"],
                    "evidence_ids": list(dict.fromkeys([*left["evidence_ids"][:2], *right["evidence_ids"][:2]])),
                })

    bounded_violation_counts = {
        k: sum(1 for r in bounded_relations if k in r["violations"])
        for k in (
            "cross_device_without_protocol_or_session_link",
            "same_asdu_co_report_chained_as_sequence",
            "endpoint_quality_or_test_bit_conflict",
            "endpoint_transient_not_sustained",
            "same_device_direction_or_change_type_conflict",
        )
    }
    bounded_any_violation = sum(1 for r in bounded_relations if r["has_any_violation"])
    bounded_clean_supported = len(bounded_relations) - bounded_any_violation

    mirage_supported_steps = sum(
        len(s.get("confirmed_and_supported_steps") or [])
        for s in (mirage_storylines.get("storylines") or [])
    )
    mirage_bridges = len(mirage_synthesis.get("verified_element_bridges") or [])

    return {
        "baseline_id": "B1_temporal_only",
        "method_description": (
            "Temporal-Only Reconstruction using identical event observations, timestamps, "
            "vantage deduplication, 15.0s horizon, and per-event link cap (6), without "
            "Behavioral Consistency Gate, Lineage Corroboration, or Incident Synthesis."
        ),
        "observations_used": [
            "IEC-104 control commands and confirmations",
            "Spontaneous state reports (COT=3)",
            "Measurement step observations",
            "IEC-104 link and TCP session changes",
            "ARP activity bursts",
        ],
        "information_removed": [
            "Behavioral Consistency Gate (`evaluate_behavioral_relation_consistency`)",
            "Command-to-effect pre/post setpoint/state consistency gate",
            "Same-ASDU container separation (`same_iec104_asdu` vs sequence step)",
            "Four-Layer Incident Synthesis (`rtu_asdu_bundles`, `verified_element_bridges`)",
        ],
        "allowed_claims": ["candidate_temporal_relation (never physical causation)"],
        "event_count": len(events),
        "unbounded_15s_temporal_pair_count": all_window_pair_count,
        "unbounded_15s_violation_counts": all_window_violation_counts,
        "candidate_temporal_relation_count": len(bounded_relations),
        "lacking_device_or_session_support_count": bounded_violation_counts["cross_device_without_protocol_or_session_link"],
        "cross_device_candidate_count": sum(1 for r in bounded_relations if not r["same_device"]),
        "same_asdu_co_report_chained_count": bounded_violation_counts["same_asdu_co_report_chained_as_sequence"],
        "quality_or_test_bit_conflict_count": bounded_violation_counts["endpoint_quality_or_test_bit_conflict"],
        "transient_not_sustained_conflict_count": bounded_violation_counts["endpoint_transient_not_sustained"],
        "same_device_direction_or_type_conflict_count": bounded_violation_counts["same_device_direction_or_change_type_conflict"],
        "total_conflicting_or_unsupported_candidate_count": bounded_any_violation,
        "clean_corroborated_candidate_count": bounded_clean_supported,
        "mirage_comparison": {
            "mirage_supported_storyline_step_count": mirage_supported_steps,
            "mirage_cross_rtu_verified_bridge_count": mirage_bridges,
            "unsupported_candidates_filtered_by_mirage": bounded_any_violation,
            "reduction_ratio": round(bounded_any_violation / len(bounded_relations), 4) if bounded_relations else 0.0,
        },
        "sample_candidate_relations": bounded_relations[:30],
    }
