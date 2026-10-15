"""Event Anchor Discovery for windows without an IEC-104 control command.

An anchor is a concrete observation worth starting an investigation from:

- `spontaneous_state_report`: an IEC-104 single/double point sent with COT=3.
- `measurement_step`: IEC-104 measurements of one device, carried by one ASDU,
  that dropped to zero, rose from zero, or shifted by at least half and stayed.
  Changes where both values are below 0.001 are numerical noise and ignored.
- `communication_change`: on one master-RTU IEC-104 link, TCP teardown,
  unanswered or completed connection attempts, a general interrogation or clock
  synchronisation, or a telemetry gap longer than the link's usual cadence.
- `arp_activity_increase`: ARP traffic from one host well above its background.

Every anchor is explicitly classified as `"verified_observation"` or
`"unverified_observation"` with `verification_issues`, checking pre/post
quality descriptors (IV/NT/SB/BL/OV), COT test bits, pre-sample cadence gap,
and multi-sample post-change persistence. Insufficiently supported observations
are preserved as `"unverified_observation"` so they cannot automatically enter
a supported storyline spine.
"""
from __future__ import annotations
import json
import statistics

STATE_TYPES = {1, 3, 30, 31}
MEASUREMENT_TYPES = {9, 10, 11, 12, 13, 14, 34, 35, 36}
STEP_RELATIVE = 0.5
PERSIST_RELATIVE = 0.1
MAGNITUDE_FLOOR = 1e-3
NEAR_ZERO_RELATIVE = 1e-6
MIN_PERSIST_SAMPLES = 2
MIN_PERSIST_RATIO = 0.8
MAX_PRE_SAMPLE_GAP_SECONDS = 30.0
VANTAGE_MERGE_SECONDS = 0.5
ARP_MIN_COUNT = 10
ARP_RATE_FACTOR = 5.0
GAP_MIN_SECONDS = 25.0
GAP_CADENCE_FACTOR = 3.0
_SYN, _FIN, _RST, _ACK = 0x02, 0x01, 0x04, 0x10


def split_attribute_endpoint(attribute: str | None) -> tuple[str | None, str | None]:
    """Split a point attribute into `(base_attribute, endpoint_side)` where side is `'from'`, `'to'`, or `None`."""
    if not attribute:
        return None, None
    if attribute.endswith("_from"):
        return attribute[:-5], "from"
    if attribute.endswith("_to"):
        return attribute[:-3], "to"
    return attribute, None


def discover_event_anchors(db, start: float, end: float, *, background_start: float,
                           transactions: list[dict] | None = None) -> dict:
    rows = _load_rows(db, background_start, end)
    observations = _merge_iec_vantages([r for r in rows if r["kind"] == "iec104_asdu"])
    anchors = [
        *_state_report_anchors(observations, start, end),
        *_measurement_step_anchors(observations, start, end),
        *_communication_anchors(rows, observations, start, end, background_start),
        *_arp_anchors(rows, start, end, background_start),
    ]
    _attach_ipal_rows(anchors, [r for r in rows if r["kind"] == "electrical_update"])
    covered = {tx.get("device_stem") for tx in transactions or []}
    for anchor in anchors:
        anchor["covered_by_transaction"] = bool(anchor.get("device_stem")) and anchor.get("device_stem") in covered
    anchors.sort(key=lambda a: (a["time"], a["anchor_type"], a.get("entity") or ""))
    for index, anchor in enumerate(anchors, start=1):
        anchor["anchor_id"] = f"A{index:03d}"
    ranked = sorted(
        anchors,
        key=lambda a: (
            0 if a.get("verification_status") == "verified_observation" else 1,
            -a["score"],
            a["time"],
        ),
    )
    for rank, anchor in enumerate(ranked, start=1):
        anchor["rank"] = rank
    verified_count = sum(1 for a in anchors if a.get("verification_status") == "verified_observation")
    unverified_count = sum(1 for a in anchors if a.get("verification_status") == "unverified_observation")
    return {
        "method": "evidence_anchor_discovery",
        "window": {"start": start, "end": end, "background_start": background_start},
        "parameters": {
            "step_relative": STEP_RELATIVE, "persist_relative": PERSIST_RELATIVE,
            "magnitude_floor": MAGNITUDE_FLOOR, "near_zero_relative": NEAR_ZERO_RELATIVE,
            "min_persist_samples": MIN_PERSIST_SAMPLES, "min_persist_ratio": MIN_PERSIST_RATIO,
            "max_pre_sample_gap_seconds": MAX_PRE_SAMPLE_GAP_SECONDS,
            "vantage_merge_seconds": VANTAGE_MERGE_SECONDS, "arp_min_count": ARP_MIN_COUNT,
            "arp_rate_factor": ARP_RATE_FACTOR, "gap_min_seconds": GAP_MIN_SECONDS,
            "gap_cadence_factor": GAP_CADENCE_FACTOR,
        },
        "inputs_not_used": ["official event labels", "attack type", "malicious flags", "physical.zip"],
        "observation_inventory": _inventory(rows, observations, start, end, background_start),
        "anchor_count": len(anchors),
        "verified_anchor_count": verified_count,
        "unverified_anchor_count": unverified_count,
        "anchors": anchors,
    }


