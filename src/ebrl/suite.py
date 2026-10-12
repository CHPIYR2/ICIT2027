"""Constructed challenge cases.

These cases are synthetic. They are not Sherlock events and are not an estimate
of operational prevalence.
"""
from __future__ import annotations


def _net(evidence_id, at, ca, ioa, cot, value, select=False, retransmission=False, type_id=45):
    return {
        "evidence_id": evidence_id,
        "observed_at": at,
        "flow": "10.0.0.8:2404>10.0.0.1:40000",
        "format": "I",
        "type_id": type_id,
        "cot": cot,
        "ca": ca,
        "ioa": ioa,
        "value": value,
        "qualifier_select": select,
        "is_retransmission": retransmission,
        "tcp_ack_only": False,
        "parent_ids": [],
    }


def _proc(evidence_id, at, asset, variable, value, unit="NONE", quality=None, stale=False, context="MEASUREMENT", parents=None):
    return {
        "evidence_id": evidence_id,
        "observed_at": at,
        "asset_id": asset,
        "variable": variable,
        "unit": unit,
        "value": value,
        "quality": quality or [],
        "stale": stale,
        "context": context,
        "parent_ids": parents or [],
    }


def _map(evidence_id, ca, ioa, asset, variable, command, context="MEASUREMENT"):
    return {
        "evidence_id": evidence_id,
        "ca": ca,
        "ioa": ioa,
        "asset_id": asset,
        "variable": variable,
        "command_semantics": command,
        "context": context,
        "unit": "NONE",
    }


def _bundle(event_id, network, process, mappings, neighborhood=None, execution=None, effects=None, scopes=None):
    bundle = {
        "event_id": event_id,
        "t0": 1000.0,
        "window": [970.0, 1030.0],
        "network_records": network,
        "process_records": process,
        "mappings": mappings,
        "asset_neighborhood": neighborhood or [],
        "execution_records": execution or [],
        "action_effect_records": effects or [],
    }
    if scopes:
        bundle["ontology_scopes"] = scopes
    return bundle


def _closed_pair(prefix, command_at, after_at, before_at=None):
    if before_at is None:
        before_at = after_at - 1.0
    network = [
        _net(f"{prefix}_act", command_at, 11, 70, 6, 0),
        _net(f"{prefix}_ack", command_at + 0.2, 11, 70, 7, 0),
    ]
    process = [
        _proc(f"{prefix}_before", before_at, "breaker_7", "closed", True),
        _proc(f"{prefix}_after", after_at, "breaker_7", "closed", False),
    ]
    mappings = [_map(f"{prefix}_map", 11, 70, "breaker_7", "closed", "open_breaker")]
    return network, process, mappings


