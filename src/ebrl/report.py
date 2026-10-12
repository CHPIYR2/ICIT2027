"""Render an investigation report only from admitted ledger rows."""
from __future__ import annotations

FORBIDDEN_UNLESS_CAUSAL = (
    "caused the",
    "causal effect",
    "physical completion is established",
    "was executed",
    "command executed",
    "compromised",
    "attacker",
    "attributed to an adversary",
)


def render_report(bundle: dict, rows: list[dict]) -> dict:
    statements = []
    for row in rows:
        if not row.get("row_valid"):
            statements.append({
                "candidate_id": row.get("candidate_id"),
                "text": "Ledger row failed validation and is not a relation finding.",
                "evidence_ids": [],
            })
            continue
        disposition = row["published_disposition"]
        level = row["published_level"]
        flags = row["published_flags"]
        evidence_ids = (
            list(row.get("network_evidence_ids") or [])
            + list(row.get("process_evidence_ids") or [])
            + list(row.get("mapping_evidence_ids") or [])
            + list(row.get("support_evidence_ids") or [])
        )
        if disposition == "L" and level == "R1":
            text = (
                f"Temporal co-occurrence is supported for candidate {row['candidate_id']}. "
                "This does not establish execution, physical completion, or causation."
            )
        elif disposition == "L" and level == "R2":
            text = (
                f"A bounded association is supported for candidate {row['candidate_id']}. "
                "This does not establish execution, physical completion, or causation."
            )
        elif disposition == "L" and level == "R3":
            text = (
                f"An operational-response record supports execution wording for candidate {row['candidate_id']}. "
                "Physical completion and causation are not established."
            )
        elif disposition == "L" and level == "R4" and flags.get("causal"):
            text = (
                f"Independent action-effect provenance supports a causal wording for candidate {row['candidate_id']}."
            )
        elif disposition == "N":
            text = (
                f"A supported non-link is recorded for candidate {row['candidate_id']} "
                f"because {row['reason_code']}."
            )
        else:
            text = (
                f"Evidence is insufficient for candidate {row['candidate_id']} "
                f"({row['reason_code']}). No link or non-link is published."
            )
        if not flags.get("causal"):
            lowered = text.lower()
            for phrase in FORBIDDEN_UNLESS_CAUSAL:
                if phrase in lowered:
                    raise ValueError(f"Report exceeded the ledger wording: {phrase}")
        statements.append({
            "candidate_id": row["candidate_id"],
            "text": text,
            "evidence_ids": evidence_ids,
            "disposition": disposition,
            "level": level,
        })
    return {
        "event_id": bundle["event_id"],
        "statement_count": len(statements),
        "statements": statements,
        "renderer": "ebrl.report.v1",
    }
