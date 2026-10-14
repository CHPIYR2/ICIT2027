"""Support, contradiction, and source-dependence checks.

A relation is supported only when the stored records contain the claimed
link. Two values moving in the same window are not enough. Rows that share a
frame hash, or an IEC-104 point and the IPAL state of that same point, are
one source rather than two independent confirmations.
"""
from __future__ import annotations
from ..evidence.queries import EvidenceDB

_LINEAGE = {"communication", "same_frame", "shared_source", "same_device"}


def verify_edge(db: EvidenceDB, edge: dict, *, contradiction_search: bool = True,
                source_dependency: bool = True) -> dict:
    cited = list(dict.fromkeys(edge.get("evidence_ids") or []))
    loaded = db.get(cited)
    rows = loaded["rows"]
    found = {row["evidence_id"]: row for row in rows}
    missing = [item for item in cited if item not in found and item not in set(loaded.get("hidden_evidence_ids") or [])]
    hidden = list(loaded.get("hidden_evidence_ids") or [])
    source = _node(edge, "source")
    target = _node(edge, "target")
    supporting = []
    attribution_errors = []
    for evidence_id in cited:
        row = found.get(evidence_id)
        if row is None:
            continue
        if _matches(row, source) or _matches(row, target):
            supporting.append(row)
        else:
            attribution_errors.append(evidence_id)
    notes = []
    if missing:
        notes.append("Cited evidence ids are not in the database: " + ", ".join(missing))
    if hidden:
        notes.append("Cited evidence ids are hidden from this view: " + ", ".join(hidden))
    if attribution_errors:
        notes.append("Cited rows that match neither endpoint were not counted as support.")
    contradictions = []
    if contradiction_search:
        contradictions.extend(_value_disagreements(supporting))
        contradictions.extend(_hold_used_as_change(edge, supporting))
        contradictions.extend(_time_order(edge, supporting, source, target))
        notes.append("Contradiction search queried value disagreement, hold-as-new citations, and timestamp order.")
    else:
        notes.append("Contradiction search was disabled for this run.")
    dependencies = _dependencies(supporting) if source_dependency else [
        {"evidence_ids": [row["evidence_id"]], "reason": "dependency_audit_disabled"} for row in supporting
    ]
    if not source_dependency:
        notes.append("Source-dependency audit was disabled. Each cited row was counted separately.")
    independent = [group for group in dependencies if not _group_is_only_hold(group, supporting)]
    link, recommended = _record_link(edge, supporting, dependencies, source_dependency)
    if contradictions:
        status = "disputed"
    elif link and independent:
        status = "supported"
    else:
        status = "unresolved"
        if edge.get("relation_type") == "temporal_association" and not link:
            notes.append("Co-occurrence in the incident window is not a supported association.")
    if recommended and recommended != edge.get("relation_type"):
        notes.append(
            f"The records support {recommended} rather than {edge.get('relation_type')}. "
            "A shared IEC-104 report is one source, not independent multimodal confirmation."
        )
        if not supporting:
            notes.append("No cited row matches the endpoints.")
    return {
        "status": status,
        "supporting_evidence": [row["evidence_id"] for row in supporting],
        "contradicting_evidence": [item["evidence_id"] for item in contradictions],
        "contradiction_details": contradictions,
        "source_dependencies": dependencies,
        "independent_groups": len(independent),
        "direct_record_link": link,
        "recommended_relation_type": recommended,
        "contradiction_searched": contradiction_search,
        "source_dependency_checked": source_dependency,
        "attribution_errors": attribution_errors,
        "missing_evidence_ids": missing,
        "notes": notes,
    }