def _load_rows(db, start: float, end: float) -> list[dict]:
    found = db.conn.execute(
        "SELECT * FROM evidence WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp, evidence_id",
        (start, end),
    ).fetchall()
    rows = []
    for row in found:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        rows.append(item)
    return rows


def _obs_quality_fields(p: dict) -> dict:
    q_inv = p.get("quality_invalid")
    q_flags = p.get("quality_flags")
    flags_set = sorted(k for k, v in q_flags.items() if v is True) if isinstance(q_flags, dict) else []
    flags_unknown = (
        (not isinstance(q_flags, dict) or any(v is None for v in q_flags.values()))
        if q_flags is not None else False
    )
    q_good_raw = p.get("quality_good")
    if q_inv is True or flags_set:
        q_good = False
    elif flags_unknown:
        q_good = None
    elif q_good_raw is not None:
        q_good = bool(q_good_raw)
    elif q_inv is False:
        q_good = True
    else:
        q_good = None
    return {
        "quality_good": q_good,
        "quality_invalid": q_inv,
        "quality_flags_set": flags_set,
        "quality_flags_unknown": flags_unknown,
        "cot_test": p.get("cot_test"),
    }


def _sample_quality_issues(prefix: str, obs: dict | None) -> list[str]:
    if obs is None:
        return [f"{prefix}_sample_missing"]
    issues = []
    if obs.get("quality_invalid") is True:
        issues.append(f"{prefix}_quality_invalid")
    elif obs.get("quality_flags_set"):
        issues.append(f"{prefix}_quality_flags_set:{','.join(obs['quality_flags_set'])}")
    elif obs.get("quality_flags_unknown") or obs.get("quality_good") is None:
        issues.append(f"{prefix}_quality_unknown")
    elif obs.get("quality_good") is False:
        issues.append(f"{prefix}_quality_not_good")
    if obs.get("cot_test") is True:
        issues.append(f"{prefix}_test_bit_set")
    elif obs.get("cot_test") is None:
        issues.append(f"{prefix}_test_bit_unknown")
    return issues


