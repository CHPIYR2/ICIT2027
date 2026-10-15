"""Baseline B1: Temporal-Only Reconstruction (Paper-Readiness Audit Hardened).

Fairness & Epistemic Separation Design (Task 1):
- Uses the exact same event observations, timestamps, vantage-deduplicated events,
  and 15.0s time horizon (`HORIZON_SECONDS = 15.0`, with `MAX_LINKS_PER_EVENT = 6`
  on cross-device candidates and full retention of same-device/same-ASDU pairs)
  as MIRAGE-OT.
- Every relation produced by B1 is typed as `"candidate_temporal_relation"` and is
  NEVER described as a "false causal inference".
- Strictly separates candidate relations into three mutually clear categories:
  1. `unsubstantiated_temporal_candidates`: temporally proximate (`0 <= dt <= 15s`),
     lacking direct relation evidence (e.g. `not same_device` without a shared control
     session, or lacking a prior in-window state baseline), but WITHOUT a direct
     telemetry constraint conflict. `not same_device` is NEVER treated as a proven
     false relation.
  2. `explicit_evidence_constraint_conflicts`: candidate temporal links that directly
     conflict with checkable telemetry properties:
     - `endpoint_quality_or_test_bit_conflict`: invalid/unknown quality bits, `cot_test=True`,
       or `cross_vantage_payload_conflict`.
     - `endpoint_transient_not_sustained_conflict`: measurement step that fails post-sample
       persistence (`< 2` post samples or `< 80%` consistent samples).
     - `same_device_direction_or_ratio_conflict`: same-device endpoints with opposing
       magnitude change directions, incompatible shift ratios (`< 0.5`), or non-opposing
       active-power signs across `from`/`to`.
     - `same_device_change_type_or_side_conflict`: same-device endpoints with mismatched
       `step_kinds` (`to_zero` vs `level_shift`) or non-complementary sides (`from` vs `from`).
     - `same_asdu_co_report_temporal_ordering_conflict`: information objects carried in
       the exact same IEC-104 ASDU (`same_asdu`) treated as a sequential temporal step.
  3. `corroborated_same_device_candidates`: same-device, separate-ASDU pairs that pass
     all quality, persistence, side-complementarity, and direction checks.
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
            "transaction_id": tx["transaction_id"],
            "time": float(cmd["timestamp"]),
            "time_end": float(cmd["timestamp_end"]),
            "entity": cmd["entity"],
            "device_stem": tx.get("device_stem"),
            "rtu_ip": tx.get("rtu_ip"),
            "master_ip": tx.get("master_ip"),
            "asdu_key": f"TX-{cmd['message_id']}",
            "quality_ok": cmd.get("cot_test") is False,
            "transient_not_sustained": False,
            "lacks_prior_baseline": False,
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
                "transaction_id": tx["transaction_id"],
                "time": float(ack["timestamp"]),
                "time_end": float(ack["timestamp_end"]),
                "entity": ack["entity"],
                "device_stem": tx.get("device_stem"),
                "rtu_ip": tx.get("rtu_ip"),
                "master_ip": tx.get("master_ip"),
                "asdu_key": f"TX-{ack['message_id']}",
                "quality_ok": ack.get("cot_test") is False and ack.get("cot_negative") is False,
                "transient_not_sustained": False,
                "lacks_prior_baseline": False,
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
            transient_bad = False
            no_prior = False
        elif atype == "spontaneous_state_report":
            q_ok = a.get("quality_good") is True and not has_conflict
            no_prior = "no_prior_state_value_in_window" in issues or "pre_sample_gap_exceeded" in issues
            transient_bad = (
                "not_sustained_in_later_samples" in issues
                or "state_value_unchanged" in issues
            )
        else:
            q_ok = a.get("quality_good") is True and not has_conflict
            no_prior = "pre_sample_gap_exceeded" in issues
            transient_bad = (
                "not_sustained_in_later_samples" in issues
                or "insufficient_post_samples" in issues
                or a.get("sustained_in_later_samples") is not True
            )
        events.append({
            "event_id": a["anchor_id"],
            "origin_kind": atype,
            "transaction_id": None,
            "time": float(a["time"]),
            "time_end": float(a.get("time_end", a["time"])),
            "entity": a["entity"],
            "device_stem": a.get("device_stem"),
            "rtu_ip": a.get("rtu_ip"),
            "master_ip": a.get("master_ip"),
            "host_ip": a.get("host_ip"),
            "asdu_key": a.get("asdu_key"),
            "quality_ok": q_ok,
            "transient_not_sustained": transient_bad,
            "lacks_prior_baseline": no_prior,
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
    """Separate unsubstantiated temporal candidates from explicit evidence constraint conflicts."""
    same_device = bool(left.get("device_stem")) and left.get("device_stem") == right.get("device_stem")
    same_asdu = bool(left.get("asdu_key")) and left.get("asdu_key") == right.get("asdu_key")
    same_rtu = bool(left.get("rtu_ip")) and left.get("rtu_ip") == right.get("rtu_ip")
    same_tx = bool(left.get("transaction_id")) and left.get("transaction_id") == right.get("transaction_id")

    explicit_conflicts: list[str] = []
    unsubstantiated_reasons: list[str] = []

    if same_asdu:
        explicit_conflicts.append("same_asdu_co_report_temporal_ordering_conflict")
    if not left["quality_ok"] or not right["quality_ok"]:
        explicit_conflicts.append("endpoint_quality_or_test_bit_conflict")
    if left["transient_not_sustained"] or right["transient_not_sustained"]:
        explicit_conflicts.append("endpoint_transient_not_sustained_conflict")

    if same_device and not same_asdu and not same_tx:
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
                explicit_conflicts.append("same_device_change_type_or_side_conflict")
            else:
                if set(left.get("step_kinds") or []) != set(right.get("step_kinds") or []):
                    explicit_conflicts.append("same_device_change_type_or_side_conflict")
                dir_conflict = False
                for q in shared_q:
                    lp, rp = l_by_base[q], r_by_base[q]
                    if lp.get("step_kind") != rp.get("step_kind"):
                        if "same_device_change_type_or_side_conflict" not in explicit_conflicts:
                            explicit_conflicts.append("same_device_change_type_or_side_conflict")
                    elif lp.get("step_kind") == "level_shift":
                        l_delta = abs(float(lp["post_value"])) - abs(float(lp["pre_value"]))
                        r_delta = abs(float(rp["post_value"])) - abs(float(rp["pre_value"]))
                        if l_delta * r_delta <= 0:
                            dir_conflict = True
                        l_ratio = abs(float(lp["post_value"])) / max(abs(float(lp["pre_value"])), MAGNITUDE_FLOOR)
                        r_ratio = abs(float(rp["post_value"])) / max(abs(float(rp["pre_value"])), MAGNITUDE_FLOOR)
                        if min(l_ratio, r_ratio) / max(l_ratio, r_ratio) < 0.5:
                            dir_conflict = True
                        if q in ("active_power", "p") and float(lp["post_value"]) * float(rp["post_value"]) >= 0:
                            dir_conflict = True
                if dir_conflict:
                    explicit_conflicts.append("same_device_direction_or_ratio_conflict")
        elif left["origin_kind"] == "spontaneous_state_report" and right["origin_kind"] == "measurement_step":
            if left.get("lacks_prior_baseline"):
                unsubstantiated_reasons.append("state_report_lacks_prior_in_window_baseline")
            elif left.get("transition_status") != "state_change_observed":
                explicit_conflicts.append("same_device_change_type_or_side_conflict")

    if not same_device and not same_asdu:
        unsubstantiated_reasons.append("cross_device_no_protocol_or_topology_evidence")
    if left.get("lacks_prior_baseline") or right.get("lacks_prior_baseline"):
        if "state_report_lacks_prior_in_window_baseline" not in unsubstantiated_reasons:
            unsubstantiated_reasons.append("endpoint_lacks_prior_in_window_baseline")

    has_explicit_conflict = bool(explicit_conflicts)
    is_unsubstantiated = (not has_explicit_conflict) and bool(unsubstantiated_reasons)
    is_corroborated = (not has_explicit_conflict) and (not is_unsubstantiated) and same_device and not same_asdu

    if same_asdu:
        pair_topology = "same_asdu_co_report"
    elif same_device:
        pair_topology = "same_device_separate_asdu"
    else:
        pair_topology = "cross_device"

    return {
        "pair_topology": pair_topology,
        "same_device": same_device,
        "same_asdu": same_asdu,
        "same_rtu": same_rtu,
        "independent_rtu": bool(left.get("rtu_ip")) and bool(right.get("rtu_ip")) and not same_rtu,
        "explicit_conflicts": explicit_conflicts,
        "has_explicit_conflict": has_explicit_conflict,
        "unsubstantiated_reasons": unsubstantiated_reasons,
        "is_unsubstantiated_candidate": is_unsubstantiated,
        "is_corroborated_candidate": is_corroborated,
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
    unbounded_explicit_conflict_count = 0
    unbounded_unsubstantiated_count = 0

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
            if audit["has_explicit_conflict"]:
                unbounded_explicit_conflict_count += 1
            elif audit["is_unsubstantiated_candidate"]:
                unbounded_unsubstantiated_count += 1

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
                    "pair_topology": audit["pair_topology"],
                    "same_device": audit["same_device"],
                    "same_asdu": audit["same_asdu"],
                    "independent_rtu": audit["independent_rtu"],
                    "explicit_conflicts": audit["explicit_conflicts"],
                    "has_explicit_conflict": audit["has_explicit_conflict"],
                    "unsubstantiated_reasons": audit["unsubstantiated_reasons"],
                    "is_unsubstantiated_candidate": audit["is_unsubstantiated_candidate"],
                    "is_corroborated_candidate": audit["is_corroborated_candidate"],
                    "evidence_ids": list(dict.fromkeys([*left["evidence_ids"][:2], *right["evidence_ids"][:2]])),
                })

    explicit_conflict_breakdown = {
        k: sum(1 for r in bounded_relations if k in r["explicit_conflicts"])
        for k in (
            "endpoint_quality_or_test_bit_conflict",
            "endpoint_transient_not_sustained_conflict",
            "same_device_direction_or_ratio_conflict",
            "same_device_change_type_or_side_conflict",
            "same_asdu_co_report_temporal_ordering_conflict",
        )
    }
    explicit_conflict_total = sum(1 for r in bounded_relations if r["has_explicit_conflict"])
    unsubstantiated_total = sum(1 for r in bounded_relations if r["is_unsubstantiated_candidate"])
    corroborated_total = sum(1 for r in bounded_relations if r["is_corroborated_candidate"])

    cross_device_total = sum(1 for r in bounded_relations if r["pair_topology"] == "cross_device")
    same_device_sep_asdu_total = sum(1 for r in bounded_relations if r["pair_topology"] == "same_device_separate_asdu")
    same_asdu_total = sum(1 for r in bounded_relations if r["pair_topology"] == "same_asdu_co_report")

    mirage_supported_steps = sum(
        len(s.get("confirmed_and_supported_steps") or [])
        for s in (mirage_storylines.get("storylines") or [])
    )
    mirage_bridges = len(mirage_synthesis.get("verified_element_bridges") or [])

    return {
        "baseline_id": "B1_temporal_only",
        "method_description": (
            "Temporal-Only Reconstruction using identical event observations, timestamps, "
            "vantage deduplication, 15.0s horizon, and per-event cross-device link cap (6), "
            "without Behavioral Consistency Gate, Lineage Corroboration, or Incident Synthesis."
        ),
        "epistemic_note": (
            "Candidate temporal relations are NOT false causal inferences. They are partitioned "
            "into (1) `unsubstantiated_temporal_candidates` (temporally proximate without direct "
            "protocol/topology link, not proven false), (2) `explicit_evidence_constraint_conflicts` "
            "(direct quality, test-bit, persistence, direction, change-type, or same-ASDU conflicts), "
            "and (3) `corroborated_same_device_candidates`."
        ),
        "event_count": len(events),
        "unbounded_15s_temporal_pair_count": all_window_pair_count,
        "unbounded_15s_explicit_conflict_count": unbounded_explicit_conflict_count,
        "unbounded_15s_unsubstantiated_candidate_count": unbounded_unsubstantiated_count,
        "candidate_temporal_relation_count": len(bounded_relations),
        "topology_breakdown": {
            "cross_device_candidate_count": cross_device_total,
            "same_device_separate_asdu_candidate_count": same_device_sep_asdu_total,
            "same_asdu_co_report_candidate_count": same_asdu_total,
        },
        "unsubstantiated_temporal_candidate_count": unsubstantiated_total,
        "explicit_evidence_constraint_conflict_count": explicit_conflict_total,
        "explicit_conflict_breakdown": explicit_conflict_breakdown,
        "corroborated_same_device_candidate_count": corroborated_total,
        # Combined non-corroborated count (unsubstantiated + explicit conflicts) kept for transparent reconciliation
        "non_corroborated_total_count": unsubstantiated_total + explicit_conflict_total,
        "mirage_comparison": {
            "mirage_supported_storyline_step_count": mirage_supported_steps,
            "mirage_cross_rtu_verified_bridge_count": mirage_bridges,
            "explicit_conflicts_eliminated_by_mirage": explicit_conflict_total,
            "unsubstantiated_candidates_held_unresolved_by_mirage": unsubstantiated_total,
        },
        "sample_candidate_relations": bounded_relations[:30],
    }