def apply_assessment(graph, edge_id: str, assessment: dict, *, revise: bool) -> str:
    """Write the assessment. Revision changes the published status; otherwise it is only logged."""
    edge = graph.edges[edge_id]
    edge["contradiction_searched"] = assessment["contradiction_searched"]
    edge["direct_record_link"] = assessment["direct_record_link"]
    if not revise:
        graph.annotate(
            edge_id, unapplied_assessment=assessment,
            uncertainty_notes=list(dict.fromkeys([*edge["uncertainty_notes"], *assessment["notes"]])),
        )
        return edge["status"]
    if edge.get("origin") == "inferred" and not assessment["supporting_evidence"]:
        graph.remove(edge_id, reason="Inferred relation cited no evidence that matches its endpoints.")
        return "removed"
    relation_type = edge["relation_type"]
    if assessment["direct_record_link"] and assessment["recommended_relation_type"]:
        relation_type = assessment["recommended_relation_type"]
    graph.revise(
        edge_id, status=assessment["status"], relation_type=relation_type,
        supporting=assessment["supporting_evidence"], contradicting=assessment["contradicting_evidence"],
        dependencies=assessment["source_dependencies"], notes=assessment["notes"],
        reason="Programmatic evidence assessment.",
    )
    return assessment["status"]


def _node(edge: dict, side: str) -> dict:
    return {
        "entity": edge.get(f"{side}_entity"),
        "modality": edge.get(f"{side}_modality"),
        "node_id": edge.get(side),
    }


def _matches(row: dict, node: dict) -> bool:
    entity = node.get("entity") or ""
    if not entity:
        return False
    if row["entity"] == entity:
        return True
    if entity in (row.get("ca_ioa") or ""):
        return True
    for ip in (row.get("src_ip"), row.get("dst_ip")):
        if ip and ip in entity:
            return True
    return False


def _value_disagreements(rows: list[dict]) -> list[dict]:
    found = []
    for index, left in enumerate(rows):
        if not left.get("value_present"):
            continue
        if left["kind"] not in ("electrical_update", "electrical_initial", "electrical_hold_summary", "iec104_asdu"):
            continue
        for right in rows[index + 1:]:
            if right["kind"] != left["kind"] or not right.get("value_present"):
                continue
            if left["entity"] != right["entity"] or left.get("ca_ioa") != right.get("ca_ioa"):
                continue
            if abs(left["timestamp"] - right["timestamp"]) > 1.0:
                continue
            scale = max(1.0, abs(left["value"]), abs(right["value"]))
            if abs(left["value"] - right["value"]) > 1e-3 * scale:
                found.append({
                    "evidence_id": right["evidence_id"],
                    "reason": "value_disagreement",
                    "other_evidence_id": left["evidence_id"],
                })
    return found


def _hold_used_as_change(edge: dict, rows: list[dict]) -> list[dict]:
    if edge.get("relation_type") not in ("temporal_association", "shared_source"):
        return []
    found = []
    for row in rows:
        if row["modality"] == "electrical" and row.get("update_status") in ("hold", "initial"):
            found.append({"evidence_id": row["evidence_id"], "reason": "hold_or_initial_cited_as_change"})
    return found


