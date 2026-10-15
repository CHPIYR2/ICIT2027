"""Behavioral facts and relations for windows without an IEC-104 control command.

Anchors become graph facts. Relations between them are typed by the evidence
and behavioral consistency criteria that link them, never by time alone:

- Same device reported in a separate ASDU that passes the behavioral transition
  consistency gate (`evaluate_behavioral_relation_consistency`):
  `corroborated_same_device_behavioral_transition` (`measurement_state_transition`,
  `claim_level="observed_fact"`, `verification_status="supported"`).
- Same device reported in a separate ASDU within the time horizon that does NOT
  pass the behavioral transition consistency gate (e.g. unverified prior state,
  unverified post-sample persistence, same-endpoint repeated jump, or mismatched
  change type/direction): `same_entity_sequential_observation`
  (`sequential_observation`, `claim_level="sequential_observation"`,
  `verification_status="unverified"`). It records a sequential observation on
  the same grid element without claiming a corroborated transition.
- Different devices carried by one ASDU: `same_iec104_asdu`, a shared packet
  container. It says they were reported together, not that one affected the other.
- Different devices in separate messages within the horizon:
  `cross_device_temporal_candidate`, kept unresolved. Shared RTU, host IP, or
  ARP target address overlap is recorded as context but does not upgrade the
  candidate.
- IPAL rows of the anchor's points: `temporal_correspondence`; the common
  source is unconfirmed because IPAL rows carry no packet reference.
"""
from __future__ import annotations
from .anchors import MAGNITUDE_FLOOR, split_attribute_endpoint

HORIZON_SECONDS = 15.0
MAX_CANDIDATES_PER_ANCHOR = 6
MIN_LEVEL_SHIFT_RATIO_AGREEMENT = 0.5
_KIND = {
    "spontaneous_state_report": "iec104_state_report",
    "measurement_step": "iec104_measurement_step",
    "communication_change": "iec104_link_activity",
    "arp_activity_increase": "arp_activity",
}
_STATE_ATTRS = {"is_closed", "closed", "is_connected", "in_service"}
_FLOW_ATTRS = {"active_power", "reactive_power", "current", "p", "q", "i"}


def _points_summary(anchor: dict) -> list[dict]:
    out = []
    for p in anchor.get("points") or []:
        base_attr = p.get("base_attribute")
        side = p.get("endpoint_side")
        if base_attr is None and p.get("attribute"):
            base_attr, side = split_attribute_endpoint(p.get("attribute"))
        out.append({
            "attribute": p["attribute"],
            "base_attribute": base_attr,
            "endpoint_side": side,
            "ca_ioa": p["ca_ioa"],
            "step_kind": p["step_kind"],
            "pre_value": p["pre_value"],
            "post_value": p["post_value"],
            "pre_time": p["pre_time"],
            "post_time": p["post_time"],
            "pre_quality_good": p.get("pre_quality_good"),
            "post_quality_good": p.get("post_quality_good"),
            "pre_cot_test": p.get("pre_cot_test"),
            "post_cot_test": p.get("post_cot_test"),
            "pre_sample_gap_seconds": p.get("pre_sample_gap_seconds"),
            "later_samples_consistent": p.get("later_samples_consistent"),
            "later_samples_total": p.get("later_samples_total"),
            "persistence_ratio": p.get("persistence_ratio"),
            "quality_ok": p.get("quality_ok"),
            "sustained": p.get("sustained"),
            "verification_status": p.get("verification_status"),
            "verification_issues": list(p.get("verification_issues") or []),
        })
    return out