def _merge_iec_vantages(rows: list[dict]) -> list[dict]:
    """One observation per information object, however many mirror ports captured it."""
    merged: dict[tuple, dict] = {}
    out = []
    for row in rows:
        p = row["payload"]
        q = _obs_quality_fields(p)
        asdu_key = (row.get("src_ip"), row.get("src_port"), row.get("dst_ip"), row.get("dst_port"),
                    p.get("apci_tx"), p.get("asdu_index"))
        key = (asdu_key, row.get("ca_ioa"), p.get("object_index"))
        prior = merged.get(key)
        if prior is not None and p.get("apci_tx") is not None and abs(row["timestamp"] - prior["time"]) <= VANTAGE_MERGE_SECONDS:
            prior["vantages"] = sorted({*prior["vantages"], row.get("vantage")} - {None})
            prior["evidence_ids"].append(row["evidence_id"])
            if prior["quality_good"] is True and q["quality_good"] is True:
                prior["quality_good"] = True
            elif False in (prior["quality_good"], q["quality_good"]):
                prior["quality_good"] = False
            else:
                prior["quality_good"] = None
            if True in (prior["quality_invalid"], q["quality_invalid"]):
                prior["quality_invalid"] = True
            elif prior["quality_invalid"] is False and q["quality_invalid"] is False:
                prior["quality_invalid"] = False
            else:
                prior["quality_invalid"] = None
            prior["quality_flags_set"] = sorted({*prior["quality_flags_set"], *q["quality_flags_set"]})
            prior["quality_flags_unknown"] = bool(prior["quality_flags_unknown"] or q["quality_flags_unknown"])
            if True in (prior["cot_test"], q["cot_test"]):
                prior["cot_test"] = True
            elif prior["cot_test"] is False and q["cot_test"] is False:
                prior["cot_test"] = False
            else:
                prior["cot_test"] = None
            continue
        entity = row["entity"]
        obs = {
            "time": row["timestamp"],
            "entity": entity,
            "device_stem": entity.split(":", 1)[0] if ":" in entity else None,
            "attribute": entity.split(":", 1)[1] if ":" in entity else None,
            "ca_ioa": row.get("ca_ioa"),
            "ca": row.get("ca"),
            "type_id": p.get("type_id"),
            "cause": None if p.get("cause") in (None, "") else int(p["cause"]),
            "value": row.get("value") if row.get("value_present") else None,
            **q,
            "src_ip": row.get("src_ip"), "dst_ip": row.get("dst_ip"),
            "src_port": row.get("src_port"), "dst_port": row.get("dst_port"),
            "asdu_key": "|".join(str(x) for x in asdu_key),
            "vantages": [row.get("vantage")] if row.get("vantage") else [],
            "evidence_ids": [row["evidence_id"]],
        }
        merged[key] = obs
        out.append(obs)
    out.sort(key=lambda o: (o["time"], o["entity"]))
    return out


def _rtu_ip(obs: dict) -> str | None:
    if obs.get("src_port") == 2404:
        return obs.get("src_ip")
    if obs.get("dst_port") == 2404:
        return obs.get("dst_ip")
    return None


def _attach_ipal_rows(anchors: list[dict], ipal_rows: list[dict]) -> None:
    """IPAL rows of the anchor's points (or, for a state report, its device) shortly after it.

    These rows carry no packet reference, so they are listed as time-aligned values only.
    """
    for anchor in anchors:
        if anchor["anchor_type"] == "measurement_step":
            points = {p["ca_ioa"] for p in anchor["points"]}
            match = lambda r: r.get("ca_ioa") in points  # noqa: E731
            basis = "same_ca_ioa"
        elif anchor["anchor_type"] == "spontaneous_state_report":
            match = lambda r: r["entity"].split(":", 1)[0] == anchor["device_stem"]  # noqa: E731
            basis = "same_device_other_attribute"
        else:
            continue
        found = [r for r in ipal_rows if anchor["time"] - 0.5 <= r["timestamp"] <= anchor["time"] + 2.5 and match(r)]
        anchor["ipal_rows"] = [{
            "evidence_id": r["evidence_id"], "entity": r["entity"], "ca_ioa": r.get("ca_ioa"),
            "time": r["timestamp"], "value": r.get("value"),
            "match_basis": "same_ca_ioa" if anchor["anchor_type"] == "spontaneous_state_report"
            and r.get("ca_ioa") == anchor.get("ca_ioa") else basis,
        } for r in found]


