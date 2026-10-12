"""Audit whether saved Sherlock artifacts confirm an independent command-effect join.

This script reads inventories and the evaluator catalog only. It does not open
model-visible evidence and it does not download the archives.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    catalog = json.loads((ROOT / "data" / "evaluator" / "event_catalog.json").read_text(encoding="utf-8"))
    counts = Counter((event["scenario"], event["recording"], event["event_truth"]) for event in catalog["events"])
    by_scenario = Counter(event["scenario"] for event in catalog["events"])
    basic = json.loads((ROOT / "data" / "manifests" / "content_audit" / "01-Basic.json").read_text(encoding="utf-8"))
    members = basic["members"]
    physical = members["01-Basic/raw/test/physical.zip"]["samples"][0]
    control = members["01-Basic/raw/test/control-center.zip"]["samples"][0]
    device = members["01-Basic/raw/test/log/mtu-n1-vcc-service.log"]
    events_log = members["01-Basic/raw/test/events.jsonl"]
    raw_present = (ROOT / "data" / "raw").exists()
    summary = {
        "audit_date": "2026-10-13",
        "raw_archives_present": raw_present,
        "catalog_event_count": len(catalog["events"]),
        "by_scenario": dict(by_scenario),
        "by_scenario_recording_label": {f"{a}|{b}|{c}": n for (a, b, c), n in sorted(counts.items())},
        "paper_split_status": "NOT_CONFIRMED",
        "paper_split_note": "The manuscript plans 16 Basic development events and 32 evaluation events. The evaluator catalog contains 35 Basic, 48 Semiurban, and 36 Rural events. No EBRL pair manifest selects 16 of the 35.",
        "physical_sample_keys": physical["sample_top_keys"],
        "physical_access": members["01-Basic/raw/test/physical.zip"].get("access"),
        "control_center_sample_keys": control["sample_top_keys"],
        "control_center_preview_type": "CONNECTION_CHANGE",
        "events_jsonl_has_saved_record_sample": "sample_preview" in events_log,
        "device_log_sample": device["sample_first_line"],
        "independent_command_to_effect_join": "NOT_CONFIRMED",
        "r3_r4_factual_metrics": "NA",
        "reason": (
            "Saved audit samples show physical snapshots keyed by timestamp/values, "
            "a control-center CONNECTION_CHANGE notification, procedure-level event logs, "
            "and RTU/MTU startup logs. None of the saved samples records a command identifier "
            "joined to an execution response and a physical effect. The raw archives are not "
            "mounted here, so this is not a new full-text proof of absence."
        ),
    }
    out = ROOT / "results" / "ebrl-provenance-audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
