"""Time-aware incident graph.

Edges keep every revision. Replacing a status appends history; it does not
discard the proposal that was revised.
"""
from __future__ import annotations
import time
from copy import deepcopy


class TemporalEvidenceGraph:
    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self.removed: dict[str, dict] = {}
        self._node_seq = 0
        self._edge_seq = 0

    def add_node(self, *, modality: str, entity: str, event_type: str, start_time: float,
                 end_time: float, description: str, evidence_ids: list[str],
                 vantage: str | None = None) -> dict:
        self._node_seq += 1
        node = {
            "node_id": f"N{self._node_seq:04d}",
            "modality": modality,
            "entity_id": entity,
            "event_type": event_type,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "vantage": vantage,
        }
        self.nodes[node["node_id"]] = node
        return node

    def add_edge(self, *, source: str, target: str, relation_type: str, origin: str,
                 evidence_ids: list[str], time_order: str = "undirected",
                 rationale: str = "", alternatives: list[str] | None = None,
                 built_by: str = "investigator") -> dict:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("Edge endpoints must already be nodes")
        if source == target:
            raise ValueError("An evidence edge needs two nodes")
        source_node = self.nodes[source]
        target_node = self.nodes[target]
        self._edge_seq += 1
        edge = {
            "edge_id": f"R{self._edge_seq:04d}",
            "source": source,
            "target": target,
            "source_entity": source_node["entity_id"],
            "source_modality": source_node["modality"],
            "target_entity": target_node["entity_id"],
            "target_modality": target_node["modality"],
            "relation_type": relation_type,
            "origin": origin,
            "status": "unresolved",
            "time_order": time_order,
            "directed": time_order != "undirected" or relation_type == "communication",
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "source_dependencies": [],
            "uncertainty_notes": [],
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "rationale": rationale,
            "alternatives": list(alternatives or []),
            "built_by": built_by,
            "model_status": None,
            "history": [],
        }
        self._record(edge, "relation_proposed", {"status": "unresolved", "relation_type": relation_type})
        self.edges[edge["edge_id"]] = edge
        return edge

    def revise(self, edge_id: str, *, status: str | None = None, relation_type: str | None = None,
               supporting=None, contradicting=None, dependencies=None, notes=None,
               reason: str) -> dict:
        edge = self.edges[edge_id]
        before = {"status": edge["status"], "relation_type": edge["relation_type"]}
        if status is not None:
            edge["status"] = status
        if relation_type is not None:
            edge["relation_type"] = relation_type
        if supporting is not None:
            edge["supporting_evidence"] = list(supporting)
        if contradicting is not None:
            edge["contradicting_evidence"] = list(contradicting)
        if dependencies is not None:
            edge["source_dependencies"] = list(dependencies)
        if notes:
            edge["uncertainty_notes"] = list(dict.fromkeys([*edge["uncertainty_notes"], *notes]))
        self._record(edge, "relation_revised", {"before": before, "reason": reason,
                                                 "status": edge["status"], "relation_type": edge["relation_type"]})
        return edge

    def remove(self, edge_id: str, *, reason: str) -> dict:
        edge = self.edges.pop(edge_id)
        edge["status"] = "removed"
        self._record(edge, "relation_removed", {"reason": reason})
        self.removed[edge_id] = edge
        return edge

    def annotate(self, edge_id: str, **fields) -> dict:
        edge = self.edges[edge_id]
        edge.update(fields)
        self._record(edge, "verification_recorded", {"fields": sorted(fields)})
        return edge

    def snapshot(self) -> dict:
        return {
            "nodes": list(self.nodes.values()),
            "edges": list(self.edges.values()),
            "removed_edges": list(self.removed.values()),
        }

    def find_node(self, entity: str, modality: str) -> dict | None:
        for node in self.nodes.values():
            if node["entity_id"] == entity and node["modality"] == modality:
                return node
        return None

    @staticmethod
    def _record(edge: dict, operation: str, detail: dict) -> None:
        edge["history"].append({"operation": operation, "unix_time": time.time(), "detail": deepcopy(detail)})