def _state_report_anchors(observations: list[dict], start: float, end: float) -> list[dict]:
    anchors = []
    last_by_point: dict[str, dict] = {}
    for obs in observations:
        point = obs["ca_ioa"]
        if obs["type_id"] in STATE_TYPES and obs["cause"] == 3 and start <= obs["time"] < end:
            prior = last_by_point.get(point)
            issues: list[str] = []
            if obs["value"] is None:
                issues.append("state_value_undecoded")
            issues.extend(_sample_quality_issues("post", obs))
            if prior is None or prior["value"] is None:
                issues.append("no_prior_state_value_in_window")
            else:
                issues.extend(_sample_quality_issues("pre", prior))
                if prior["value"] == obs["value"]:
                    issues.append("state_value_unchanged")
                if obs["time"] - prior["time"] > MAX_PRE_SAMPLE_GAP_SECONDS:
                    issues.append("pre_sample_gap_exceeded")
            later_states = [
                o for o in observations
                if o["ca_ioa"] == point and o["type_id"] in STATE_TYPES
                and o["value"] is not None and obs["time"] < o["time"] < end
            ]
            if any(o["value"] != obs["value"] or _sample_quality_issues("later", o) for o in later_states):
                issues.append("not_sustained_in_later_samples")

            if obs["value"] is None:
                status = "state_report_value_undecoded"
            elif prior is None or prior["value"] is None:
                status = "state_report_no_prior_value_in_window"
            elif prior["value"] == obs["value"]:
                status = "state_report_same_as_prior"
            elif not issues:
                status = "state_change_observed"
            else:
                status = "state_change_quality_or_test_bit_unverified"
            verified = status == "state_change_observed" and not issues
            quality_ok = not (_sample_quality_issues("post", obs) or (prior is not None and _sample_quality_issues("pre", prior)))
            anchors.append({
                "anchor_type": "spontaneous_state_report",
                "time": obs["time"],
                "entity": obs["entity"],
                "device_stem": obs["device_stem"],
                "ca_ioa": point,
                "rtu_ip": _rtu_ip(obs),
                "asdu_key": obs["asdu_key"],
                "value": obs["value"],
                "prior_value": prior["value"] if prior else None,
                "prior_time": prior["time"] if prior else None,
                "prior_evidence_ids": prior["evidence_ids"][:2] if prior else [],
                "pre_quality_good": prior["quality_good"] if prior else None,
                "pre_cot_test": prior["cot_test"] if prior else None,
                "quality_good": quality_ok if obs["quality_good"] is not None else None,
                "cot_test": obs["cot_test"],
                "sustained_in_later_samples": verified,
                "transition_status": status,
                "verification_status": "verified_observation" if verified else "unverified_observation",
                "verification_issues": issues,
                "vantages": obs["vantages"],
                "evidence_ids": obs["evidence_ids"],
                "score": 4.0 + (1.0 if verified else -0.5),
                "observation": (
                    f"{obs['entity']} (CA/IOA={point}) reported value {obs['value']} with COT=3 by RTU "
                    f"{_rtu_ip(obs)}; prior IEC-104 value in window: "
                    f"{prior['value'] if prior else 'not observed'} ({status}; "
                    f"verification={'verified_observation' if verified else 'unverified_observation'})."
                ),
            })
        if obs["type_id"] in STATE_TYPES and obs["value"] is not None:
            last_by_point[point] = obs
    return anchors


