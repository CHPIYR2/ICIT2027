"""Structured memory of an investigation.

The model is shown this digest, not the raw rows from every earlier query.
A repeated query is not sent to the database again.
"""
from __future__ import annotations


class InvestigationMemory:
    def __init__(self):
        self.queries: list[dict] = []
        self.cards: dict[str, dict] = {}
        self.by_signature: dict[str, dict] = {}

    def record(self, *, signature: str, tool: str, arguments: dict, goal: str,
               summary: dict, evidence_ids: list[str], new_evidence_ids: list[str]) -> None:
        entry = {
            "tool": tool,
            "arguments": _brief(arguments),
            "goal": (goal or "")[:300],
            "duplicate": False,
            "evidence_ids": list(evidence_ids),
            "new_evidence_ids": list(new_evidence_ids),
            "summary": summary,
        }
        self.queries.append(entry)
        self.by_signature[signature] = entry

    def previous(self, signature: str) -> dict | None:
        return self.by_signature.get(signature)

    def add_cards(self, rows: list[dict]) -> None:
        for row in rows:
            evidence_id = row.get("evidence_id")
            if not evidence_id or evidence_id in self.cards:
                continue
            self.cards[evidence_id] = {
                "evidence_id": evidence_id,
                "entity": row.get("entity"),
                "kind": row.get("kind"),
                "modality": row.get("modality"),
                "timestamp": row.get("timestamp"),
                "ca_ioa": row.get("ca_ioa"),
            }

    def digest(self, *, unresolved: list[str], candidates: list[dict]) -> dict:
        recent = list(self.cards.values())[-12:]
        return {
            "completed_queries": [
                {key: item[key] for key in ("tool", "arguments", "goal", "duplicate", "new_evidence_ids")}
                | {"evidence_id_count": len(item["evidence_ids"])}
                for item in self.queries[-8:]
            ],
            "known_evidence": recent,
            "known_evidence_count": len(self.cards),
            "unresolved_questions": unresolved[-6:],
            "candidate_relations": candidates[-6:],
        }

    def as_dict(self) -> dict:
        return {"queries": self.queries, "cards": self.cards}


def _brief(arguments: dict) -> dict:
    kept = {}
    for key in ("start", "end", "entity", "ip", "ca", "ioa", "vantage", "limit", "offset",
                "evidence_ids", "start_a", "end_a", "start_b", "end_b"):
        if key in arguments and arguments[key] not in (None, "", []):
            value = arguments[key]
            kept[key] = value[:8] if isinstance(value, list) else value
    return kept
