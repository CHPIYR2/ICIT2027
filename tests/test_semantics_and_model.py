import io
import json
import torch
from mirage_ot.features import build_matrix
from mirage_ot.ipal import iter_state
from mirage_ot.leakage import assert_disjoint
from mirage_ot.model import TemporalRelationModel, train_model, KIND_COUNT
from mirage_ot.study import run_study
from mirage_ot.transcribe import parse_rule_names, transcriber_command, compare_messages_to_state
from mirage_ot.types import Observation


def _physical(t, entity, value, source, context='MEASUREMENT'):
    return Observation(t, 'physical', entity, 'observed_telemetry', value, source,
                       {'trust': 'network-reported', 'ipal_context': context})


def test_malicious_field_is_not_an_observation():
    raw = json.dumps({'timestamp': 10, 'malicious': True,
                      'state': {'bus.0:voltage': 1.2, 'malicious': 1}}).encode()
    audit = {}
    rows = list(iter_state(io.BytesIO(raw), source='train.state', audit=audit))
    assert [row.entity for row in rows] == ['bus.0:voltage']
    assert audit['malicious_true'] == 1
    assert all('malicious' not in (row.attrs or {}) for row in rows)


def test_equal_aliases_collapse_and_conflicts_remain():
    rows = [
        _physical(0, 'switch.8:closed', 1, 'keep', 'CONFIGURATION'),
        _physical(0, 'switch.8:is_closed', 1, 'alias', 'MEASUREMENT'),
        _physical(0, 'load.0:connected', 1, 'c', 'CONFIGURATION'),
        _physical(0, 'load.0:is_connected', 0, 'd', 'MEASUREMENT'),
    ]
    matrix = build_matrix(rows, bin_seconds=10, start=0, end=10)
    entities = {node.entity for node in matrix.nodes}
    assert 'switch.8:is_closed' not in entities
    assert 'switch.8:closed' in entities and 'load.0:connected' in entities
    assert 'load.0:is_connected' in entities
    closed = next(node for node in matrix.nodes if node.entity == 'switch.8:closed')
    assert closed.context == 'CONFIGURATION'
    assert any(item['alias'] == 'switch.8:is_closed' for item in matrix.metadata['collapsed_aliases'])
    assert matrix.metadata['alias_disagreements']


def test_evaluator_attr_is_rejected():
    bad = Observation(0, 'physical', 'bus.0:voltage', 'observed_telemetry', 1, 's',
                      {'malicious': True})
    try:
        build_matrix([bad], bin_seconds=10, start=0, end=10)
    except ValueError as exc:
        assert 'Evaluator-only' in str(exc)
    else:
        raise AssertionError('evaluator field was accepted')


def test_sparse_gates_are_not_a_simplex():
    torch.manual_seed(0)
    model = TemporalRelationModel(hidden=8, association='sparse', rank=4)
    kinds = torch.tensor([0, 1, 2, 1])
    _pred, adj = model(torch.zeros(1, 4, 5, 8), kinds)
    assert adj.shape == (1, 4, 4)
    assert torch.count_nonzero(torch.diagonal(adj[0])) == 0
    assert float(adj.detach().sum()) < 1.5
    assert model.block_bias.shape == (KIND_COUNT, KIND_COUNT)


def test_overlap_is_rejected_and_tiny_study_runs():
    def series(start):
        return [_physical(start + i, 'bus.0:voltage', 1.0 + i / 100, f'p{start}-{i}')
                for i in range(0, 80, 10)] + [
            Observation(start + i, 'network', '10.0.0.1:1->10.0.0.2:2404/TCP', 'tcp_packet',
                        20, f'n{start}-{i}', {'payload_bytes': 1, 'iec104_candidate': 1, 'tcp_flags': 16})
            for i in range(0, 80, 10)]
    train = build_matrix(series(0), bin_seconds=10, start=0, end=80)
    later = build_matrix(series(100), bin_seconds=10, start=100, end=180)
    try:
        assert_disjoint(train, train)
    except ValueError:
        pass
    else:
        raise AssertionError('overlapping windows were accepted')
    report = run_study(train, later, seeds=[0], epochs=1, hidden=8, rank=4, window=4,
                       max_steps=2, subsets=('both',), device='cpu')
    assert report['isolation']['disjoint']
    assert {row['variant'] for row in report['rows']} == {
        'no-graph', 'sparse', 'random-graph', 'shuffled-graph'}
    assert 'edge accuracy' not in report['predictive_claim'].lower() or 'not' in report['predictive_claim'].lower()


def test_rule_map_and_transcriber_command_exclude_labels():
    rules = parse_rule_names('{"var": ["101.10010"],"name": "bus.0:voltage"}')
    assert rules['101.10010'] == 'bus.0:voltage'
    argv = transcriber_command(executable='ipal-transcriber', pcap=__import__('pathlib').Path('slice.pcap'),
                               output=__import__('pathlib').Path('out.json'))
    assert '--malicious' not in argv and 'events.json' not in argv
    compared = compare_messages_to_state(
        [{'timestamp': 10.2, 'activity': 'inform', 'type': 'I-13', 'malicious': None,
          'data': {'101.10010': 1.25}}],
        rules, [(11.0, {'bus.0:voltage': 1.25})])
    assert compared['matched_points'] == 1
    assert compared['activities']['inform'] == 1