def add_anchor_facts(anchors: list[dict], add_fact) -> dict[str, dict]:
    """Add one fact per anchor plus one IPAL fact per anchor. Returns anchor_id -> fact ids."""
    placed: dict[str, dict] = {}
    for anchor in anchors:
        if anchor.get("covered_by_transaction"):
            continue
        evidence = list(dict.fromkeys([
            *anchor["evidence_ids"],
            *anchor.get("prior_evidence_ids", []),
            *(e for p in anchor.get("points", []) for e in p["pre_evidence_ids"]),
        ]))
        if anchor.get("asdu_key"):
            container = f"SRC-ASDU-{anchor['asdu_key']}"
        else:
            container = f"SRC-{anchor['anchor_type'].upper()}-{anchor['entity']}"
        fid = add_fact(
            key=("behavioral_anchor", anchor["anchor_id"]),
            preferred_id=f"BA{anchor['anchor_id'][1:]}",
            time=anchor["time"],
            time_end=anchor.get("time_end", anchor["time"]),
            entity=anchor["entity"],
            ca_ioa=anchor.get("ca_ioa"),
            modality="network",
            kind=_KIND[anchor["anchor_type"]],
            role=anchor["anchor_type"],
            record_class="direct_observation",
            value=anchor.get("value"),
            value_present=anchor.get("value") is not None,
            vantages=anchor.get("vantages") or [],
            vantage_capture_count=len(anchor["evidence_ids"]),
            evidence_ids=evidence,
            source_containers=[container],
            transaction_id=None,
            protocol_meta={
                "anchor_id": anchor["anchor_id"],
                "anchor_type": anchor["anchor_type"],
                "anchor_rank": anchor["rank"],
                "anchor_score": anchor["score"],
                "verification_status": anchor.get("verification_status", "unverified_observation"),
                "verification_issues": list(anchor.get("verification_issues") or []),
                "rtu_ip": anchor.get("rtu_ip"),
                "master_ip": anchor.get("master_ip"),
                "host_ip": anchor.get("host_ip"),
                "asdu_key": anchor.get("asdu_key"),
                "transition_status": anchor.get("transition_status"),
                "prior_value": anchor.get("prior_value"),
                "prior_time": anchor.get("prior_time"),
                "pre_quality_good": anchor.get("pre_quality_good"),
                "pre_cot_test": anchor.get("pre_cot_test"),
                "cot_test": anchor.get("cot_test"),
                "step_kinds": anchor.get("step_kinds"),
                "points_summary": _points_summary(anchor),
                "event_kinds": anchor.get("event_kinds"),
                "quality_good": anchor.get("quality_good"),
                "sustained_in_later_samples": anchor.get("sustained_in_later_samples"),
                "arp_targets": anchor.get("targets"),
                "arp_target_first_seen": anchor.get("target_first_seen"),
            },
            observation=anchor["observation"],
            device_stem=anchor.get("device_stem"),
        )
        entry = {"fact_id": fid, "ipal_fact_id": None}
        rows = anchor.get("ipal_rows") or []
        if rows:
            entry["ipal_fact_id"] = add_fact(
                key=("behavioral_ipal", anchor["anchor_id"]),
                preferred_id=f"BI{anchor['anchor_id'][1:]}",
                time=min(r["time"] for r in rows),
                time_end=max(r["time"] for r in rows),
                entity=f"{anchor['device_stem']}:" + ",".join(sorted({r['entity'].split(':', 1)[1] for r in rows})),
                ca_ioa=rows[0].get("ca_ioa"),
                modality="electrical",
                kind="electrical_update",
                role="ipal_correspondence",
                record_class="transcription",
                value=rows[0].get("value"),
                value_present=rows[0].get("value") is not None,
                vantages=["ipal_state"],
                vantage_capture_count=len(rows),
                evidence_ids=[r["evidence_id"] for r in rows],
                source_containers=[f"SRC-IPAL-{anchor['anchor_id']}"],
                transaction_id=None,
                protocol_meta={
                    "anchor_id": anchor["anchor_id"],
                    "match_basis": sorted({r["match_basis"] for r in rows}),
                    "source_binding": "unconfirmed_temporal_correspondence",
                    "parent_evidence_id": None,
                },
                observation="; ".join(f"IPAL {r['entity']}={r['value']} @ {round(r['time'], 3)}" for r in rows[:6]),
                counts_as_independent_source=False,
                device_stem=anchor.get("device_stem"),
            )
        placed[anchor["anchor_id"]] = entry
    return placed


