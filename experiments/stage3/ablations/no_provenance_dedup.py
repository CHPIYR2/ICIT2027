"""Ablation A2: Without Provenance Deduplication.

Evaluates the impact of removing MIRAGE-OT's three provenance deduplication mechanisms on
the exact same indexed evidence without modifying the Evidence Database:
1. Multi-Vantage Mirror Deduplication (`_merge_iec_vantages` / `collapse_multi_vantage_messages`):
   The same Ethernet/TCP/IEC-104 packet captured at multiple switch mirror ports (`n302`, `n318`,
   `n406`, `n495`, etc.) is one network transmission, not multiple independent sensors.
2. Same-ASDU Multi-IOA Container Accounting (`SRC-ASDU-...` in `rtu_asdu_bundles`):
   Multiple information objects carried in a single multi-IOA ASDU from one RTU share a single
   protocol message container (`independent_source_count = 1`).
3. IPAL State Transcription Non-Independence (`counts_as_independent_source = False`, weight 0):
   IPAL `electrical_update` rows are network-derived transcriptions without packet lineage, not
   independent physical process sensors.
"""
from __future__ import annotations


def run_ablation_without_provenance_dedup(
    *,
    tx_result: dict,
    anchor_result: dict,
    mirage_event_graph: dict,
    mirage_storylines: dict,
    mirage_synthesis: dict,
) -> dict:
    anchors = list(anchor_result.get("anchors") or [])
    verified_anchors = [
        a for a in anchors
        if a.get("verification_status") == "verified_observation" and not a.get("covered_by_transaction")
    ]
    txs = list(tx_result.get("transactions") or [])
    ledger = mirage_synthesis.get("source_dependency_ledger") or {}

    if txs and not anchor_result.get("behavioral_mode"):
        # Control-command window accounting
        distinct_containers = len({
            cid for tx in txs for cid in (tx.get("canonical_source_ids") or [])
        })
        distinct_rtus = len({tx.get("rtu_ip") for tx in txs if tx.get("rtu_ip")})
        vantage_captures = 0
        logical_msgs = 0
        for tx in txs:
            for stage_key in ("command_activation", "activation_confirmation", "activation_termination"):
                msg = tx.get(stage_key)
                if msg:
                    logical_msgs += 1
                    vantage_captures += int(msg.get("vantage_capture_count") or len(msg.get("evidence_ids") or [1]))
            for fb in tx.get("protocol_state_feedback") or []:
                logical_msgs += 1
                vantage_captures += int(fb.get("vantage_capture_count") or len(fb.get("evidence_ids") or [1]))
            mt = tx.get("measurement_transition")
            if mt:
                if mt.get("pre_command_evidence_ids"):
                    logical_msgs += 1
                    vantage_captures += max(1, len(mt["pre_command_evidence_ids"]) // 2)
                if mt.get("post_command_evidence_ids"):
                    logical_msgs += 1
                    vantage_captures += len(mt["post_command_evidence_ids"])
        mirror_duplicates = max(0, vantage_captures - logical_msgs)
        same_asdu_expansion = 0
        ipal_derived_rows = sum(len(tx.get("ipal_state_updates") or []) for tx in txs)
        raw_obs_count = vantage_captures + ipal_derived_rows
    else:
        # Behavioral window accounting on verified observations
        distinct_containers = int(ledger.get("verified_source_container_count") or 0)
        distinct_rtus = int(ledger.get("distinct_rtu_count") or 0)
        point_objects_total = 0
        vantage_captures = 0
        for a in verified_anchors:
            pts = a.get("points") or []
            if pts:
                point_objects_total += len(pts)
                vantage_captures += sum(len(p.get("evidence_ids") or [1]) for p in pts)
            else:
                point_objects_total += 1
                vantage_captures += len(a.get("evidence_ids") or [1])
        mirror_duplicates = max(0, vantage_captures - point_objects_total)
        same_asdu_expansion = max(0, point_objects_total - distinct_containers)
        ipal_derived_rows = sum(len(a.get("ipal_rows") or []) for a in verified_anchors)
        raw_obs_count = vantage_captures + ipal_derived_rows

    falsely_counted_independent = max(0, raw_obs_count - distinct_containers)
    inflation_factor = round(raw_obs_count / distinct_containers, 4) if distinct_containers > 0 else 1.0

    # Check how many single-RTU / single-ASDU storylines would appear "multi-source corroborated" (>= 2 sources)
    # if mirror vantages, multi-IOA points, or IPAL rows were counted as independent sources
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
        "method_description": (
            "Cancels MIRAGE-OT's multi-vantage mirror deduplication, same-ASDU multi-IOA container "
            "bundling, and IPAL zero-weight correspondence accounting on identical observations."
        ),
        "observations_used": ["Identical to full MIRAGE-OT"],
        "information_removed": [
            "Multi-vantage packet deduplication (`_merge_iec_vantages`, `collapse_multi_vantage_messages`)",
            "Same-ASDU container grouping (`SRC-ASDU-...`)",
            "Non-independence marking on IPAL transcriptions (`counts_as_independent_source=False`)",
        ],
        "allowed_claims": ["Treats every raw vantage capture, IOA point, and IPAL row as an independent source"],
        "raw_observation_count": raw_obs_count,
        "distinct_source_container_count": distinct_containers,
        "distinct_asdu_container_count": int(ledger.get("iec104_asdu_container_count") or distinct_containers),
        "distinct_rtu_count": distinct_rtus,
        "mirror_duplicate_count": mirror_duplicates,
        "same_asdu_multi_point_expansion_count": same_asdu_expansion,
        "ipal_derived_observation_count": ipal_derived_rows,
        "falsely_counted_independent_source_count": falsely_counted_independent,
        "source_inflation_factor": inflation_factor,
        "spurious_multi_source_storyline_count_without_dedup": spurious_multi_source_storylines,
    }
