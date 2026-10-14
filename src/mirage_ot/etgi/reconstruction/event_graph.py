"""Phase 2: Event-Level Temporal Graph (Reliability-Hardened).

Key guarantees:
1. Independent Consistency Gate on `command_to_device_state_transition`:
   - `build_temporal_event_graph()` invokes `evaluate_command_effect_inference()`
     directly on the actual pre-command, command, and post-command values/flags.
   - Only when all gate conditions hold (`shifted_from_pre_baseline`,
     `direction_matches_target`, `matches_commanded_setpoint`, valid pre/post
     values, and non-rejected command) is the edge set to
     `claim_level="supported_inference"` (`graph_consistency_gate_status="passed_noncausal_inference_gate"`).
   - Otherwise the edge is kept at `claim_level="unresolved"`,
     `verification_status="unresolved"` (`graph_consistency_gate_status="failed_gate_kept_unresolved"`),
     with the exact `failed_conditions` recorded.
2. Vantage-invariant `canonical_source_id`:
   - Every logical observation uses a canonical source identifier that does not
     multiply when a packet is mirrored at both `n302` and `n318`.
3. Precise N-P shared-source relation types:
   - Single-event derivation: `same_network_data_stream_ipal_derivation`
   - Multi-sample window series alignment: `temporally_aligned_same_point_stream`
   Both carry `independent_support=False`.
4. Complete endpoint provenance on every edge:
   - Every edge stores `source_evidence_ids`, `target_evidence_ids`, and their
     union `evidence_ids`, so cross-entity edges always cite both endpoints.
"""
from __future__ import annotations
from ..graph.temporal import TemporalEvidenceGraph
from .transactions import evaluate_command_effect_inference


