"""One completion over a prepared timeline. The model does not choose tools.

`expose_timeline()` picks a bounded set of Fact Cards across roles so an early
burst of network packets does not hide electrical updates. Two claim styles
are supported: `typed_refs` (the model selects `fact_id` or `edge_id` anchors)
and `free_form` (the model fills entity/time/value fields). Truncated replies
are marked `partial_output=True` and are not treated as complete structured
outputs unless salvage is explicitly requested.
"""
from __future__ import annotations
import json

SYSTEM_FREE_FORM = """You explain one supplied time window from the JSON only.
Return one JSON object with keys abstain, hypotheses, and claims.
Each claim has claim_type (observation_claim, measurement_claim, relation_claim, or absence_claim),
evidence_ids, entity, time, start_time, end_time, value, direction, source_entity, target_entity,
relation_type, and claim_level.
claim_level is observed_fact, temporal_cooccurrence, supported_inference, unresolved, or disputed.
Use only evidence_ids present in the input. Time proximity is not a supported inference.
Do not state a cause. Do not name an attack class.
If the records are not enough, set abstain to true and leave claims empty.
"""

SYSTEM_TYPED_REFS = """You explain one supplied time window from the JSON only.
Return one JSON object with keys abstain, hypotheses, and claims.
Do not rewrite timestamps, IP addresses, CA/IOA strings, or measurement numbers.
Instead, reference the supplied anchors and keep their canonical claim_level:
- For a single timeline fact: {"claim_type": "observation_claim" or "measurement_claim", "fact_id": "TL...", "claim_level": "observed_fact"}
- For a candidate relation: {"claim_type": "relation_claim", "edge_id": "R...", "relation_type": "<exact edge relation_type>", "claim_level": "<exact edge claim_level>"}
Do not upgrade an observed_fact record link (communication, same_device, shared_source) or a temporal_cooccurrence to supported_inference.
Keep at most 6 claims. Time proximity is not a supported inference. Do not state a cause. Do not name an attack class.
If the records are not enough, set abstain to true and leave claims empty.
"""

_TYPED_CLAIM_ITEM = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "claim_type": {"type": "string", "enum": ["observation_claim", "measurement_claim"]},
                "fact_id": {"type": "string"},
                "claim_level": {"type": "string", "enum": ["observed_fact", "unresolved"]},
            },
            "required": ["claim_type", "fact_id", "claim_level"],
        },
        {
            "type": "object",
            "properties": {
                "claim_type": {"type": "string", "enum": ["relation_claim"]},
                "edge_id": {"type": "string"},
                "relation_type": {"type": "string"},
                "claim_level": {"type": "string", "enum": ["observed_fact", "temporal_cooccurrence", "supported_inference", "unresolved", "disputed"]},
            },
            "required": ["claim_type", "edge_id", "claim_level"],
        },
        {
            "type": "object",
            "properties": {
                "claim_type": {"type": "string", "enum": ["absence_claim"]},
                "absent_kind": {"type": "string", "enum": ["arp_packet", "iec104_control"]},
                "claim_level": {"type": "string", "enum": ["observed_fact"]},
            },
            "required": ["claim_type", "absent_kind", "claim_level"],
        },
    ],
}

CLAIM_FORMAT_FREE = {
    "type": "object",
    "properties": {
        "abstain": {"type": "boolean"},
        "hypotheses": {"type": "array"},
        "claims": {"type": "array"},
    },
    "required": ["abstain", "claims"],
}

CLAIM_FORMAT_TYPED = {
    "type": "object",
    "properties": {
        "abstain": {"type": "boolean"},
        "hypotheses": {"type": "array", "items": {"type": "string"}},
        "claims": {"type": "array", "items": _TYPED_CLAIM_ITEM},
    },
    "required": ["abstain", "claims"],
}


def expose_timeline(timeline: list[dict], *, limit: int = 10) -> list[dict]:
    """Stratified Fact Card exposure across roles, then score, then time."""
    chosen = []
    seen = set()
    quotas = (
        ("command", 2),
        ("electrical_change", 4),
        ("electrical_report", 2),
        ("communication", 4),
        ("response", 2),
    )
    by_score = sorted(timeline, key=lambda item: (-float(item.get("score") or 0.0), item["time"]))
    for role, quota in quotas:
        count = 0
        for event in by_score:
            if event.get("role") != role or event["timeline_id"] in seen:
                continue
            chosen.append(event)
            seen.add(event["timeline_id"])
            count += 1
            if count >= quota or len(chosen) >= limit:
                break
    for event in by_score:
        if len(chosen) >= limit:
            break
        if event["timeline_id"] in seen:
            continue
        chosen.append(event)
        seen.add(event["timeline_id"])
    chosen.sort(key=lambda item: (item["time"], item["timeline_id"]))
    return [_compact_card(event) for event in chosen]


def expose_relations(relations: list[dict], exposed_timeline: list[dict], *, limit: int = 8) -> list[dict]:
    exposed_facts = {event.get("timeline_id") for event in exposed_timeline if event.get("timeline_id")}
    exposed_ids = {evidence_id for event in exposed_timeline for evidence_id in event.get("evidence_ids") or []}

    def _rank(rel: dict) -> tuple:
        both_endpoints = int(rel.get("source_fact_id") in exposed_facts and rel.get("target_fact_id") in exposed_facts)
        any_id = int(bool(set(rel.get("evidence_ids") or []) & exposed_ids))
        is_supported = int(rel.get("claim_level") == "observed_fact" and rel.get("verification_status") == "supported")
        return (-both_endpoints, -is_supported, -any_id, rel.get("edge_id") or "")

    prioritized = sorted(relations, key=_rank)
    return prioritized[:limit]