def _measurement_step_anchors(observations: list[dict], start: float, end: float) -> list[dict]:
    series: dict[str, list[dict]] = {}
    for obs in observations:
        if obs["type_id"] in MEASUREMENT_TYPES and obs["value"] is not None:
            series.setdefault(obs["ca_ioa"], []).append(obs)
    groups: dict[tuple, list[dict]] = {}
    for samples in series.values():
        for index in range(1, len(samples)):
            prev, cur = samples[index - 1], samples[index]
            if not (start <= cur["time"] < end):
                continue
            kind = _step_kind(prev["value"], cur["value"])
            if kind is None:
                continue
            if (
                kind == "level_shift"
                and index >= 2
                and _step_kind(samples[index - 2]["value"], prev["value"]) == "level_shift"
                and _close(cur["value"], samples[index - 2]["value"])
            ):
                continue
            later = [s for s in samples[index + 1:] if s["time"] < end]
            val_persistent = [
                s for s in later
                if _sample_consistent_with_step(kind, prev["value"], cur["value"], s["value"])
            ]
            val_reverted = next(
                (s for s in later if not _sample_consistent_with_step(kind, prev["value"], cur["value"], s["value"])),
                None,
            )
            if kind == "level_shift" and (
                not val_persistent or (val_reverted is not None and val_reverted["time"] < val_persistent[0]["time"])
            ):
                continue

            point_issues = [*_sample_quality_issues("pre", prev), *_sample_quality_issues("post", cur)]
            pre_gap = round(cur["time"] - prev["time"], 6)
            if pre_gap <= 0 or pre_gap > MAX_PRE_SAMPLE_GAP_SECONDS:
                point_issues.append("pre_sample_gap_exceeded")

            qualified_persistent = [
                s for s in later
                if _sample_consistent_with_step(kind, prev["value"], cur["value"], s["value"])
                and not _sample_quality_issues("later", s)
            ]
            total_later = len(later)
            consistent_count = len(qualified_persistent)
            persist_ratio = round(consistent_count / total_later, 4) if total_later > 0 else 0.0
            immediate_val_ok = (
                total_later >= MIN_PERSIST_SAMPLES
                and all(
                    _sample_consistent_with_step(kind, prev["value"], cur["value"], s["value"])
                    for s in later[:MIN_PERSIST_SAMPLES]
                )
            )
            later_quality_bad = any(_sample_quality_issues("later", s) for s in later[:MIN_PERSIST_SAMPLES])
            if total_later < MIN_PERSIST_SAMPLES:
                point_issues.append("insufficient_post_samples")
            else:
                if later_quality_bad:
                    point_issues.append("later_sample_quality_or_test_bit_not_good")
                if not immediate_val_ok or persist_ratio < MIN_PERSIST_RATIO:
                    point_issues.append("not_sustained_in_later_samples")

            point_quality_ok = not (_sample_quality_issues("pre", prev) or _sample_quality_issues("post", cur))
            point_sustained = (
                total_later >= MIN_PERSIST_SAMPLES
                and immediate_val_ok
                and not later_quality_bad
                and persist_ratio >= MIN_PERSIST_RATIO
            )
            base_attr, endpoint_side = split_attribute_endpoint(cur["attribute"])
            groups.setdefault((cur["asdu_key"], cur["device_stem"], bool(point_issues)), []).append({
                "entity": cur["entity"],
                "attribute": cur["attribute"],
                "base_attribute": base_attr,
                "endpoint_side": endpoint_side,
                "ca_ioa": cur["ca_ioa"],
                "step_kind": kind,
                "pre_value": prev["value"],
                "pre_time": prev["time"],
                "pre_quality_good": prev["quality_good"],
                "pre_cot_test": prev["cot_test"],
                "pre_evidence_ids": prev["evidence_ids"][:2],
                "post_value": cur["value"],
                "post_time": cur["time"],
                "post_quality_good": cur["quality_good"],
                "post_cot_test": cur["cot_test"],
                "pre_sample_gap_seconds": pre_gap,
                "evidence_ids": cur["evidence_ids"],
                "later_samples_consistent": consistent_count,
                "later_samples_total": total_later,
                "persistence_ratio": persist_ratio,
                "quality_ok": point_quality_ok,
                "sustained": point_sustained,
                "verification_status": "verified_observation" if not point_issues else "unverified_observation",
                "verification_issues": point_issues,
                "_obs": cur,
            })
    anchors = []
    for (_asdu, stem, _has_issues), points in groups.items():
        first = points[0]["_obs"]
        quality_ok = all(p["quality_ok"] for p in points)
        sustained = all(p["sustained"] for p in points)
        issues = list(dict.fromkeys(iss for p in points for iss in p["verification_issues"]))
        ver_status = "verified_observation" if not issues else "unverified_observation"
        vantages = sorted({v for p in points for v in p.pop("_obs")["vantages"]})
        kinds = sorted({p["step_kind"] for p in points})
        anchors.append({
            "anchor_type": "measurement_step",
            "time": first["time"],
            "entity": f"{stem}:{','.join(p['attribute'] for p in points)}",
            "device_stem": stem,
            "ca_ioa": points[0]["ca_ioa"],
            "rtu_ip": _rtu_ip(first),
            "asdu_key": first["asdu_key"],
            "step_kinds": kinds,
            "points": points,
            "quality_good": quality_ok,
            "sustained_in_later_samples": sustained,
            "verification_status": ver_status,
            "verification_issues": issues,
            "vantages": vantages,
            "evidence_ids": list(dict.fromkeys(e for p in points for e in p["evidence_ids"])),
            "score": round(
                2.0 + min(1.0, len(points) / 4)
                + (0.5 if sustained else 0.0)
                + (0.5 if quality_ok else 0.0)
                + (0.5 if kinds != ["level_shift"] else 0.0)
                - (1.5 if ver_status != "verified_observation" else 0.0),
                4,
            ),
            "observation": (
                f"{stem}: {len(points)} measurement(s) in one ASDU from RTU {_rtu_ip(first)} changed "
                + "; ".join(f"{p['attribute']} {p['pre_value']} -> {p['post_value']}" for p in points[:4])
                + f" ({'/'.join(kinds)}; quality good={quality_ok}; sustained={sustained}; "
                f"verification={ver_status}"
                + (f"; issues={issues}" if issues else "")
                + ")."
            ),
        })
    return anchors