def evaluate_behavioral_relation_consistency(
    left_fact: dict,
    right_fact: dict,
    *,
    horizon_seconds: float = HORIZON_SECONDS,
) -> dict:
    """Testable consistency gate separating corroborated behavioral transitions from sequential observations."""
    lm = left_fact.get("protocol_meta") or {}
    rm = right_fact.get("protocol_meta") or {}
    failed: list[str] = []

    same_device = bool(left_fact.get("device_stem")) and left_fact.get("device_stem") == right_fact.get("device_stem")
    if not same_device:
        failed.append("device_stem_mismatch")
    separate_asdu = bool(lm.get("asdu_key")) and bool(rm.get("asdu_key")) and lm.get("asdu_key") != rm.get("asdu_key")
    if not separate_asdu:
        failed.append("same_or_missing_asdu")

    dt = round(float(right_fact["time"]) - float(left_fact["time"]), 6)
    temporal_window_ok = 0.0 <= dt <= horizon_seconds
    if not temporal_window_ok:
        failed.append("outside_temporal_horizon")

    left_quality_ok = lm.get("quality_good") is True
    right_quality_ok = rm.get("quality_good") is True
    left_sustained = lm.get("sustained_in_later_samples") is True
    right_sustained = rm.get("sustained_in_later_samples") is True
    left_verified = (
        lm.get("verification_status") == "verified_observation"
        and left_quality_ok
        and left_sustained
    )
    right_verified = (
        rm.get("verification_status") == "verified_observation"
        and right_quality_ok
        and right_sustained
    )
    if not left_quality_ok:
        failed.append("left_quality_or_test_bit_not_good")
    if not right_quality_ok:
        failed.append("right_quality_or_test_bit_not_good")
    if not left_sustained:
        failed.append("left_not_sustained")
    if not right_sustained:
        failed.append("right_not_sustained")
    if not left_verified:
        failed.append("left_anchor_unverified")
    if not right_verified:
        failed.append("right_anchor_unverified")

    l_type = lm.get("anchor_type") or left_fact.get("role")
    r_type = rm.get("anchor_type") or right_fact.get("role")
    l_points = lm.get("points_summary") or []
    r_points = rm.get("points_summary") or []

    intervals_aligned = False
    attribute_compatible = False
    change_compatible = False
    matched_quantities: list[str] = []
    pair_mode = f"{l_type}->{r_type}"

    if l_type == "measurement_step" and r_type == "measurement_step" and l_points and r_points:
        l_post_max = max(float(p["post_time"]) for p in l_points)
        r_pre_min = min(float(p["pre_time"]) for p in r_points)
        intervals_aligned = r_pre_min <= l_post_max + 1.0
        if not intervals_aligned:
            failed.append("transition_intervals_disjoint")

        l_sides = {p.get("endpoint_side") for p in l_points}
        r_sides = {p.get("endpoint_side") for p in r_points}
        complementary_sides = (
            l_sides in ({"from"}, {"to"})
            and r_sides in ({"from"}, {"to"})
            and l_sides != r_sides
        )
        l_by_base = {p["base_attribute"]: p for p in l_points if p.get("base_attribute")}
        r_by_base = {p["base_attribute"]: p for p in r_points if p.get("base_attribute")}
        matched_quantities = sorted(set(l_by_base) & set(r_by_base))
        attribute_compatible = complementary_sides and bool(matched_quantities)
        if not complementary_sides:
            failed.append("endpoints_not_complementary")
        elif not matched_quantities:
            failed.append("no_shared_measurement_quantity")

        l_kinds = set(lm.get("step_kinds") or [p["step_kind"] for p in l_points])
        r_kinds = set(rm.get("step_kinds") or [p["step_kind"] for p in r_points])
        if attribute_compatible:
            kind_mismatch = l_kinds != r_kinds or any(
                l_by_base[q]["step_kind"] != r_by_base[q]["step_kind"]
                for q in matched_quantities
            )
            if kind_mismatch:
                failed.append("change_type_mismatch")
            else:
                dir_ok = True
                for q in matched_quantities:
                    lp, rp = l_by_base[q], r_by_base[q]
                    if lp["step_kind"] == "level_shift":
                        l_delta = abs(float(lp["post_value"])) - abs(float(lp["pre_value"]))
                        r_delta = abs(float(rp["post_value"])) - abs(float(rp["pre_value"]))
                        if l_delta * r_delta <= 0:
                            dir_ok = False
                            failed.append(f"magnitude_direction_mismatch:{q}")
                            continue
                        l_ratio = abs(float(lp["post_value"])) / max(abs(float(lp["pre_value"])), MAGNITUDE_FLOOR)
                        r_ratio = abs(float(rp["post_value"])) / max(abs(float(rp["pre_value"])), MAGNITUDE_FLOOR)
                        if min(l_ratio, r_ratio) / max(l_ratio, r_ratio) < MIN_LEVEL_SHIFT_RATIO_AGREEMENT:
                            dir_ok = False
                            failed.append(f"magnitude_ratio_mismatch:{q}")
                        if q in ("active_power", "p") and float(lp["post_value"]) * float(rp["post_value"]) >= 0:
                            dir_ok = False
                            failed.append(f"active_power_flow_sign_mismatch:{q}")
                change_compatible = dir_ok
    elif l_type == "spontaneous_state_report" and r_type == "measurement_step" and r_points:
        r_pre_min = min(float(p["pre_time"]) for p in r_points)
        r_post_max = max(float(p["post_time"]) for p in r_points)
        l_time = float(left_fact["time"])
        intervals_aligned = r_pre_min <= l_time + 1.0 and l_time <= r_post_max + 1.0
        if not intervals_aligned:
            failed.append("transition_intervals_disjoint")

        l_attr = left_fact["entity"].split(":", 1)[1] if ":" in left_fact["entity"] else ""
        r_bases = {p.get("base_attribute") for p in r_points}
        matched_quantities = sorted(r_bases & _FLOW_ATTRS)
        attribute_compatible = l_attr in _STATE_ATTRS and bool(matched_quantities)
        if not attribute_compatible:
            failed.append("state_to_measurement_attribute_incompatible")
        else:
            r_kinds = set(rm.get("step_kinds") or [p["step_kind"] for p in r_points])
            prior_val = lm.get("prior_value")
            post_val = left_fact.get("value")
            if (
                lm.get("transition_status") == "state_change_observed"
                and prior_val == 1.0 and post_val == 0.0
                and r_kinds == {"to_zero"}
            ) or (
                lm.get("transition_status") == "state_change_observed"
                and prior_val == 0.0 and post_val == 1.0
                and r_kinds == {"from_zero"}
            ):
                change_compatible = True
            else:
                failed.append("state_to_measurement_change_mismatch")
    else:
        failed.append("unsupported_anchor_type_pair")

    dedup_failed = list(dict.fromkeys(failed))
    gate_passed = (
        same_device
        and separate_asdu
        and temporal_window_ok
        and intervals_aligned
        and left_verified
        and right_verified
        and attribute_compatible
        and change_compatible
        and not dedup_failed
    )
    independent_rtu = bool(lm.get("rtu_ip")) and bool(rm.get("rtu_ip")) and lm.get("rtu_ip") != rm.get("rtu_ip")
    return {
        "gate_passed": gate_passed,
        "pair_mode": pair_mode,
        "same_device_stem": same_device,
        "separate_asdu": separate_asdu,
        "temporal_window_ok": temporal_window_ok,
        "dt_seconds": dt,
        "transition_intervals_aligned": intervals_aligned,
        "left_anchor_verified": left_verified,
        "right_anchor_verified": right_verified,
        "left_quality_good": left_quality_ok,
        "right_quality_good": right_quality_ok,
        "left_sustained": left_sustained,
        "right_sustained": right_sustained,
        "left_verification_issues": list(lm.get("verification_issues") or []),
        "right_verification_issues": list(rm.get("verification_issues") or []),
        "attribute_compatible": attribute_compatible,
        "matched_quantities": matched_quantities,
        "change_type_and_direction_compatible": change_compatible,
        "independent_rtu_support": independent_rtu,
        "failed_conditions": dedup_failed,
        "recommended_relation_category": "measurement_state_transition" if gate_passed else "sequential_observation",
        "recommended_relation_type": (
            "corroborated_same_device_behavioral_transition"
            if gate_passed else "same_entity_sequential_observation"
        ),
        "recommended_claim_level": "observed_fact" if gate_passed else "sequential_observation",
        "recommended_verification_status": "supported" if gate_passed else "unverified",
    }


