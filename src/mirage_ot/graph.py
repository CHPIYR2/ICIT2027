"""Graph export with traceable observations and explicitly UNCALIBRATED edges."""
import html
import json
import math
from pathlib import Path
import networkx as nx
import numpy as np
from .features import Matrix


def _attention_diagnostic(adjacency: np.ndarray, top_k: int) -> dict:
    """Describe whether displayed edges are just a slice of a flat softmax."""
    n = adjacency.shape[0]
    if n < 2:
        return {'attention_is_near_uniform': False, 'reason': 'fewer than 2 nodes'}
    clipped = np.clip(adjacency, 1e-12, 1.0)
    entropy = -(clipped * np.log(clipped)).sum(axis=1)
    uniform = math.log(n - 1)
    top = np.sort(adjacency, axis=1)[:, -top_k:].sum(axis=1)
    ratio = float(np.median(entropy) / uniform)
    return {
        'attention_entropy_median': float(np.median(entropy)),
        'uniform_entropy': float(uniform),
        'entropy_over_uniform': ratio,
        'display_topk_mass_median': float(np.median(top)),
        'attention_is_near_uniform': ratio > 0.98,
        'interpretation': (
            'Row-softmax attention. Near-uniform rows mean the displayed top-k '
            'edges are not a sparse relation estimate.'
        ),
    }


def graph_dict(matrix: Matrix, adjacency: np.ndarray, *, top_k: int = 2, model_metadata=None):
    n = len(matrix.nodes)
    if adjacency.shape != (n, n):
        raise ValueError('Adjacency dimension mismatch')
    graph = nx.DiGraph()
    for nd in matrix.nodes:
        graph.add_node(nd.id, modality=nd.modality, entity=nd.entity)
    diagnostic = _attention_diagnostic(adjacency, top_k)
    edges = []
    for i, node in enumerate(matrix.nodes):
        ranked = sorted((j for j in range(n) if i != j),
                        key=lambda j: (-float(adjacency[i, j]), matrix.nodes[j].id))
        for j in ranked[:top_k]:
            other = matrix.nodes[j]
            w = float(adjacency[i, j])
            if not math.isfinite(w):
                raise ValueError('Nonfinite edge score')
            graph.add_edge(node.id, other.id, weight=w)
            edges.append({'source': node.id, 'target': other.id,
                          'type': node.modality[0].upper() + '-' + other.modality[0].upper(),
                          'score': w, 'score_semantics': 'row-normalized learned attention, NOT probability',
                          'evidence_ids': [*node.source_ids[:3], *other.source_ids[:3]],
                          'claim_level': 'statistical_predictive_dependency'})
    result = {'schema_version': 1,
              'title': 'MIRAGE-OT Learned Incident Association Graph',
              'nodes': [n.to_json() for n in matrix.nodes],
              'edges': edges,
              'metadata': {'window_start': matrix.start,
                           'window_end': matrix.start + len(matrix.data) * matrix.bin_seconds,
                           'bin_seconds': matrix.bin_seconds,
                           'top_k_for_display': top_k,
                           'node_counts': matrix.metadata['node_counts'],
                           'relation_claim': 'Predictive statistical dependence only: no proven event causation',
                           'association_scores_are_calibrated': False,
                           'graph_provenance': 'model learned on observables; representative sample of raw source IDs in nodes',
                           'physical_trust': 'network-reported telemetry, NOT physical.zip ground truth',
                           'attention_diagnostic': diagnostic,
                           'model_metadata': model_metadata or {}}}
    return result, graph


def save_graph(bundle: dict, networkx_graph: nx.DiGraph, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'graph.json').write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding='utf-8')
    nx.write_graphml(networkx_graph, output / 'graph.graphml')
    _html(bundle, networkx_graph, output / 'graph.html')


