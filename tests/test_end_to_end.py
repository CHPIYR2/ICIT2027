import json
import torch
import numpy as np
from mirage_ot.fixture import generate
from mirage_ot.types import Observation
from mirage_ot.features import build_matrix, save_matrix, load_matrix
from mirage_ot.model import (train_model, save_checkpoint, load_checkpoint,
                             infer_graph, evaluate_forecast)
from mirage_ot.graph import graph_dict, save_graph


def test_learning_and_graph(tmp_path):
    torch.set_num_threads(1)
    path = tmp_path / 'synthetic.jsonl'
    generate(path, bins=24)
    obs = [Observation(**json.loads(line)) for line in path.read_text().splitlines()]
    mat = build_matrix(obs)
    assert set(n.modality for n in mat.nodes) == {'physical','network'}
    assert mat.data.shape[2] == 8
    data_path = tmp_path / 'features.npz'
    save_matrix(mat, data_path)
    mat = load_matrix(data_path)
    model, meta = train_model(mat, epochs=1, length=6, hidden=12,
                              device='cpu', max_steps_per_epoch=3)
    ckpt = tmp_path / 'model.pt'
    save_checkpoint(model, meta, ckpt)
    restored, meta2 = load_checkpoint(ckpt, device='cpu')
    graph, _ = infer_graph(restored, mat, meta2)
    assert graph.shape == (len(mat.nodes), len(mat.nodes))
    bundle, nx_graph = graph_dict(mat, graph, top_k=len(mat.nodes)-1)
    assert all(e['claim_level'] == 'statistical_predictive_dependency' for e in bundle['edges'])
    assert set(e['type'] for e in bundle['edges']) >= {'N-N','P-P','N-P','P-N'}
    save_graph(bundle, nx_graph, tmp_path/'graphs')
    assert (tmp_path/'graphs'/'graph.json').exists()
    assert 'NOT causal' in (tmp_path/'graphs'/'graph.html').read_text()
    report = evaluate_forecast(restored, mat, meta2)
    assert np.isfinite(report['mae_normalized'])


def test_large_graph_export_does_not_require_scipy(tmp_path):
    import networkx as nx
    graph = nx.DiGraph()
    nodes = []
    for i in range(520):
        modality = 'network' if i < 40 else 'physical'
        node_id = f'n{i}'
        graph.add_node(node_id, modality=modality, entity=f'e{i}')
        nodes.append({'id': node_id, 'modality': modality, 'entity': f'e{i}',
                      'description': f'e{i}', 'source_ids': ['src']})
    graph.add_edge('n0', 'n1', weight=0.2)
    bundle = {'nodes': nodes, 'edges': [{
        'source': 'n0', 'target': 'n1', 'type': 'N-N', 'score': 0.2,
        'evidence_ids': ['src'], 'claim_level': 'statistical_predictive_dependency'}]}
    save_graph(bundle, graph, tmp_path / 'graphs')
    page = (tmp_path / 'graphs' / 'graph.html').read_text()
    assert 'NOT causal' in page
    assert 'n519' in page


def test_no_attack_rules():
    from mirage_ot import model, graph, features
    assert hasattr(model, 'TemporalRelationModel')
    assert not hasattr(model, 'attack_type_from_count')