def audit_anchor_lineage(db, anchors: list[dict], placed: dict[str, dict], *, tolerance: float = 0.5) -> dict:
    """Check every anchor evidence row against the point, link or host it is cited for."""
    expected: list[tuple[str, str, dict]] = []
    for anchor in anchors:
        aid = anchor["anchor_id"]
        if aid not in placed:
            continue
        t, te = anchor["time"], anchor.get("time_end", anchor["time"])
        kind = anchor["anchor_type"]
        if kind == "spontaneous_state_report":
            point = {"entity": {anchor["entity"]}, "ca_ioa": {anchor["ca_ioa"]}}
            expected += [(aid, e, {**point, "lo": t - tolerance, "hi": te + tolerance}) for e in anchor["evidence_ids"]]
            expected += [(aid, e, {**point, "lo": float("-inf"), "hi": t}) for e in anchor.get("prior_evidence_ids", [])]
        elif kind == "measurement_step":
            for p in anchor["points"]:
                point = {"entity": {p["entity"]}, "ca_ioa": {p["ca_ioa"]}}
                expected += [(aid, e, {**point, "lo": p["post_time"] - tolerance, "hi": p["post_time"] + tolerance})
                             for e in p["evidence_ids"]]
                expected += [(aid, e, {**point, "lo": p["pre_time"] - tolerance, "hi": p["pre_time"] + tolerance})
                             for e in p["pre_evidence_ids"]]
        elif kind == "communication_change":
            hosts = {anchor["master_ip"], anchor["rtu_ip"]}
            expected += [(aid, e, {"hosts": hosts, "lo": t, "hi": te}) for e in anchor["evidence_ids"]]
        elif kind == "arp_activity_increase":
            expected += [(aid, e, {"src_ip": anchor["host_ip"], "lo": t, "hi": te}) for e in anchor["evidence_ids"]]
        if anchor.get("ipal_rows"):
            entities = {p["entity"] for p in anchor.get("points", [])}
            for r in anchor["ipal_rows"]:
                rule = {"lo": t - tolerance, "hi": t + 2.5}
                if entities:
                    rule["entity"] = entities
                else:
                    rule["device_stem"] = anchor["device_stem"]
                expected.append((aid, r["evidence_id"], rule))

    ids = list(dict.fromkeys(e for _, e, _ in expected))
    rows: dict[str, dict] = {}
    for i in range(0, len(ids), 100):
        for row in db.get(ids[i:i + 100])["rows"]:
            rows[row["evidence_id"]] = row
    failures = []
    for aid, eid, rule in expected:
        row = rows.get(eid)
        if row is None:
            continue
        reasons = []
        if "entity" in rule and row.get("entity") not in rule["entity"]:
            reasons.append("entity_not_an_anchor_point")
        if "ca_ioa" in rule and row.get("ca_ioa") not in rule["ca_ioa"]:
            reasons.append("ca_ioa_not_an_anchor_point")
        if "device_stem" in rule and str(row.get("entity", "")).split(":", 1)[0] != rule["device_stem"]:
            reasons.append("device_differs_from_anchor")
        if "hosts" in rule and not {row.get("src_ip"), row.get("dst_ip")} <= rule["hosts"]:
            reasons.append("hosts_outside_anchor_link")
        if "src_ip" in rule and row.get("src_ip") != rule["src_ip"]:
            reasons.append("source_differs_from_anchor_host")
        if not (rule["lo"] - 1e-9 <= row["timestamp"] <= rule["hi"] + 1e-9):
            reasons.append("time_outside_cited_sample")
        failures += [{"anchor_id": aid, "evidence_id": eid, "reason": r} for r in reasons]
    return {
        "checked_anchor_count": len(placed),
        "checked_reference_count": len(expected),
        "missing_ids": sorted(set(ids) - set(rows)),
        "row_check_failures": failures,
    }