def _step_kind(prev: float, cur: float) -> str | None:
    if prev == cur or max(abs(prev), abs(cur)) < MAGNITUDE_FLOOR:
        return None
    if abs(cur) < MAGNITUDE_FLOOR and abs(cur) <= NEAR_ZERO_RELATIVE * abs(prev):
        return "to_zero"
    if abs(prev) < MAGNITUDE_FLOOR and abs(prev) <= NEAR_ZERO_RELATIVE * abs(cur):
        return "from_zero"
    if abs(cur - prev) / max(abs(cur), abs(prev)) >= STEP_RELATIVE:
        return "level_shift"
    return None


def _sample_consistent_with_step(kind: str, prev: float, cur: float, sample: float) -> bool:
    if kind == "to_zero":
        return abs(sample) < MAGNITUDE_FLOOR
    return _close(sample, cur)


def _close(a: float, b: float) -> bool:
    if a == b:
        return True
    return abs(a - b) <= PERSIST_RELATIVE * max(abs(a), abs(b))


def _communication_anchors(rows, observations, start, end, background_start) -> list[dict]:
    links: dict[tuple, dict] = {}

    def link(master: str, rtu: str) -> dict:
        return links.setdefault((master, rtu), {"events": [], "background_events": 0})

    seen: dict[tuple, float] = {}
    syn_by_tuple: dict[tuple, dict] = {}
    for row in rows:
        if row["kind"] != "tcp_packet" or 2404 not in (row.get("src_port"), row.get("dst_port")):
            continue
        flags = row["payload"].get("tcp_flags") or 0
        if not flags & (_SYN | _FIN | _RST):
            continue
        rtu_side = row.get("dst_port") == 2404
        master, rtu = (row["src_ip"], row["dst_ip"]) if rtu_side else (row["dst_ip"], row["src_ip"])
        five = (row["src_ip"], row["src_port"], row["dst_ip"], row["dst_port"], flags)
        if five in seen and abs(row["timestamp"] - seen[five]) <= VANTAGE_MERGE_SECONDS:
            continue
        seen[five] = row["timestamp"]
        if row["timestamp"] < start:
            link(master, rtu)["background_events"] += 1
            continue
        conn_key = tuple(sorted([(row["src_ip"], row["src_port"]), (row["dst_ip"], row["dst_port"])]))
        if flags & _SYN and not flags & _ACK:
            entry = syn_by_tuple.setdefault(conn_key, {"time": row["timestamp"], "attempts": 0,
                                                       "answered": False, "evidence_ids": [],
                                                       "master": master, "rtu": rtu})
            entry["attempts"] += 1
            entry["evidence_ids"].append(row["evidence_id"])
            entry["time_end"] = row["timestamp"]
        elif flags & _SYN and flags & _ACK:
            entry = syn_by_tuple.get(conn_key)
            if entry is not None:
                entry["answered"] = True
                entry["evidence_ids"].append(row["evidence_id"])
                entry["time_end"] = row["timestamp"]
        else:
            link(master, rtu)["events"].append({
                "event": "tcp_reset" if flags & _RST else "tcp_fin",
                "time": row["timestamp"],
                "session": f"{row['src_ip']}:{row['src_port']}->{row['dst_ip']}:{row['dst_port']}",
                "evidence_ids": [row["evidence_id"]],
            })
    for conn_key, entry in syn_by_tuple.items():
        link(entry["master"], entry["rtu"])["events"].append({
            "event": "connection_established" if entry["answered"] else "connection_attempt_unanswered",
            "time": entry["time"],
            "time_end": entry["time_end"],
            "session": f"{conn_key[0][0]}:{conn_key[0][1]}<->{conn_key[1][0]}:{conn_key[1][1]}",
            "syn_count": entry["attempts"],
            "evidence_ids": entry["evidence_ids"][:3],
        })
    for obs in observations:
        if not (start <= obs["time"] < end):
            continue
        rtu = _rtu_ip(obs)
        master = obs["src_ip"] if obs.get("dst_port") == 2404 else obs["dst_ip"]
        if obs["type_id"] in (100, 103):
            name = {100: "general_interrogation", 103: "clock_synchronisation"}[obs["type_id"]]
            link(master, rtu)["events"].append({
                "event": f"{name}_cot{obs['cause']}", "time": obs["time"],
                "ca": obs["ca"], "evidence_ids": obs["evidence_ids"][:2],
            })
        elif obs["cause"] == 20:
            link(master, rtu).setdefault("interrogated_objects", 0)
            link(master, rtu)["interrogated_objects"] += 1
    for (master, rtu), item in _telemetry_gaps(observations, start, end, background_start).items():
        link(master, rtu)["events"].append(item)

    anchors = []
    for (master, rtu), item in links.items():
        events = sorted(item["events"], key=lambda e: e["time"])
        if not events:
            continue
        kinds = sorted({e["event"] for e in events})
        ev_ids = list(dict.fromkeys(e for ev in events for e in ev["evidence_ids"]))[:12]
        issues = [] if ev_ids else ["no_packet_evidence"]
        ver_status = "verified_observation" if not issues else "unverified_observation"
        anchors.append({
            "anchor_type": "communication_change",
            "time": events[0]["time"],
            "time_end": max(e.get("time_end", e["time"]) for e in events),
            "entity": f"{master}<->{rtu}:2404/IEC104",
            "device_stem": None,
            "ca_ioa": None,
            "rtu_ip": rtu,
            "master_ip": master,
            "event_kinds": kinds,
            "events": events[:40],
            "event_count": len(events),
            "interrogated_objects": item.get("interrogated_objects", 0),
            "background_tcp_control_segments": item["background_events"],
            "verification_status": ver_status,
            "verification_issues": issues,
            "evidence_ids": ev_ids,
            "score": 2.0 + 0.5 * len(kinds),
            "observation": (
                f"IEC-104 link {master} <-> {rtu}: " + ", ".join(
                    f"{k} x{sum(1 for e in events if e['event'] == k)}" for k in kinds
                ) + f"; first at {round(events[0]['time'], 3)} (verification={ver_status})."
            ),
        })
    return anchors