def _time_order(edge: dict, rows: list[dict], source: dict, target: dict) -> list[dict]:
    order = edge.get("time_order") or "undirected"
    if order == "undirected":
        return []
    left = [row["timestamp"] for row in rows if _matches(row, source)]
    right = [row["timestamp"] for row in rows if _matches(row, target)]
    if not left or not right:
        return []
    left_m = sorted(left)[len(left) // 2]
    right_m = sorted(right)[len(right) // 2]
    violated = (order == "source_before_target" and left_m > right_m + 1.0) or (
        order == "target_before_source" and right_m > left_m + 1.0
    )
    if not violated:
        return []
    return [{"evidence_id": rows[0]["evidence_id"], "reason": "temporal_order",
             "source_median": left_m, "target_median": right_m}]


def _dependencies(rows: list[dict]) -> list[dict]:
    groups: list[dict] = []

    def place(row, reason, key):
        for group in groups:
            if key is not None and group.get("key") == key:
                group["evidence_ids"].append(row["evidence_id"])
                return
        groups.append({"key": key, "evidence_ids": [row["evidence_id"]], "reason": reason})

    for row in rows:
        fingerprint = row.get("fingerprint")
        if fingerprint:
            place(row, "same_frame_hash", ("frame", fingerprint))
        else:
            place(row, "separate_row", ("id", row["evidence_id"]))
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if _same_point_report(left, right):
                _merge(groups, left["evidence_id"], right["evidence_id"], "same_ca_ioa_report")
    for group in groups:
        group.pop("key", None)
        group["evidence_ids"] = list(dict.fromkeys(group["evidence_ids"]))
    return groups


def _same_point_report(left: dict, right: dict) -> bool:
    pair = {left["modality"], right["modality"]}
    kinds = {left["kind"], right["kind"]}
    if pair != {"network", "electrical"} and "iec104_asdu" not in kinds:
        return False
    if not left.get("ca_ioa") or left.get("ca_ioa") != right.get("ca_ioa"):
        if left["entity"] != right["entity"]:
            return False
    if abs(left["timestamp"] - right["timestamp"]) > 2.0:
        return False
    if left.get("value_present") and right.get("value_present"):
        scale = max(1.0, abs(left["value"]), abs(right["value"]))
        return abs(left["value"] - right["value"]) <= 1e-3 * scale
    return True


def _merge(groups: list[dict], left_id: str, right_id: str, reason: str) -> None:
    left = next(group for group in groups if left_id in group["evidence_ids"])
    right = next(group for group in groups if right_id in group["evidence_ids"])
    if left is right:
        return
    left["evidence_ids"].extend(right["evidence_ids"])
    left["reason"] = reason
    groups.remove(right)


def _group_is_only_hold(group: dict, rows: list[dict]) -> bool:
    by_id = {row["evidence_id"]: row for row in rows}
    members = [by_id[item] for item in group["evidence_ids"] if item in by_id]
    return bool(members) and all(row.get("update_status") in ("hold", "initial") for row in members)


def _record_link(edge: dict, rows: list[dict], groups: list[dict], dependency: bool) -> tuple[bool, str | None]:
    relation = edge.get("relation_type")
    if relation == "communication" and _bidirectional(rows):
        return True, "communication"
    if relation == "same_frame" and any(len(group["evidence_ids"]) > 1 and group.get("reason") == "same_frame_hash"
                                        for group in groups):
        return True, "same_frame"
    shared = any(group.get("reason") == "same_ca_ioa_report" or (
        len(group["evidence_ids"]) > 1 and _modalities(group, rows) == {"network", "electrical"}
    ) for group in groups)
    if relation == "shared_source" and shared:
        return True, "shared_source"
    if relation == "same_device" and _same_element(rows):
        return True, "same_device"
    if relation == "temporal_association":
        if shared and dependency:
            return True, "shared_source"
        return False, None
    if relation in _LINEAGE:
        return False, None
    return False, None


def _bidirectional(rows: list[dict]) -> bool:
    flows = [row["entity"] for row in rows if row["kind"] == "tcp_packet" or str(row["entity"]).endswith("/TCP")]
    for entity in flows:
        reverse = _reverse(entity)
        if reverse and reverse in flows:
            return True
    return False


def _reverse(entity: str) -> str | None:
    if "->" not in entity:
        return None
    body = entity[: -len("/TCP")] if entity.endswith("/TCP") else entity
    if "->" not in body:
        return None
    left, right = body.split("->", 1)
    suffix = "/TCP" if entity.endswith("/TCP") else ""
    return f"{right}->{left}{suffix}"


def _modalities(group: dict, rows: list[dict]) -> set[str]:
    by_id = {row["evidence_id"]: row for row in rows}
    return {by_id[item]["modality"] for item in group["evidence_ids"] if item in by_id}


def _same_element(rows: list[dict]) -> bool:
    elements = {row["entity"].split(":", 1)[0] for row in rows if row["modality"] == "electrical" and ":" in row["entity"]}
    return len(elements) == 1 and len(rows) >= 2
