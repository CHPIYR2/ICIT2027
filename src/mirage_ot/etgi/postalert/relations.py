"""Candidate relations from the timeline.

A shared TCP direction, IEC-104 frame, CA/IOA point, or device prefix is an
observed record link. Edge provenance is the lineage of `source_fact_id` and
`target_fact_id` only. A gap of at most two seconds with no other shared identifier stays
temporal co-occurrence. It is not a supported inference and not a cause.
Candidate kind (`candidate_level`) is kept separate from `verification_status`.
"""
from __future__ import annotations
from ..graph.temporal import TemporalEvidenceGraph

GAP = 2.0


def discover_relations(timeline: list[dict]) -> dict:
    graph = TemporalEvidenceGraph()
    nodes = {}
    for event in timeline:
        nodes[event["timeline_id"]] = graph.add_node(
            modality="electrical" if event["role"] == "electrical_change" else "network",
            entity=event["entity"], event_type=event["role"],
            start_time=event["time"], end_time=event["time_end"],
            description=event["observation"], evidence_ids=event["evidence_ids"],
            vantage=(event["source"]["vantages"] or [None])[0],
        )
    linked = set()
    _communications(graph, timeline, nodes, linked)
    _same_device(graph, timeline, nodes, linked)
    _shared_source(graph, timeline, nodes, linked)
    _same_frame(graph, timeline, nodes, linked)
    _cooccurrence(graph, timeline, nodes, linked)
    _disputes(graph, timeline, nodes)
    node_to_fact = {node["node_id"]: tid for tid, node in nodes.items()}
    for edge in graph.edges.values():
        edge["causal_status"] = "not_established"
        edge["source_fact_id"] = node_to_fact.get(edge["source"])
        edge["target_fact_id"] = node_to_fact.get(edge["target"])
    return {"graph": graph, "relations": [_public(edge) for edge in graph.edges.values()]}


def _communications(graph, timeline, nodes, linked) -> None:
    flows = [event for event in timeline if event["role"] == "communication"]
    for left in flows:
        for right in flows:
            if left["timeline_id"] >= right["timeline_id"]:
                continue
            if _reverse(left["entity"]) != right["entity"]:
                continue
            if set(left["source"]["vantages"]) and set(right["source"]["vantages"]) and not (
                    set(left["source"]["vantages"]) & set(right["source"]["vantages"])):
                continue
            edge = graph.add_edge(
                source=nodes[left["timeline_id"]]["node_id"], target=nodes[right["timeline_id"]]["node_id"],
                relation_type="communication", origin="observed", time_order="undirected",
                evidence_ids=[*left["evidence_ids"][:2], *right["evidence_ids"][:2]],
                rationale="Both directions of one TCP 5-tuple were observed.", built_by="record_link",
            )
            _mark(edge, "observed_fact", "supported", "Recorded TCP directions. Not a cause.")
            linked.add((left["timeline_id"], right["timeline_id"]))


def _same_device(graph, timeline, nodes, linked) -> None:
    electrical = [event for event in timeline if event["role"] == "electrical_change" and ":" in event["entity"]]
    by_element = {}
    for event in electrical:
        by_element.setdefault(event["entity"].split(":", 1)[0], []).append(event)
    for element, events in by_element.items():
        if len(events) < 2:
            continue
        left, right = events[0], events[1]
        edge = graph.add_edge(
            source=nodes[left["timeline_id"]]["node_id"], target=nodes[right["timeline_id"]]["node_id"],
            relation_type="same_device", origin="observed",
            evidence_ids=[left["evidence_ids"][0], right["evidence_ids"][0]],
            rationale=f"Both attributes belong to {element}. Not a cause.", built_by="record_link",
        )
        _mark(edge, "observed_fact", "supported", "Same device prefix. Not a cause.")
        linked.add((left["timeline_id"], right["timeline_id"]))


def _shared_source(graph, timeline, nodes, linked) -> None:
    electrical = {event["entity"]: event for event in timeline if event["role"] == "electrical_change"}
    for event in timeline:
        if event["role"] not in ("command", "electrical_report", "response"):
            continue
        other = electrical.get(event["entity"])
        if other is None:
            continue
        edge = graph.add_edge(
            source=nodes[event["timeline_id"]]["node_id"], target=nodes[other["timeline_id"]]["node_id"],
            relation_type="shared_source", origin="observed",
            evidence_ids=[event["evidence_ids"][0], other["evidence_ids"][0]],
            rationale="The IEC-104 point and the IPAL name are the same mapped point. One source, not two modalities.",
            built_by="record_link",
        )
        _mark(edge, "observed_fact", "supported", "One mapped point. Not a second modality and not a cause.")
        linked.add((event["timeline_id"], other["timeline_id"]))