def _layout(graph) -> dict:
    """Screen positions without SciPy.

    NetworkX's spring layout switches to a SciPy sparse solver at 500 nodes.
    Smaller graphs keep the seeded force layout. Larger graphs use a
    modality-grouped circle so export still runs with numpy/networkx only.
    """
    count = graph.number_of_nodes()
    if count == 0:
        return {}
    if count < 500:
        pos = nx.spring_layout(graph, seed=23, weight=None, method='force')
        return {key: [300 + float(value[0]) * 260, 300 + float(value[1]) * 260]
                for key, value in pos.items()}
    groups = {'network': [], 'physical': []}
    for node, attrs in graph.nodes(data=True):
        groups.get(attrs.get('modality'), groups['network']).append(node)
    positions = {}

    def place(group, cx, cy, radius):
        ordered = sorted(group)
        total = len(ordered)
        for index, node in enumerate(ordered):
            angle = (2 * math.pi * index / total) - math.pi / 2
            positions[node] = [cx + radius * math.cos(angle), cy + radius * math.sin(angle)]

    place(groups['network'], 170, 320, 130)
    place(groups['physical'], 430, 320, 200)
    return positions


def _html(bundle, graph, path):
    # All JS/CSS inline. Standalone offline HTML; no CDN.
    positions = _layout(graph)
    data_json = json.dumps({'nodes': bundle['nodes'], 'edges': bundle['edges'],
                            'positions': positions}, ensure_ascii=False).replace('<', '\\u003c')
    diagnostic = (bundle.get('metadata') or {}).get('attention_diagnostic') or {}
    uniform_note = ''
    if diagnostic.get('attention_is_near_uniform'):
        uniform_note = (
            '<p><strong>Near-uniform attention.</strong> The drawn edges are only the '
            'largest slices of an almost flat softmax. They are not identified relations.</p>'
        )
    page = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>MIRAGE-OT Learned Incident Graph</title><style>
body{font:14px system-ui;background:#0e1522;color:#dbe6f4;margin:0}
header{padding:14px 24px;background:#162334}h1{font-size:20px;margin:0}
p{color:#9cb1c5}main{display:flex;gap:14px;padding:12px}
svg{background:#101b2a;border:1px solid #415269;flex:1;max-height:80vh}
aside{width:290px;background:#1b2a3c;padding:12px;overflow:auto;max-height:80vh}
text{pointer-events:none;fill:white;font:12px system-ui} .edge{opacity:.6}
button{background:#2f445b;color:white;border:0;border-radius:4px;padding:6px;cursor:pointer}
small{color:#a6bdce}
</style></head><body>
<header><h1>MIRAGE-OT — learned event associations</h1>
<p>Solid edges = model statistical predictive dependencies, NOT causal pathways or calibrated probabilities.
Physical nodes are network-reported IEC telemetry, not independent simulator truth.</p>
__UNIFORM__</header>
<main><svg id="scene" width="800" height="660" viewBox="0 0 650 650"></svg>
<aside><h3>Evidence</h3><div id="details">Click a node or edge.</div><p>
<button onclick="toggle('N-N')">N–N</button>
<button onclick="toggle('N-P')">N–P</button>
<button onclick="toggle('P-P')">P–P</button></p><small>Click a relationship to view its raw evidence identifiers.</small></aside></main>
<script>
const D = __DATA__;
const xmlns='http://www.w3.org/2000/svg';
const svg=document.getElementById('scene');
let visible={'N-N':true,'P-P':true,'N-P':true};
function element(tag,attrs){const n=document.createElementNS(xmlns,tag);for(const k in attrs)n.setAttribute(k,attrs[k]);return n;}
function show(obj){document.getElementById('details').textContent=JSON.stringify(obj,null,2);document.getElementById('details').style.whiteSpace='pre-wrap';}
function toggle(key){visible[key]=!visible[key];draw();}
function draw(){svg.innerHTML='';
 for(const e of D.edges){const key=[...new Set(e.type.split('-'))].sort().join('-');
 if(!visible[key]) continue;const a=D.positions[e.source],b=D.positions[e.target];if(!a||!b)continue;
 const line=element('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#9dacbf','stroke-width':Math.max(0.9,e.score*7),class:'edge'});
 line.addEventListener('click',()=>show(e));svg.appendChild(line);}
 for(const n of D.nodes){const p=D.positions[n.id];if(!p)continue;
 const g=element('g',{});const c=element('circle',{cx:p[0],cy:p[1],r:10,fill:n.modality==='network'?'#369fc8':'#dcab4d'});
 const txt=element('text',{x:p[0]+12,y:p[1]+4});txt.textContent=n.id;g.appendChild(c);g.appendChild(txt);
 g.addEventListener('click',()=>show(n));svg.appendChild(g);}}
draw();
</script></body></html>'''
    path.write_text(page.replace('__DATA__', data_json).replace('__UNIFORM__', uniform_note),
                    encoding='utf-8')
