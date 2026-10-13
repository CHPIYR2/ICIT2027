"""Eventization into time-bin × node × feature tensors without attack labels.

No attack-specific thresholds, no cross-modal edges hardcoded, no ground truth read.
"""
from __future__ import annotations
import collections
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from .types import Observation, Node

F = 8
FEATURE_NAMES = {
    'network': ['log_count', 'log_total_bytes', 'log_arp', 'log_tcp',
                'log_udp', 'log_payload', 'log_iec104_port', 'log_tcp_syn'],
    'physical': ['mean', 'min', 'max', 'std', 'delta',
                 'log_sample_count', 'present', 'abs_delta'],
}


@dataclass
class Matrix:
    data: np.ndarray  # T, N, F
    nodes: list[Node]
    start: float
    bin_seconds: float
    metadata: dict


def _node_id(modality: str, entity: str) -> str:
    return modality[0].upper() + '-' + hashlib.sha256(entity.encode()).hexdigest()[:12]


def build_matrix(observations: list[Observation], *, bin_seconds: float = 10.0,
                 max_network_nodes: int = 30, max_physical_nodes: int = 30,
                 start: float | None = None, end: float | None = None) -> Matrix:
    if not observations:
        raise ValueError('Cannot build matrix from empty observations')
    if bin_seconds <= 0:
        raise ValueError('bin_seconds must be positive')
    beginning = math.floor((min(x.timestamp for x in observations) if start is None else start) / bin_seconds) * bin_seconds
    ending = max(x.timestamp for x in observations) + bin_seconds if end is None else end
    nbin = max(1, math.ceil((ending - beginning) / bin_seconds))
    if nbin > 500_000:
        raise ValueError('Unbounded time grid; restrict --start / --end')
    observed: dict[tuple[str, str], list[Observation]] = collections.defaultdict(list)
    for o in observations:
        if o.modality not in ('network', 'physical'):
            raise ValueError(f'Invalid modality {o.modality}')
        if beginning <= o.timestamp < ending:
            observed[(o.modality, o.entity)].append(o)
    channels = []
    for modality, capacity in [('network', max_network_nodes), ('physical', max_physical_nodes)]:
        candidates = [(k, seq) for k, seq in observed.items() if k[0] == modality]
        candidates.sort(key=lambda v: (-len(v[1]), v[0][1]))
        channels.extend(candidates[:capacity])
    if not channels:
        raise ValueError('No observations in requested window')
    data = np.zeros((nbin, len(channels), F), dtype=np.float32)
    nodes = []
    for j, ((modality, entity), seq) in enumerate(channels):
        buckets: dict[int, list[Observation]] = collections.defaultdict(list)
        for o in seq:
            t = int((o.timestamp - beginning) // bin_seconds)
            if 0 <= t < nbin:
                buckets[t].append(o)
        # Distinct provenance: keep a bounded, explicit sample and its count.
        source_ids = list(dict.fromkeys(o.source_id for o in seq))
        sample = source_ids[:12] + (source_ids[-4:] if len(source_ids) > 16 else [])
        nodes.append(Node(_node_id(modality, entity), modality, entity, entity,
                          tuple(dict.fromkeys(sample))))
        previous = None
        for t, obs in sorted(buckets.items()):
            if modality == 'physical':
                vals = np.array([o.value for o in obs], dtype=np.float64)
                mean = float(np.mean(vals))
                delta = mean - previous if previous is not None else 0.0
                previous = mean
                data[t, j] = [mean, float(np.min(vals)), float(np.max(vals)),
                              float(np.std(vals)), delta, math.log1p(len(vals)), 1.0, abs(delta)]
            else:
                count = len(obs)
                total_bytes = sum(o.value for o in obs if o.kind != 'arp_packet')
                arp = sum(o.kind == 'arp_packet' for o in obs)
                tcp = sum(o.kind == 'tcp_packet' for o in obs)
                udp = sum(o.kind == 'udp_packet' for o in obs)
                payload = sum((o.attrs or {}).get('payload_bytes', 0) for o in obs)
                iec = sum((o.attrs or {}).get('iec104_candidate', 0) for o in obs)
                syn = sum(bool((o.attrs or {}).get('tcp_flags', 0) & 2) for o in obs)
                data[t, j] = np.log1p([count, total_bytes, arp, tcp, udp, payload, iec, syn])
    return Matrix(data, nodes, beginning, bin_seconds,
                  {'schema_version': 1, 'observation_count': len(observations),
                   'node_counts': dict(collections.Counter(n.modality for n in nodes)),
                   'feature_names': FEATURE_NAMES,
                   'dropped_channel_counts': {
                       m: max(0, sum(k[0] == m for k in observed) - cap)
                       for m, cap in [('network', max_network_nodes),
                                      ('physical', max_physical_nodes)]},
                   'source_counts_by_node': {
                       _node_id(*k): len(set(o.source_id for o in seq))
                       for k, seq in channels},
                   'note': 'physical features are network-reported, not simulator ground truth'})


def save_matrix(matrix: Matrix, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, data=matrix.data)
    path.with_suffix('.json').write_text(json.dumps({
        'start': matrix.start, 'bin_seconds': matrix.bin_seconds,
        'nodes': [n.to_json() for n in matrix.nodes], 'metadata': matrix.metadata},
        indent=2, ensure_ascii=False), encoding='utf-8')


def load_matrix(path: Path) -> Matrix:
    with np.load(path, allow_pickle=False) as arr:
        data = arr['data'].astype(np.float32)
    meta = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    nodes = [Node(v['id'], v['modality'], v['entity'], v['description'],
                  tuple(v['source_ids'])) for v in meta['nodes']]
    if data.ndim != 3 or data.shape[1] != len(nodes) or data.shape[2] != F:
        raise ValueError(f'Invalid matrix schema in {path}')
    return Matrix(data, nodes, meta['start'], meta['bin_seconds'], meta['metadata'])
