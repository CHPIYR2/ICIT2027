"""Assessment of inferred temporal associations.

Record-level verification still decides whether a communication, shared frame,
shared IEC-104 report, or same-device pair is an observed fact. This module
is separate. A temporal association can be evidence-supported when each
endpoint has a matching non-hold record and the two times fall inside a
stated gap. That status is not a cause, and it is not a record link.
"""
from __future__ import annotations
from ..evidence.queries import EvidenceDB

ASSOCIATION_GAP_SECONDS = 2.0


def assess_inference(db: EvidenceDB, edge: dict, record: dict) -> dict:
    causal = "not_established"
    if record.get("direct_record_link") and record.get("status") == "supported":
        return _result("not_applicable", "observed_fact", causal,
                       ["This edge restates a record link. It is not an inferred cause."])
    if record.get("contradicting_evidence"):
        return _result("disputed", "unresolved_hypothesis", causal,
                       ["Cited rows disagree with the claimed association. This is not a cause."])
    rows = db.get(list(edge.get("evidence_ids") or []))["rows"]
    source_times = _times(rows, edge, "source")
    target_times = _times(rows, edge, "target")
    if not source_times or not target_times:
        return _result("unresolved", "unresolved_hypothesis", causal,
                       ["At least one endpoint has no matching non-hold evidence."])
    gap = abs(_median(source_times) - _median(target_times))
    order = edge.get("time_order") or "undirected"
    order_holds = True
    if order == "source_before_target":
        order_holds = _median(source_times) <= _median(target_times) + 1.0
    elif order == "target_before_source":
        order_holds = _median(target_times) <= _median(source_times) + 1.0
    if gap <= ASSOCIATION_GAP_SECONDS and order_holds:
        return _result(
            "evidence_supported", "supported_inference", causal,
            [f"Both endpoints have evidence {gap:.3f}s apart, inside {ASSOCIATION_GAP_SECONDS}s. "
             "This is an association, not a demonstrated cause."],
            observed_gap_seconds=gap,
        )
    return _result(
        "unresolved", "unresolved_hypothesis", causal,
        [f"The cited times are {gap:.3f}s apart or the claimed order does not hold. "
         "Sharing the incident window is not enough."],
        observed_gap_seconds=gap,
    )


def _result(inference_status: str, claim_level: str, causal: str, notes: list[str],
            observed_gap_seconds: float | None = None) -> dict:
    return {
        "inference_status": inference_status,
        "claim_level": claim_level,
        "causal_status": causal,
        "association_gap_seconds": ASSOCIATION_GAP_SECONDS,
        "observed_gap_seconds": observed_gap_seconds,
        "notes": notes,
    }


def _times(rows: list[dict], edge: dict, side: str) -> list[float]:
    entity = edge.get(f"{side}_entity") or ""
    modality = edge.get(f"{side}_modality")
    found = []
    for row in rows:
        if row.get("update_status") in ("hold", "initial"):
            continue
        same_entity = row["entity"] == entity or (row.get("ca_ioa") and row["ca_ioa"] == entity)
        same_modality = modality is None or row["modality"] == modality or same_entity
        if same_entity and same_modality:
            found.append(row["timestamp"])
    return found


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]