def add_behavioral_edges(placed: dict[str, dict], facts_by_id: dict[str, dict], add_edge) -> None:
    anchor_facts = sorted((facts_by_id[e["fact_id"]] for e in placed.values()), key=lambda f: (f["time"], f["fact_id"]))
    for entry in placed.values():
        if entry["ipal_fact_id"]:
            fact = facts_by_id[entry["fact_id"]]
            ipal = facts_by_id[entry["ipal_fact_id"]]
            add_edge(
                source_fid=fact["fact_id"], target_fid=ipal["fact_id"],
                relation_category="temporal_correspondence",
                relation_type="temporally_aligned_same_point_stream"
                if "same_ca_ioa" in ipal["protocol_meta"]["match_basis"] else "temporally_aligned_same_device_ipal_row",
                claim_level="temporal_correspondence",
                verification_status="common_source_unconfirmed",
                graph_consistency_gate_status="no_lineage_temporal_correspondence_only",
                independent_support=False,
                temporal_condition=f"IPAL rows within [-0.5s, +2.5s] of {round(fact['time'], 3)}",
                support_basis=(
                    f"IPAL rows of {ipal['entity']} near the IEC-104 observation. IPAL state rows carry no packet "
                    "reference, so a common source is not confirmed and the rows are not independent evidence."
                ),
            )
    for i, left in enumerate(anchor_facts):
        candidates = 0
        for right in anchor_facts[i + 1:]:
            dt = right["time"] - left["time"]
            if dt > HORIZON_SECONDS:
                break
            lm, rm = left["protocol_meta"], right["protocol_meta"]
            same_device = bool(left.get("device_stem")) and left.get("device_stem") == right.get("device_stem")
            same_asdu = bool(lm.get("asdu_key")) and lm.get("asdu_key") == rm.get("asdu_key")
            if same_device and not same_asdu:
                gate = evaluate_behavioral_relation_consistency(left, right, horizon_seconds=HORIZON_SECONDS)
                if gate["gate_passed"]:
                    add_edge(
                        source_fid=left["fact_id"], target_fid=right["fact_id"],
                        relation_category="measurement_state_transition",
                        relation_type="corroborated_same_device_behavioral_transition",
                        claim_level="observed_fact",
                        verification_status="supported",
                        graph_consistency_gate_status="passed_behavioral_consistency_gate",
                        independent_support=gate["independent_rtu_support"],
                        temporal_condition=f"0 <= dt ({round(dt, 3)}s) <= {HORIZON_SECONDS}s; transition_intervals_aligned=True",
                        support_basis=(
                            f"Both verified observations belong to {left['device_stem']} (separate ASDUs from "
                            f"RTU {lm.get('rtu_ip')} then {rm.get('rtu_ip')}), match on quantities "
                            f"{gate['matched_quantities']} with compatible change type/direction "
                            f"{lm.get('step_kinds') or lm.get('transition_status')} -> "
                            f"{rm.get('step_kinds') or rm.get('transition_status')}, good quality, T=0, and "
                            "sustained post-change samples. Corroborated same-element behavior; not a causal claim."
                        ),
                        consistency_gate=gate,
                    )
                else:
                    add_edge(
                        source_fid=left["fact_id"], target_fid=right["fact_id"],
                        relation_category="sequential_observation",
                        relation_type="same_entity_sequential_observation",
                        claim_level="sequential_observation",
                        verification_status="unverified",
                        graph_consistency_gate_status="failed_behavioral_consistency_gate",
                        independent_support=False,
                        temporal_condition=f"0 <= dt ({round(dt, 3)}s) <= {HORIZON_SECONDS}s",
                        support_basis=(
                            f"Sequential observations on {left['device_stem']} in separate ASDUs "
                            f"(RTU {lm.get('rtu_ip')} then {rm.get('rtu_ip')}), but behavioral transition "
                            f"consistency gate failed: {gate['failed_conditions']}. Recorded as a sequential "
                            "same-entity observation only, not a supported behavioral transition."
                        ),
                        consistency_gate=gate,
                    )
            elif same_asdu:
                add_edge(
                    source_fid=left["fact_id"], target_fid=right["fact_id"],
                    relation_category="shared_source",
                    relation_type="same_iec104_asdu",
                    claim_level="observed_fact",
                    verification_status="supported",
                    graph_consistency_gate_status="direct_record_observation",
                    independent_support=False,
                    temporal_condition="same ASDU (source, destination, APCI send sequence)",
                    support_basis=(
                        f"{left['entity']} and {right['entity']} were carried by one ASDU from RTU {lm.get('rtu_ip')}. "
                        "Reported together; whether one device's change relates to the other's is not established."
                    ),
                )
            elif candidates < MAX_CANDIDATES_PER_ANCHOR:
                context = []
                if lm.get("rtu_ip") and lm.get("rtu_ip") == rm.get("rtu_ip"):
                    context.append(f"same RTU {lm.get('rtu_ip')}")
                hosts_l = {lm.get("rtu_ip"), lm.get("host_ip"), lm.get("master_ip")} - {None}
                hosts_r = {rm.get("rtu_ip"), rm.get("host_ip"), rm.get("master_ip")} - {None}
                if hosts_l & hosts_r and not context:
                    context.append(f"shared host {sorted(hosts_l & hosts_r)}")
                for arp, other in ((lm, rm), (rm, lm)):
                    hit = {other.get("rtu_ip"), other.get("master_ip")} & set(arp.get("arp_targets") or {})
                    if hit:
                        first_seen = arp.get("arp_target_first_seen") or {}
                        timing = [
                            f"{h} first ARP at {round(first_seen[h], 3)}"
                            for h in sorted(hit) if h in first_seen
                        ]
                        context.append(
                            f"ARP from {arp['host_ip']} addressed {sorted(hit)} "
                            f"({sum(arp['arp_targets'][h] for h in hit)} packets"
                            + (f"; {', '.join(timing)}" if timing else "")
                            + ")"
                        )
                add_edge(
                    source_fid=left["fact_id"], target_fid=right["fact_id"],
                    relation_category="temporal_cooccurrence",
                    relation_type="cross_device_temporal_candidate",
                    claim_level="temporal_cooccurrence",
                    verification_status="unresolved",
                    graph_consistency_gate_status="no_direct_relation_evidence",
                    independent_support=False,
                    temporal_condition=f"0 <= dt ({round(dt, 3)}s) <= {HORIZON_SECONDS}s",
                    support_basis=(
                        f"{right['entity']} changed {round(dt, 3)}s after {left['entity']}"
                        + (f" ({'; '.join(context)})" if context else "")
                        + ". No protocol link, shared message or topology evidence connects them; time proximity "
                        "is a candidate only."
                    ),
                )
                candidates += 1
