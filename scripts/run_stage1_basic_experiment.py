"""Stage 1 Frozen Basic Experiment Batch Runner (`01-Basic`, all 28 test windows).

Guarantees enforced before and during execution:
1. Verifies every module SHA256 and aggregate `code_sha256` / `evidence_code_sha256`
   against `configs/etgi/method_freeze.v1.json`. Refuses to run if any frozen module
   was modified.
2. Verifies `01-Basic.zip`, `02-Semiurban.zip`, and `03-Rural.zip` byte sizes and MD5
   digests against `configs/etgi/method_freeze.v1.json`.
3. Enforces strict input isolation: reads only `(episode_id, scenario, recording, start, end)`
   from `configs/etgi/basic_test_windows.v1.json`. Never opens `events.json`, `events.jsonl`,
   attack labels, `malicious` flags, or `physical.zip`.
4. Audits all existing Basic SQLite indexes for R4/Freeze IEC-104 field compatibility
   (`quality_flags`, `quality_good`, `cot_test`, 4 mirror PCAPs, 6 blocked members).
   Re-indexes any incompatible or missing window using the frozen `index_window()`.
5. Runs `reconstruct_incident(..., llm=None)` across all 28 windows into a fresh output
   directory and compiles the complete 28-window metrics, timing, and storage table.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sqlite3
import time
from pathlib import Path

from mirage_ot.etgi.evidence.index import index_window, open_indexed
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import get_meta
from mirage_ot.etgi.reconstruction.engine import reconstruct_incident
from mirage_ot.etgi.reconstruction.synthesis import synthesize_incident_scenario


CANDIDATE_EXISTING_INDEXES = {
    "ev_0961f1c2da8a257e3ebc": [
        Path("runs/etgi/basic-ev0961/evidence.sqlite"),
        Path("runs/etgi/r4-reindex-20261015/ev_0961f1c2da8a257e3ebc/evidence.sqlite"),
    ],
    "ev_12dcd56b2f5e78144cfb": [
        Path("runs/etgi/memory-comparison-20261014/ev_12dcd56b2f5e78144cfb/evidence.sqlite"),
        Path("runs/etgi/r4-reindex-20261015/ev_12dcd56b2f5e78144cfb/evidence.sqlite"),
    ],
    "ev_3e4d36008b29595ef246": [
        Path("runs/etgi/memory-comparison-20261014/ev_3e4d36008b29595ef246/evidence.sqlite"),
    ],
    "ev_4e913b93a51e7b3c9e31": [
        Path("runs/etgi/behavioral-20261015/index/ev_4e913b93a51e7b3c9e31/evidence.sqlite"),
    ],
    "ev_564bebaa45f0686cf98d": [
        Path("runs/etgi/behavioral-20261015/index/ev_564bebaa45f0686cf98d/evidence.sqlite"),
    ],
    "ev_812f8057d7c974d9cf36": [
        Path("runs/etgi/behavioral-20261015/index/ev_812f8057d7c974d9cf36/evidence.sqlite"),
    ],
    "ev_b15ac1c8e04d148f09cb": [
        Path("runs/etgi/behavioral-20261015/index/ev_b15ac1c8e04d148f09cb/evidence.sqlite"),
    ],
    "ev_cbe1e5bef23346604396": [
        Path("runs/etgi/behavioral-20261015/index/ev_cbe1e5bef23346604396/evidence.sqlite"),
    ],
}


def verify_frozen_code_hashes(freeze: dict, repo_root: Path) -> dict:
    etgi_dir = repo_root / "src" / "mirage_ot" / "etgi"
    post_dir = etgi_dir / "postalert"
    recon_dir = etgi_dir / "reconstruction"
    ev_dir = etgi_dir / "evidence"

    code_digest = hashlib.sha256()
    module_hashes = {}
    for folder in (post_dir, recon_dir):
        for p in sorted(folder.glob("*.py")):
            rel = f"{folder.name}/{p.name}"
            b = p.read_bytes()
            module_hashes[rel] = hashlib.sha256(b).hexdigest()
            code_digest.update(rel.encode("utf-8"))
            code_digest.update(b)

    ev_digest = hashlib.sha256()
    ev_hashes = {}
    for p in sorted(ev_dir.glob("*.py")):
        rel = f"evidence/{p.name}"
        b = p.read_bytes()
        ev_hashes[rel] = hashlib.sha256(b).hexdigest()
        ev_digest.update(rel.encode("utf-8"))
        ev_digest.update(b)

    actual_code_sha = code_digest.hexdigest()
    actual_ev_sha = ev_digest.hexdigest()
    if actual_code_sha != freeze["code_sha256"]:
        raise RuntimeError(f"Frozen code_sha256 mismatch: {actual_code_sha} != {freeze['code_sha256']}")
    if actual_ev_sha != freeze["evidence_code_sha256"]:
        raise RuntimeError(f"Frozen evidence_code_sha256 mismatch: {actual_ev_sha} != {freeze['evidence_code_sha256']}")
    if module_hashes != freeze["module_hashes"]:
        raise RuntimeError("Frozen postalert/reconstruction module hashes do not match method_freeze.v1.json")
    if ev_hashes != freeze["evidence_module_hashes"]:
        raise RuntimeError("Frozen evidence module hashes do not match method_freeze.v1.json")

    return {
        "verified": True,
        "frozen_engine_git_commit": freeze["frozen_engine_git_commit"],
        "code_sha256": actual_code_sha,
        "evidence_code_sha256": actual_ev_sha,
        "module_count": len(module_hashes) + len(ev_hashes),
    }


def verify_upstream_archives(freeze: dict, raw_dir: Path) -> dict:
    out = {}
    for zname, expected in freeze["upstream_datasets"].items():
        zp = raw_dir / zname
        sz = zp.stat().st_size
        h = hashlib.md5()
        with zp.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024 * 8), b""):
                h.update(chunk)
        md5 = h.hexdigest()
        if sz != expected["compressed_bytes"] or md5 != expected["md5"]:
            raise RuntimeError(f"Archive {zname} mismatch: size={sz}, md5={md5}")
        out[zname] = {
            "compressed_bytes": sz,
            "compressed_gib_binary": round(sz / (1024 ** 3), 4),
            "compressed_gb_decimal": round(sz / (10 ** 9), 4),
            "uncompressed_bytes": expected.get("uncompressed_bytes"),
            "md5": md5,
            "matches_freeze_manifest": True,
        }
    return out


def audit_sqlite_index(db_path: Path, expected_start: float, expected_end: float) -> dict:
    if not db_path.exists():
        return {"path": str(db_path), "exists": False, "compatible": False, "reasons": ["file_not_found"]}
    conn, meta = open_indexed(db_path)
    try:
        reasons = []
        if abs(float(meta["incident_start"]) - expected_start) > 1e-6 or abs(float(meta["incident_end"]) - expected_end) > 1e-6:
            reasons.append("window_bounds_mismatch")
        members = get_meta(conn, "members") or {}
        pcaps = members.get("pcaps") or []
        not_opened = members.get("not_opened") or []
        if len(pcaps) != 4:
            reasons.append(f"pcap_count_mismatch:{len(pcaps)}")
        if len(not_opened) != 6:
            reasons.append(f"blocked_member_count_mismatch:{len(not_opened)}")
        iec_rows = conn.execute("SELECT payload_json FROM evidence WHERE kind='iec104_asdu'").fetchall()
        if not iec_rows:
            reasons.append("no_iec104_rows")
        meas_state_total = 0
        qflags_ok = 0
        qgood_ok = 0
        cot_test_ok = 0
        for r in iec_rows:
            p = json.loads(r["payload_json"])
            tid = p.get("type_id")
            if tid in (1, 2, 3, 4, 9, 10, 11, 12, 13, 14, 30, 31, 34, 35, 36):
                meas_state_total += 1
                qf = p.get("quality_flags")
                if isinstance(qf, dict) and qf and all(isinstance(v, bool) for v in qf.values()):
                    qflags_ok += 1
                if isinstance(p.get("quality_good"), bool):
                    qgood_ok += 1
            if isinstance(p.get("cot_test"), bool):
                cot_test_ok += 1
        if qflags_ok != meas_state_total:
            reasons.append(f"missing_or_incomplete_quality_flags:{qflags_ok}/{meas_state_total}")
        if qgood_ok != meas_state_total:
            reasons.append(f"missing_quality_good:{qgood_ok}/{meas_state_total}")
        if cot_test_ok != len(iec_rows):
            reasons.append(f"missing_cot_test_bit:{cot_test_ok}/{len(iec_rows)}")
        total_rows = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        return {
            "path": str(db_path),
            "exists": True,
            "compatible": not reasons,
            "reasons": reasons,
            "total_evidence_rows": total_rows,
            "iec104_rows": len(iec_rows),
            "meas_state_rows": meas_state_total,
            "quality_flags_complete_rows": qflags_ok,
            "cot_test_decoded_rows": cot_test_ok,
            "sqlite_bytes": db_path.stat().st_size,
        }
    finally:
        conn.close()


def _dir_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _classify_window_profile_and_reasons(res: dict) -> tuple[str, list[str], str]:
    txs = res["transactions"]["transactions"]
    anchors = res["event_anchors"]["anchors"]
    inv = res["event_anchors"]["observation_inventory"]
    sl_res = res["storylines"]
    syn = res["incident_synthesis"]
    part = syn["local_storyline_partition"]

    anchor_types = {a["anchor_type"] for a in anchors}
    if txs:
        profile = "S1_control_command_window"
    elif "arp_activity_increase" in anchor_types or "communication_change" in anchor_types:
        profile = "S3_arp_or_iec104_link_disruption_window"
    elif "spontaneous_state_report" in anchor_types:
        profile = "S2_spontaneous_state_and_measurement_drop_window"
    else:
        profile = "S4_periodic_measurement_only_window"

    reasons: list[str] = []
    if not txs and inv.get("iec104_control_objects_in_window", 0) == 0:
        if not anchors:
            reasons.append("LOW_INFORMATION_PERIODIC_ONLY:no_anchors_detected")
        elif profile == "S4_periodic_measurement_only_window":
            if part["counts"]["supported_multi_node_storyline_count"] == 0 and part["counts"]["verified_single_anchor_storyline_count"] == 0:
                reasons.append("LOW_INFORMATION_PERIODIC_ONLY:only_unverified_transient_oscillations")
            else:
                reasons.append("NO_CONTROL_OR_STATE_TRIGGER:periodic_telemetry_only")

    for tx in txs:
        st = tx["device_state_change_status"]
        if st == "state_report_observed_no_pre_baseline":
            reasons.append(f"COMMAND_WITHOUT_PRE_BASELINE:{tx['transaction_id']}:{tx['entity']}")
        elif st == "no_state_change_observed":
            reasons.append(f"COMMAND_CONFIRMATION_WITHOUT_STATE_CHANGE:{tx['transaction_id']}:{tx['entity']}")
        elif st not in ("verified_state_transition", "verified_measurement_transition"):
            reasons.append(f"COMMAND_TRANSITION_UNVERIFIED:{tx['transaction_id']}:{st}")

    for q in part["quarantined_unverified_observations"]:
        reasons.append(f"UNVERIFIED_ANCHOR_QUARANTINED:{q['anchor_id']}:{','.join(q['verification_issues'])}")

    for sq in part["sequential_same_device_observations"]:
        reasons.append(f"SAME_DEVICE_GATE_REJECTED_SEQUENTIAL:{sq['edge_id']}:{sq['device_stem']}:{','.join(sq['failed_conditions'])}")

    if sl_res.get("unresolved_branches"):
        reasons.append(f"CROSS_DEVICE_NO_TOPOLOGY_UNRESOLVED:{len(sl_res['unresolved_branches'])}_branches")

    # Why higher-level cross-device / causal synthesis cannot be claimed when bridges == 0
    verified_tx = sum(
        1 for t in txs if t["device_state_change_status"] in ("verified_state_transition", "verified_measurement_transition")
    )
    bridges = len(syn["verified_element_bridges"])
    if bridges > 0:
        why_note = (
            f"Formed {bridges} cross-RTU verified element bridge(s) across {len(syn['bridged_bundle_components'])} "
            f"component(s); cross-device co-occurrences ({len(sl_res['unresolved_branches'])}) remain unresolved "
            "because no grid topology model exists."
        )
    elif verified_tx > 0:
        why_note = (
            f"Reconstructed {len(txs)} control transaction(s) with {verified_tx} verified same-device transition(s); "
            "cross-entity impacts remain unresolved without a physical topology model."
        )
    elif txs:
        why_note = (
            f"Reconstructed {len(txs)} control transaction(s) (command + confirmation/state report), but 0 verified "
            "transitions because pre-command state baselines or post-command shifts were absent in telemetry."
        )
    elif part["counts"]["verified_single_anchor_storyline_count"] > 0:
        why_note = (
            f"Preserved {part['counts']['verified_single_anchor_storyline_count']} verified single-anchor storyline(s) "
            f"and {len(syn['rtu_asdu_bundles'])} source bundle(s), but 0 cross-RTU bridges because no single grid "
            "element exhibited corroborated two-end transitions across distinct RTUs."
        )
    else:
        why_note = (
            f"Honest abstention from supported storylines/bridges: window contains 0 control commands, 0 verified "
            f"anchors, and {part['counts']['quarantined_unverified_observation_count']} quarantined unverified "
            "observation(s) on periodic M_ME_NC_1 (COT=1) telemetry."
        )

    return profile, reasons, why_note


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 1 Frozen Basic 28-Window Experiment")
    parser.add_argument("--freeze-manifest", type=Path, default=Path("configs/etgi/method_freeze.v1.json"))
    parser.add_argument("--windows", type=Path, default=Path("configs/etgi/basic_test_windows.v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/sherlock/v3"))
    parser.add_argument("--out-root", type=Path, default=Path("runs/etgi/stage1-basic-frozen-20261015"))
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    freeze = json.loads(args.freeze_manifest.read_text(encoding="utf-8"))
    windows = json.loads(args.windows.read_text(encoding="utf-8"))

    # 1. Verify frozen module hashes
    code_check = verify_frozen_code_hashes(freeze, repo_root)
    # 2. Verify Sherlock v3 ZIP sizes & MD5s
    archive_check = verify_upstream_archives(freeze, args.raw_dir)
    # 3. Verify strict input isolation on windows specification
    allowed_keys = set(freeze["strict_input_isolation"]["allowed_window_specification_fields"])
    for w in windows:
        if set(w.keys()) != allowed_keys:
            raise RuntimeError(f"Window spec contains non-isolated keys: {set(w.keys())} != {allowed_keys}")

    if args.out_root.exists():
        raise FileExistsError(f"{args.out_root} already exists; refusing to overwrite")
    index_root = args.out_root / "index"
    recon_root = args.out_root / "reconstruction"
    index_root.mkdir(parents=True)
    recon_root.mkdir(parents=True)

    # 4. Audit existing 8 Basic SQLite indexes
    existing_index_audit = {}
    reusable_db_by_episode: dict[str, Path] = {}
    w_by_ep = {w["episode_id"]: w for w in windows}
    for ep_id, cand_paths in sorted(CANDIDATE_EXISTING_INDEXES.items()):
        w = w_by_ep[ep_id]
        ep_audits = []
        for cp in cand_paths:
            aud = audit_sqlite_index(cp, float(w["start"]), float(w["end"]))
            ep_audits.append(aud)
            if aud["compatible"]:
                reusable_db_by_episode[ep_id] = cp
        existing_index_audit[ep_id] = {
            "candidates": ep_audits,
            "selected_reusable_path": str(reusable_db_by_episode[ep_id]) if ep_id in reusable_db_by_episode else None,
            "action": "reuse_verified_compatible_index" if ep_id in reusable_db_by_episode else "reindex_with_frozen_indexer",
        }

    # 5. Index or copy all 28 windows and run frozen reconstruction + synthesis
    archive_path = args.raw_dir / "01-Basic.zip"
    window_rows = []
    total_index_sec = 0.0
    total_recon_sec = 0.0
    total_syn_sec = 0.0

    for idx, w in enumerate(windows, start=1):
        ep_id = w["episode_id"]
        start = float(w["start"])
        end = float(w["end"])
        ep_index_dir = index_root / ep_id
        ep_index_dir.mkdir(parents=True)
        db_path = ep_index_dir / "evidence.sqlite"

        t0_idx = time.perf_counter()
        if ep_id in reusable_db_by_episode:
            shutil.copy2(reusable_db_by_episode[ep_id], db_path)
            index_mode = "reused_compatible_r4_index"
        else:
            index_window(
                archive_path,
                scenario="01-Basic",
                recording="test",
                start=start,
                end=end,
                out=db_path,
                context_seconds=15.0,
                work=ep_index_dir / "slices",
                modalities="both",
            )
            shutil.rmtree(ep_index_dir / "slices", ignore_errors=True)
            index_mode = "indexed_fresh_by_frozen_indexer"
        index_sec = round(time.perf_counter() - t0_idx, 3)
        total_index_sec += index_sec

        post_audit = audit_sqlite_index(db_path, start, end)
        if not post_audit["compatible"]:
            raise RuntimeError(f"Indexed DB for {ep_id} failed compatibility audit: {post_audit}")

        conn, meta = open_indexed(db_path)
        db = EvidenceDB(conn, incident_start=start, incident_end=end)
        ep_recon_dir = recon_root / ep_id

        t0_rec = time.perf_counter()
        res = reconstruct_incident(
            db,
            start,
            end,
            background_start=start - 15.0,
            background_end=start,
            llm=None,
            selection_limit=24,
            seed=1,
            out_dir=ep_recon_dir,
        )
        recon_total_sec = round(time.perf_counter() - t0_rec, 3)

        # Measure standalone synthesis step duration deterministically
        t0_syn = time.perf_counter()
        _ = synthesize_incident_scenario(
            incident_start=start,
            incident_end=end,
            tx_result=res["transactions"],
            anchor_result=res["event_anchors"],
            event_graph=res["event_graph"],
            storyline_result=res["storylines"],
        )
        syn_sec = round(time.perf_counter() - t0_syn, 4)
        conn.close()

        total_recon_sec += recon_total_sec
        total_syn_sec += syn_sec

        tx_res = res["transactions"]
        anc_res = res["event_anchors"]
        eg_res = res["event_graph"]
        sl_res = res["storylines"]
        syn_res = res["incident_synthesis"]
        qc_res = res["quality_consistency"]
        lc_res = res["lineage_consistency"]
        rep_res = res["report"]

        profile, reasons, why_note = _classify_window_profile_and_reasons(res)
        anc_by_type = {}
        for a in anc_res["anchors"]:
            anc_by_type[a["anchor_type"]] = anc_by_type.get(a["anchor_type"], 0) + 1

        edges_by_status = {}
        for e in eg_res["edges"]:
            st = e.get("verification_status", "unknown")
            edges_by_status[st] = edges_by_status.get(st, 0) + 1

        part_counts = syn_res["local_storyline_partition"]["counts"]
        ledger = syn_res["source_dependency_ledger"]
        has_supported_local_component = bool(
            len(syn_res["verified_element_bridges"]) > 0
            or tx_res["verified_state_or_measurement_transition_count"] > 0
            or part_counts["supported_multi_node_storyline_count"] > 0
            or part_counts["verified_single_anchor_storyline_count"] > 0
        )
        has_multi_source_corroborated_component = bool(
            len(syn_res["verified_element_bridges"]) > 0
            or tx_res["verified_state_or_measurement_transition_count"] > 0
        )

        row_summary = {
            "window_index": idx,
            "episode_id": ep_id,
            "scenario": "01-Basic",
            "recording": "test",
            "window_start": start,
            "window_end": end,
            "window_duration_s": round(end - start, 3),
            "observation_profile": profile,
            "index_mode": index_mode,
            "sqlite_evidence_rows": post_audit["total_evidence_rows"],
            "iec104_rows_in_db": post_audit["iec104_rows"],
            "iec104_control_objects_in_window": anc_res["observation_inventory"]["iec104_control_objects_in_window"],
            "transaction_count_total": tx_res["transaction_count"],
            "transaction_count_accepted": tx_res["accepted_count"],
            "transaction_count_verified_transition": tx_res["verified_state_or_measurement_transition_count"],
            "transaction_count_unverified_state_report": tx_res["state_report_observed_unverified_count"],
            "transaction_count_no_state_change": tx_res["no_state_change_count"],
            "anchor_count_total": anc_res["anchor_count"],
            "anchor_count_verified": anc_res["verified_anchor_count"],
            "anchor_count_unverified": anc_res["unverified_anchor_count"],
            "anchor_counts_by_type": anc_by_type,
            "graph_node_count": eg_res["node_count"],
            "graph_edge_count": eg_res["edge_count"],
            "graph_edges_by_verification_status": edges_by_status,
            "graph_edges_by_claim_level": eg_res["edges_by_claim_level"],
            "storyline_count_total": sl_res["storyline_count"],
            "storyline_count_supported_multi_node": part_counts["supported_multi_node_storyline_count"],
            "storyline_count_verified_single_anchor": part_counts["verified_single_anchor_storyline_count"],
            "storyline_count_protocol_partial_or_unverified": part_counts["protocol_partial_or_unverified_storyline_count"],
            "storyline_count_unverified_observation": part_counts["quarantined_unverified_observation_count"],
            "sequential_same_device_observation_count": part_counts["sequential_same_device_observation_count"],
            "rtu_asdu_bundle_count": len(syn_res["rtu_asdu_bundles"]),
            "cross_rtu_verified_element_bridge_count": len(syn_res["verified_element_bridges"]),
            "same_rtu_supported_relation_count": len(syn_res.get("same_rtu_supported_relations") or []),
            "bridged_bundle_component_count": len(syn_res["bridged_bundle_components"]),
            "candidate_scenario_phase_count": len(syn_res["candidate_scenario_phases"]),
            "competing_explanation_count": len(syn_res["competing_explanations"]),
            "competing_explanation_classes": [e["hypothesis_class"] for e in syn_res["competing_explanations"]],
            "unresolved_cross_device_branch_count": len(sl_res["unresolved_branches"]),
            "source_ledger_counts_by_container_family": {
                "iec104_asdu": ledger["iec104_asdu_container_count"],
                "tcp_link": ledger["tcp_link_container_count"],
                "arp": ledger["arp_container_count"],
                "composite_event": ledger["composite_event_container_count"],
                "verified_source_total": ledger["verified_source_container_count"],
                "co_reported_same_asdu_reduction": ledger["co_reported_same_asdu_reduction_count"],
                "ipal_correspondence_rows_excluded": ledger["ipal_correspondence_row_count"],
            },
            "has_supported_local_component": has_supported_local_component,
            "has_multi_source_corroborated_component": has_multi_source_corroborated_component,
            "quality_consistency_passed": qc_res["consistent"],
            "lineage_consistency_passed": lc_res["consistent"],
            "final_report_status": rep_res["report_status"],
            "reconstruction_failure_or_abstention_reasons": reasons,
            "higher_level_synthesis_boundary_explanation": why_note,
            "timing_seconds": {
                "indexing_s": index_sec,
                "reconstruction_and_synthesis_total_s": recon_total_sec,
                "synthesis_step_s": syn_sec,
            },
            "storage_bytes": {
                "sqlite_bytes": post_audit["sqlite_bytes"],
                "reconstruction_artifacts_bytes": _dir_bytes(ep_recon_dir),
            },
        }
        window_rows.append(row_summary)
        print(
            f"[{idx:02d}/28] {ep_id} ({profile[:2]}): "
            f"tx={row_summary['transaction_count_total']} (ver={row_summary['transaction_count_verified_transition']}), "
            f"anc={row_summary['anchor_count_total']} (ver={row_summary['anchor_count_verified']}, unv={row_summary['anchor_count_unverified']}), "
            f"sl={row_summary['storyline_count_total']}, bnd={row_summary['rtu_asdu_bundle_count']}, "
            f"brg={row_summary['cross_rtu_verified_element_bridge_count']}, "
            f"qc={row_summary['quality_consistency_passed']}, lc={row_summary['lineage_consistency_passed']}, "
            f"idx={index_sec:.2f}s, rec={recon_total_sec:.2f}s"
        )

    total_sqlite_bytes = sum(r["storage_bytes"]["sqlite_bytes"] for r in window_rows)
    total_recon_bytes = sum(r["storage_bytes"]["reconstruction_artifacts_bytes"] for r in window_rows)

    aggregate = {
        "total_windows": len(window_rows),
        "windows_by_profile": {
            p: sum(1 for r in window_rows if r["observation_profile"] == p)
            for p in sorted({r["observation_profile"] for r in window_rows})
        },
        "indexing_breakdown": {
            "reused_compatible_r4_indexes": sum(1 for r in window_rows if r["index_mode"] == "reused_compatible_r4_index"),
            "freshly_indexed_windows": sum(1 for r in window_rows if r["index_mode"] == "indexed_fresh_by_frozen_indexer"),
        },
        "totals": {
            "transactions_total": sum(r["transaction_count_total"] for r in window_rows),
            "transactions_accepted": sum(r["transaction_count_accepted"] for r in window_rows),
            "transactions_verified_transition": sum(r["transaction_count_verified_transition"] for r in window_rows),
            "transactions_unverified_state_report": sum(r["transaction_count_unverified_state_report"] for r in window_rows),
            "transactions_no_state_change": sum(r["transaction_count_no_state_change"] for r in window_rows),
            "anchors_total": sum(r["anchor_count_total"] for r in window_rows),
            "anchors_verified": sum(r["anchor_count_verified"] for r in window_rows),
            "anchors_unverified": sum(r["anchor_count_unverified"] for r in window_rows),
            "storylines_total": sum(r["storyline_count_total"] for r in window_rows),
            "storylines_supported_multi_node": sum(r["storyline_count_supported_multi_node"] for r in window_rows),
            "storylines_verified_single_anchor": sum(r["storyline_count_verified_single_anchor"] for r in window_rows),
            "storylines_protocol_partial_or_unverified": sum(r["storyline_count_protocol_partial_or_unverified"] for r in window_rows),
            "storylines_unverified_observation": sum(r["storyline_count_unverified_observation"] for r in window_rows),
            "sequential_same_device_observations": sum(r["sequential_same_device_observation_count"] for r in window_rows),
            "rtu_asdu_bundles": sum(r["rtu_asdu_bundle_count"] for r in window_rows),
            "cross_rtu_verified_element_bridges": sum(r["cross_rtu_verified_element_bridge_count"] for r in window_rows),
            "same_rtu_supported_relations": sum(r["same_rtu_supported_relation_count"] for r in window_rows),
            "bridged_bundle_components": sum(r["bridged_bundle_component_count"] for r in window_rows),
            "unresolved_cross_device_branches": sum(r["unresolved_cross_device_branch_count"] for r in window_rows),
            "windows_with_supported_local_component": sum(1 for r in window_rows if r["has_supported_local_component"]),
            "windows_with_multi_source_corroborated_component": sum(1 for r in window_rows if r["has_multi_source_corroborated_component"]),
            "quality_consistency_pass_count": sum(1 for r in window_rows if r["quality_consistency_passed"]),
            "lineage_consistency_pass_count": sum(1 for r in window_rows if r["lineage_consistency_passed"]),
            "quality_consistency_pass_rate": round(sum(1 for r in window_rows if r["quality_consistency_passed"]) / len(window_rows), 4),
            "lineage_consistency_pass_rate": round(sum(1 for r in window_rows if r["lineage_consistency_passed"]) / len(window_rows), 4),
        },
        "runtime_seconds": {
            "indexing_total_s": round(total_index_sec, 3),
            "reconstruction_and_synthesis_total_s": round(total_recon_sec, 3),
            "synthesis_step_total_s": round(total_syn_sec, 4),
            "wall_clock_total_s": round(total_index_sec + total_recon_sec, 3),
        },
        "storage_bytes": {
            "sqlite_index_total_bytes": total_sqlite_bytes,
            "sqlite_index_total_mib": round(total_sqlite_bytes / (1024 ** 2), 2),
            "reconstruction_artifacts_total_bytes": total_recon_bytes,
            "reconstruction_artifacts_total_mib": round(total_recon_bytes / (1024 ** 2), 2),
        },
    }

    summary = {
        "stage": "Stage 1 Frozen Basic 28-Window Experiment",
        "freeze_verification": code_check,
        "upstream_archive_verification": archive_check,
        "strict_input_isolation_verified": True,
        "existing_index_audit": existing_index_audit,
        "aggregate_summary": aggregate,
        "windows": window_rows,
    }
    (args.out_root / "stage1_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8",
    )
    print("Stage 1 complete. Summary written to", args.out_root / "stage1_summary.json")


if __name__ == "__main__":
    main()
