"""Investigation tools. Each one is a bounded read of the evidence database."""
from __future__ import annotations
from ..evidence.queries import DEFAULT_LIMIT, EvidenceDB

_OBJECT = {"type": "object", "properties": {}, "additionalProperties": True}

SPECS = [
    ("query_network_events", "TCP and ARP observations in a time window."),
    ("query_iec104_messages", "Decoded IEC-104 ASDU objects. protocol_class is the IEC type-id class, not an attack label."),
    ("query_electrical_telemetry", "Network-reported electrical rows, including holds and initial fills."),
    ("query_electrical_changes", "Electrical rows whose value changed. Holds are excluded."),
    ("query_entity_timeline", "Rows for one entity."),
    ("query_related_entities", "Other entities observed near this entity. Proximity is not causation."),
    ("query_tcp_flows", "Aggregated TCP flows."),
    ("query_arp_activity", "ARP packets."),
    ("query_device_observations", "Rows whose entity starts with a device prefix, or that mention an IP."),
    ("query_multi_vantage_evidence", "Frames captured at more than one vantage."),
    ("compare_time_windows", "Observation counts in two time windows."),
    ("retrieve_raw_evidence", "Rows for explicit evidence ids."),
    ("propose_relations", "Propose candidate relations. This does not mark them supported."),
    ("revise_relation", "Ask to change a relation. A supported status is kept only if record checks agree."),
    ("stop_investigation", "Stop requesting evidence and say what is still missing."),
    ("set_subgoal", "Planner only. Name the next subgoal. This does not read the database."),
    ("complete_subgoal", "Investigator only. Close the current subgoal and update the belief state."),
    ("retrieve_subgoal_trajectory", "Return the stored action-observation pairs of one earlier subgoal."),
]


_TIME = {"start": {"type": "number"}, "end": {"type": "number"},
         "limit": {"type": "integer"}, "offset": {"type": "integer"}}
_RELATION = {
    "type": "object",
    "required": ["source_entity", "target_entity", "source_modality", "target_modality",
                 "relation_type", "evidence_ids"],
    "properties": {
        "source_entity": {"type": "string"},
        "target_entity": {"type": "string"},
        "source_modality": {"type": "string", "enum": ["network", "electrical"]},
        "target_modality": {"type": "string", "enum": ["network", "electrical"]},
        "relation_type": {"type": "string"},
        "time_order": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "rationale": {"type": "string"},
        "alternatives": {"type": "array", "items": {"type": "string"}},
    },
}
_SCHEMAS = {
    "query_network_events": {"required": [], "properties": {**_TIME, "ip": {"type": "string"}, "vantage": {"type": "string"}}},
    "query_iec104_messages": {"required": [], "properties": {**_TIME, "ca": {"type": "string"}, "ioa": {"type": "string"},
                                                             "ip": {"type": "string"}, "vantage": {"type": "string"}}},
    "query_electrical_telemetry": {"required": [], "properties": {**_TIME, "entity": {"type": "string"}}},
    "query_electrical_changes": {"required": [], "properties": {**_TIME, "entity": {"type": "string"}}},
    "query_entity_timeline": {"required": ["entity"], "properties": {**_TIME, "entity": {"type": "string"}}},
    "query_related_entities": {"required": ["entity"], "properties": {**_TIME, "entity": {"type": "string"},
                                                                      "gap_seconds": {"type": "number"}}},
    "query_tcp_flows": {"required": [], "properties": {**_TIME, "ip": {"type": "string"}, "vantage": {"type": "string"}}},
    "query_arp_activity": {"required": [], "properties": {**_TIME, "ip": {"type": "string"}}},
    "query_device_observations": {"required": [], "properties": {**_TIME, "entity": {"type": "string"},
                                                                 "entity_prefix": {"type": "string"}, "ip": {"type": "string"}}},
    "query_multi_vantage_evidence": {"required": [], "properties": dict(_TIME)},
    "compare_time_windows": {"required": ["start_a", "end_a", "start_b", "end_b"], "properties": {
        "start_a": {"type": "number"}, "end_a": {"type": "number"},
        "start_b": {"type": "number"}, "end_b": {"type": "number"}}},
    "retrieve_raw_evidence": {"required": ["evidence_ids"], "properties": {
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1}}},
    "propose_relations": {"required": ["relations"], "properties": {
        "relations": {"type": "array", "minItems": 1, "items": _RELATION},
        "unresolved_questions": {"type": "array", "items": {"type": "string"}}}},
    "revise_relation": {"required": ["edge_id", "proposed_status", "reason"], "properties": {
        "edge_id": {"type": "string"}, "proposed_status": {"type": "string"},
        "reason": {"type": "string"}, "evidence_ids": {"type": "array", "items": {"type": "string"}}}},
    "stop_investigation": {"required": [], "properties": {
        "unresolved_questions": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"}}},
    "set_subgoal": {"required": ["subgoal"], "properties": {"subgoal": {"type": "string"}}},
    "complete_subgoal": {"required": ["status"], "properties": {
        "status": {"type": "string", "enum": ["achieved", "not_achieved", "insufficient_evidence"]},
        "known_facts": {"type": "array"},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "contradictory_evidence": {"type": "array"}}},
    "retrieve_subgoal_trajectory": {"required": ["subgoal_index"], "properties": {
        "subgoal_index": {"type": "integer"}}},
}


def schemas(names: tuple[str, ...] | None = None) -> list[dict]:
    selected = [(name, description) for name, description in SPECS if names is None or name in names]
    return [{
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": _SCHEMAS[name]["properties"],
                "required": _SCHEMAS[name]["required"],
            },
        },
    } for name, description in selected]