def build_suite() -> list[dict]:
    cases = []
    network, process, mappings = _closed_pair("open", 1000.0, 1003.0)
    cases.append({
        "case_id": "syn_open_supported",
        "bundle": _bundle("syn_open_supported", network, process, mappings),
        "labels": [{"network_evidence_id": "open_act", "process_evidence_id": "open_after", "g": 1, "o_star": "L"}],
    })
    network, process, mappings = _closed_pair("dec", 1000.0, 1003.0)
    cases.append({
        "case_id": "syn_deceptive_cooccurrence",
        "bundle": _bundle("syn_deceptive_cooccurrence", network, process, mappings),
        "labels": [{"network_evidence_id": "dec_act", "process_evidence_id": "dec_after", "g": 1, "o_star": "N"}],
        "note": "Visible rules support a bounded association. Independent label says the pair is operationally unlinked.",
    })
    cases.append({
        "case_id": "syn_unmapped_temporal",
        "bundle": _bundle(
            "syn_unmapped_temporal",
            [_net("unmap_act", 1000.0, 11, 70, 6, 0)],
            [
                _proc("unmap_before", 1002.0, "breaker_7", "closed", True),
                _proc("unmap_after", 1003.0, "breaker_7", "closed", False),
            ],
            [],
        ),
        "labels": [{"network_evidence_id": "unmap_act", "process_evidence_id": "unmap_after", "g": 1, "o_star": "L"}],
    })
    cases.append({
        "case_id": "syn_wrong_asset",
        "bundle": _bundle(
            "syn_wrong_asset",
            [_net("wrong_act", 1000.0, 11, 70, 6, 0), _net("wrong_ack", 1000.2, 11, 70, 7, 0)],
            [
                _proc("wrong_before", 1002.0, "line_9", "current_from", 10.0, unit="AMPERE"),
                _proc("wrong_after", 1003.0, "line_9", "current_from", 4.0, unit="AMPERE"),
            ],
            [_map("wrong_map", 11, 70, "breaker_7", "closed", "open_breaker")],
        ),
        "labels": [{"network_evidence_id": "wrong_act", "process_evidence_id": "wrong_after", "g": 1, "o_star": "N"}],
    })
    network, process, mappings = _closed_pair("stale", 1000.0, 1003.0)
    process[1]["stale"] = True
    cases.append({
        "case_id": "syn_stale",
        "bundle": _bundle("syn_stale", network, process, mappings),
        "labels": [{"network_evidence_id": "stale_act", "process_evidence_id": "stale_after", "g": 1, "o_star": "N"}],
    })
    network, process, mappings = _closed_pair("rev", 1000.0, 980.0, before_at=979.0)
    cases.append({
        "case_id": "syn_reverse_time",
        "bundle": _bundle("syn_reverse_time", network, process, mappings),
        "labels": [{"network_evidence_id": "rev_act", "process_evidence_id": "rev_after", "g": 1, "o_star": "N"}],
    })
    cases.append({
        "case_id": "syn_incompatible",
        "bundle": _bundle(
            "syn_incompatible",
            [_net("inc_act", 1000.0, 11, 70, 6, 0)],
            [
                _proc("inc_before", 1002.0, "breaker_7", "tap_position", 1),
                _proc("inc_after", 1003.0, "breaker_7", "tap_position", 2),
            ],
            [_map("inc_map", 11, 70, "breaker_7", "closed", "open_breaker")],
        ),
        "labels": [{"network_evidence_id": "inc_act", "process_evidence_id": "inc_after", "g": 1, "o_star": "N"}],
    })
    network, process, mappings = _closed_pair("skew", 1000.0, 999.5)
    cases.append({
        "case_id": "syn_clock_skew",
        "bundle": _bundle("syn_clock_skew", network, process, mappings),
        "labels": [{"network_evidence_id": "skew_act", "process_evidence_id": "skew_after", "g": 1, "o_star": "L"}],
    })
    cases.append({
        "case_id": "syn_competition",
        "bundle": _bundle(
            "syn_competition",
            [
                _net("far_act", 1000.0, 11, 70, 6, 0),
                _net("far_ack", 1000.2, 11, 70, 7, 0),
                _net("near_act", 1004.0, 11, 70, 6, 0),
                _net("near_ack", 1004.2, 11, 70, 7, 0),
            ],
            [
                _proc("cmp_before", 1006.0, "breaker_7", "closed", True),
                _proc("cmp_after", 1007.0, "breaker_7", "closed", False),
            ],
            [_map("cmp_map", 11, 70, "breaker_7", "closed", "open_breaker")],
        ),
        "labels": [
            {"network_evidence_id": "near_act", "process_evidence_id": "cmp_after", "g": 1, "o_star": "L"},
            {"network_evidence_id": "far_act", "process_evidence_id": "cmp_after", "g": 1, "o_star": "N"},
        ],
    })
    network, process, mappings = _closed_pair("r3", 1000.0, 1003.0)
    cases.append({
        "case_id": "syn_operational_response",
        "bundle": _bundle(
            "syn_operational_response",
            network,
            process,
            mappings,
            execution=[{
                "evidence_id": "r3_response",
                "role": "operational_response",
                "ca": 11,
                "ioa": 70,
                "observed_at": 1002.5,
            }],
        ),
        "labels": [{"network_evidence_id": "r3_act", "process_evidence_id": "r3_after", "g": 1, "o_star": "L"}],
    })
    network, process, mappings = _closed_pair("r4", 1000.0, 1003.0)
    cases.append({
        "case_id": "syn_action_effect",
        "bundle": _bundle(
            "syn_action_effect",
            network,
            process,
            mappings,
            execution=[{
                "evidence_id": "r4_response",
                "role": "operational_response",
                "ca": 11,
                "ioa": 70,
                "observed_at": 1002.5,
            }],
            effects=[{
                "evidence_id": "r4_effect",
                "role": "action_effect",
                "ca": 11,
                "ioa": 70,
                "asset_id": "breaker_7",
                "observed_at": 1003.0,
            }],
        ),
        "labels": [{"network_evidence_id": "r4_act", "process_evidence_id": "r4_after", "g": 1, "o_star": "L"}],
    })
    cases.append({
        "case_id": "syn_indirect",
        "bundle": _bundle(
            "syn_indirect",
            [_net("ind_act", 1000.0, 11, 70, 6, 0)],
            [
                _proc("ind_before", 1002.0, "line_9", "current_from", 10.0, unit="AMPERE"),
                _proc("ind_after", 1003.0, "line_9", "current_from", 4.0, unit="AMPERE"),
            ],
            [_map("ind_map", 11, 70, "breaker_7", "closed", "open_breaker")],
            neighborhood=[["breaker_7", "line_9"]],
        ),
        "labels": [{"network_evidence_id": "ind_act", "process_evidence_id": "ind_after", "g": 1, "o_star": "N"}],
    })
    cases.append({
        "case_id": "syn_alias_collision",
        "bundle": _bundle(
            "syn_alias_collision",
            [_net("alias_act", 1000.0, 21, 10, 6, 1, type_id=47)],
            [
                _proc("alias_before", 1002.0, "transformer_1", "tap_position", 1, context="MEASUREMENT"),
                _proc("alias_after", 1003.0, "transformer_1", "tap_position", 2, context="MEASUREMENT"),
            ],
            [_map("alias_map", 21, 10, "transformer_1", "tap_position", "raise_tap", context="CONFIGURATION")],
        ),
        "labels": [],
    })
    cases.append({
        "case_id": "syn_select_only",
        "bundle": _bundle(
            "syn_select_only",
            [_net("sel_act", 1000.0, 11, 70, 6, 0, select=True)],
            [
                _proc("sel_before", 1002.0, "breaker_7", "closed", True),
                _proc("sel_after", 1003.0, "breaker_7", "closed", False),
            ],
            [_map("sel_map", 11, 70, "breaker_7", "closed", "open_breaker")],
        ),
        "labels": [],
    })
    cases.append({
        "case_id": "syn_direction_conflict",
        "bundle": _bundle(
            "syn_direction_conflict",
            [_net("dir_act", 1000.0, 11, 70, 6, 0)],
            [
                _proc("dir_before", 1002.0, "breaker_7", "closed", False),
                _proc("dir_after", 1003.0, "breaker_7", "closed", True),
            ],
            [_map("dir_map", 11, 70, "breaker_7", "closed", "open_breaker")],
        ),
        "labels": [{"network_evidence_id": "dir_act", "process_evidence_id": "dir_after", "g": 1, "o_star": "N"}],
    })
    cases.append({
        "case_id": "syn_pump_portability",
        "bundle": _bundle(
            "syn_pump_portability",
            [_net("pump_act", 1000.0, 30, 1, 6, 0, type_id=45)],
            [
                _proc("pump_before", 1002.0, "pump_1", "flow_rate", 5.0, unit="FLOW"),
                _proc("pump_after", 1003.0, "pump_1", "flow_rate", 1.0, unit="FLOW"),
            ],
            [_map("pump_map", 30, 1, "pump_1", "flow_rate", "stop_pump")],
            scopes=["sherlock_attributes", "synthetic_portability_only"],
        ),
        "labels": [],
        "portability_only": True,
    })
    cases.append({
        "case_id": "syn_outside_window",
        "bundle": _bundle(
            "syn_outside_window",
            [_net("out_act", 1000.0, 11, 70, 6, 0)],
            [
                _proc("out_before", 1599.0, "line_9", "current_from", 8.0, unit="AMPERE"),
                _proc("out_after", 1600.0, "line_9", "current_from", 3.0, unit="AMPERE"),
            ],
            [_map("out_map", 11, 70, "breaker_7", "closed", "open_breaker")],
        ),
        "labels": [],
        "universe_only": [{"network_evidence_id": "out_act", "process_evidence_id": "out_after"}],
    })
    return cases
