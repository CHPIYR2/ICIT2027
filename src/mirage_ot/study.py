"""Small, consistent forecast comparison. Not an attack-detection benchmark."""
from __future__ import annotations
import collections
from .features import Matrix
from .leakage import assert_disjoint
from .model import (train_model, evaluate_forecast, infer_graph, gate_summary)


def select_entities(matrix: Matrix, entities: list[str]) -> Matrix:
    index = {node.entity: i for i, node in enumerate(matrix.nodes)}
    missing = [entity for entity in entities if entity not in index]
    if missing:
        raise ValueError(f'Matrix is missing {len(missing)} train entities, e.g. {missing[:3]}')
    chosen = [index[entity] for entity in entities]
    nodes = [matrix.nodes[i] for i in chosen]
    meta = dict(matrix.metadata)
    meta['node_counts'] = dict(collections.Counter(node.modality for node in nodes))
    meta['aligned_entity_count'] = len(entities)
    return Matrix(matrix.data[:, chosen, :], nodes, matrix.start, matrix.bin_seconds, meta)


def _entities(matrix: Matrix, subset: str) -> list[str]:
    if subset == 'network':
        modalities = {'network'}
    elif subset == 'physical':
        modalities = {'physical'}
    elif subset == 'both':
        modalities = {'network', 'physical'}
    else:
        raise ValueError(subset)
    return [node.entity for node in matrix.nodes if node.modality in modalities]


def varying_entities(matrix: Matrix, min_std: float) -> list[str]:
    """Channels whose train features actually move. Initial-state holds stay out."""
    kept = []
    for index, node in enumerate(matrix.nodes):
        if float(matrix.data[:, index, :].std()) > min_std:
            kept.append(node.entity)
    return kept


def run_study(train: Matrix, evaluation: Matrix, *, seeds: list[int], epochs: int = 8,
              hidden: int = 32, rank: int = 8, window: int = 12, max_steps: int = 32,
              sparsity: float = 1e-3, device: str = 'cpu',
              subsets: tuple[str, ...] = ('network', 'physical', 'both'),
              min_std: float | None = None) -> dict:
    """Fit no-graph, sparse, and frozen-random graphs on train; score eval only."""
    isolation = assert_disjoint(train, evaluation)
    active = set(varying_entities(train, min_std)) if min_std is not None else None
    rows = []
    for subset in subsets:
        entities = _entities(train, subset)
        if active is not None:
            entities = [entity for entity in entities if entity in active]
        if len(entities) < 2:
            continue
        train_sub = select_entities(train, entities)
        eval_sub = select_entities(evaluation, entities)
        assert_disjoint(train_sub, eval_sub)
        for seed in seeds:
            common = dict(epochs=epochs, length=window, hidden=hidden, rank=rank,
                          max_steps_per_epoch=max_steps, sparsity=sparsity,
                          device=device, seed=seed)
            no_graph, no_meta = train_model(train_sub, use_graph=False, **common)
            sparse, sparse_meta = train_model(train_sub, use_graph=True, association='sparse',
                                              freeze_association=False, **common)
            random_model, _random_meta = train_model(
                train_sub, use_graph=True, association='sparse', freeze_association=True, **common)
            specs = (
                ('no-graph', no_graph, no_meta, None),
                ('sparse', sparse, sparse_meta, None),
                ('random-graph', random_model, sparse_meta, None),
                ('shuffled-graph', sparse, sparse_meta, seed + 1009),
            )
            for name, model, meta, shuffle in specs:
                # Random-graph must be scored with its own normalization.
                if name == 'random-graph':
                    meta = _random_meta
                score = evaluate_forecast(model, eval_sub, meta, shuffle_seed=shuffle)
                adjacency, kinds = infer_graph(model, eval_sub, meta, shuffle_seed=shuffle)
                summary = gate_summary(adjacency, kinds)
                rows.append({'subset': subset, 'seed': seed, 'variant': name,
                             'mae_normalized': score['mae_normalized'],
                             'n_samples': score['n_samples'],
                             'train_nodes': len(train_sub.nodes),
                             'final_train_loss': meta['training_losses'][-1],
                             'gates': summary})
    paired = []
    for subset in subsets:
        for seed in seeds:
            got = {row['variant']: row for row in rows
                   if row['subset'] == subset and row['seed'] == seed}
            if 'sparse' in got and 'no-graph' in got:
                paired.append({
                    'subset': subset, 'seed': seed,
                    'sparse_minus_nograph': got['sparse']['mae_normalized'] - got['no-graph']['mae_normalized'],
                    'random_minus_nograph': got['random-graph']['mae_normalized'] - got['no-graph']['mae_normalized'],
                    'shuffled_minus_sparse': got['shuffled-graph']['mae_normalized'] - got['sparse']['mae_normalized'],
                })
    both = [item['sparse_minus_nograph'] for item in paired if item['subset'] == 'both']
    if not both:
        claim = 'No both-modality comparison was run.'
    elif all(delta < -0.01 for delta in both):
        claim = ('Sparse gates lowered forecast MAE versus no-graph on every seed '
                 'of this window. This is a predictive contribution, not edge accuracy.')
    else:
        claim = ('Sparse gates did not show a consistent forecast gain over no-graph '
                 'on this unseen window. Displayed edges are not identified event relations.')
    return {'isolation': isolation, 'min_std': min_std, 'rows': rows, 'paired': paired,
            'predictive_claim': claim,
            'not_edge_accuracy': True}
