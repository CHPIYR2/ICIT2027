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

Only indexed evidence rows are read. Anchors are not attack names, and the
score only orders anchors for the storyline search; it is not a probability.
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
VANTAGE_MERGE_SECONDS = 0.5
ARP_MIN_COUNT = 10
ARP_RATE_FACTOR = 5.0
GAP_MIN_SECONDS = 25.0
GAP_CADENCE_FACTOR = 3.0
_SYN, _FIN, _RST, _ACK = 0x02, 0x01, 0x04, 0x10


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
    ranked = sorted(anchors, key=lambda a: (-a["score"], a["time"]))
    for rank, anchor in enumerate(ranked, start=1):
        anchor["rank"] = rank
    return {
        "method": "evidence_anchor_discovery",
        "window": {"start": start, "end": end, "background_start": background_start},
        "parameters": {
            "step_relative": STEP_RELATIVE, "persist_relative": PERSIST_RELATIVE,
            "magnitude_floor": MAGNITUDE_FLOOR,
            "vantage_merge_seconds": VANTAGE_MERGE_SECONDS, "arp_min_count": ARP_MIN_COUNT,
            "arp_rate_factor": ARP_RATE_FACTOR, "gap_min_seconds": GAP_MIN_SECONDS,
            "gap_cadence_factor": GAP_CADENCE_FACTOR,
        },
        "inputs_not_used": ["official event labels", "attack type", "malicious flags", "physical.zip"],
        "observation_inventory": _inventory(rows, observations, start, end, background_start),
        "anchor_count": len(anchors),
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


def _merge_iec_vantages(rows: list[dict]) -> list[dict]:
    """One observation per information object, however many mirror ports captured it."""
    merged: dict[tuple, dict] = {}
    out = []
    for row in rows:
        p = row["payload"]
        asdu_key = (row.get("src_ip"), row.get("src_port"), row.get("dst_ip"), row.get("dst_port"),
                    p.get("apci_tx"), p.get("asdu_index"))
        key = (asdu_key, row.get("ca_ioa"), p.get("object_index"))
        prior = merged.get(key)
        if prior is not None and p.get("apci_tx") is not None and abs(row["timestamp"] - prior["time"]) <= VANTAGE_MERGE_SECONDS:
            prior["vantages"] = sorted({*prior["vantages"], row.get("vantage")} - {None})
            prior["evidence_ids"].append(row["evidence_id"])
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
            "quality_good": p.get("quality_good"),
            "cot_test": p.get("cot_test"),
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
            if obs["value"] is None:
                status = "state_report_value_undecoded"
            elif prior is None or prior["value"] is None:
                status = "state_report_no_prior_value_in_window"
            elif prior["value"] == obs["value"]:
                status = "state_report_same_as_prior"
            elif obs["quality_good"] is True and prior["quality_good"] is True and obs["cot_test"] is False:
                status = "state_change_observed"
            else:
                status = "state_change_quality_or_test_bit_unverified"
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
                "quality_good": obs["quality_good"],
                "cot_test": obs["cot_test"],
                "transition_status": status,
                "vantages": obs["vantages"],
                "evidence_ids": obs["evidence_ids"],
                "score": 4.0 + (1.0 if status == "state_change_observed" else 0.0),
                "observation": (
                    f"{obs['entity']} (CA/IOA={point}) reported value {obs['value']} with COT=3 by RTU "
                    f"{_rtu_ip(obs)}; prior IEC-104 value in window: "
                    f"{prior['value'] if prior else 'not observed'} ({status})."
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
            later = samples[index + 1:]
            persistent = [s for s in later if _close(s["value"], cur["value"])]
            reverted = next((s for s in later if not _close(s["value"], cur["value"])), None)
            if kind == "level_shift" and (not persistent or reverted is not None and reverted["time"] < persistent[0]["time"]):
                continue
            groups.setdefault((cur["asdu_key"], cur["device_stem"]), []).append({
                "entity": cur["entity"],
                "attribute": cur["attribute"],
                "ca_ioa": cur["ca_ioa"],
                "step_kind": kind,
                "pre_value": prev["value"],
                "pre_time": prev["time"],
                "pre_quality_good": prev["quality_good"],
                "pre_evidence_ids": prev["evidence_ids"][:2],
                "post_value": cur["value"],
                "post_time": cur["time"],
                "post_quality_good": cur["quality_good"],
                "post_cot_test": cur["cot_test"],
                "evidence_ids": cur["evidence_ids"],
                "later_samples_consistent": len(persistent),
                "later_samples_total": len(later),
                "_obs": cur,
            })
    anchors = []
    for (_asdu, stem), points in groups.items():
        first = points[0]["_obs"]
        quality_ok = all(p["pre_quality_good"] is True and p["post_quality_good"] is True
                         and p["post_cot_test"] is False for p in points)
        sustained = all(p["later_samples_consistent"] > 0 for p in points)
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
            "vantages": vantages,
            "evidence_ids": list(dict.fromkeys(e for p in points for e in p["evidence_ids"])),
            "score": 2.0 + min(1.0, len(points) / 4) + (0.5 if sustained else 0.0) + (0.5 if quality_ok else 0.0)
            + (0.5 if kinds != ["level_shift"] else 0.0),
            "observation": (
                f"{stem}: {len(points)} measurement(s) in one ASDU from RTU {_rtu_ip(first)} changed "
                + "; ".join(f"{p['attribute']} {p['pre_value']} -> {p['post_value']}" for p in points[:4])
                + f" ({'/'.join(kinds)}; quality good={quality_ok}; sustained={sustained})."
            ),
        })
    return anchors


def _step_kind(prev: float, cur: float) -> str | None:
    if prev == cur or max(abs(prev), abs(cur)) < MAGNITUDE_FLOOR:
        return None
    if abs(cur) <= NEAR_ZERO_RELATIVE * abs(prev):
        return "to_zero"
    if abs(prev) <= NEAR_ZERO_RELATIVE * abs(cur):
        return "from_zero"
    if abs(cur - prev) / max(abs(cur), abs(prev)) >= STEP_RELATIVE:
        return "level_shift"
    return None


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
            "evidence_ids": list(dict.fromkeys(e for ev in events for e in ev["evidence_ids"]))[:12],
            "score": 2.0 + 0.5 * len(kinds),
            "observation": (
                f"IEC-104 link {master} <-> {rtu}: " + ", ".join(
                    f"{k} x{sum(1 for e in events if e['event'] == k)}" for k in kinds
                ) + f"; first at {round(events[0]['time'], 3)}."
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
            "evidence_ids": [row["evidence_id"] for row in item["window"][:6]],
            "score": 1.0 + min(1.0, count / 100),
            "observation": (
                f"ARP from {host}: {count} packets in window ({ops['request']} requests, {ops['reply']} replies) "
                f"to {sorted(targets)}; {item['background']} in background."
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
