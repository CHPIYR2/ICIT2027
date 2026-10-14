"""Record-level graph candidates.

These edges restate facts already in the indexed records: a bidirectional
TCP conversation, the same frame at two vantages, an IEC-104 point joined to
the IPAL name of that CA/IOA, or two attributes of one device. They are
candidates until verification. They are not attack rules and they are not
causal claims.
"""
from __future__ import annotations
from .temporal import TemporalEvidenceGraph
from ..evidence.queries import EvidenceDB


def build_observed(graph: TemporalEvidenceGraph, db: EvidenceDB, *, start: float, end: float,
                   enabled: bool = True) -> dict:
    """Add observation nodes. Add record-link edges only when `enabled`."""
    flows = db.flow_summary(start=start, end=end, limit=15)["rows"]
    electrical = db.search(modality="electrical", kind="electrical_update", start=start, end=end, limit=50)
    iec = db.search(kind="iec104_asdu", start=start, end=end, limit=80)
    shared = db.multi_vantage(start=start, end=end, limit=15)
    stats = {"flow_nodes": 0, "electrical_nodes": 0, "iec104_nodes": 0, "candidate_edges": 0,
             "truncated_flows": flows and db.flow_summary(start=start, end=end, limit=1)["total"] > 15}
    flow_nodes = {}
    for flow in flows:
        node = graph.add_node(
            modality="network", entity=flow["entity"], event_type="tcp_flow",
            start_time=flow["start_time"], end_time=flow["end_time"],
            description=f"TCP flow at {flow['vantage']} with {flow['packets']} packets",
            evidence_ids=flow["evidence_ids"], vantage=flow["vantage"],
        )
        flow_nodes[(flow["entity"], flow["vantage"])] = node
        stats["flow_nodes"] += 1
    electrical_nodes = {}
    for row in _first_by_entity(electrical["rows"]):
        node = graph.add_node(
            modality="electrical", entity=row["entity"], event_type="electrical_update",
            start_time=row["timestamp"], end_time=row["timestamp"],
            description="New network-reported electrical value. Not simulator ground truth.",
            evidence_ids=[row["evidence_id"]], vantage=row.get("vantage"),
        )
        electrical_nodes[row["entity"]] = (node, row)
        stats["electrical_nodes"] += 1
    iec_groups: dict[tuple, dict] = {}
    for row in iec["rows"]:
        key = (row.get("vantage"), row.get("ca_ioa") or row["entity"], row.get("protocol_class"))
        group = iec_groups.setdefault(key, {"rows": [], "entity": row["entity"]})
        group["rows"].append(row)
    iec_nodes = {}
    for key, group in list(iec_groups.items())[:40]:
        rows = group["rows"]
        node = graph.add_node(
            modality="network", entity=group["entity"], event_type="iec104_observation",
            start_time=min(row["timestamp"] for row in rows),
            end_time=max(row["timestamp"] for row in rows),
            description=f"IEC-104 {key[2]} ASDU {key[1]} at {key[0]}",
            evidence_ids=[row["evidence_id"] for row in rows[:12]], vantage=key[0],
        )
        iec_nodes[key] = (node, rows)
        stats["iec104_nodes"] += 1
    if not enabled:
        stats["record_edges"] = "not_built"
        return stats
    for (entity, vantage), node in flow_nodes.items():
        reverse = _reverse_flow(entity)
        other = flow_nodes.get((reverse, vantage)) if reverse else None
        if other is None or node["node_id"] >= other["node_id"]:
            continue
        graph.add_edge(
            source=node["node_id"], target=other["node_id"], relation_type="communication",
            origin="observed", time_order="undirected",
            evidence_ids=[*node["evidence_ids"], *other["evidence_ids"]],
            rationale="Both directions of one TCP 5-tuple were captured at this vantage.",
            built_by="record_link",
        )
        stats["candidate_edges"] += 1
    for item in shared["rows"]:
        members = db.get(item["evidence_ids"][:4])["rows"]
        used = []
        for member in members:
            found = flow_nodes.get((member["entity"], member["vantage"]))
            if found and found["node_id"] not in used:
                used.append(found["node_id"])
        if len(used) >= 2:
            graph.add_edge(
                source=used[0], target=used[1], relation_type="same_frame", origin="observed",
                evidence_ids=item["evidence_ids"][:8],
                rationale="These vantages captured one Ethernet frame hash.",
                built_by="record_link",
            )
            stats["candidate_edges"] += 1
    for key, (node, rows) in iec_nodes.items():
        entity = node["entity_id"]
        electrical_node = electrical_nodes.get(entity)
        if electrical_node is None:
            nearby = db.search(entity=entity, modality="electrical", kind="electrical_update",
                               start=node["start_time"] - 2, end=node["end_time"] + 2, limit=1)
            if not nearby["rows"]:
                continue
            electrical_node = electrical_nodes.get(entity)
            if electrical_node is None:
                created = graph.add_node(
                    modality="electrical", entity=entity, event_type="electrical_update",
                    start_time=nearby["rows"][0]["timestamp"], end_time=nearby["rows"][0]["timestamp"],
                    description="New network-reported electrical value. Not simulator ground truth.",
                    evidence_ids=[nearby["rows"][0]["evidence_id"]],
                )
                electrical_node = (created, nearby["rows"][0])
                electrical_nodes[entity] = electrical_node
                stats["electrical_nodes"] += 1
        graph.add_edge(
            source=node["node_id"], target=electrical_node[0]["node_id"],
            relation_type="shared_source", origin="observed", time_order="undirected",
            evidence_ids=[rows[0]["evidence_id"], electrical_node[1]["evidence_id"]],
            rationale="The IEC-104 CA/IOA and the IPAL state name are the same point map entry.",
            built_by="record_link",
        )
        stats["candidate_edges"] += 1
    by_element: dict[str, list] = {}
    for entity, (node, row) in electrical_nodes.items():
        element = entity.split(":", 1)[0]
        by_element.setdefault(element, []).append((node, row))
    device_edges = 0
    for element, pairs in by_element.items():
        if len(pairs) < 2 or device_edges >= 20:
            continue
        left, right = pairs[0], pairs[1]
        graph.add_edge(
            source=left[0]["node_id"], target=right[0]["node_id"], relation_type="same_device",
            origin="observed", evidence_ids=[left[1]["evidence_id"], right[1]["evidence_id"]],
            rationale=f"Both attributes belong to {element}. This is not a causal claim.",
            built_by="record_link",
        )
        device_edges += 1
        stats["candidate_edges"] += 1
    return stats


def _first_by_entity(rows: list[dict]) -> list[dict]:
    chosen = {}
    for row in rows:
        chosen.setdefault(row["entity"], row)
    return list(chosen.values())[:20]


def _reverse_flow(entity: str) -> str | None:
    if not entity.endswith("/TCP") or "->" not in entity:
        return None
    body = entity[: -len("/TCP")]
    left, right = body.split("->", 1)
    return f"{right}->{left}/TCP"