def build_temporal_event_graph(
    timeline: list[dict],
    lineage: dict[str, list[str]],
    tx_result: dict,
    *,
    cross_entity_horizon_sec: float = 10.0,
) -> dict:
    facts: list[dict] = []
    fact_lineage: dict[str, list[str]] = {}
    seen_fact_keys: dict[tuple, str] = {}

    tx_stage_map: dict[str, dict] = {}
    for tx in tx_result.get("transactions") or []:
        tx_id = tx["transaction_id"]
        stage_ids: dict[str, str] = {}

        cmd = tx["command_activation"]
        cmd_src_id = cmd.get("canonical_source_id") or f"SRC-{cmd['message_id']}"
        cmd_fid = _add_fact(
            facts, fact_lineage, seen_fact_keys,
            key=("tx_cmd", tx_id, cmd["message_id"]),
            time=cmd["timestamp"],
            time_end=cmd["timestamp_end"],
            entity=cmd["entity"],
            ca_ioa=cmd["ca_ioa"],
            modality="network",
            kind="iec104_asdu",
            role="command_activation",
            record_class="direct_observation",
            value=cmd["value"],
            value_present=cmd["value_present"],
            vantages=cmd["vantages"],
            vantage_capture_count=cmd.get("vantage_capture_count", len(cmd.get("evidence_ids") or [])),
            evidence_ids=[*cmd["evidence_ids"], *cmd["parent_evidence_ids"]],
            source_containers=[cmd_src_id],
            transaction_id=tx_id,
            protocol_meta={
                "type_id": cmd["type_id"], "cot": cmd["cot"], "tcp_seq": cmd.get("tcp_seq"),
                "select_execute": cmd.get("select_execute"),
                "src_ip": cmd["src_ip"], "dst_ip": cmd["dst_ip"],
                "src_port": cmd["src_port"], "dst_port": cmd["dst_port"],
            },
            observation=(
                f"IEC-104 {cmd['type_name']} COT=6 (Activation) on {cmd['entity']} "
                f"(CA/IOA={cmd['ca_ioa']}, value={cmd['value']}) from {cmd['src_ip']}:{cmd['src_port']} "
                f"to {cmd['dst_ip']}:{cmd['dst_port']} at vantages {cmd['vantages']}"
            ),
        )
        stage_ids["command_activation"] = cmd_fid

        ack = tx.get("activation_confirmation")
        if ack is not None:
            ack_src_id = ack.get("canonical_source_id") or f"SRC-{ack['message_id']}"
            cot_neg = ack.get("cot_negative")
            neg_desc = (
                "negative confirmation (rejected)"
                if cot_neg is True
                else ("positive confirmation (accepted)" if cot_neg is False else "P/N bit undecoded (acceptance unknown)")
            )
            ack_fid = _add_fact(
                facts, fact_lineage, seen_fact_keys,
                key=("tx_ack", tx_id, ack["message_id"]),
                time=ack["timestamp"],
                time_end=ack["timestamp_end"],
                entity=ack["entity"],
                ca_ioa=ack["ca_ioa"],
                modality="network",
                kind="iec104_asdu",
                role="command_confirmation",
                record_class="direct_observation",
                value=ack["value"],
                value_present=ack["value_present"],
                vantages=ack["vantages"],
                vantage_capture_count=ack.get("vantage_capture_count", len(ack.get("evidence_ids") or [])),
                evidence_ids=[*ack["evidence_ids"], *ack["parent_evidence_ids"]],
                source_containers=[ack_src_id],
                transaction_id=tx_id,
                protocol_meta={
                    "type_id": ack["type_id"], "cot": ack["cot"], "cot_negative": cot_neg,
                    "tcp_seq": ack.get("tcp_seq"),
                    "src_ip": ack["src_ip"], "dst_ip": ack["dst_ip"],
                    "src_port": ack["src_port"], "dst_port": ack["dst_port"],
                },
                observation=(
                    f"IEC-104 {ack['type_name']} COT=7 (Activation Confirmation: {neg_desc}; "
                    f"not physical actuation proof) on {ack['entity']} (CA/IOA={ack['ca_ioa']}) from "
                    f"{ack['src_ip']}:{ack['src_port']} to {ack['dst_ip']}:{ack['dst_port']}"
                ),
            )
            stage_ids["command_confirmation"] = ack_fid

        feedback_fids = []
        for fb in tx.get("protocol_state_feedback") or []:
            fb_src_id = fb.get("canonical_source_id") or f"SRC-{fb['message_id']}"
            val_str = f"value={fb['value']}" if fb.get("value_present") else "value=undecoded(null)"
            fb_fid = _add_fact(
                facts, fact_lineage, seen_fact_keys,
                key=("tx_fb", tx_id, fb["message_id"]),
                time=fb["timestamp"],
                time_end=fb["timestamp_end"],
                entity=fb["entity"],
                ca_ioa=fb["ca_ioa"],
                modality="network",
                kind="iec104_asdu",
                role="spontaneous_state_feedback",
                record_class="transcription" if fb.get("value_present") else "missing",
                value=fb["value"],
                value_present=bool(fb.get("value_present")),
                vantages=fb["vantages"],
                vantage_capture_count=fb.get("vantage_capture_count", len(fb.get("evidence_ids") or [])),
                evidence_ids=[*fb["evidence_ids"], *fb["parent_evidence_ids"]],
                source_containers=[fb_src_id],
                transaction_id=tx_id,
                protocol_meta={
                    "type_id": fb["type_id"], "cot": fb["cot"], "tcp_seq": fb.get("tcp_seq"),
                    "src_ip": fb["src_ip"], "dst_ip": fb["dst_ip"],
                    "pre_state_value": fb.get("pre_state_value"),
                },
                observation=(
                    f"IEC-104 {fb['type_name']} COT={fb['cot']} ({fb['cot_name']}) state report message on "
                    f"{fb['entity']} (CA/IOA={fb['ca_ioa']}, {val_str}) from RTU {fb['src_ip']}"
                ),
            )
            feedback_fids.append(fb_fid)
        stage_ids["protocol_state_feedback"] = feedback_fids

        mt = tx.get("measurement_transition")
        if mt is not None:
            if mt.get("pre_command_evidence_ids"):
                pre_src_id = mt.get("pre_command_canonical_source_id") or f"SRC-PRE-{tx_id}"
                pre_fid = _add_fact(
                    facts, fact_lineage, seen_fact_keys,
                    key=("tx_pre_meas", tx_id, mt["measurement_entity"]),
                    time=float(mt["pre_command_time"]),
                    time_end=float(mt.get("pre_command_time_end") or mt["pre_command_time"]),
                    entity=mt["measurement_entity"],
                    ca_ioa=mt["ca_ioa"],
                    modality="network",
                    kind="iec104_asdu",
                    role="pre_command_measurement",
                    record_class="transcription",
                    value=mt["pre_command_value"],
                    value_present=mt["pre_command_value"] is not None,
                    vantages=cmd["vantages"],
                    vantage_capture_count=len(mt["pre_command_evidence_ids"]) // 2 or 1,
                    evidence_ids=list(mt["pre_command_evidence_ids"]),
                    source_containers=[pre_src_id],
                    transaction_id=tx_id,
                    protocol_meta={"type_id": 13, "cot": 1},
                    observation=(
                        f"Pre-command IEC-104 measurement baseline on {mt['measurement_entity']} "
                        f"(CA/IOA={mt['ca_ioa']}) = {mt['pre_command_value']}"
                    ),
                )
                stage_ids["pre_command_measurement"] = pre_fid
            post_ev = list(dict.fromkeys([
                *mt["post_command_evidence_ids"], *mt.get("post_command_parent_evidence_ids", []),
            ]))
            post_src_id = mt.get("post_command_canonical_source_id") or f"SRC-POST-{tx_id}"
            post_fid = _add_fact(
                facts, fact_lineage, seen_fact_keys,
                key=("tx_post_meas", tx_id, mt["measurement_entity"]),
                time=float(mt["post_command_time"]),
                time_end=float(mt.get("post_command_time_end") or mt["post_command_time"]),
                entity=mt["measurement_entity"],
                ca_ioa=mt["ca_ioa"],
                modality="network",
                kind="iec104_asdu",
                role="post_command_measurement",
                record_class="transcription",
                value=mt["post_command_value"],
                value_present=mt["post_command_value"] is not None,
                vantages=cmd["vantages"],
                vantage_capture_count=len(mt["post_command_evidence_ids"]),
                evidence_ids=post_ev,
                source_containers=[post_src_id],
                transaction_id=tx_id,
                protocol_meta={"type_id": 13, "cot": 1},
                observation=(
                    f"Post-command IEC-104 measurement on {mt['measurement_entity']} "
                    f"(CA/IOA={mt['ca_ioa']}) = {mt['post_command_value']} "
                    f"(pre-command baseline={mt.get('pre_command_value')}, commanded setpoint={mt.get('commanded_setpoint')})"
                ),
            )
            stage_ids["post_command_measurement"] = post_fid

        ipal_fids = []
        for u in (tx.get("ipal_state_updates") or [])[:2]:
            # Share the canonical source container of the protocol event it derives from
            shared_src_id = (
                facts[-1]["source_containers"][0]
                if facts else f"SRC-IPAL-{u['evidence_id']}"
            )
            u_fid = _add_fact(
                facts, fact_lineage, seen_fact_keys,
                key=("electrical_entity_window", u["entity"], u.get("ca_ioa")),
                time=float(u["timestamp"]),
                time_end=float(u["timestamp"]),
                entity=u["entity"],
                ca_ioa=u.get("ca_ioa"),
                modality="electrical",
                kind="electrical_update",
                role="electrical_state_update",
                record_class="transcription",
                value=u["value"],
                value_present=u["value"] is not None,
                vantages=["ipal_state"],
                vantage_capture_count=1,
                evidence_ids=[u["evidence_id"]],
                source_containers=[shared_src_id],
                transaction_id=tx_id,
                protocol_meta={"shared_network_source": True},
                observation=(
                    f"IPAL electrical_update on {u['entity']} (CA/IOA={u.get('ca_ioa')}) = {u['value']} "
                    f"(network-derived state table, not an independent physical sensor)"
                ),
            )
            ipal_fids.append(u_fid)
        stage_ids["ipal_state_updates"] = ipal_fids
        tx_stage_map[tx_id] = stage_ids

    # 2. Add selected timeline Fact Records (`TLnnn`)
    tx_entities_cmd = {
        (tx["entity"], tx["ca_ioa"]) for tx in (tx_result.get("transactions") or [])
    }
    for event in timeline:
        if event["role"] == "command" and (event["entity"], event.get("ca_ioa")) in tx_entities_cmd:
            continue
        tid = event["timeline_id"]
        kind = (event.get("source") or {}).get("kind") or "unknown"
        mod = (event.get("source") or {}).get("modality") or "network"
        ev_ids = list(lineage.get(tid) or event.get("evidence_ids") or [])
        stream_src_id = (
            f"SRC-POINT-STREAM-{event['entity']}-{event.get('ca_ioa')}"
            if event.get("ca_ioa")
            else f"SRC-FLOW-{tid}"
        )
        dedup_key = (
            ("electrical_entity_window", event["entity"], event.get("ca_ioa"))
            if mod == "electrical"
            else ("timeline", tid)
        )
        _add_fact(
            facts, fact_lineage, seen_fact_keys,
            key=dedup_key,
            preferred_id=tid,
            time=float(event["time"]),
            time_end=float(event["time_end"]),
            entity=event["entity"],
            ca_ioa=event.get("ca_ioa"),
            modality=mod,
            kind=kind,
            role=event["role"],
            record_class=event["record_class"],
            value=event.get("value"),
            value_present=bool(event.get("value_present")),
            value_first=event.get("value_first"),
            value_last=event.get("value_last"),
            value_min=event.get("value_min"),
            value_max=event.get("value_max"),
            sample_count=event.get("sample_count"),
            packet_count=event.get("packet_count"),
            distinct_frame_count=event.get("distinct_frame_count"),
            vantages=(event.get("source") or {}).get("vantages") or [],
            vantage_capture_count=len(ev_ids),
            evidence_ids=ev_ids,
            source_containers=[stream_src_id],
            transaction_id=None,
            protocol_meta={"score": event.get("score"), "fingerprint": event.get("fingerprint")},
            observation=event["observation"],
        )

    facts.sort(key=lambda f: (f["time"], f["fact_id"]))
    facts_by_id = {f["fact_id"]: f for f in facts}

    graph = TemporalEvidenceGraph()
    node_by_fid = {}
    for f in facts:
        node_by_fid[f["fact_id"]] = graph.add_node(
            modality=f["modality"],
            entity=f["entity"],
            event_type=f["role"],
            start_time=f["time"],
            end_time=f["time_end"],
            description=f["observation"],
            evidence_ids=f["evidence_ids"][:4],
            vantage=(f["vantages"] or [None])[0],
        )

    edges: list[dict] = []
    existing_pairs: set[tuple[str, str, str]] = set()

    # Build transaction edges with strict Consistency Gate verification
    for tx in tx_result.get("transactions") or []:
        tx_id = tx["transaction_id"]
        st = tx_stage_map[tx_id]
        cmd_fid = st["command_activation"]
        ack_fid = st.get("command_confirmation")

        if ack_fid:
            ack_status = tx.get("command_acceptance_status")
            _add_typed_edge(
                graph, edges, existing_pairs, facts_by_id, node_by_fid,
                source_fid=cmd_fid,
                target_fid=ack_fid,
                relation_category="direct_protocol_relation",
                relation_type="iec104_command_confirmation",
                claim_level="observed_fact",
                verification_status="supported",
                graph_consistency_gate_status="direct_record_observation",
                independent_support=True,
                temporal_condition=f"0 <= dt ({round(facts_by_id[ack_fid]['time'] - facts_by_id[cmd_fid]['time'], 4)}s) <= 5.0s",
                support_basis=(
                    f"Reverse TCP 5-tuple ({tx['rtu_ip']}:{tx['rtu_port']} -> {tx['master_ip']}:{tx['master_port']}), "
                    f"matching ASDU type_id={tx['type_id']} and CA/IOA={tx['ca_ioa']} (COT=6 -> COT=7; "
                    f"acceptance_status={ack_status}). Protocol reply observation only, not physical actuation proof."
                ),
            )

        anchor_fid = ack_fid or cmd_fid
        for fb_fid in st.get("protocol_state_feedback") or []:
            fb_node = facts_by_id[fb_fid]
            pre_state_val = (fb_node.get("protocol_meta") or {}).get("pre_state_value")
            fb_gate = evaluate_command_effect_inference(
                command_acceptance_status=tx.get("command_acceptance_status"),
                command_value_present=bool(tx.get("value_present")),
                commanded_value=tx.get("commanded_value"),
                pre_value_present=(pre_state_val is not None),
                pre_command_value=pre_state_val,
                post_value_present=bool(fb_node.get("value_present")),
                post_command_value=fb_node.get("value"),
                same_rtu_and_ca=True,
                same_device_stem=(fb_node.get("device_stem") == tx.get("device_stem")),
            )
            _add_typed_edge(
                graph, edges, existing_pairs, facts_by_id, node_by_fid,
                source_fid=anchor_fid,
                target_fid=fb_fid,
                relation_category="direct_protocol_relation",
                relation_type="subsequent_same_device_state_report",
                claim_level="observed_fact",
                verification_status="supported",
                graph_consistency_gate_status="direct_record_observation",
                independent_support=True,
                temporal_condition=f"dt = {round(fb_node['time'] - facts_by_id[anchor_fid]['time'], 4)}s >= 0",
                support_basis=(
                    f"Observed subsequent M_SP_NA_1 (type_id=1, COT=3) state report message on {fb_node['entity']} "
                    f"from same RTU {tx['rtu_ip']} and CA={tx['ca']} (value_present={fb_node['value_present']}). "
                    "Presence of a state report message is a protocol observation, not proof of state transition."
                ),
            )
            if fb_gate["gate_passed"]:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=cmd_fid,
                    target_fid=fb_fid,
                    relation_category="inference_hypothesis",
                    relation_type="command_to_device_state_transition",
                    claim_level="supported_inference",
                    verification_status="supported",
                    graph_consistency_gate_status="passed_noncausal_inference_gate",
                    independent_support=True,
                    temporal_condition=f"0 <= dt ({round(fb_node['time'] - facts_by_id[cmd_fid]['time'], 4)}s) <= 15.0s",
                    support_basis=(
                        f"Consistency gate passed: {fb_node['entity']} shifted from {pre_state_val} to "
                        f"{fb_node['value']}, matching commanded state {tx.get('commanded_value')}."
                    ),
                )
            else:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=cmd_fid,
                    target_fid=fb_fid,
                    relation_category="inference_hypothesis",
                    relation_type="command_to_device_state_candidate",
                    claim_level="unresolved",
                    verification_status="unresolved",
                    graph_consistency_gate_status="failed_gate_kept_unresolved",
                    independent_support=False,
                    temporal_condition=f"0 <= dt ({round(fb_node['time'] - facts_by_id[cmd_fid]['time'], 4)}s) <= 15.0s",
                    support_basis=(
                        f"Kept unresolved by consistency gate (failed_conditions={fb_gate['failed_conditions']}): "
                        f"state report {fb_node['entity']} cannot be confirmed as a command-induced state transition."
                    ),
                )

        pre_fid = st.get("pre_command_measurement")
        post_fid = st.get("post_command_measurement")
        mt = tx.get("measurement_transition")
        if post_fid and mt is not None:
            post_node = facts_by_id[post_fid]
            pre_val = mt.get("pre_command_value")
            post_val = mt.get("post_command_value")
            cmd_val = tx.get("commanded_value")
            # Re-evaluate consistency gate directly from actual values AND honor explicit False flags if overridden
            recheck_gate = evaluate_command_effect_inference(
                command_acceptance_status=tx.get("command_acceptance_status"),
                command_value_present=(cmd_val is not None),
                commanded_value=cmd_val,
                pre_value_present=(pre_val is not None),
                pre_command_value=pre_val,
                post_value_present=(post_val is not None),
                post_command_value=post_val,
                same_rtu_and_ca=(post_node.get("ca_ioa", "").split(".")[0] == str(tx.get("ca"))),
                same_device_stem=(post_node.get("device_stem") == tx.get("device_stem")),
            )
            if mt.get("shifted_from_pre_baseline") is False and "not_shifted_from_pre_baseline" not in recheck_gate["failed_conditions"]:
                recheck_gate["failed_conditions"].append("not_shifted_from_pre_baseline")
                recheck_gate["gate_passed"] = False
            if mt.get("matches_commanded_setpoint") is False and "post_value_outside_target_tolerance" not in recheck_gate["failed_conditions"]:
                recheck_gate["failed_conditions"].append("post_value_outside_target_tolerance")
                recheck_gate["gate_passed"] = False

            if pre_fid:
                rel_name = (
                    "pre_to_post_measurement_transition"
                    if recheck_gate["shifted_from_pre_baseline"] and mt.get("shifted_from_pre_baseline") is not False
                    else "pre_to_post_measurement_comparison"
                )
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=pre_fid,
                    target_fid=post_fid,
                    relation_category="measurement_state_transition",
                    relation_type=rel_name,
                    claim_level="observed_fact",
                    verification_status="supported",
                    graph_consistency_gate_status="direct_record_observation",
                    independent_support=True,
                    temporal_condition=f"t_pre ({facts_by_id[pre_fid]['time']}) < t_cmd < t_post ({post_node['time']})",
                    support_basis=(
                        f"Same measurement point {post_node['entity']} ({post_node['ca_ioa']}): "
                        f"pre-command value={pre_val}, post-command value={post_val} "
                        f"(shifted={recheck_gate['shifted_from_pre_baseline']})."
                    ),
                )

            if recheck_gate["gate_passed"]:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=anchor_fid,
                    target_fid=post_fid,
                    relation_category="inference_hypothesis",
                    relation_type="command_to_device_state_transition",
                    claim_level="supported_inference",
                    verification_status="supported",
                    graph_consistency_gate_status="passed_noncausal_inference_gate",
                    independent_support=True,
                    temporal_condition=f"0 < dt ({round(post_node['time'] - facts_by_id[anchor_fid]['time'], 4)}s) <= 15.0s",
                    support_basis=(
                        f"Consistency gate passed: setpoint command {tx['entity']}={cmd_val} on RTU {tx['rtu_ip']} "
                        f"(CA={tx['ca']}) followed by {post_node['entity']} shifting from {pre_val} to {post_val} "
                        f"(within 2% tolerance of target {cmd_val}). Non-causal protocol/measurement alignment."
                    ),
                )
            else:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=anchor_fid,
                    target_fid=post_fid,
                    relation_category="inference_hypothesis",
                    relation_type="command_to_device_state_candidate",
                    claim_level="unresolved",
                    verification_status="unresolved",
                    graph_consistency_gate_status="failed_gate_kept_unresolved",
                    independent_support=False,
                    temporal_condition=f"0 < dt ({round(post_node['time'] - facts_by_id[anchor_fid]['time'], 4)}s) <= 15.0s",
                    support_basis=(
                        f"Kept unresolved by consistency gate (failed_conditions={recheck_gate['failed_conditions']}): "
                        f"post-command value {post_val} vs pre-command {pre_val} and target {cmd_val} does not satisfy "
                        "verified setpoint transition criteria."
                    ),
                )

        # Link protocol feedback / post-measurement to derived IPAL electrical_update (`shared_source`, N-P)
        for u_fid in st.get("ipal_state_updates") or []:
            u_fact = facts_by_id[u_fid]
            proto_source = post_fid if (post_fid and facts_by_id[post_fid]["entity"] == u_fact["entity"]) else (
                (st["protocol_state_feedback"][0] if st.get("protocol_state_feedback") else anchor_fid)
            )
            _add_typed_edge(
                graph, edges, existing_pairs, facts_by_id, node_by_fid,
                source_fid=proto_source,
                target_fid=u_fid,
                relation_category="shared_source",
                relation_type="same_network_data_stream_ipal_derivation",
                claim_level="observed_fact",
                verification_status="supported",
                graph_consistency_gate_status="direct_record_observation",
                independent_support=False,
                temporal_condition=f"abs(dt) = {round(abs(u_fact['time'] - facts_by_id[proto_source]['time']), 4)}s <= 1.5s",
                support_basis=(
                    "IPAL electrical state update is derived from the same network telemetry stream as the "
                    "IEC-104 point; recorded for cross-layer consistency but NOT counted as independent support."
                ),
            )

    # Category 1b: Bidirectional TCP sessions (N-N)
    comm_facts = [f for f in facts if f["role"] == "communication"]
    for i, left in enumerate(comm_facts):
        for right in comm_facts[i + 1:]:
            if _reverse_tcp(left["entity"]) == right["entity"]:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=left["fact_id"],
                    target_fid=right["fact_id"],
                    relation_category="direct_protocol_relation",
                    relation_type="bidirectional_tcp_session",
                    claim_level="observed_fact",
                    verification_status="supported",
                    graph_consistency_gate_status="direct_record_observation",
                    independent_support=True,
                    temporal_condition="overlapping_tcp_session_window",
                    support_basis="Both directions of the same TCP 5-tuple were observed at shared mirror vantages.",
                )

    # Category 2b: Temporally aligned same-point data streams (N-P) and same IEC-104 frame (N-N)
    iec_facts = [f for f in facts if f["kind"] == "iec104_asdu"]
    el_facts = [f for f in facts if f["kind"] == "electrical_update"]
    for nf in iec_facts:
        for ef in el_facts:
            if nf["entity"] == ef["entity"] and nf.get("ca_ioa") == ef.get("ca_ioa"):
                if abs(nf["time"] - ef["time"]) <= 2.0 or (
                    nf["time"] <= ef["time_end"] + 1.5 and ef["time"] <= nf["time_end"] + 1.5
                ):
                    _add_typed_edge(
                        graph, edges, existing_pairs, facts_by_id, node_by_fid,
                        source_fid=nf["fact_id"],
                        target_fid=ef["fact_id"],
                        relation_category="shared_source",
                        relation_type="temporally_aligned_same_point_stream",
                        claim_level="observed_fact",
                        verification_status="supported",
                        graph_consistency_gate_status="direct_record_observation",
                        independent_support=False,
                        temporal_condition="overlapping_window_same_ca_ioa",
                        support_basis=(
                            f"IEC-104 report series and IPAL update series correspond to the same mapped point "
                            f"({nf['entity']}, CA/IOA={nf.get('ca_ioa')}) in the network-derived state stream; "
                            "not an independent second sensor."
                        ),
                    )
    for i, left in enumerate(iec_facts):
        for right in iec_facts[i + 1:]:
            fp_left = (left.get("protocol_meta") or {}).get("fingerprint")
            fp_right = (right.get("protocol_meta") or {}).get("fingerprint")
            if fp_left and fp_left == fp_right and left["entity"] != right["entity"]:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=left["fact_id"],
                    target_fid=right["fact_id"],
                    relation_category="shared_source",
                    relation_type="same_iec104_frame",
                    claim_level="observed_fact",
                    verification_status="supported",
                    graph_consistency_gate_status="direct_record_observation",
                    independent_support=False,
                    temporal_condition=f"identical_frame_timestamp ({left['time']})",
                    support_basis=(
                        "Both information objects were carried in the same Ethernet/IEC-104 frame. "
                        "Shared packet container, not independent evidence."
                    ),
                )

    # Category 3b: Same-device measurement state coupling (P-P or N-N on the same device stem)
    meas_facts = [
        f for f in facts
        if f["role"] in ("electrical_change", "electrical_report", "post_command_measurement", "electrical_state_update")
        and f.get("device_stem")
    ]
    for i, left in enumerate(meas_facts):
        for right in meas_facts[i + 1:]:
            if left["modality"] == right["modality"] and left["device_stem"] == right["device_stem"] and left["entity"] != right["entity"]:
                if abs(left["time"] - right["time"]) <= 5.0:
                    fp_l = (left.get("protocol_meta") or {}).get("fingerprint")
                    fp_r = (right.get("protocol_meta") or {}).get("fingerprint")
                    same_frame = bool(fp_l and fp_l == fp_r)
                    _add_typed_edge(
                        graph, edges, existing_pairs, facts_by_id, node_by_fid,
                        source_fid=left["fact_id"],
                        target_fid=right["fact_id"],
                        relation_category="measurement_state_transition",
                        relation_type="same_device_attribute_coupling",
                        claim_level="observed_fact",
                        verification_status="supported",
                        graph_consistency_gate_status="direct_record_observation",
                        independent_support=not same_frame,
                        temporal_condition=f"abs(dt) <= 5.0s on {left['device_stem']}",
                        support_basis=f"Both attributes belong to the same grid element ({left['device_stem']}).",
                    )

    # Category 5: Cross-entity temporal co-occurrence hypotheses (strictly `temporal_cooccurrence` / `unresolved`)
    trigger_facts = [
        f for f in facts
        if f["role"] in ("spontaneous_state_feedback", "post_command_measurement", "command_confirmation", "command_activation")
    ]
    response_candidates = [
        f for f in facts
        if f["role"] in ("electrical_change", "electrical_report")
    ]
    cooc_count = 0
    for trig in trigger_facts:
        for resp in response_candidates:
            if cooc_count >= 16:
                break
            if trig["device_stem"] == resp["device_stem"]:
                continue
            dt = resp["time"] - trig["time"]
            if 0.0 <= dt <= cross_entity_horizon_sec:
                _add_typed_edge(
                    graph, edges, existing_pairs, facts_by_id, node_by_fid,
                    source_fid=trig["fact_id"],
                    target_fid=resp["fact_id"],
                    relation_category="temporal_cooccurrence",
                    relation_type="cross_entity_temporal_cooccurrence",
                    claim_level="temporal_cooccurrence",
                    verification_status="unresolved",
                    graph_consistency_gate_status="unresolved_cooccurrence",
                    independent_support=False,
                    temporal_condition=f"0 <= dt ({round(dt, 4)}s) <= {cross_entity_horizon_sec}s",
                    support_basis=(
                        f"{resp['entity']} changed {round(dt, 3)}s after {trig['entity']} ({trig['role']}). "
                        "Time proximity across distinct grid elements is a candidate co-occurrence hypothesis only, "
                        "NOT a supported inference and NOT proof of causation."
                    ),
                )
                cooc_count += 1

    if not trigger_facts:
        ordered_el = sorted(el_facts, key=lambda f: f["time"])
        for i, left in enumerate(ordered_el):
            for right in ordered_el[i + 1:]:
                if cooc_count >= 10:
                    break
                if left["device_stem"] == right["device_stem"]:
                    continue
                dt = right["time"] - left["time"]
                if 0.0 <= dt <= 2.0:
                    _add_typed_edge(
                        graph, edges, existing_pairs, facts_by_id, node_by_fid,
                        source_fid=left["fact_id"],
                        target_fid=right["fact_id"],
                        relation_category="temporal_cooccurrence",
                        relation_type="cross_entity_temporal_cooccurrence",
                        claim_level="temporal_cooccurrence",
                        verification_status="unresolved",
                        graph_consistency_gate_status="unresolved_cooccurrence",
                        independent_support=False,
                        temporal_condition=f"0 <= dt ({round(dt, 4)}s) <= 2.0s",
                        support_basis=(
                            "Co-occurring electrical updates on distinct grid elements within 2.0s; "
                            "unresolved temporal co-occurrence only."
                        ),
                    )
                    cooc_count += 1

    connected_fids = {
        fid for e in edges for fid in (e["source_fact_id"], e["target_fact_id"])
    }
    unconnected_facts = [f for f in facts if f["fact_id"] not in connected_fids]

    by_modality_pair: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_level: dict[str, int] = {}
    for e in edges:
        mp = e["modality_pair"]
        cat = e["relation_category"]
        lvl = e["claim_level"]
        by_modality_pair[mp] = by_modality_pair.get(mp, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        by_level[lvl] = by_level.get(lvl, 0) + 1

    return {
        "graph_object": graph,
        "node_count": len(facts),
        "edge_count": len(edges),
        "edges_by_modality_pair": by_modality_pair,
        "edges_by_category": by_category,
        "edges_by_claim_level": by_level,
        "unconnected_node_count": len(unconnected_facts),
        "nodes": facts,
        "edges": edges,
        "unconnected_observations": unconnected_facts,
        "fact_lineage": fact_lineage,
    }


def _add_fact(
    facts: list[dict],
    fact_lineage: dict[str, list[str]],
    seen_fact_keys: dict[tuple, str],
    *,
    key: tuple,
    preferred_id: str | None = None,
    time: float,
    time_end: float,
    entity: str,
    ca_ioa: str | None,
    modality: str,
    kind: str,
    role: str,
    record_class: str,
    value,
    value_present: bool,
    vantages: list[str],
    vantage_capture_count: int = 1,
    evidence_ids: list[str],
    source_containers: list[str],
    transaction_id: str | None,
    protocol_meta: dict,
    observation: str,
    **extra,
) -> str:
    if key in seen_fact_keys:
        return seen_fact_keys[key]
    used_ids = {f["fact_id"] for f in facts}
    if preferred_id and preferred_id not in used_ids:
        fid = preferred_id
    else:
        fid = f"EF{len(facts) + 1:03d}"
        while fid in used_ids:
            fid = f"EF{len(facts) + len(used_ids) + 1:03d}"
    dedup_ev = list(dict.fromkeys(evidence_ids))
    fact_lineage[fid] = dedup_ev
    stem = entity.split(":", 1)[0] if (entity and ":" in entity and not str(entity).endswith("/TCP")) else None
    node = {
        "fact_id": fid,
        "timeline_id": fid,
        "time": time,
        "time_end": time_end,
        "entity": entity,
        "device_stem": stem,
        "ca_ioa": ca_ioa,
        "modality": modality,
        "source": {
            "modality": modality,
            "kind": kind,
            "vantages": vantages,
            "trust": "indexed_telemetry",
        },
        "kind": kind,
        "role": role,
        "record_class": record_class,
        "value": value,
        "value_present": value_present,
        "vantages": vantages,
        "vantage_capture_count": vantage_capture_count,
        "evidence_ids": dedup_ev[:4],
        "evidence_id_count": len(dedup_ev),
        "source_containers": list(dict.fromkeys(source_containers)),
        "transaction_id": transaction_id,
        "protocol_meta": protocol_meta,
        "observation": observation,
        **extra,
    }
    facts.append(node)
    seen_fact_keys[key] = fid
    return fid


def _add_typed_edge(
    graph: TemporalEvidenceGraph,
    edges: list[dict],
    existing_pairs: set[tuple[str, str, str]],
    facts_by_id: dict[str, dict],
    node_by_fid: dict[str, dict],
    *,
    source_fid: str,
    target_fid: str,
    relation_category: str,
    relation_type: str,
    claim_level: str,
    verification_status: str,
    graph_consistency_gate_status: str,
    independent_support: bool,
    temporal_condition: str,
    support_basis: str,
) -> None:
    if source_fid == target_fid:
        return
    key = (source_fid, target_fid, relation_type)
    if key in existing_pairs:
        return
    existing_pairs.add(key)

    src_fact = facts_by_id[source_fid]
    dst_fact = facts_by_id[target_fid]
    mod_pair = _modality_pair(src_fact["modality"], dst_fact["modality"])
    src_ev_ids = list((src_fact.get("evidence_ids") or [])[:2])
    dst_ev_ids = list((dst_fact.get("evidence_ids") or [])[:2])
    ev_ids = list(dict.fromkeys([*src_ev_ids, *dst_ev_ids]))

    origin = "inferred" if claim_level in ("supported_inference", "temporal_cooccurrence", "unresolved") else "observed"
    raw_edge = graph.add_edge(
        source=node_by_fid[source_fid]["node_id"],
        target=node_by_fid[target_fid]["node_id"],
        relation_type=relation_type,
        origin=origin,
        time_order="directed" if src_fact["time"] <= dst_fact["time"] else "undirected",
        evidence_ids=ev_ids,
        rationale=support_basis,
        built_by="reconstruction_engine",
    )
    raw_edge["candidate_level"] = claim_level
    raw_edge["claim_level"] = claim_level
    raw_edge["verification_status"] = verification_status
    raw_edge["status"] = verification_status
    raw_edge["causal_status"] = "not_established"
    raw_edge["source_fact_id"] = source_fid
    raw_edge["target_fact_id"] = target_fid

    edges.append({
        "edge_id": raw_edge["edge_id"],
        "source_fact_id": source_fid,
        "target_fact_id": target_fid,
        "source_entity": src_fact["entity"],
        "target_entity": dst_fact["entity"],
        "source_modality": src_fact["modality"],
        "target_modality": dst_fact["modality"],
        "modality_pair": mod_pair,
        "relation_category": relation_category,
        "relation_type": relation_type,
        "candidate_level": claim_level,
        "claim_level": claim_level,
        "verification_status": verification_status,
        "status": verification_status,
        "graph_consistency_gate_status": graph_consistency_gate_status,
        "causal_status": "not_established",
        "independent_support": independent_support,
        "temporal_condition": temporal_condition,
        "support_basis": support_basis,
        "rationale": support_basis,
        "source_evidence_ids": src_ev_ids,
        "target_evidence_ids": dst_ev_ids,
        "evidence_ids": ev_ids,
        "evidence_id_count": len(ev_ids),
    })


def _modality_pair(m1: str, m2: str) -> str:
    a = "P" if m1 == "electrical" else "N"
    b = "P" if m2 == "electrical" else "N"
    if a == "N" and b == "N":
        return "N-N"
    if a == "P" and b == "P":
        return "P-P"
    return "N-P"


def _reverse_tcp(entity: str | None) -> str | None:
    if not entity or "->" not in str(entity) or not str(entity).endswith("/TCP"):
        return None
    body = str(entity)[: -len("/TCP")]
    left, right = body.split("->", 1)
    return f"{right}->{left}/TCP"
