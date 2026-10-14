"""Subgoal working memory.

HiAgent (Hu et al., ACL 2025) keeps action-observation pairs only for the
current subgoal and replaces a finished subgoal with a summary. CoEx
(Kim and Hwang, Findings of EMNLP 2025) separates the planner, which names
the subgoal, from the actor, which carries it out, and updates an explicit
belief state after the subgoal. The summary here is a rendering of the stored
tool results plus the status the model reported. It is not a second model call.
"""
from __future__ import annotations

PLANNER_TOOLS = (
    "set_subgoal", "propose_relations", "stop_investigation", "retrieve_subgoal_trajectory",
)
CONTROL_TOOLS = PLANNER_TOOLS + ("complete_subgoal",)
SUBGOAL_STATUSES = ("achieved", "not_achieved", "insufficient_evidence")


class Subgoal:
    def __init__(self, text: str, index: int):
        self.text = text[:500]
        self.index = index
        self.status = "active"
        self.steps: list[dict] = []
        self.messages: list[dict] = []
        self.summary = ""

    def public(self) -> dict:
        return {
            "index": self.index,
            "subgoal": self.text,
            "status": self.status,
            "summary": self.summary,
            "step_count": len(self.steps),
        }


class Belief:
    def __init__(self):
        self.known_facts: list[dict] = []
        self.unknowns: list[str] = []
        self.contradictory_evidence: list[dict] = []
        self.verification_results: list[dict] = []

    def as_dict(self) -> dict:
        return {
            "known_facts": self.known_facts[-8:],
            "unknowns": self.unknowns[-8:],
            "contradictory_evidence": self.contradictory_evidence[-8:],
            "verification_results": self.verification_results[-6:],
        }


def accept_statements(db, items) -> tuple[list[dict], list[dict]]:
    """Keep a model statement only when it cites an evidence id that exists."""
    accepted, rejected = [], []
    for item in items or []:
        if isinstance(item, str):
            item = {"statement": item, "evidence_ids": []}
        if not isinstance(item, dict):
            continue
        statement = str(item.get("statement") or "")[:300]
        ids = [str(value) for value in item.get("evidence_ids") or [] if str(value).startswith("EV-")]
        rows = db.get(ids)["rows"] if ids else []
        present = [row["evidence_id"] for row in rows]
        if not statement or not present:
            rejected.append({"statement": statement, "evidence_ids": ids})
            continue
        accepted.append({"statement": statement, "evidence_ids": present})
    return accepted, rejected


def render_summary(subgoal: Subgoal) -> str:
    parts = [f"status={subgoal.status}"]
    for step in subgoal.steps:
        new_ids = ",".join(step.get("new_evidence_ids") or []) or "none"
        parts.append(f"{step.get('tool')} new={new_ids} duplicate={bool(step.get('duplicate'))}")
    return "; ".join(parts)[:800]