def _telemetry_gaps(observations, start, end, background_start) -> dict:
    times: dict[tuple, list[float]] = {}
    for obs in observations:
        if obs.get("src_port") != 2404:
            continue
        times.setdefault((obs["dst_ip"], obs["src_ip"]), []).append(obs["time"])
    out = {}
    for key, values in times.items():
        distinct = sorted(set(round(t, 2) for t in values))
        background = [b - a for a, b in zip(distinct, distinct[1:]) if b < start]
        cadence = statistics.median(background) if background else None
        threshold = max(GAP_MIN_SECONDS, GAP_CADENCE_FACTOR * cadence) if cadence else None
        bounds = [background_start, *distinct, end]
        if threshold is None:
            continue
        for a, b in zip(bounds, bounds[1:]):
            if b - a >= threshold and b > start:
                out[key] = {"event": "telemetry_gap", "time": max(a, start), "gap_seconds": round(b - a, 3),
                            "usual_cadence_seconds": round(cadence, 3), "evidence_ids": []}
                break
    return out


def _arp_anchors(rows, start, end, background_start) -> list[dict]:
    window = max(end - start, 1e-9)
    background = max(start - background_start, 1e-9)
    by_host: dict[str, dict] = {}
    for row in rows:
        if row["kind"] != "arp_packet":
            continue
        host = by_host.setdefault(row.get("src_ip") or row["entity"], {"window": [], "background": 0})
        if row["timestamp"] < start:
            host["background"] += 1
        else:
            host["window"].append(row)
    anchors = []
    for host, item in by_host.items():
        count = len(item["window"])
        expected = item["background"] * window / background
        if count < ARP_MIN_COUNT or count < ARP_RATE_FACTOR * max(expected, 1.0):
            continue
        ops = {"request": 0, "reply": 0}
        targets: dict[str, int] = {}
        for row in item["window"]:
            ops["reply" if row["payload"].get("op") == 2 else "request"] += 1
            targets[row.get("dst_ip")] = targets.get(row.get("dst_ip"), 0) + 1
        anchors.append({
            "anchor_type": "arp_activity_increase",
            "time": item["window"][0]["timestamp"],
            "time_end": item["window"][-1]["timestamp"],
            "entity": f"{host}/ARP",
            "device_stem": None,
            "ca_ioa": None,
            "host_ip": host,
            "packet_count": count,
            "background_count": item["background"],
            "ops": ops,
            "targets": targets,
            "verification_status": "verified_observation",
            "verification_issues": [],
            "evidence_ids": [row["evidence_id"] for row in item["window"][:6]],
            "score": 1.0 + min(1.0, count / 100),
            "observation": (
                f"ARP from {host}: {count} packets in window ({ops['request']} requests, {ops['reply']} replies) "
                f"to {sorted(targets)}; {item['background']} in background (verification=verified_observation)."
            ),
        })
    return anchors


