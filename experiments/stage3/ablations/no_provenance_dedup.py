"""Ablation A2: Without Provenance Deduplication (Paper-Readiness Audit Hardened).

Counterfactual Ablation Design (Task 2):
- Evaluates the counterfactual impact of removing MIRAGE-OT's provenance deduplication
  on the exact same indexed evidence without modifying the Evidence Database.
- Strictly distinguishes "protocol message / event source containers" from "independent
  physical process sensors" (network containers are telemetry messages, never physical
  sensors).
- Uses actual packet identity and verifiable source fingerprints from `evidence.sqlite`
  (`vantage`, 4-tuple, `timestamp`, `fingerprint`, `apci_tx`, `asdu_index`, `ca_ioa`,
  `object_index`, `tcp_seq`, `tcp_flags`, `op`) rather than `len(evidence_ids) - point_count`
  to classify every non-primary observation into five explicit categories plus `unknown`:
  1. `true_cross_vantage_mirror_duplicate_count`: the exact same network packet captured
     at multiple switch mirror vantages (`n302`, `n318`, `n406`, `n495`, etc.).
  2. `same_asdu_different_ioa_point_count`: distinct `ca_ioa` / `object_index` points
     carried inside the exact same IEC-104 ASDU (`apci_tx`, `asdu_index`).
  3. `distinct_messages_in_same_tcp_session_count`: separate packets at different times
     or sequence numbers on the same TCP 4-tuple session (e.g. repeated SYN retries or
     FIN segments in `communication_change`).
  4. `distinct_time_network_events_in_anchor_count`: network events occurring at different
     times or across different ephemeral TCP sessions / ARP targets inside an aggregated
     `communication_change` or `arp_activity_increase` anchor (e.g. `ev_cbe1e5bef23346604396`).
  5. `ipal_derived_observation_count`: IPAL `electrical_update` state rows derived from
     network telemetry without packet lineage.
  6. `unknown_provenance_relation_count`: any row lacking sufficient packet identity
     fields to classify reliably (never assumed to be a mirror duplicate).
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path


def _fetch_evidence_rows(db_path: Path | None, evidence_ids: list[str]) -> dict[str, dict]:
    if db_path is None or not db_path.exists() or not evidence_ids:
        return {}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    out: dict[str, dict] = {}
    try:
        uniq = list(dict.fromkeys(evidence_ids))
        for i in range(0, len(uniq), 100):
            batch = uniq[i : i + 100]
            q = f"SELECT * FROM evidence WHERE evidence_id IN ({','.join('?' for _ in batch)})"
            for r in conn.execute(q, batch).fetchall():
                d = dict(r)
                d["payload"] = json.loads(d.pop("payload_json") or "{}")
                out[d["evidence_id"]] = d
    finally:
        conn.close()
    return out


def _is_true_cross_vantage_mirror(cand: dict, prev: dict) -> bool:
    v1, v2 = cand.get("vantage"), prev.get("vantage")
    if not v1 or not v2 or v1 == v2:
        return False
    t1, t2 = float(cand["timestamp"]), float(prev["timestamp"])
    if abs(t1 - t2) > 0.5:
        return False
    k1, k2 = cand.get("kind"), prev.get("kind")
    if k1 != k2:
        return False
    p1, p2 = cand.get("payload") or {}, prev.get("payload") or {}
    ft1 = (cand.get("src_ip"), cand.get("src_port"), cand.get("dst_ip"), cand.get("dst_port"))
    ft2 = (prev.get("src_ip"), prev.get("src_port"), prev.get("dst_ip"), prev.get("dst_port"))

    if k1 == "iec104_asdu":
        return (
            ft1 == ft2
            and p1.get("apci_tx") is not None
            and p1.get("apci_tx") == p2.get("apci_tx")
            and p1.get("asdu_index") == p2.get("asdu_index")
            and cand.get("ca_ioa") == prev.get("ca_ioa")
            and p1.get("object_index") == p2.get("object_index")
        )
    if k1 == "tcp_packet":
        if cand.get("fingerprint") and cand.get("fingerprint") == prev.get("fingerprint"):
            return True
        return (
            ft1 == ft2
            and p1.get("tcp_seq") is not None
            and p1.get("tcp_seq") == p2.get("tcp_seq")
            and p1.get("tcp_flags") == p2.get("tcp_flags")
        )
    if k1 == "arp_packet":
        if cand.get("fingerprint") and cand.get("fingerprint") == prev.get("fingerprint"):
            return True
        return (
            cand.get("src_ip") == prev.get("src_ip")
            and cand.get("dst_ip") == prev.get("dst_ip")
            and p1.get("op") is not None
            and p1.get("op") == p2.get("op")
            and abs(t1 - t2) <= 0.05
        )
    return False


def _classify_container_rows(rows: list[dict | None]) -> dict[str, int]:
    counts = {
        "true_cross_vantage_mirror_duplicate_count": 0,
        "same_asdu_different_ioa_point_count": 0,
        "distinct_messages_in_same_tcp_session_count": 0,
        "distinct_time_network_events_in_anchor_count": 0,
        "unknown_provenance_relation_count": 0,
    }
    if len(rows) <= 1:
        return counts

    valid_rows: list[dict] = []
    for r in rows:
        if r is None:
            counts["unknown_provenance_relation_count"] += 1
        else:
            valid_rows.append(r)

    if len(valid_rows) <= 1:
        # If the first row was None and only 1 valid row exists, adjust unknown count
        counts["unknown_provenance_relation_count"] = max(0, len(rows) - 1)
        return counts

    valid_rows.sort(key=lambda r: (float(r["timestamp"]), r["evidence_id"]))
    seen_packets: list[dict] = []
    seen_asdu_containers: set[tuple] = set()
    seen_tcp_sessions: set[tuple] = set()

    for idx, r in enumerate(valid_rows):
        p = r.get("payload") or {}
        kind = r.get("kind")
        ft = (r.get("src_ip"), r.get("src_port"), r.get("dst_ip"), r.get("dst_port"))

        if idx == 0:
            seen_packets.append(r)
            if kind == "iec104_asdu" and p.get("apci_tx") is not None:
                seen_asdu_containers.add((*ft, p.get("apci_tx"), p.get("asdu_index")))
            if None not in ft:
                seen_tcp_sessions.add(tuple(sorted([(ft[0], ft[1]), (ft[2], ft[3])])))
            continue

        # 1. True cross-vantage mirror duplicate of an already-seen packet in this container
        if any(_is_true_cross_vantage_mirror(r, prev) for prev in seen_packets):
            counts["true_cross_vantage_mirror_duplicate_count"] += 1
            continue

        seen_packets.append(r)

        # 2. Different IOA point inside the exact same IEC-104 ASDU container
        if kind == "iec104_asdu":
            if p.get("apci_tx") is not None and None not in ft:
                asdu_id = (*ft, p.get("apci_tx"), p.get("asdu_index"))
                if asdu_id in seen_asdu_containers:
                    counts["same_asdu_different_ioa_point_count"] += 1
                    continue
                seen_asdu_containers.add(asdu_id)
            else:
                counts["unknown_provenance_relation_count"] += 1
                continue

        # 3. Distinct message on the exact same TCP 4-tuple session
        if None not in ft:
            sess_key = tuple(sorted([(ft[0], ft[1]), (ft[2], ft[3])]))
            if sess_key in seen_tcp_sessions:
                counts["distinct_messages_in_same_tcp_session_count"] += 1
                continue
            seen_tcp_sessions.add(sess_key)
            counts["distinct_time_network_events_in_anchor_count"] += 1
            continue

        # 4. Distinct-time ARP packet in an ARP burst anchor
        if kind == "arp_packet" and r.get("src_ip") and r.get("dst_ip"):
            counts["distinct_time_network_events_in_anchor_count"] += 1
            continue

        counts["unknown_provenance_relation_count"] += 1

    return counts


def run_ablation_without_provenance_dedup(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
    db_path: Path | None = None,
    evidence_rows_by_id: dict[str, dict] | None = None,
) -> dict:
    anchors = list(anchor_result.get("anchors") or [])
    verified_anchors = [
        a for a in anchors
        if a.get("verification_status") == "verified_observation" and not a.get("covered_by_transaction")
    ]
    txs = list(tx_result.get("transactions") or [])
    ledger = mirage_synthesis.get("source_dependency_ledger") or {}

    container_groups: list[tuple[str, list[str]]] = []
    if txs and not anchor_result.get("behavioral_mode"):
        # Each logical protocol message (`SRC-MSG-...`) in a transaction is one message container
        seen_cids: set[str] = set()
        for tx in txs:
            for stage_key in ("command_activation", "activation_confirmation", "activation_termination"):
                msg = tx.get(stage_key)
                if msg and msg.get("canonical_source_id") not in seen_cids:
                    cid = msg["canonical_source_id"]
                    seen_cids.add(cid)
                    container_groups.append((cid, list(dict.fromkeys(msg.get("evidence_ids") or []))))
            for fb in tx.get("protocol_state_feedback") or []:
                cid = fb.get("canonical_source_id")
                if cid and cid not in seen_cids:
                    seen_cids.add(cid)
                    container_groups.append((cid, list(dict.fromkeys(fb.get("evidence_ids") or []))))
            mt = tx.get("measurement_transition")
            if mt:
                pre_cid = mt.get("pre_command_canonical_source_id")
                if pre_cid and pre_cid not in seen_cids:
                    seen_cids.add(pre_cid)
                    # Exclude parent TCP packet IDs appended after the IEC-104 evidence IDs
                    pre_all = list(mt.get("pre_command_evidence_ids") or [])
                    container_groups.append((pre_cid, pre_all))
                post_cid = mt.get("post_command_canonical_source_id")
                if post_cid and post_cid not in seen_cids:
                    seen_cids.add(post_cid)
                    container_groups.append((post_cid, list(dict.fromkeys(mt.get("post_command_evidence_ids") or []))))
        distinct_containers = len(container_groups)
        distinct_rtus = len({tx.get("rtu_ip") for tx in txs if tx.get("rtu_ip")})
        ipal_derived_rows = sum(len(tx.get("ipal_state_updates") or []) for tx in txs)
    else:
        bundles = list(mirage_synthesis.get("rtu_asdu_bundles") or [])
        anc_by_id = {a["anchor_id"]: a for a in verified_anchors}
        for b in bundles:
            b_eids: list[str] = []
            for aid in b.get("member_anchor_ids") or []:
                a = anc_by_id.get(aid) or {}
                pts = a.get("points") or []
                if pts:
                    for p in pts:
                        b_eids.extend(p.get("evidence_ids") or [])
                else:
                    b_eids.extend(a.get("evidence_ids") or [])
            container_groups.append((b["asdu_container_id"], list(dict.fromkeys(b_eids))))
        distinct_containers = len(container_groups)
        distinct_rtus = int(ledger.get("distinct_rtu_count") or 0)
        ipal_derived_rows = len({
            r["evidence_id"]
            for a in verified_anchors
            for r in (a.get("ipal_rows") or [])
            if r.get("evidence_id")
        })

    all_cited_eids = list(dict.fromkeys(eid for _, eids in container_groups for eid in eids))
    row_lookup = evidence_rows_by_id if evidence_rows_by_id is not None else _fetch_evidence_rows(db_path, all_cited_eids)

    total_breakdown = {
        "true_cross_vantage_mirror_duplicate_count": 0,
        "same_asdu_different_ioa_point_count": 0,
        "distinct_messages_in_same_tcp_session_count": 0,
        "distinct_time_network_events_in_anchor_count": 0,
        "unknown_provenance_relation_count": 0,
    }
    raw_net_obs_count = 0

    for _cid, eids in container_groups:
        rows = [row_lookup.get(eid) for eid in eids]
        # Filter out parent tcp_packet rows when the group is an iec104_asdu message container
        if any(r is not None and r.get("kind") == "iec104_asdu" for r in rows):
            parent_ids = {
                r.get("parent_evidence_id")
                for r in rows
                if r is not None and r.get("kind") == "iec104_asdu" and r.get("parent_evidence_id")
            }
            filtered_eids = [
                eid for eid in eids
                if eid not in parent_ids or (row_lookup.get(eid) and row_lookup[eid].get("kind") == "iec104_asdu")
            ]
            rows = [row_lookup.get(eid) for eid in filtered_eids]
        raw_net_obs_count += len(rows)
        c_break = _classify_container_rows(rows)
        for k, v in c_break.items():
            total_breakdown[k] += v

    raw_obs_count = raw_net_obs_count + ipal_derived_rows
    true_duplicate_or_derived_inflation = (
        total_breakdown["true_cross_vantage_mirror_duplicate_count"]
        + total_breakdown["same_asdu_different_ioa_point_count"]
        + ipal_derived_rows
    )
    multi_event_anchor_aggregation = (
        total_breakdown["distinct_messages_in_same_tcp_session_count"]
        + total_breakdown["distinct_time_network_events_in_anchor_count"]
    )
    falsely_counted_over_containers = max(0, raw_obs_count - distinct_containers)
    inflation_factor = round(raw_obs_count / distinct_containers, 4) if distinct_containers > 0 else 1.0
    strict_dup_inflation_factor = (
        round((distinct_containers + true_duplicate_or_derived_inflation) / distinct_containers, 4)
        if distinct_containers > 0 else 1.0
    )

    spurious_multi_source_storylines = 0
    for sl in mirage_storylines.get("storylines") or []:
        true_indep_edges = int(sl.get("independent_support_edge_count") or 0)
        naive_sources = (
            int(sl.get("vantage_capture_count") or 0)
            + len(sl.get("temporal_correspondences") or [])
            + len(sl.get("co_reported_in_same_asdu") or [])
        )
        if true_indep_edges == 0 and naive_sources >= 2:
            spurious_multi_source_storylines += 1

    return {
        "ablation_id": "A2_without_provenance_deduplication",
        "analysis_nature": "counterfactual_ablation_on_source_container_accounting",
        "epistemic_note": (
            "Source containers (`SRC-ASDU-...`, `SRC-MSG-...`) represent deduplicated network "
            "message/event containers, NOT independent physical process sensors. Furthermore, "
            "multi-packet `communication_change` and `arp_activity_increase` anchors aggregate "
            "distinct-time network events (`distinct_time_network_events_in_anchor_count` and "
            "`distinct_messages_in_same_tcp_session_count`), which are strictly separated from "
            "`true_cross_vantage_mirror_duplicate_count`."
        ),
        "raw_observation_count": raw_obs_count,
        "raw_network_observation_count": raw_net_obs_count,
        "distinct_source_container_count": distinct_containers,
        "distinct_asdu_container_count": int(ledger.get("iec104_asdu_container_count") or distinct_containers),
        "distinct_rtu_count_in_window": distinct_rtus,
        "true_cross_vantage_mirror_duplicate_count": total_breakdown["true_cross_vantage_mirror_duplicate_count"],
        "same_asdu_different_ioa_point_count": total_breakdown["same_asdu_different_ioa_point_count"],
        "distinct_messages_in_same_tcp_session_count": total_breakdown["distinct_messages_in_same_tcp_session_count"],
        "distinct_time_network_events_in_anchor_count": total_breakdown["distinct_time_network_events_in_anchor_count"],
        "ipal_derived_observation_count": ipal_derived_rows,
        "unknown_provenance_relation_count": total_breakdown["unknown_provenance_relation_count"],
        "true_duplicate_or_derived_source_inflation_count": true_duplicate_or_derived_inflation,
        "multi_event_anchor_aggregation_count": multi_event_anchor_aggregation,
        "total_excess_observations_over_containers": falsely_counted_over_containers,
        "strict_duplicate_and_derived_inflation_factor": strict_dup_inflation_factor,
        "raw_to_container_ratio": inflation_factor,
        "spurious_multi_source_storyline_count_without_dedup": spurious_multi_source_storylines,
    }