def _compact_card(event: dict) -> dict:
    card = {
        "timeline_id": event["timeline_id"],
        "time": event["time"],
        "time_end": event["time_end"],
        "role": event["role"],
        "record_class": event["record_class"],
        "modality": (event.get("source") or {}).get("modality"),
        "kind": (event.get("source") or {}).get("kind"),
        "vantages": (event.get("source") or {}).get("vantages"),
        "entity": event["entity"],
        "evidence_ids": list(event.get("evidence_ids") or [])[:4],
        "independent": event.get("independent", True),
    }
    if event.get("ca_ioa"):
        card["ca_ioa"] = event["ca_ioa"]
    if event.get("value_present"):
        card["value"] = event.get("value")
        card["value_semantics"] = event.get("value_semantics")
    elif event.get("packet_count") is not None:
        card["packet_count"] = event.get("packet_count")
    elif event.get("source_frame_count") is not None:
        card["source_frame_count"] = event.get("source_frame_count")
    return card


def explain(llm, prepared: dict, *, level: str, claim_mode: str = "typed_refs",
            allow_salvage: bool = False, num_predict: int = 512, num_ctx: int = 8192, seed: int = 1) -> dict:
    body, exposed_events, exposed_rels = _input(prepared, level)
    system = SYSTEM_TYPED_REFS if claim_mode == "typed_refs" else SYSTEM_FREE_FORM
    schema = CLAIM_FORMAT_TYPED if claim_mode == "typed_refs" else CLAIM_FORMAT_FREE
    turn = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(body, default=str)}],
        tools=None, temperature=0, seed=seed, num_predict=num_predict, num_ctx=num_ctx,
        response_format=schema,
    )
    parsed = _object(turn.content, allow_salvage=allow_salvage)
    partial = bool(turn.done_reason == "length" or parsed.get("json_truncated"))
    raw_claims = parsed.get("claims") if isinstance(parsed.get("claims"), list) else []
    salvaged_pool = parsed.get("salvaged_claims") if isinstance(parsed.get("salvaged_claims"), list) else raw_claims
    salvaged = [item for item in salvaged_pool if isinstance(item, dict)] if partial else []
    claims = salvaged if (partial and allow_salvage) else ([item for item in raw_claims if isinstance(item, dict)] if not partial else [])
    hypotheses = parsed.get("hypotheses") if isinstance(parsed.get("hypotheses"), list) else []
    explicit_abstain = bool(parsed.get("abstain")) and not partial and not claims
    return {
        "level": level,
        "claim_mode": claim_mode,
        "abstain": explicit_abstain,
        "partial_output": partial,
        "salvaged_claim_count": len(salvaged),
        "hypotheses": hypotheses,
        "claims": claims,
        "exposed_timeline_ids": [item["timeline_id"] for item in exposed_events],
        "exposed_edge_ids": [item["edge_id"] for item in exposed_rels],
        "raw": turn.content,
        "prompt_tokens": turn.prompt_tokens,
        "completion_tokens": turn.completion_tokens,
        "done_reason": turn.done_reason,
        "context_limited": bool((turn.raw or {}).get("context_limited")),
        "model": getattr(turn, "model", "") or getattr(llm, "model_name", ""),
    }


def _input(prepared: dict, level: str) -> tuple[dict, list[dict], list[dict]]:
    base = {
        "incident_start": prepared["incident_start"],
        "incident_end": prepared["incident_end"],
    }
    if level == "B0":
        return base, [], []
    if level == "B1":
        return {**base, "fixed_summary": prepared["fixed_summary"]}, [], []
    exposed_events = expose_timeline(prepared["timeline"], limit=10)
    if level == "B2":
        return {**base, "timeline": exposed_events}, exposed_events, []
    exposed_rels = expose_relations(prepared["relations"], exposed_events, limit=8)
    return {**base, "timeline": exposed_events, "candidate_relations": exposed_rels}, exposed_events, exposed_rels


def _object(text: str, *, allow_salvage: bool = True) -> dict:
    raw = text or ""
    parsed = _json_dict(raw)
    if parsed.get("claims") is not None or parsed.get("abstain") is not None:
        return parsed
    claims = _salvage_claims(raw)
    if claims:
        if allow_salvage:
            return {"abstain": False, "claims": claims, "hypotheses": [], "json_truncated": True, "partial_output": True}
        return {"abstain": False, "claims": [], "salvaged_claims": claims, "hypotheses": [], "json_truncated": True, "partial_output": True}
    return parsed


def _json_dict(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        value = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _salvage_claims(raw: str) -> list[dict]:
    """Keep claim objects that closed before a length cutoff."""
    claims = []
    index = 0
    while index < len(raw):
        start = raw.find("{", index)
        if start < 0:
            break
        depth = 0
        closed = None
        for cursor in range(start, len(raw)):
            if raw[cursor] == "{":
                depth += 1
            elif raw[cursor] == "}":
                depth -= 1
                if depth == 0:
                    closed = cursor
                    break
        if closed is None:
            index = start + 1
            continue
        try:
            value = json.loads(raw[start:closed + 1])
        except json.JSONDecodeError:
            index = start + 1
            continue
        has_anchor = any(value.get(key) for key in ("fact_id", "edge_id", "statement")) or isinstance(value.get("evidence_ids"), list)
        if isinstance(value, dict) and has_anchor and "claims" not in value:
            claims.append(value)
        index = closed + 1
    return claims