def validate_arguments(name: str, arguments: dict) -> tuple[bool, list[str]]:
    """Reject a tool call whose required fields are missing. An empty proposal is invalid."""
    if name not in _SCHEMAS:
        return False, [f"unknown tool {name}"]
    if not isinstance(arguments, dict):
        return False, ["arguments must be an object"]
    errors = []
    for key in _SCHEMAS[name]["required"]:
        value = arguments.get(key)
        if value is None or value == "" or value == []:
            errors.append(f"missing required {key}")
    if name == "propose_relations" and isinstance(arguments.get("relations"), list):
        if not arguments["relations"]:
            errors.append("relations must contain at least one relation")
        for index, item in enumerate(arguments["relations"]):
            if not isinstance(item, dict):
                errors.append(f"relations[{index}] must be an object")
                continue
            for key in _RELATION["required"]:
                value = item.get(key)
                if value is None or value == "" or value == []:
                    errors.append(f"relations[{index}] missing {key}")
    if name == "complete_subgoal" and arguments.get("status") not in (
            "achieved", "not_achieved", "insufficient_evidence"):
        errors.append("status must be achieved, not_achieved, or insufficient_evidence")
    if name == "retrieve_subgoal_trajectory" and not isinstance(arguments.get("subgoal_index"), int):
        errors.append("subgoal_index must be an integer")
    return not errors, errors


def dispatch(db: EvidenceDB, name: str, arguments: dict, *, incident_start: float, incident_end: float) -> dict:
    args = dict(arguments or {})
    start, end, window_note = _incident_window(args, incident_start, incident_end)
    limit = args.get("limit", DEFAULT_LIMIT)
    offset = args.get("offset", 0)
    result = _query(db, name, args, start, end, limit, offset, incident_start, incident_end)
    return _annotate(result, window_note)


def _query(db, name, args, start, end, limit, offset, incident_start, incident_end) -> dict:
    if name == "query_network_events":
        return db.search(modality="network", start=start, end=end, ip=args.get("ip"),
                         vantage=args.get("vantage"), limit=limit, offset=offset,
                         kinds=("tcp_packet", "arp_packet"))
    if name == "query_iec104_messages":
        return db.search(kind="iec104_asdu", start=start, end=end, ca=args.get("ca"), ioa=args.get("ioa"),
                         ip=args.get("ip"), vantage=args.get("vantage"), limit=limit, offset=offset)
    if name == "query_electrical_telemetry":
        return db.search(modality="electrical", start=start, end=end, entity=args.get("entity"),
                         ca_ioa=args.get("ca_ioa"), limit=limit, offset=offset)
    if name == "query_electrical_changes":
        return db.search(modality="electrical", kind="electrical_update", start=start, end=end,
                         entity=args.get("entity"), limit=limit, offset=offset)
    if name == "query_entity_timeline":
        if not args.get("entity"):
            return {"query": name, "rows": [], "notes": ["entity is required"], "evidence_ids": [],
                    "data_is_untrusted_telemetry": True}
        return db.entity_timeline(args["entity"], start=start, end=end, limit=limit, offset=offset)
    if name == "query_related_entities":
        if not args.get("entity"):
            return {"query": name, "rows": [], "notes": ["entity is required"], "evidence_ids": [],
                    "data_is_untrusted_telemetry": True}
        return db.related_entities(args["entity"], start=start, end=end,
                                   gap_seconds=float(args.get("gap_seconds", 2.0)), limit=min(int(limit), 20))
    if name == "query_tcp_flows":
        return db.flow_summary(start=start, end=end, limit=limit, offset=offset,
                               ip=args.get("ip"), vantage=args.get("vantage"))
    if name == "query_arp_activity":
        return db.search(kind="arp_packet", start=start, end=end, ip=args.get("ip"), limit=limit, offset=offset)
    if name == "query_device_observations":
        return db.search(start=start, end=end, entity_prefix=args.get("entity_prefix") or args.get("entity"),
                         ip=args.get("ip"), limit=limit, offset=offset)
    if name == "query_multi_vantage_evidence":
        return db.multi_vantage(start=start, end=end, limit=limit, offset=offset)
    if name == "compare_time_windows":
        return db.compare_windows(
            float(args.get("start_a", incident_start)), float(args.get("end_a", incident_end)),
            float(args.get("start_b", incident_start - 15)), float(args.get("end_b", incident_start)),
        )
    if name == "retrieve_raw_evidence":
        return db.get(list(args.get("evidence_ids") or []))
    if name in ("propose_relations", "revise_relation", "stop_investigation",
                "set_subgoal", "complete_subgoal", "retrieve_subgoal_trajectory"):
        return {"query": name, "accepted": True, "arguments": args, "data_is_untrusted_telemetry": True,
                "rows": [], "evidence_ids": []}
    return {"query": name, "rows": [], "notes": [f"Unknown tool {name}"], "evidence_ids": [],
            "data_is_untrusted_telemetry": True}


def _incident_window(args: dict, incident_start: float, incident_end: float) -> tuple[float, float, str | None]:
    """Use the incident window when a model time range does not overlap it."""
    try:
        start = float(args.get("start", incident_start))
        end = float(args.get("end", incident_end))
    except (TypeError, ValueError):
        return incident_start, incident_end, "Unparseable times were replaced with the incident window."
    if end <= incident_start - 30 or start >= incident_end + 30 or end <= start:
        return incident_start, incident_end, "The requested time range does not overlap the incident window, so the incident window was used."
    return start, end, None


def _annotate(result: dict, note: str | None) -> dict:
    if note:
        result.setdefault("notes", []).append(note)
    return result
