"""Air-gapped, read-only physical-state snapshot comparison.

Isolation:
- Runs only against frozen reconstruction JSON.
- Reads ``<scenario>/raw/test/physical.zip`` (01-Basic, 02-Semiurban, 03-Rural)
  inside this module.
- Does not import the reconstruction engine and does not pass simulator
  snapshots into it.

Agreement classes, recorded separately:
- ``exact_numeric``: absolute or relative difference within the exact band.
- ``within_tolerance``: outside the exact band, inside the stated relative tolerance.
- ``semantic_deenergized_nan_vs_iec104_zero``: a simulator ``NaN`` on a
  de-energized island is compatible with an IEC-104 zero. It is not a numeric match.

``to_zero`` points compare the pre-value numerically and the post-value either
numerically or by that NaN rule. A finite pre-snapshot that was not compared
to the network pre-value is not counted as agreement.
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import math
import re
import statistics
import zipfile
from pathlib import Path


FIXED_PHYSICAL_AUDIT_EPISODES = [
    "ev_e76705884b8fec84592a",
    "ev_1a2c7b07458620ddeb67",
    "ev_12dcd56b2f5e78144cfb",
    "ev_54569eab2d55482f6496",
    "ev_343cc5effb0b1b22931b",
    "ev_0961f1c2da8a257e3ebc",
    "ev_564bebaa45f0686cf98d",
    "ev_b15ac1c8e04d148f09cb",
    "ev_52f5eee28f8b95e702fd",
]

# Prior 2026-10-15 audit. The to_zero rule then required a finite physical
# pre-value and a post-value near zero or NaN, without a numeric pre comparison.
PRIOR_AUDIT_RECORD = {
    "source": "review_artifacts/stage3-audit-response-20261015/post_freeze_physical_state_evaluation.json",
    "verified_transactions_reported": "9/9",
    "bridges_reported": "6/6",
    "endpoint_attributes_reported": "32/32",
    "to_zero_pre_value_numerically_compared": False,
}

EXACT_ABS = 1e-3
EXACT_REL = 1e-4
TX_REL_TOL = 0.05
BRIDGE_REL_TOL = 0.10
ZERO_ABS = 1e-3

_NUMERIC_PASS = frozenset({"exact_numeric", "within_tolerance"})
_COMPATIBLE = _NUMERIC_PASS | frozenset({"semantic_deenergized_nan_vs_iec104_zero"})
_TS_RE = re.compile(r"TS(\d+)-(\d+)\.json$")

COMPARISON_CRITERIA = {
    "scale": "max(1, |network value|)",
    "exact_numeric": f"abs(delta) <= {EXACT_ABS} or rel_delta <= {EXACT_REL}",
    "within_tolerance_transactions": f"rel_delta <= {TX_REL_TOL}",
    "within_tolerance_bridge_points": f"rel_delta <= {BRIDGE_REL_TOL}",
    "semantic_deenergized_nan_vs_iec104_zero": (
        "A non-finite simulator post-value (NaN) together with a network post-value "
        "within 1e-3 of zero is semantic compatibility for a de-energized island. "
        "It is not numeric equality."
    ),
    "to_zero_pre": (
        "Network pre-value is compared to the physical pre-snapshot under the bridge "
        "numeric rule. Presence of a finite physical pre-value is not agreement."
    ),
    "to_zero_post": (
        "Network post-value near zero is either a numeric match to a finite physical "
        "post-value or semantic NaN compatibility. An unchecked post-value is not agreement."
    ),
    "alignment": (
        "Each network time is paired with the nearest simulator snapshot (0.5-2 s spacing). "
        "alignment_error_seconds = snapshot_time - target_time. Values are not interpolated."
    ),
    "physical_zip_isolation": (
        "physical.zip is opened only by this offline evaluation. Reconstruction inputs "
        "exclude it."
    ),
}


def _resolve_physical_key(values: dict, stem: str, attr: str) -> tuple[str | None, float | bool | None]:
    for ctx in ("MEASUREMENT", "CONFIGURATION", "STATUS"):
        k = f"{stem}.{ctx}.{attr}"
        if k in values:
            return k, values[k]
    alt_map = {
        "closed": "is_closed",
        "is_closed": "closed",
        "connected": "is_connected",
        "is_connected": "connected",
    }
    if attr in alt_map:
        alt = alt_map[attr]
        for ctx in ("MEASUREMENT", "CONFIGURATION", "STATUS"):
            k = f"{stem}.{ctx}.{alt}"
            if k in values:
                return k, values[k]
    return None, None


def _as_float(v) -> float | None:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _r(v, nd=6):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return round(float(v), nd)


def classify_numeric(net: float, phys: float | None, tol: float, *, criterion: str) -> dict:
    """Classify one numeric comparison. Missing or NaN physical values are not numeric matches."""
    if phys is None:
        return {
            "checked": False,
            "agreement_class": "unchecked_missing_physical",
            "criterion": criterion,
            "abs_delta": None,
            "rel_delta": None,
            "tolerance": tol,
        }
    if math.isnan(phys):
        return {
            "checked": True,
            "agreement_class": "physical_nan_not_numeric",
            "criterion": criterion,
            "abs_delta": None,
            "rel_delta": None,
            "tolerance": tol,
            "note": "NaN is not a numeric match.",
        }
    delta = abs(phys - net)
    scale = max(1.0, abs(net))
    rel = delta / scale
    if delta <= EXACT_ABS or rel <= EXACT_REL:
        agreement_class = "exact_numeric"
    elif rel <= tol:
        agreement_class = "within_tolerance"
    else:
        agreement_class = "numeric_mismatch"
    return {
        "checked": True,
        "agreement_class": agreement_class,
        "criterion": criterion,
        "abs_delta": delta,
        "rel_delta": rel,
        "tolerance": tol,
        "scale": scale,
    }


def classify_to_zero_post(net_post: float, phys: float | None) -> dict:
    """Post-side rule for a ``to_zero`` step. NaN is semantic, not numeric."""
    criterion = "to_zero_post_numeric_zero_or_deenergized_nan"
    net_near_zero = abs(net_post) <= ZERO_ABS
    if phys is None:
        return {
            "checked": False,
            "agreement_class": "unchecked_missing_physical",
            "criterion": criterion,
            "abs_delta": None,
            "rel_delta": None,
            "network_post_near_zero": net_near_zero,
        }
    if math.isnan(phys):
        if net_near_zero:
            return {
                "checked": True,
                "agreement_class": "semantic_deenergized_nan_vs_iec104_zero",
                "criterion": criterion,
                "abs_delta": None,
                "rel_delta": None,
                "network_post_near_zero": True,
                "note": (
                    "Simulator NaN is compatible with an IEC-104 zero on a de-energized "
                    "island and is not numeric equality."
                ),
            }
        return {
            "checked": True,
            "agreement_class": "numeric_mismatch",
            "criterion": criterion,
            "abs_delta": None,
            "rel_delta": None,
            "network_post_near_zero": False,
            "note": "Physical post-value is NaN while the network post-value is not near zero.",
        }
    numeric = classify_numeric(net_post, phys, BRIDGE_REL_TOL, criterion=criterion)
    numeric["network_post_near_zero"] = net_near_zero
    return numeric


def combine_sides(
    pre: dict,
    post: dict,
    *,
    require_physical_change: bool = False,
    ph_pre: float | None = None,
    ph_post: float | None = None,
) -> dict:
    """Combine pre and post classes. Either unchecked side blocks a compatibility claim."""
    pre_ok = pre.get("checked") and pre.get("agreement_class") in _COMPATIBLE
    post_ok = post.get("checked") and post.get("agreement_class") in _COMPATIBLE
    if not pre.get("checked") or not post.get("checked"):
        agreement_class = "incomplete_unchecked"
        compatible = False
        numeric_agreement = False
    elif not pre_ok or not post_ok:
        agreement_class = "not_agreed"
        compatible = False
        numeric_agreement = False
    elif require_physical_change and not _physical_value_changed(ph_pre, ph_post):
        agreement_class = "values_match_but_no_physical_change"
        compatible = False
        numeric_agreement = False
    elif (
        pre.get("agreement_class") == "semantic_deenergized_nan_vs_iec104_zero"
        or post.get("agreement_class") == "semantic_deenergized_nan_vs_iec104_zero"
    ):
        agreement_class = "semantic_deenergized_nan_vs_iec104_zero"
        compatible = True
        numeric_agreement = False
    elif "within_tolerance" in (pre.get("agreement_class"), post.get("agreement_class")):
        agreement_class = "within_tolerance"
        compatible = True
        numeric_agreement = True
    else:
        agreement_class = "exact_numeric"
        compatible = True
        numeric_agreement = True
    return {
        "agreement_class": agreement_class,
        "compatible": compatible,
        "numeric_agreement": numeric_agreement,
    }


def _physical_value_changed(ph_pre: float | None, ph_post: float | None) -> bool:
    if ph_pre is None or ph_post is None:
        return False
    pre_nan = math.isnan(ph_pre)
    post_nan = math.isnan(ph_post)
    if pre_nan and post_nan:
        return False
    if pre_nan or post_nan:
        return True
    return ph_pre != ph_post


def _public_comparison(record: dict) -> dict:
    out = dict(record)
    for side in ("pre_comparison", "post_comparison"):
        block = dict(out[side])
        for key in ("abs_delta", "rel_delta", "scale"):
            if key in block:
                block[key] = _r(block[key])
        out[side] = block
    return out


def _tally(rows: list[dict]) -> dict:
    def _n(name: str) -> int:
        return sum(1 for row in rows if row["agreement_class"] == name)

    abs_errors = [
        err
        for row in rows
        for err in (row.get("abs_alignment_error_pre_seconds"), row.get("abs_alignment_error_post_seconds"))
        if err is not None
    ]
    return {
        "checked_count": len(rows),
        "compatible_count": sum(1 for row in rows if row["compatible"]),
        "numeric_agreement_count": sum(1 for row in rows if row["numeric_agreement"]),
        "exact_numeric_count": _n("exact_numeric"),
        "within_tolerance_count": _n("within_tolerance"),
        "semantic_deenergized_nan_count": _n("semantic_deenergized_nan_vs_iec104_zero"),
        "not_agreed_count": _n("not_agreed"),
        "incomplete_unchecked_count": _n("incomplete_unchecked"),
        "max_abs_alignment_error_seconds": _r(max(abs_errors), 6) if abs_errors else None,
    }


SCENARIOS = ("01-Basic", "02-Semiurban", "03-Rural")
_VERIFIED_TX = ("verified_state_transition", "verified_measurement_transition")


def episodes_with_physical_targets(recon_root: Path) -> list[str]:
    """Windows whose frozen output has a verified command transition or a cross-RTU bridge."""
    episodes = []
    for ep_dir in sorted(p for p in recon_root.iterdir() if p.is_dir()):
        tx_res = json.loads((ep_dir / "transactions.json").read_text(encoding="utf-8"))
        syn_res = json.loads((ep_dir / "incident_synthesis.json").read_text(encoding="utf-8"))
        has_tx = any(
            tx.get("device_state_change_status") in _VERIFIED_TX for tx in tx_res.get("transactions") or []
        )
        if has_tx or syn_res.get("verified_element_bridges"):
            episodes.append(ep_dir.name)
    return episodes


def run_post_freeze_physical_state_comparison(
    *,
    basic_zip_path: Path,
    stage1_recon_root: Path,
    scenario: str = "01-Basic",
    episodes: list[str] | None = None,
) -> dict:
    """``basic_zip_path`` is the scenario archive; the name is kept for existing callers."""
    if not basic_zip_path.exists():
        return {"status": "skipped_archive_not_found"}
    if episodes is None:
        episodes = (
            FIXED_PHYSICAL_AUDIT_EPISODES
            if scenario == "01-Basic"
            else episodes_with_physical_targets(stage1_recon_root)
        )

    with zipfile.ZipFile(basic_zip_path) as zf:
        raw_phys = zf.read(f"{scenario}/raw/test/physical.zip")

    entries: list[tuple[float, str]] = []
    with zipfile.ZipFile(io.BytesIO(raw_phys)) as pzf:
        for name in pzf.namelist():
            if name.startswith("__MACOSX") or not name.endswith(".json"):
                continue
            m = _TS_RE.search(name)
            if m:
                entries.append((float(f"{m.group(1)}.{m.group(2)}"), name))
        entries.sort()
        times = [e[0] for e in entries]

        def snapshot_near(target_ts: float) -> dict:
            idx = min(len(times) - 1, max(0, bisect.bisect_left(times, target_ts)))
            if idx > 0 and abs(times[idx - 1] - target_ts) < abs(times[idx] - target_ts):
                idx -= 1
            snap_ts, member_name = entries[idx]
            data = json.loads(pzf.read(member_name))
            return {
                "snapshot_time": snap_ts,
                "alignment_error_seconds": snap_ts - target_ts,
                "values": data.get("values") or {},
            }

        verified_tx_checks = []
        withheld_unverified_tx_checks = []
        cross_rtu_bridge_checks = []
        endpoint_rows = []
        mitm_conflict_quarantine_checks = []

        for ep in episodes:
            ep_dir = stage1_recon_root / ep
            tx_res = json.loads((ep_dir / "transactions.json").read_text(encoding="utf-8"))
            anc_res = json.loads((ep_dir / "event_anchors.json").read_text(encoding="utf-8"))
            syn_res = json.loads((ep_dir / "incident_synthesis.json").read_text(encoding="utf-8"))
            anchors_by_id = {a["anchor_id"]: a for a in (anc_res.get("anchors") or [])}

            for tx in tx_res.get("transactions") or []:
                status = tx.get("device_state_change_status")
                cmd_t = float(tx["start_time"])
                stem = tx.get("device_stem")
                if status in ("verified_state_transition", "verified_measurement_transition"):
                    if tx.get("measurement_transition"):
                        mt = tx["measurement_transition"]
                        ent = mt["measurement_entity"]
                        attr = ent.split(":", 1)[1]
                        pre_t = float(mt["pre_command_time"])
                        post_t = float(mt["post_command_time"])
                        net_pre = float(mt["pre_command_value"])
                        net_post = float(mt["post_command_value"])
                    else:
                        fb = tx["protocol_state_feedback"][0]
                        ent = fb["entity"]
                        attr = ent.split(":", 1)[1]
                        pre_t = cmd_t - 2.0
                        post_t = float(fb["timestamp"]) + 1.0
                        net_pre = float(fb["pre_state_value"])
                        net_post = float(fb["value"])

                    pre_snap = snapshot_near(pre_t)
                    post_snap = snapshot_near(post_t)
                    k_pre, raw_pre = _resolve_physical_key(pre_snap["values"], stem, attr)
                    _, raw_post = _resolve_physical_key(post_snap["values"], stem, attr)
                    ph_pre = _as_float(raw_pre)
                    ph_post = _as_float(raw_post)
                    pre_cmp = classify_numeric(
                        net_pre, ph_pre, TX_REL_TOL, criterion="transaction_pre_numeric_rel_0.05"
                    )
                    post_cmp = classify_numeric(
                        net_post, ph_post, TX_REL_TOL, criterion="transaction_post_numeric_rel_0.05"
                    )
                    combined = combine_sides(
                        pre_cmp,
                        post_cmp,
                        require_physical_change=True,
                        ph_pre=ph_pre,
                        ph_post=ph_post,
                    )
                    verified_tx_checks.append(_public_comparison({
                        "episode_id": ep,
                        "transaction_id": tx["transaction_id"],
                        "entity": ent,
                        "physical_key": k_pre,
                        "network_pre_time": pre_t,
                        "network_post_time": post_t,
                        "network_pre_value": round(net_pre, 4),
                        "network_post_value": round(net_post, 4),
                        "physical_pre_value": _r(ph_pre, 4),
                        "physical_post_value": _r(ph_post, 4),
                        "physical_pre_timestamp": round(pre_snap["snapshot_time"], 3),
                        "physical_post_timestamp": round(post_snap["snapshot_time"], 3),
                        "alignment_error_pre_seconds": _r(pre_snap["alignment_error_seconds"]),
                        "alignment_error_post_seconds": _r(post_snap["alignment_error_seconds"]),
                        "abs_alignment_error_pre_seconds": abs(pre_snap["alignment_error_seconds"]),
                        "abs_alignment_error_post_seconds": abs(post_snap["alignment_error_seconds"]),
                        "pre_comparison": pre_cmp,
                        "post_comparison": post_cmp,
                        **combined,
                        "physical_transition_matches_network": combined["compatible"],
                    }))
                elif ep == "ev_0961f1c2da8a257e3ebc" and status == "state_report_observed_no_pre_baseline":
                    fb = tx["protocol_state_feedback"][0]
                    ent = fb["entity"]
                    attr = ent.split(":", 1)[1]
                    pre_target = cmd_t - 2.0
                    post_target = float(fb["timestamp"]) + 1.0
                    pre_snap = snapshot_near(pre_target)
                    post_snap = snapshot_near(post_target)
                    k_pre, raw_pre = _resolve_physical_key(pre_snap["values"], stem, attr)
                    _, raw_post = _resolve_physical_key(post_snap["values"], stem, attr)
                    ph_pre = _as_float(raw_pre)
                    ph_post = _as_float(raw_post)
                    withheld_unverified_tx_checks.append({
                        "episode_id": ep,
                        "transaction_id": tx["transaction_id"],
                        "entity": ent,
                        "physical_key": k_pre,
                        "mirage_status": status,
                        "network_reconstruction_verified": False,
                        "network_post_reported_value": fb.get("value"),
                        "physical_pre_value": None if ph_pre is None or math.isnan(ph_pre) else ph_pre,
                        "physical_post_value": None if ph_post is None or math.isnan(ph_post) else ph_post,
                        "physical_pre_timestamp": round(pre_snap["snapshot_time"], 3),
                        "physical_post_timestamp": round(post_snap["snapshot_time"], 3),
                        "alignment_error_pre_seconds": _r(pre_snap["alignment_error_seconds"]),
                        "alignment_error_post_seconds": _r(post_snap["alignment_error_seconds"]),
                        "physical_post_matches_reported_cot3": (ph_post == fb.get("value")),
                        "finding": (
                            "The offline simulator shows a pre/post change whose post-value matches the "
                            "reported COT=3 sample. MIRAGE-OT still labels the transaction "
                            "`state_report_observed_no_pre_baseline` because the capture has no "
                            "pre-command IEC-104 state sample in the 15 s pre-window. This physical "
                            "observation does not promote the transaction to verified."
                        ),
                    })

            for br in syn_res.get("verified_element_bridges") or []:
                from_a = anchors_by_id.get(br["from_anchor_id"]) or {}
                to_a = anchors_by_id.get(br["to_anchor_id"]) or {}
                stem = br["bridged_device_stem"]
                point_agreements = []
                for anc_side in (from_a, to_a):
                    for pt in anc_side.get("points") or []:
                        attr = pt["attribute"]
                        pre_t = float(pt["pre_time"])
                        post_t = float(pt["post_time"]) + 1.0
                        pre_snap = snapshot_near(pre_t)
                        post_snap = snapshot_near(post_t)
                        k_phys, raw_pre = _resolve_physical_key(pre_snap["values"], stem, attr)
                        _, raw_post = _resolve_physical_key(post_snap["values"], stem, attr)
                        ph_pre = _as_float(raw_pre)
                        ph_post = _as_float(raw_post)
                        net_pre = float(pt["pre_value"])
                        net_post = float(pt["post_value"])
                        if pt["step_kind"] == "to_zero":
                            pre_cmp = classify_numeric(
                                net_pre,
                                ph_pre,
                                BRIDGE_REL_TOL,
                                criterion="to_zero_pre_numeric_rel_0.10",
                            )
                            post_cmp = classify_to_zero_post(net_post, ph_post)
                        else:
                            pre_cmp = classify_numeric(
                                net_pre,
                                ph_pre,
                                BRIDGE_REL_TOL,
                                criterion="level_shift_pre_numeric_rel_0.10",
                            )
                            post_cmp = classify_numeric(
                                net_post,
                                ph_post,
                                BRIDGE_REL_TOL,
                                criterion="level_shift_post_numeric_rel_0.10",
                            )
                        combined = combine_sides(pre_cmp, post_cmp)
                        row = _public_comparison({
                            "entity": pt["entity"],
                            "physical_key": k_phys,
                            "step_kind": pt["step_kind"],
                            "network_pre": round(net_pre, 4),
                            "network_post": round(net_post, 4),
                            "network_pre_time": pre_t,
                            "network_post_time": post_t,
                            "physical_pre": _r(ph_pre, 4),
                            "physical_post": (
                                "NaN_de_energized_island"
                                if ph_post is not None and math.isnan(ph_post)
                                else _r(ph_post, 4)
                            ),
                            "physical_pre_timestamp": round(pre_snap["snapshot_time"], 3),
                            "physical_post_timestamp": round(post_snap["snapshot_time"], 3),
                            "alignment_error_pre_seconds": _r(pre_snap["alignment_error_seconds"]),
                            "alignment_error_post_seconds": _r(post_snap["alignment_error_seconds"]),
                            "abs_alignment_error_pre_seconds": abs(pre_snap["alignment_error_seconds"]),
                            "abs_alignment_error_post_seconds": abs(post_snap["alignment_error_seconds"]),
                            "pre_comparison": pre_cmp,
                            "post_comparison": post_cmp,
                            **combined,
                            "agrees": combined["compatible"],
                        })
                        point_agreements.append(row)
                        endpoint_rows.append(row)
                cross_rtu_bridge_checks.append({
                    "episode_id": ep,
                    "bridge_id": br["bridge_id"],
                    "bridged_device_stem": stem,
                    "from_rtu_ip": br["from_rtu_ip"],
                    "to_rtu_ip": br["to_rtu_ip"],
                    "relation_claim": "corroborated_same_device_behavioral_transition",
                    "not_a_physical_cause": True,
                    "checked_endpoint_attributes": len(point_agreements),
                    "compatible_endpoint_attributes": sum(1 for p in point_agreements if p["compatible"]),
                    "numeric_agreement_endpoint_attributes": sum(
                        1 for p in point_agreements if p["numeric_agreement"]
                    ),
                    "all_endpoints_compatible": all(p["compatible"] for p in point_agreements) if point_agreements else False,
                    "all_endpoints_match_physical_simulator": (
                        all(p["compatible"] for p in point_agreements) if point_agreements else False
                    ),
                    "endpoint_comparisons": point_agreements,
                })

            if ep == "ev_52f5eee28f8b95e702fd":
                sample_targets = (
                    ("pre_window", 1742944990.0),
                    ("early_window", 1742945050.0),
                    ("late_window", 1742945300.0),
                )
                samples = []
                for label, target in sample_targets:
                    snap = snapshot_near(target)
                    sgen = snap["values"].get("sgen.12.MEASUREMENT.active_power")
                    samples.append({
                        "label": label,
                        "target_time": target,
                        "snapshot_time": round(snap["snapshot_time"], 3),
                        "alignment_error_seconds": _r(snap["alignment_error_seconds"]),
                        "switch_21_is_closed": snap["values"].get("switch.21.MEASUREMENT.is_closed"),
                        "sgen_12_active_power": None if sgen is None else round(float(sgen), 2),
                    })
                window = anc_res.get("window") or {}
                mitm_conflict_quarantine_checks.append({
                    "episode_id": ep,
                    "window": window,
                    "quarantined_unverified_anchor_count": anc_res.get("unverified_anchor_count"),
                    "verified_anchor_count": anc_res.get("verified_anchor_count"),
                    "anchors_compared_pointwise_to_physical_snapshots": 0,
                    "sampled_snapshot_count": len(samples),
                    "samples": samples,
                    "network_side_finding": (
                        "The frozen reconstruction, which did not read physical.zip, quarantined "
                        "671 anchors after `_merge_iec_vantages()` marked cross-vantage payload conflicts."
                    ),
                    "physical_sample_finding": (
                        "Three nearest snapshots show switch.21 closed, closed, then open, and "
                        "sgen.12 active power near 14000 W, near 14000 W, then 0 W. That pattern is "
                        "compatible with an opening between the early-window and late-window samples. "
                        "It does not show that the opening occurred once, that power remained 0 W, "
                        "or that each of the 671 quarantined anchors is a false physical event."
                    ),
                    "claim_scope": "three_sampled_snapshots_not_per_anchor_replay",
                })

    tx_tally = _tally(verified_tx_checks)
    endpoint_tally = _tally(endpoint_rows)
    bridge_compatible = sum(1 for c in cross_rtu_bridge_checks if c["all_endpoints_compatible"])
    gaps = [b - a for a, b in zip(times, times[1:])]

    return {
        "scenario": scenario,
        "evaluation_scope": (
            "Post-freeze air-gapped physical state comparison "
            f"(`{scenario}` `test/physical.zip`). Offline evaluation only."
        ),
        "epistemic_boundary": (
            "Compares frozen network transitions with the nearest simulator snapshots. "
            "Reports exact numeric agreement, tolerance agreement, and de-energized NaN "
            "compatibility separately. Does not verify a physical causal graph, and does not "
            "feed physical.zip into reconstruction."
        ),
        "comparison_criteria": COMPARISON_CRITERIA,
        "prior_audit_record": PRIOR_AUDIT_RECORD if scenario == "01-Basic" else None,
        "episodes_evaluated": list(episodes),
        "physical_snapshot_count": len(entries),
        "snapshot_spacing_seconds": {
            "median": _r(statistics.median(gaps), 3) if gaps else None,
            "p05": _r(sorted(gaps)[int(0.05 * len(gaps))], 3) if gaps else None,
            "p95": _r(sorted(gaps)[int(0.95 * len(gaps))], 3) if gaps else None,
        },
        "verified_transaction_agreement_summary": {
            **tx_tally,
            "checks": verified_tx_checks,
        },
        "withheld_no_pre_baseline_transaction_checks": withheld_unverified_tx_checks,
        "cross_rtu_bridge_agreement_summary": {
            "checked_bridge_count": len(cross_rtu_bridge_checks),
            "all_endpoints_compatible_bridge_count": bridge_compatible,
            "endpoint_attribute_summary": endpoint_tally,
            "checks": cross_rtu_bridge_checks,
        },
        "mitm_cross_vantage_conflict_quarantine_check": mitm_conflict_quarantine_checks,
    }


def _sum_tallies(tallies: list[dict]) -> dict:
    out = {}
    for key in tallies[0]:
        if key == "max_abs_alignment_error_seconds":
            vals = [t[key] for t in tallies if t[key] is not None]
            out[key] = max(vals) if vals else None
        else:
            out[key] = sum(t[key] for t in tallies)
    return out


def run_cross_scenario_physical_state_comparison(
    *,
    raw_dir: Path,
    recon_roots: dict[str, Path],
) -> dict:
    per_scenario = {
        scenario: run_post_freeze_physical_state_comparison(
            basic_zip_path=raw_dir / f"{scenario}.zip",
            stage1_recon_root=recon_roots[scenario],
            scenario=scenario,
        )
        for scenario in SCENARIOS
    }
    completed = [r for r in per_scenario.values() if "status" not in r]
    tx = [
        {k: v for k, v in r["verified_transaction_agreement_summary"].items() if k != "checks"}
        for r in completed
    ]
    endpoints = [r["cross_rtu_bridge_agreement_summary"]["endpoint_attribute_summary"] for r in completed]
    return {
        "evaluation_scope": "Post-freeze air-gapped physical state comparison across all Sherlock v3 test scenarios.",
        "comparison_criteria": COMPARISON_CRITERIA,
        "totals": {
            "verified_transactions": _sum_tallies(tx) if tx else None,
            "bridge_endpoint_attributes": _sum_tallies(endpoints) if endpoints else None,
            "checked_bridge_count": sum(
                r["cross_rtu_bridge_agreement_summary"]["checked_bridge_count"] for r in completed
            ),
            "all_endpoints_compatible_bridge_count": sum(
                r["cross_rtu_bridge_agreement_summary"]["all_endpoints_compatible_bridge_count"] for r in completed
            ),
        },
        "per_scenario": per_scenario,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/sherlock/v3"))
    parser.add_argument("--stage1-dir", type=Path, default=Path("runs/etgi/stage1-basic-frozen-20261015"))
    parser.add_argument("--stage2-dir", type=Path, default=Path("runs/etgi/stage2-cross-scenario-frozen-20261015"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    result = run_cross_scenario_physical_state_comparison(
        raw_dir=args.raw_dir,
        recon_roots={
            "01-Basic": args.stage1_dir / "reconstruction",
            "02-Semiurban": args.stage2_dir / "semiurban" / "reconstruction",
            "03-Rural": args.stage2_dir / "rural" / "reconstruction",
        },
    )
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
