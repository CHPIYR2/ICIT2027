"""Stage 2 Frozen Cross-Scenario Experiment Runner (`02-Semiurban` 39 windows & `03-Rural` 36 windows).

Supports:
- `--mode stage2a`: Runs the 6 pre-selected deterministic pilot windows (3 Semiurban, 3 Rural:
  earliest, mid-recording, and max-duration) to verify end-to-end engineering compatibility.
- `--mode full`: Runs all 39 Semiurban test windows and all 36 Rural test windows (reusing any
  window already indexed and verified during `--mode stage2a` in the same `--out-root`).

Hardened requirements enforced without modifying any frozen module:
1. Per-type required IEC-104 quality bit audit (`{"iv", "nt", "sb", "bl"}` for state types
   1/2/3/4/30/31 and `{"iv", "nt", "sb", "bl", "ov"}` for measurement types 9-14/34-36).
2. Post-run verification that every window's `run_manifest.json` matches `frozen_engine_git_commit`,
   `code_sha256`, and `evidence_code_sha256` in `configs/etgi/method_freeze.v1.json`.
3. Strict separation of data-insufficiency `Honest Abstention` (`execution_status="COMPLETED_OK"`)
   from software/data `Execution Failure` (`execution_status="EXECUTION_FAILURE"`).
4. Separate timing accounting for `code_freeze_verification_s`, `archive_integrity_audit_s`,
   `existing_index_audit_s`, `windows_processing_wall_clock_s`, and true `process_end_to_end_s`.
5. Per-window isolated subprocess execution recording `indexing_s`, `reconstruction_s`,
   `synthesis_step_s`, `window_total_s`, `sqlite_bytes`, `reconstruction_artifacts_bytes`, and
   isolated process `peak_rss_mib` via `resource.getrusage`.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
import os
import resource
import shutil
import statistics
import sys
import time
import traceback
from pathlib import Path

from mirage_ot.etgi.evidence.index import index_window, open_indexed
from mirage_ot.etgi.evidence.queries import EvidenceDB
from mirage_ot.etgi.evidence.store import get_meta
from mirage_ot.etgi.reconstruction.engine import reconstruct_incident
from mirage_ot.etgi.reconstruction.synthesis import synthesize_incident_scenario


REQUIRED_BITS_BY_TYPE = {
    **{t: ("iv", "nt", "sb", "bl") for t in (1, 2, 3, 4, 30, 31)},
    **{t: ("iv", "nt", "sb", "bl", "ov") for t in (9, 10, 11, 12, 13, 14, 34, 35, 36)},
}
EXPECTED_PCAPS_BY_SCENARIO = {
    "01-Basic": 4,
    "02-Semiurban": 6,
    "03-Rural": 8,
}
EXPECTED_BLOCKED_BY_SCENARIO = {
    "01-Basic": 6,
    "02-Semiurban": 6,
    "03-Rural": 3,
}
CANDIDATE_EXISTING_STAGE2_INDEXES = {
    "ev_0431e34c3ed30056a8f0": [
        Path("runs/etgi/semiurban-ev0431/evidence.sqlite"),
    ],
}


def _peak_rss_mib() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # On macOS (darwin), ru_maxrss is in bytes; on Linux it is in kilobytes.
    if sys.platform == "darwin":
        return round(ru / (1024 ** 2), 2)
    return round(ru / 1024.0, 2)


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


def audit_sqlite_index_strict(
    db_path: Path,
    *,
    scenario: str,
    expected_start: float,
    expected_end: float,
    expected_context_sec: float = 15.0,
) -> dict:
    """Strictly audit every IEC-104 row for exact per-type quality bits (`iv,nt,sb,bl` vs `iv,nt,sb,bl,ov`)."""
    if not db_path.exists():
        return {"path": str(db_path), "exists": False, "compatible": False, "reasons": ["file_not_found"]}
    conn, meta = open_indexed(db_path)
    try:
        reasons = []
        if abs(float(meta["incident_start"]) - expected_start) > 1e-6 or abs(float(meta["incident_end"]) - expected_end) > 1e-6:
            reasons.append("window_bounds_mismatch")
        ctx_sec = meta.get("context_seconds")
        if ctx_sec is None or abs(float(ctx_sec) - expected_context_sec) > 1e-6:
            reasons.append(f"context_seconds_mismatch:{ctx_sec}!={expected_context_sec}")

        members = get_meta(conn, "members") or {}
        pcaps = members.get("pcaps") or []
        not_opened = members.get("not_opened") or []
        exp_pcaps = EXPECTED_PCAPS_BY_SCENARIO[scenario]
        exp_blocked = EXPECTED_BLOCKED_BY_SCENARIO[scenario]
        if len(pcaps) != exp_pcaps:
            reasons.append(f"pcap_count_mismatch:{len(pcaps)}!={exp_pcaps}")
        if len(not_opened) != exp_blocked:
            reasons.append(f"blocked_member_count_mismatch:{len(not_opened)}!={exp_blocked}")

        iec_rows = conn.execute("SELECT payload_json FROM evidence WHERE kind='iec104_asdu'").fetchall()
        if not iec_rows:
            reasons.append("no_iec104_rows")

        typed_total = 0
        exact_keys_ok = 0
        aligned_bool_ok = 0
        unaligned_guard_rows = 0
        qgood_contract_ok = 0
        cot_test_ok = 0
        per_type_counts: dict[str, dict[str, int]] = {}

        for r in iec_rows:
            p = json.loads(r["payload_json"])
            tid = p.get("type_id")
            tkey = str(tid)
            entry = per_type_counts.setdefault(
                tkey,
                {
                    "total": 0,
                    "exact_keyset_ok": 0,
                    "all_bits_bool_ok": 0,
                    "r4_unaligned_null_guarded": 0,
                    "cot_test_ok": 0,
                },
            )
            entry["total"] += 1
            not_aligned = set(p.get("fields_not_aligned") or [])
            if isinstance(p.get("cot_test"), bool):
                cot_test_ok += 1
                entry["cot_test_ok"] += 1
            req_bits = REQUIRED_BITS_BY_TYPE.get(tid)
            if req_bits is not None:
                typed_total += 1
                qf = p.get("quality_flags")
                if isinstance(qf, dict) and set(qf.keys()) == set(req_bits):
                    exact_keys_ok += 1
                    entry["exact_keyset_ok"] += 1
                    if all(isinstance(qf.get(b), bool) for b in req_bits):
                        aligned_bool_ok += 1
                        entry["all_bits_bool_ok"] += 1
                        if isinstance(p.get("quality_good"), bool):
                            qgood_contract_ok += 1
                    elif (
                        all(
                            isinstance(qf.get(b), bool)
                            or (qf.get(b) is None and any(f.endswith(f".{b}") for f in not_aligned))
                            for b in req_bits
                        )
                        and p.get("quality_good") is None
                    ):
                        unaligned_guard_rows += 1
                        entry["r4_unaligned_null_guarded"] += 1
                        qgood_contract_ok += 1

        if exact_keys_ok != typed_total:
            reasons.append(f"per_type_quality_keyset_mismatch:{exact_keys_ok}/{typed_total}")
        if (aligned_bool_ok + unaligned_guard_rows) != typed_total:
            reasons.append(
                f"per_type_quality_bits_invalid:{aligned_bool_ok}+{unaligned_guard_rows}/{typed_total}"
            )
        if qgood_contract_ok != typed_total:
            reasons.append(f"quality_good_contract_violation:{qgood_contract_ok}/{typed_total}")
        if cot_test_ok != len(iec_rows):
            reasons.append(f"cot_test_not_bool:{cot_test_ok}/{len(iec_rows)}")

        total_rows = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        return {
            "path": str(db_path),
            "exists": True,
            "compatible": not reasons,
            "reasons": reasons,
            "total_evidence_rows": total_rows,
            "iec104_rows": len(iec_rows),
            "typed_quality_rows": typed_total,
            "exact_per_type_quality_keyset_rows": exact_keys_ok,
            "aligned_all_bits_bool_rows": aligned_bool_ok,
            "r4_unaligned_null_guarded_rows": unaligned_guard_rows,
            "quality_good_contract_ok_rows": qgood_contract_ok,
            "cot_test_bool_ok_rows": cot_test_ok,
            "per_type_audit": per_type_counts,
            "sqlite_bytes": db_path.stat().st_size,
        }
    finally:
        conn.close()


def _dir_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _classify_window_profile_and_abstention(res: dict) -> tuple[str, str, list[str], str]:
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

    verified_tx = sum(
        1 for t in txs if t["device_state_change_status"] in ("verified_state_transition", "verified_measurement_transition")
    )
    bridges = len(syn["verified_element_bridges"])
    ver_single = part["counts"]["verified_single_anchor_storyline_count"]

    if bridges > 0 or verified_tx > 0:
        abstention_status = "NOT_ABSTAINED_MULTI_SOURCE_CORROBORATED"
    elif ver_single > 0:
        abstention_status = "PARTIAL_ABSTENTION_SINGLE_SOURCE_VERIFIED_NO_BRIDGE"
    elif txs:
        abstention_status = "PARTIAL_ABSTENTION_COMMANDS_OBSERVED_NO_VERIFIED_TRANSITION"
    else:
        abstention_status = "HONEST_ABSTENTION_NO_VERIFIED_ANCHOR_OR_COMMAND"

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
    elif ver_single > 0:
        why_note = (
            f"Preserved {ver_single} verified single-anchor storyline(s) and {len(syn['rtu_asdu_bundles'])} "
            "source bundle(s), but 0 cross-RTU bridges because no single grid element exhibited corroborated "
            "two-end transitions across distinct RTUs."
        )
    else:
        why_note = (
            f"Honest abstention from supported storylines/bridges: window contains 0 control commands, 0 verified "
            f"anchors, and {part['counts']['quarantined_unverified_observation_count']} quarantined unverified "
            "observation(s) on periodic M_ME_NC_1 (COT=1) telemetry."
        )

    return profile, abstention_status, reasons, why_note


def process_single_window(task: dict) -> dict:
    """Worker entrypoint executed in a separate process for isolated timing and peak RSS measurement."""
    w_t0 = time.perf_counter()
    ep_id = task["episode_id"]
    scenario = task["scenario"]
    recording = task["recording"]
    start = float(task["start"])
    end = float(task["end"])
    archive_path = Path(task["archive_path"])
    ep_index_dir = Path(task["ep_index_dir"])
    ep_recon_dir = Path(task["ep_recon_dir"])
    freeze_commit = task["freeze_commit"]
    freeze_code_sha = task["freeze_code_sha"]
    freeze_ev_sha = task["freeze_ev_sha"]

    db_path = ep_index_dir / "evidence.sqlite"
    failed_stage = "initialization"
    try:
        ep_index_dir.mkdir(parents=True, exist_ok=True)
        timing_file = ep_index_dir / "indexing_timing.json"
        saved_timing = json.loads(timing_file.read_text(encoding="utf-8")) if timing_file.exists() else {}
        t0_idx = time.perf_counter()
        reused_complete = False
        if db_path.exists():
            post_audit = audit_sqlite_index_strict(
                db_path, scenario=scenario, expected_start=start, expected_end=end,
            )
            if post_audit["compatible"] and (ep_recon_dir / "run_manifest.json").exists():
                wm = json.loads((ep_recon_dir / "run_manifest.json").read_text(encoding="utf-8"))
                if (
                    wm.get("git_commit") in task["allowed_git_commits"]
                    and wm.get("code_sha256") == freeze_code_sha
                    and wm.get("evidence_code_sha256") == freeze_ev_sha
                    and wm.get("module_hashes") == task["freeze_module_hashes"]
                    and wm.get("evidence_module_hashes") == task["freeze_ev_module_hashes"]
                ):
                    reused_complete = True
                    index_mode = "reused_verified_stage2a_window"
                    index_sec = float(saved_timing.get("indexing_s", 0.0))
            if not reused_complete:
                if post_audit["compatible"]:
                    if ep_recon_dir.exists():
                        shutil.rmtree(ep_recon_dir)
                    index_mode = "reused_verified_stage2_index"
                    index_sec = float(saved_timing.get("indexing_s", 0.0))
                else:
                    shutil.rmtree(ep_recon_dir, ignore_errors=True)
                    db_path.unlink(missing_ok=True)
                    failed_stage = "indexing"
                    index_window(
                        archive_path, scenario=scenario, recording=recording,
                        start=start, end=end, out=db_path, context_seconds=15.0,
                        work=ep_index_dir / "slices", modalities="both",
                    )
                    shutil.rmtree(ep_index_dir / "slices", ignore_errors=True)
                    index_mode = "indexed_fresh_by_frozen_indexer"
                    index_sec = round(time.perf_counter() - t0_idx, 3)
        else:
            failed_stage = "indexing"
            index_window(
                archive_path, scenario=scenario, recording=recording,
                start=start, end=end, out=db_path, context_seconds=15.0,
                work=ep_index_dir / "slices", modalities="both",
            )
            shutil.rmtree(ep_index_dir / "slices", ignore_errors=True)
            index_mode = "indexed_fresh_by_frozen_indexer"
            index_sec = round(time.perf_counter() - t0_idx, 3)

        failed_stage = "sqlite_index_audit"
        post_audit = audit_sqlite_index_strict(
            db_path, scenario=scenario, expected_start=start, expected_end=end,
        )
        if not post_audit["compatible"]:
            raise RuntimeError(f"Strict SQLite index audit failed for {ep_id}: {post_audit['reasons']}")

        failed_stage = "reconstruction_and_synthesis"
        if reused_complete:
            res = {
                "transactions": json.loads((ep_recon_dir / "transactions.json").read_text(encoding="utf-8")),
                "event_anchors": json.loads((ep_recon_dir / "event_anchors.json").read_text(encoding="utf-8")),
                "event_graph": json.loads((ep_recon_dir / "event_graph.json").read_text(encoding="utf-8")),
                "storylines": json.loads((ep_recon_dir / "storylines.json").read_text(encoding="utf-8")),
                "incident_synthesis": json.loads((ep_recon_dir / "incident_synthesis.json").read_text(encoding="utf-8")),
                "quality_consistency": json.loads((ep_recon_dir / "quality_consistency.json").read_text(encoding="utf-8")),
                "lineage_consistency": json.loads((ep_recon_dir / "lineage_consistency.json").read_text(encoding="utf-8")),
                "report": json.loads((ep_recon_dir / "investigation_report.json").read_text(encoding="utf-8")),
            }
            recon_total_sec = float(saved_timing.get("reconstruction_and_synthesis_total_s", 0.0))
            syn_sec = float(saved_timing.get("synthesis_step_s", 0.0))
            win_total_sec = round(index_sec + recon_total_sec, 3)
            rss_mib = float(saved_timing.get("peak_rss_mib", _peak_rss_mib()))
        else:
            conn, meta = open_indexed(db_path)
            db = EvidenceDB(conn, incident_start=start, incident_end=end)
            t0_rec = time.perf_counter()
            res = reconstruct_incident(
                db, start, end,
                background_start=start - 15.0, background_end=start,
                llm=None, selection_limit=24, seed=1, out_dir=ep_recon_dir,
            )
            recon_total_sec = round(time.perf_counter() - t0_rec, 3)

            t0_syn = time.perf_counter()
            _ = synthesize_incident_scenario(
                incident_start=start, incident_end=end,
                tx_result=res["transactions"], anchor_result=res["event_anchors"],
                event_graph=res["event_graph"], storyline_result=res["storylines"],
            )
            syn_sec = round(time.perf_counter() - t0_syn, 4)
            conn.close()
            win_total_sec = round(index_sec + recon_total_sec, 3)
            rss_mib = _peak_rss_mib()
            timing_file.write_text(
                json.dumps({
                    "indexing_s": index_sec,
                    "reconstruction_and_synthesis_total_s": recon_total_sec,
                    "synthesis_step_s": syn_sec,
                    "window_total_s": win_total_sec,
                    "peak_rss_mib": rss_mib,
                }),
                encoding="utf-8",
            )

        failed_stage = "output_manifest_verification"
        written_manifest = json.loads((ep_recon_dir / "run_manifest.json").read_text(encoding="utf-8"))
        manifest_matches_freeze = (
            written_manifest.get("git_commit") in task["allowed_git_commits"]
            and written_manifest.get("code_sha256") == freeze_code_sha
            and written_manifest.get("evidence_code_sha256") == freeze_ev_sha
            and written_manifest.get("module_hashes") == task["freeze_module_hashes"]
            and written_manifest.get("evidence_module_hashes") == task["freeze_ev_module_hashes"]
        )
        if not manifest_matches_freeze:
            raise RuntimeError(
                f"Output run_manifest.json mismatch for {ep_id}: "
                f"git_commit={written_manifest.get('git_commit')}, "
                f"code_sha256={written_manifest.get('code_sha256')}, "
                f"evidence_code_sha256={written_manifest.get('evidence_code_sha256')}"
            )

        tx_res = res["transactions"]
        anc_res = res["event_anchors"]
        eg_res = res["event_graph"]
        sl_res = res["storylines"]
        syn_res = res["incident_synthesis"]
        qc_res = res["quality_consistency"]
        lc_res = res["lineage_consistency"]
        rep_res = res["report"]

        profile, abstention_status, reasons, why_note = _classify_window_profile_and_abstention(res)
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

        return {
            "window_index": task["window_index"],
            "episode_id": ep_id,
            "scenario": scenario,
            "recording": recording,
            "window_start": start,
            "window_end": end,
            "window_duration_s": round(end - start, 3),
            "execution_status": "COMPLETED_OK",
            "execution_error": None,
            "manifest_matches_freeze": True,
            "observation_profile": profile,
            "abstention_status": abstention_status,
            "index_mode": index_mode,
            "sqlite_evidence_rows": post_audit["total_evidence_rows"],
            "iec104_rows_in_db": post_audit["iec104_rows"],
            "per_type_quality_audit": post_audit["per_type_audit"],
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
                "window_total_s": win_total_sec,
            },
            "storage_bytes": {
                "sqlite_bytes": post_audit["sqlite_bytes"],
                "reconstruction_artifacts_bytes": _dir_bytes(ep_recon_dir),
            },
            "peak_rss_mib": rss_mib,
        }
    except Exception as exc:
        win_total_sec = round(time.perf_counter() - w_t0, 3)
        return {
            "window_index": task["window_index"],
            "episode_id": ep_id,
            "scenario": scenario,
            "recording": recording,
            "window_start": start,
            "window_end": end,
            "window_duration_s": round(end - start, 3),
            "execution_status": "EXECUTION_FAILURE",
            "execution_error": {
                "failed_stage": failed_stage,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            },
            "manifest_matches_freeze": False,
            "timing_seconds": {"window_total_s": win_total_sec},
            "peak_rss_mib": _peak_rss_mib(),
        }


def _select_stage2a_windows(windows: list[dict]) -> list[dict]:
    """Deterministic time-and-duration selection: earliest, mid-recording, and max-duration."""
    first_w = windows[0]
    mid_w = windows[len(windows) // 2]
    max_w = max(windows, key=lambda w: (round(w["end"] - w["start"], 6), -w["start"]))
    seen = set()
    out = []
    for w in (first_w, mid_w, max_w):
        if w["episode_id"] not in seen:
            seen.add(w["episode_id"])
            out.append(w)
    return out


def _distribution_stats(values: list[float | int]) -> dict:
    if not values:
        return {"sum": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0}
    s = sorted(float(v) for v in values)
    n = len(s)
    p95_idx = min(n - 1, max(0, math.ceil(0.95 * n) - 1))
    return {
        "sum": round(sum(values), 4) if isinstance(values[0], float) else int(sum(values)),
        "mean": round(sum(s) / n, 3),
        "median": round(statistics.median(s), 3),
        "p95": round(s[p95_idx], 3),
        "max": round(s[-1], 3) if isinstance(values[0], float) else int(s[-1]),
    }


def summarize_scenario_rows(rows: list[dict]) -> dict:
    ok_rows = [r for r in rows if r["execution_status"] == "COMPLETED_OK"]
    fail_rows = [r for r in rows if r["execution_status"] != "COMPLETED_OK"]
    return {
        "total_windows": len(rows),
        "completed_ok_count": len(ok_rows),
        "execution_failure_count": len(fail_rows),
        "all_manifests_matched_freeze": all(r.get("manifest_matches_freeze") for r in ok_rows) and not fail_rows,
        "windows_by_profile": {
            p: sum(1 for r in ok_rows if r["observation_profile"] == p)
            for p in sorted({r["observation_profile"] for r in ok_rows})
        },
        "windows_by_abstention_status": {
            st: sum(1 for r in ok_rows if r["abstention_status"] == st)
            for st in sorted({r["abstention_status"] for r in ok_rows})
        },
        "totals": {
            "transactions_total": sum(r["transaction_count_total"] for r in ok_rows),
            "transactions_accepted": sum(r["transaction_count_accepted"] for r in ok_rows),
            "transactions_verified_transition": sum(r["transaction_count_verified_transition"] for r in ok_rows),
            "transactions_unverified_state_report": sum(r["transaction_count_unverified_state_report"] for r in ok_rows),
            "transactions_no_state_change": sum(r["transaction_count_no_state_change"] for r in ok_rows),
            "anchors_total": sum(r["anchor_count_total"] for r in ok_rows),
            "anchors_verified": sum(r["anchor_count_verified"] for r in ok_rows),
            "anchors_unverified": sum(r["anchor_count_unverified"] for r in ok_rows),
            "storylines_total": sum(r["storyline_count_total"] for r in ok_rows),
            "storylines_supported_multi_node": sum(r["storyline_count_supported_multi_node"] for r in ok_rows),
            "storylines_verified_single_anchor": sum(r["storyline_count_verified_single_anchor"] for r in ok_rows),
            "storylines_protocol_partial_or_unverified": sum(r["storyline_count_protocol_partial_or_unverified"] for r in ok_rows),
            "storylines_unverified_observation": sum(r["storyline_count_unverified_observation"] for r in ok_rows),
            "sequential_same_device_observations": sum(r["sequential_same_device_observation_count"] for r in ok_rows),
            "rtu_asdu_bundles": sum(r["rtu_asdu_bundle_count"] for r in ok_rows),
            "cross_rtu_verified_element_bridges": sum(r["cross_rtu_verified_element_bridge_count"] for r in ok_rows),
            "same_rtu_supported_relations": sum(r["same_rtu_supported_relation_count"] for r in ok_rows),
            "bridged_bundle_components": sum(r["bridged_bundle_component_count"] for r in ok_rows),
            "unresolved_cross_device_branches": sum(r["unresolved_cross_device_branch_count"] for r in ok_rows),
            "windows_with_supported_local_component": sum(1 for r in ok_rows if r["has_supported_local_component"]),
            "windows_with_multi_source_corroborated_component": sum(1 for r in ok_rows if r["has_multi_source_corroborated_component"]),
            "honest_abstention_window_count": sum(
                1 for r in ok_rows if r["abstention_status"] == "HONEST_ABSTENTION_NO_VERIFIED_ANCHOR_OR_COMMAND"
            ),
            "quality_consistency_pass_count": sum(1 for r in ok_rows if r["quality_consistency_passed"]),
            "lineage_consistency_pass_count": sum(1 for r in ok_rows if r["lineage_consistency_passed"]),
            "quality_consistency_pass_rate": round(sum(1 for r in ok_rows if r["quality_consistency_passed"]) / len(rows), 4) if rows else 0.0,
            "lineage_consistency_pass_rate": round(sum(1 for r in ok_rows if r["lineage_consistency_passed"]) / len(rows), 4) if rows else 0.0,
        },
        "per_window_distributions": {
            "transactions_total": _distribution_stats([r["transaction_count_total"] for r in ok_rows]),
            "transactions_verified_transition": _distribution_stats([r["transaction_count_verified_transition"] for r in ok_rows]),
            "anchors_total": _distribution_stats([r["anchor_count_total"] for r in ok_rows]),
            "anchors_verified": _distribution_stats([r["anchor_count_verified"] for r in ok_rows]),
            "anchors_unverified": _distribution_stats([r["anchor_count_unverified"] for r in ok_rows]),
            "storylines_total": _distribution_stats([r["storyline_count_total"] for r in ok_rows]),
            "storylines_supported_multi_node": _distribution_stats([r["storyline_count_supported_multi_node"] for r in ok_rows]),
            "rtu_asdu_bundles": _distribution_stats([r["rtu_asdu_bundle_count"] for r in ok_rows]),
            "cross_rtu_verified_element_bridges": _distribution_stats([r["cross_rtu_verified_element_bridge_count"] for r in ok_rows]),
            "unresolved_cross_device_branches": _distribution_stats([r["unresolved_cross_device_branch_count"] for r in ok_rows]),
            "indexing_s": _distribution_stats([r["timing_seconds"]["indexing_s"] for r in ok_rows]),
            "reconstruction_and_synthesis_s": _distribution_stats([r["timing_seconds"]["reconstruction_and_synthesis_total_s"] for r in ok_rows]),
            "window_total_s": _distribution_stats([r["timing_seconds"]["window_total_s"] for r in ok_rows]),
            "sqlite_mib": _distribution_stats([round(r["storage_bytes"]["sqlite_bytes"] / (1024 ** 2), 3) for r in ok_rows]),
            "artifacts_mib": _distribution_stats([round(r["storage_bytes"]["reconstruction_artifacts_bytes"] / (1024 ** 2), 3) for r in ok_rows]),
            "peak_rss_mib": _distribution_stats([r["peak_rss_mib"] for r in ok_rows]),
        },
        "storage_bytes": {
            "sqlite_index_total_bytes": sum(r["storage_bytes"]["sqlite_bytes"] for r in ok_rows),
            "sqlite_index_total_mib": round(sum(r["storage_bytes"]["sqlite_bytes"] for r in ok_rows) / (1024 ** 2), 2),
            "reconstruction_artifacts_total_bytes": sum(r["storage_bytes"]["reconstruction_artifacts_bytes"] for r in ok_rows),
            "reconstruction_artifacts_total_mib": round(sum(r["storage_bytes"]["reconstruction_artifacts_bytes"] for r in ok_rows) / (1024 ** 2), 2),
            "combined_total_mib": round(
                sum(r["storage_bytes"]["sqlite_bytes"] + r["storage_bytes"]["reconstruction_artifacts_bytes"] for r in ok_rows)
                / (1024 ** 2),
                2,
            ),
        },
    }


def main() -> None:
    process_t0 = time.perf_counter()
    parser = argparse.ArgumentParser(description="Run Stage 2 Frozen Cross-Scenario Experiment (Semiurban & Rural)")
    parser.add_argument("--mode", choices=("stage2a", "full"), required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--freeze-manifest", type=Path, default=Path("configs/etgi/method_freeze.v1.json"))
    parser.add_argument("--semiurban-windows", type=Path, default=Path("configs/etgi/semiurban_test_windows.v1.json"))
    parser.add_argument("--rural-windows", type=Path, default=Path("configs/etgi/rural_test_windows.v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/sherlock/v3"))
    parser.add_argument("--out-root", type=Path, default=Path("runs/etgi/stage2-cross-scenario-frozen-20261015"))
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    freeze = json.loads(args.freeze_manifest.read_text(encoding="utf-8"))
    semi_all = json.loads(args.semiurban_windows.read_text(encoding="utf-8"))
    rural_all = json.loads(args.rural_windows.read_text(encoding="utf-8"))

    # 1. Verify frozen module hashes (timed separately)
    t0_code = time.perf_counter()
    code_check = verify_frozen_code_hashes(freeze, repo_root)
    code_check_sec = round(time.perf_counter() - t0_code, 4)

    # 2. Verify Sherlock v3 ZIP sizes & MD5s (timed separately)
    t0_arch = time.perf_counter()
    archive_check = verify_upstream_archives(freeze, args.raw_dir)
    archive_check_sec = round(time.perf_counter() - t0_arch, 4)

    # 3. Verify strict input isolation
    allowed_keys = set(freeze["strict_input_isolation"]["allowed_window_specification_fields"])
    for w in (*semi_all, *rural_all):
        if set(w.keys()) != allowed_keys:
            raise RuntimeError(f"Window spec contains non-isolated keys: {set(w.keys())} != {allowed_keys}")

    # 4. Audit any existing Semiurban/Rural SQLite indexes (timed separately)
    t0_idx_aud = time.perf_counter()
    existing_index_audit = {}
    all_by_ep = {w["episode_id"]: w for w in (*semi_all, *rural_all)}
    for ep_id, cand_paths in sorted(CANDIDATE_EXISTING_STAGE2_INDEXES.items()):
        w = all_by_ep[ep_id]
        auds = [
            audit_sqlite_index_strict(
                cp, scenario=w["scenario"], expected_start=float(w["start"]), expected_end=float(w["end"]),
            )
            for cp in cand_paths
        ]
        existing_index_audit[ep_id] = {
            "candidates": auds,
            "action": "reindex_with_frozen_indexer" if not any(a["compatible"] for a in auds) else "reuse_compatible",
        }
    idx_audit_sec = round(time.perf_counter() - t0_idx_aud, 4)

    for sub in ("semiurban/index", "semiurban/reconstruction", "rural/index", "rural/reconstruction"):
        (args.out_root / sub).mkdir(parents=True, exist_ok=True)

    if args.mode == "stage2a":
        semi_wins = _select_stage2a_windows(semi_all)
        rural_wins = _select_stage2a_windows(rural_all)
    else:
        semi_wins = semi_all
        rural_wins = rural_all

    import subprocess
    head_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    engine_last_commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", "src/mirage_ot/etgi/postalert", "src/mirage_ot/etgi/reconstruction", "src/mirage_ot/etgi/evidence"],
        cwd=repo_root, text=True,
    ).strip()
    if engine_last_commit != freeze["frozen_engine_git_commit"]:
        raise RuntimeError(
            f"Engine last commit {engine_last_commit} != frozen_engine_git_commit {freeze['frozen_engine_git_commit']}"
        )
    allowed_git_commits = sorted({freeze["frozen_engine_git_commit"], head_commit})

    tasks = []
    for i, w in enumerate(semi_wins, start=1):
        ep = w["episode_id"]
        tasks.append({
            "window_index": i,
            "episode_id": ep,
            "scenario": "02-Semiurban",
            "recording": "test",
            "start": float(w["start"]),
            "end": float(w["end"]),
            "archive_path": str(args.raw_dir / "02-Semiurban.zip"),
            "ep_index_dir": str(args.out_root / "semiurban" / "index" / ep),
            "ep_recon_dir": str(args.out_root / "semiurban" / "reconstruction" / ep),
            "freeze_commit": freeze["frozen_engine_git_commit"],
            "allowed_git_commits": allowed_git_commits,
            "freeze_code_sha": freeze["code_sha256"],
            "freeze_ev_sha": freeze["evidence_code_sha256"],
            "freeze_module_hashes": freeze["module_hashes"],
            "freeze_ev_module_hashes": freeze["evidence_module_hashes"],
        })
    for i, w in enumerate(rural_wins, start=1):
        ep = w["episode_id"]
        tasks.append({
            "window_index": i,
            "episode_id": ep,
            "scenario": "03-Rural",
            "recording": "test",
            "start": float(w["start"]),
            "end": float(w["end"]),
            "archive_path": str(args.raw_dir / "03-Rural.zip"),
            "ep_index_dir": str(args.out_root / "rural" / "index" / ep),
            "ep_recon_dir": str(args.out_root / "rural" / "reconstruction" / ep),
            "freeze_commit": freeze["frozen_engine_git_commit"],
            "allowed_git_commits": allowed_git_commits,
            "freeze_code_sha": freeze["code_sha256"],
            "freeze_ev_sha": freeze["evidence_code_sha256"],
            "freeze_module_hashes": freeze["module_hashes"],
            "freeze_ev_module_hashes": freeze["evidence_module_hashes"],
        })

    t0_win_wall = time.perf_counter()
    results_by_key: dict[tuple[str, int], dict] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(process_single_window, t): t for t in tasks}
        done_cnt = 0
        for fut in as_completed(future_map):
            done_cnt += 1
            res = fut.result()
            results_by_key[(res["scenario"], res["window_index"])] = res
            if res["execution_status"] == "COMPLETED_OK":
                print(
                    f"[{done_cnt:02d}/{len(tasks):02d}] {res['scenario']} #{res['window_index']:02d} {res['episode_id']} "
                    f"({res['observation_profile'][:2]}): tx={res['transaction_count_total']}(ver={res['transaction_count_verified_transition']}), "
                    f"anc={res['anchor_count_total']}(ver={res['anchor_count_verified']},unv={res['anchor_count_unverified']}), "
                    f"bnd={res['rtu_asdu_bundle_count']}, brg={res['cross_rtu_verified_element_bridge_count']}, "
                    f"qc={res['quality_consistency_passed']}, lc={res['lineage_consistency_passed']}, "
                    f"idx={res['timing_seconds']['indexing_s']:.1f}s, rec={res['timing_seconds']['reconstruction_and_synthesis_total_s']:.2f}s, "
                    f"rss={res['peak_rss_mib']:.1f}MiB",
                    flush=True,
                )
            else:
                print(
                    f"[{done_cnt:02d}/{len(tasks):02d}] FAILURE {res['scenario']} {res['episode_id']}: {res['execution_error']}",
                    flush=True,
                )

    windows_wall_sec = round(time.perf_counter() - t0_win_wall, 3)
    semi_results = [results_by_key[("02-Semiurban", i)] for i in range(1, len(semi_wins) + 1)]
    rural_results = [results_by_key[("03-Rural", i)] for i in range(1, len(rural_wins) + 1)]

    semi_summary = summarize_scenario_rows(semi_results)
    rural_summary = summarize_scenario_rows(rural_results)
    process_end_to_end_sec = round(time.perf_counter() - process_t0, 3)

    execution_audit = {
        "mode": args.mode,
        "workers": args.workers,
        "freeze_verification": code_check,
        "upstream_archive_verification": archive_check,
        "strict_input_isolation_verified": True,
        "existing_index_audit": existing_index_audit,
        "timing_breakdown_seconds": {
            "code_freeze_verification_s": code_check_sec,
            "archive_integrity_audit_s": archive_check_sec,
            "existing_index_audit_s": idx_audit_sec,
            "windows_processing_wall_clock_s": windows_wall_sec,
            "sum_of_worker_indexing_cpu_wall_s": round(
                sum(r["timing_seconds"].get("indexing_s", 0.0) for r in (*semi_results, *rural_results)), 3
            ),
            "sum_of_worker_reconstruction_s": round(
                sum(r["timing_seconds"].get("reconstruction_and_synthesis_total_s", 0.0) for r in (*semi_results, *rural_results)), 3
            ),
            "process_end_to_end_wall_clock_s": process_end_to_end_sec,
        },
        "execution_failures": [
            r for r in (*semi_results, *rural_results) if r["execution_status"] != "COMPLETED_OK"
        ],
    }

    summary_payload = {
        "stage": f"Stage 2 Frozen Cross-Scenario Experiment ({args.mode})",
        "execution_audit": execution_audit,
        "semiurban_summary": semi_summary,
        "rural_summary": rural_summary,
        "semiurban_windows": semi_results,
        "rural_windows": rural_results,
    }

    if args.mode == "stage2a":
        (args.out_root / "stage2a_pilot_summary.json").write_text(
            json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8",
        )
        print("Stage 2A pilot complete. Written to", args.out_root / "stage2a_pilot_summary.json")
    else:
        (args.out_root / "stage2_summary.json").write_text(
            json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8",
        )
        (args.out_root / "execution_audit.json").write_text(
            json.dumps(execution_audit, indent=2) + "\n", encoding="utf-8",
        )
        print("Stage 2 full experiment complete. Written to", args.out_root / "stage2_summary.json")


if __name__ == "__main__":
    main()
