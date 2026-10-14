"""One completion over a prepared timeline. The model does not choose tools."""
from __future__ import annotations
import json

SYSTEM = """You explain one supplied time window from the JSON only.
Return one JSON object with keys abstain, hypotheses, and claims.
Each claim has statement, evidence_ids, entity, time, field, value, direction, relation_type, and claim_level.
claim_level is observed_fact, temporal_cooccurrence, supported_inference, unresolved, or disputed.
Use only evidence_ids present in the input. Time proximity is not a supported inference.
Do not state a cause. Do not name an attack class.
If the records are not enough, set abstain to true and leave claims empty.
"""

CLAIM_FORMAT = {
    "type": "object",
    "properties": {
        "abstain": {"type": "boolean"},
        "hypotheses": {"type": "array"},
        "claims": {"type": "array"},
    },
    "required": ["abstain", "claims"],
}


def explain(llm, prepared: dict, *, level: str, num_predict: int = 512, num_ctx: int = 8192, seed: int = 1) -> dict:
    body = _input(prepared, level)
    turn = llm.chat(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(body, default=str)}],
        tools=None, temperature=0, seed=seed, num_predict=num_predict, num_ctx=num_ctx,
        response_format=CLAIM_FORMAT,
    )
    parsed = _object(turn.content)
    claims = parsed.get("claims") if isinstance(parsed.get("claims"), list) else []
    hypotheses = parsed.get("hypotheses") if isinstance(parsed.get("hypotheses"), list) else []
    abstain = bool(parsed.get("abstain")) or not claims
    return {
        "level": level,
        "abstain": abstain and not claims,
        "hypotheses": hypotheses,
        "claims": [item for item in claims if isinstance(item, dict)],
        "raw": turn.content,
        "prompt_tokens": turn.prompt_tokens,
        "completion_tokens": turn.completion_tokens,
        "done_reason": turn.done_reason,
        "context_limited": bool((turn.raw or {}).get("context_limited")),
        "model": getattr(turn, "model", "") or getattr(llm, "model_name", ""),
    }


def _input(prepared: dict, level: str) -> dict:
    base = {
        "incident_start": prepared["incident_start"],
        "incident_end": prepared["incident_end"],
    }
    if level == "B0":
        return base
    if level == "B1":
        return {**base, "fixed_summary": prepared["fixed_summary"]}
    timeline = prepared["timeline"][:8]
    if level == "B2":
        return {**base, "timeline": timeline}
    relations = prepared["relations"][:6]
    return {**base, "timeline": timeline, "candidate_relations": relations}


def _object(text: str) -> dict:
    raw = text or ""
    parsed = _json_dict(raw)
    if parsed.get("claims") or parsed.get("abstain") is not None:
        return parsed
    claims = _salvage_claims(raw)
    if claims:
        return {"abstain": False, "claims": claims, "hypotheses": [], "json_truncated": True}
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
        if isinstance(value, dict) and value.get("statement") and isinstance(value.get("evidence_ids"), list):
            claims.append(value)
        index = closed + 1
    return claims