def _inventory(rows, observations, start, end, background_start) -> dict:
    def count(selector):
        return {"window": sum(1 for r in rows if selector(r) and r["timestamp"] >= start),
                "background": sum(1 for r in rows if selector(r) and r["timestamp"] < start)}

    by_type_cause: dict[str, int] = {}
    for obs in observations:
        if obs["time"] >= start:
            key = f"type{obs['type_id']}_cot{obs['cause']}"
            by_type_cause[key] = by_type_cause.get(key, 0) + 1
    return {
        "background_seconds": round(start - background_start, 3),
        "window_seconds": round(end - start, 3),
        "iec104_rows": count(lambda r: r["kind"] == "iec104_asdu"),
        "iec104_objects_after_vantage_merge_by_type_cot": by_type_cause,
        "iec104_control_objects_in_window": sum(
            1 for o in observations if o["time"] >= start and o["type_id"] and 45 <= o["type_id"] <= 69),
        "tcp_packets": count(lambda r: r["kind"] == "tcp_packet"),
        "tcp_syn_fin_rst_segments": count(
            lambda r: r["kind"] == "tcp_packet" and bool((r["payload"].get("tcp_flags") or 0) & (_SYN | _FIN | _RST))),
        "arp_packets": count(lambda r: r["kind"] == "arp_packet"),
        "udp_packets": count(lambda r: r["kind"] == "udp_packet"),
        "ipal_electrical_updates": count(lambda r: r["kind"] == "electrical_update"),
    }