def _same_frame(graph, timeline, nodes, linked) -> None:
    """Information objects carried by one IEC-104 frame share a source container."""
    points = [event for event in timeline if event["source"]["kind"] == "iec104_asdu" and event.get("lineage")]
    for index, left in enumerate(points):
        for right in points[index + 1:]:
            if _already(linked, left, right):
                continue
            shared = [item for item in left["lineage"] if item in set(right["lineage"])]
            if not shared:
                continue
            edge = graph.add_edge(
                source=nodes[left["timeline_id"]]["node_id"], target=nodes[right["timeline_id"]]["node_id"],
                relation_type="same_frame", origin="observed", evidence_ids=shared[:4],
                rationale="Both information objects were carried by the same IEC-104 frame. One source container, not independent evidence.",
                built_by="record_link",
            )
            _mark(edge, "observed_fact", "supported", "Same frame. Not independent and not a cause.")
            linked.add((left["timeline_id"], right["timeline_id"]))


def _cooccurrence(graph, timeline, nodes, linked) -> None:
    produced = 0
    ordered = sorted(timeline, key=lambda event: event["time"])
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            if produced >= 8:
                return
            gap = right["time"] - left["time_end"]
            if gap > GAP:
                break
            pair = tuple(sorted((left["timeline_id"], right["timeline_id"])))
            if pair in linked or (pair[1], pair[0]) in linked or pair in {(item, item) for item in pair}:
                continue
            if _already(linked, left, right):
                continue
            if _shared_identifier(left, right):
                level, status, note = (
                    "supported_inference", "supported",
                    "A shared device stem other than time is present. This is an inference, not a cause.",
                )
            else:
                level, status, note = (
                    "temporal_cooccurrence", "unresolved",
                    "The times fall within 2s. Time proximity is not a supported inference.",
                )
            edge = graph.add_edge(
                source=nodes[left["timeline_id"]]["node_id"], target=nodes[right["timeline_id"]]["node_id"],
                relation_type="temporal_cooccurrence" if level == "temporal_cooccurrence" else "temporal_association",
                origin="inferred", evidence_ids=[left["evidence_ids"][0], right["evidence_ids"][0]],
                rationale=note, built_by="timeline",
            )
            _mark(edge, level, status, note)
            produced += 1


def _disputes(graph, timeline, nodes) -> None:
    """Flag numeric disagreement on the same entity within 2 seconds."""
    for edge in graph.edges.values():
        if edge["relation_type"] != "shared_source":
            continue
        left = next((event for event in timeline if nodes[event["timeline_id"]]["node_id"] == edge["source"]), None)
        right = next((event for event in timeline if nodes[event["timeline_id"]]["node_id"] == edge["target"]), None)
        if left and right and _values_disagree(left, right):
            edge["claim_level"] = "disputed"
            edge["candidate_level"] = "shared_source"
            edge["status"] = "disputed"
            edge["verification_status"] = "disputed"
            edge["contradicting_evidence"] = list(edge["evidence_ids"][:2])
            edge["uncertainty_notes"].append("The IEC-104 value and the IPAL electrical value differ within the window.")


def _already(linked, left, right) -> bool:
    return (left["timeline_id"], right["timeline_id"]) in linked or (right["timeline_id"], left["timeline_id"]) in linked


def _shared_identifier(left, right) -> bool:
    """A device stem on both sides. A shared IP address is not enough."""
    if left.get("fingerprint") and left.get("fingerprint") == right.get("fingerprint"):
        return False
    if left.get("ca_ioa") and left.get("ca_ioa") == right.get("ca_ioa"):
        return False
    if set(left.get("lineage") or []) & set(right.get("lineage") or []):
        return False
    return _stem(left) is not None and _stem(left) == _stem(right) and left["entity"] != right["entity"]


def _stem(event: dict) -> str | None:
    entity = event.get("entity") or ""
    if ":" in entity and not entity.endswith("/TCP"):
        return entity.split(":", 1)[0]
    return None


def _values_disagree(left, right) -> bool:
    if not left.get("value_present") or not right.get("value_present"):
        return False
    if left.get("value") is None or right.get("value") is None:
        return False
    return abs(float(left["value"]) - float(right["value"])) > 1e-3


def _reverse(entity: str) -> str | None:
    if not entity or "->" not in entity or not entity.endswith("/TCP"):
        return None
    body = entity[: -len("/TCP")]
    left, right = body.split("->", 1)
    return f"{right}->{left}/TCP"


def _mark(edge, level: str, status: str, note: str) -> None:
    edge["candidate_level"] = level
    edge["claim_level"] = level
    edge["verification_status"] = status
    edge["status"] = status
    edge["causal_status"] = "not_established"
    edge["uncertainty_notes"].append(note)


def _public(edge: dict) -> dict:
    ids = list(edge.get("evidence_ids") or [])
    return {
        "edge_id": edge["edge_id"],
        "source_fact_id": edge.get("source_fact_id"),
        "target_fact_id": edge.get("target_fact_id"),
        "source_entity": edge["source_entity"],
        "target_entity": edge["target_entity"],
        "source_modality": edge["source_modality"],
        "target_modality": edge["target_modality"],
        "relation_type": edge["relation_type"],
        "candidate_level": edge.get("candidate_level"),
        "claim_level": edge.get("claim_level"),
        "verification_status": edge.get("verification_status"),
        "status": edge["status"],
        "causal_status": "not_established",
        "evidence_ids": ids[:4],
        "evidence_id_count": len(ids),
        "rationale": edge.get("rationale"),
    }
