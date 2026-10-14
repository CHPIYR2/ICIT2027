"""JSON, GraphML, timeline, and offline HTML exports."""
from __future__ import annotations
import json
from pathlib import Path
import networkx as nx
from .temporal import TemporalEvidenceGraph


def write_graph(graph: TemporalEvidenceGraph, directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    payload = graph.snapshot()
    (directory / "graph.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    timeline = sorted(payload["nodes"], key=lambda node: (node["start_time"], node["node_id"]))
    (directory / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    nx_graph = nx.DiGraph()
    for node in payload["nodes"]:
        nx_graph.add_node(node["node_id"], **{key: _text(value) for key, value in node.items()})
    for edge in payload["edges"]:
        nx_graph.add_edge(edge["source"], edge["target"], **{key: _text(value) for key, value in edge.items()
                                                              if key not in ("history", "alternatives")})
    nx.write_graphml(nx_graph, directory / "graph.graphml")
    (directory / "graph.html").write_text(_html(payload), encoding="utf-8")
    return {"graph_json": str(directory / "graph.json"), "graphml": str(directory / "graph.graphml"),
            "html": str(directory / "graph.html"), "timeline": str(directory / "timeline.json")}


def _text(value) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _html(payload: dict) -> str:
    data = json.dumps(payload).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>ETGI evidence graph</title>
<style>
body {{ font: 14px/1.4 sans-serif; margin: 0; color: #1b1b1b; }}
main {{ display: grid; grid-template-columns: 1fr 360px; min-height: 100vh; }}
svg {{ width: 100%; height: 100vh; background: #f7f5f2; }}
aside {{ border-left: 1px solid #ccc; padding: 12px; overflow: auto; }}
.supported {{ stroke: #1b7f4a; }} .disputed {{ stroke: #a33b2b; }}
.unresolved {{ stroke: #8a6a12; }} .removed {{ stroke: #888; }}
text {{ font-size: 11px; }}
</style></head><body>
<main><svg id="view"></svg><aside><h1>Evidence graph</h1>
<p>Arrows on communication edges are packet direction. Other edges are associations, not causes.</p>
<pre id="detail">Select a node or edge.</pre></aside></main>
<script>
const data = {data};
const nodes = data.nodes;
const edges = data.edges;
const svg = document.getElementById("view");
const detail = document.getElementById("detail");
const groups = {{network: [], electrical: []}};
nodes.forEach(node => (groups[node.modality] || (groups[node.modality] = [])).push(node));
const pos = {{}};
function place(list, x) {{
  list.forEach((node, i) => {{ pos[node.node_id] = [x, 40 + i * 46]; }});
}}
place(groups.network || [], 80);
place(groups.electrical || [], 520);
const ns = "http://www.w3.org/2000/svg";
edges.forEach(edge => {{
  const a = pos[edge.source], b = pos[edge.target];
  if (!a || !b) return;
  const line = document.createElementNS(ns, "line");
  line.setAttribute("x1", a[0]); line.setAttribute("y1", a[1]);
  line.setAttribute("x2", b[0]); line.setAttribute("y2", b[1]);
  line.setAttribute("class", edge.status);
  line.setAttribute("stroke-width", "2");
  line.onclick = () => detail.textContent = JSON.stringify(edge, null, 2);
  svg.appendChild(line);
}});
nodes.forEach(node => {{
  const [x, y] = pos[node.node_id];
  const circle = document.createElementNS(ns, "circle");
  circle.setAttribute("cx", x); circle.setAttribute("cy", y); circle.setAttribute("r", 8);
  circle.setAttribute("fill", node.modality === "network" ? "#2457a5" : "#9a5b16");
  circle.onclick = () => detail.textContent = JSON.stringify(node, null, 2);
  svg.appendChild(circle);
  const label = document.createElementNS(ns, "text");
  label.setAttribute("x", x + 12); label.setAttribute("y", y + 4);
  label.textContent = node.node_id + " " + node.entity_id.slice(0, 42);
  svg.appendChild(label);
}});
</script></body></html>
"""
