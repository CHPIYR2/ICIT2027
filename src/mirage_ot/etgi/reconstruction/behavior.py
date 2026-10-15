"""Behavioral facts and relations for windows without an IEC-104 control command.

Anchors become graph facts. Relations between them are typed by the evidence
that links them, never by time alone:

- Same device reported in a separate ASDU (another RTU or another message):
  `same_device_behavior_in_separate_asdu`, a supported observed relation.
- Different devices carried by one ASDU: `same_iec104_asdu`, a shared packet
  container. It says they were reported together, not that one affected the other.
- Different devices in separate messages within the horizon:
  `cross_device_temporal_candidate`, kept unresolved. Shared RTU or host IP is
  recorded as context but does not upgrade the candidate.
- IPAL rows of the anchor's points: `temporal_correspondence`; the common
  source is unconfirmed because IPAL rows carry no packet reference.
"""
from __future__ import annotations

HORIZON_SECONDS = 15.0
MAX_CANDIDATES_PER_ANCHOR = 6
_KIND = {
    "spontaneous_state_report": "iec104_state_report",
    "measurement_step": "iec104_measurement_step",
    "communication_change": "iec104_link_activity",
    "arp_activity_increase": "arp_activity",
}


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
                "rtu_ip": anchor.get("rtu_ip"),
                "master_ip": anchor.get("master_ip"),
                "host_ip": anchor.get("host_ip"),
                "asdu_key": anchor.get("asdu_key"),
                "transition_status": anchor.get("transition_status"),
                "step_kinds": anchor.get("step_kinds"),
                "event_kinds": anchor.get("event_kinds"),
                "quality_good": anchor.get("quality_good"),
                "arp_targets": anchor.get("targets"),
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
                independent = bool(lm.get("rtu_ip")) and lm.get("rtu_ip") != rm.get("rtu_ip")
                add_edge(
                    source_fid=left["fact_id"], target_fid=right["fact_id"],
                    relation_category="measurement_state_transition",
                    relation_type="same_device_behavior_in_separate_asdu",
                    claim_level="observed_fact",
                    verification_status="supported",
                    graph_consistency_gate_status="same_element_identity_from_point_map",
                    independent_support=independent,
                    temporal_condition=f"0 <= dt ({round(dt, 3)}s) <= {HORIZON_SECONDS}s",
                    support_basis=(
                        f"Both observations belong to {left['device_stem']} by the data point map and were sent in "
                        f"separate ASDUs (RTU {lm.get('rtu_ip')} then {rm.get('rtu_ip')}); change kinds "
                        f"{lm.get('step_kinds') or lm.get('transition_status')} then "
                        f"{rm.get('step_kinds') or rm.get('transition_status')}. Same element, observed twice; "
                        "this is not a cause."
                    ),
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
                        context.append(
                            f"ARP from {arp['host_ip']} addressed {sorted(hit)} "
                            f"({sum(arp['arp_targets'][h] for h in hit)} packets)"
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
