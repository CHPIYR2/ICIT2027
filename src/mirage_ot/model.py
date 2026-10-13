"""Shared-encoder forecast model with optional sparse low-rank associations.

Edges are sigmoid gates on a low-rank query/key score plus a modality-block
bias. Gates are not row-normalized, so a row can stay near zero and cross-modal
blocks are not required to exist. No attack label enters the loss.
"""
from __future__ import annotations
import json
import math
import random
from pathlib import Path
import numpy as np
import torch
from torch import nn
from .features import Matrix, F

KIND_COUNT = 3  # network, measurement, configuration
KIND_NAMES = ('network', 'measurement', 'configuration')


def node_kind_id(node) -> int:
    if node.modality == 'network':
        return 0
    if node.context == 'CONFIGURATION':
        return 2
    return 1


class TemporalRelationModel(nn.Module):
    def __init__(self, hidden: int = 48, use_graph: bool = True,
                 association: str = 'sparse', rank: int = 8):
        super().__init__()
        if association not in ('sparse', 'softmax', 'none'):
            raise ValueError(f'Unknown association {association}')
        self.use_graph = use_graph and association != 'none'
        self.association = association if self.use_graph else 'none'
        self.hidden = hidden
        self.rank = rank
        self.encoder = nn.GRU(F + KIND_COUNT, hidden, batch_first=True)
        self.query = nn.Linear(hidden, rank, bias=False)
        self.key = nn.Linear(hidden, rank, bias=False)
        # Negative bias starts sparse. Each of the 3x3 blocks can stay closed.
        self.block_bias = nn.Parameter(torch.full((KIND_COUNT, KIND_COUNT), -4.0))
        self.predictor = nn.Sequential(nn.Linear(hidden * 2, hidden), nn.ReLU(),
                                       nn.Linear(hidden, F))
        self.reset_association(closed=True)

    def reset_association(self, *, closed: bool) -> None:
        nn.init.xavier_uniform_(self.query.weight)
        nn.init.xavier_uniform_(self.key.weight)
        self.block_bias.data.fill_(-4.0 if closed else 0.0)

    def freeze_association(self) -> None:
        self.query.requires_grad_(False)
        self.key.requires_grad_(False)
        self.block_bias.requires_grad_(False)

    def forward(self, x: torch.Tensor, kinds: torch.Tensor,
                source_permutation: torch.Tensor | None = None):
        batch, nodes, length, feat = x.shape
        if feat != F or len(kinds) != nodes:
            raise ValueError('Bad node/feature shape')
        one_hot = nn.functional.one_hot(kinds.long(), KIND_COUNT).to(x.dtype)
        encoded = torch.cat(
            [x, one_hot[None, :, None, :].expand(batch, nodes, length, KIND_COUNT)], dim=-1)
        _output, state = self.encoder(encoded.reshape(batch * nodes, length, F + KIND_COUNT))
        state = state[0].reshape(batch, nodes, self.hidden)
        if self.association == 'none' or nodes < 2:
            adjacency = state.new_zeros(batch, nodes, nodes)
            message = torch.zeros_like(state)
        else:
            scale = math.sqrt(self.rank)
            logits = self.query(state) @ self.key(state).transpose(-1, -2) / scale
            src = kinds.long()
            logits = logits + self.block_bias[src[:, None], src[None, :]]
            eye = torch.eye(nodes, dtype=torch.bool, device=x.device)
            if self.association == 'softmax':
                logits = logits.masked_fill(eye, -1e4)
                adjacency = logits.softmax(dim=-1)
            else:
                adjacency = torch.sigmoid(logits).masked_fill(eye, 0)
            if source_permutation is not None:
                adjacency = adjacency.index_select(-1, source_permutation).masked_fill(eye, 0)
            message = adjacency @ state
        prediction = self.predictor(torch.cat([state, message], -1))
        return prediction, adjacency


def _samples(features: np.ndarray, length: int):
    if features.shape[0] <= length:
        raise ValueError(f'Need at least {length+1} bins, got {len(features)}')
    return [(features[t-length:t], features[t]) for t in range(length, len(features))]


def kind_tensor(matrix: Matrix, device: str):
    return torch.tensor([node_kind_id(node) for node in matrix.nodes], device=device)


def device_name() -> str:
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _norm_fit(matrix: Matrix) -> dict:
    stats = {}
    for modality in ['network', 'physical']:
        idx = [i for i, node in enumerate(matrix.nodes) if node.modality == modality]
        if idx:
            sub = matrix.data[:, idx, :].reshape(-1, F)
            mean = sub.mean(axis=0).astype(np.float64)
            std = sub.std(axis=0).astype(np.float64)
        else:
            mean, std = np.zeros(F), np.ones(F)
        std = np.where(std < 1e-6, 1.0, std)
        stats[modality] = {'mean': mean.tolist(), 'std': std.tolist()}
    return stats


def normalize(matrix: Matrix, stats: dict) -> np.ndarray:
    result = matrix.data.copy()
    for i, node in enumerate(matrix.nodes):
        center = np.asarray(stats[node.modality]['mean'], dtype=np.float32)
        scale = np.asarray(stats[node.modality]['std'], dtype=np.float32)
        result[:, i, :] = (result[:, i, :] - center) / scale
    return np.clip(result, -15, 15)


def train_model(matrix: Matrix, *, epochs=8, length=12, hidden=48,
                lr=0.003, seed=20261014, use_graph=True, device=None,
                max_steps_per_epoch=256, association='sparse', rank=8,
                sparsity=1e-3, freeze_association=False
                ) -> tuple[TemporalRelationModel, dict]:
    set_seed(seed)
    device = device or device_name()
    chosen = 'none' if not use_graph else association
    scaler = _norm_fit(matrix)
    features = normalize(matrix, scaler)
    samples = _samples(features, length)
    kinds = kind_tensor(matrix, device)
    model = TemporalRelationModel(hidden=hidden, use_graph=use_graph,
                                  association=chosen, rank=rank).to(device)
    if freeze_association and model.association == 'sparse':
        model.reset_association(closed=False)
        model.freeze_association()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=lr)
    losses = []
    gate_means = []
    for epoch in range(epochs):
        model.train()
        indices = np.random.default_rng(seed + epoch).permutation(len(samples))[:max_steps_per_epoch]
        epoch_loss = []
        epoch_gates = []
        for idx in indices:
            window, target = samples[int(idx)]
            x = torch.from_numpy(window[None].transpose(0, 2, 1, 3).copy()).to(device)
            y = torch.from_numpy(target[None].copy()).to(device)
            optimizer.zero_grad()
            predicted, adjacency = model(x, kinds)
            loss = nn.functional.smooth_l1_loss(predicted, y)
            if model.association == 'sparse' and not freeze_association:
                loss = loss + sparsity * adjacency.mean()
            if not torch.isfinite(loss):
                raise RuntimeError('Nonfinite training loss')
            loss.backward()
            nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), 1.0)
            optimizer.step()
            epoch_loss.append(float(loss.detach().cpu()))
            epoch_gates.append(float(adjacency.detach().mean().cpu()))
        losses.append(float(np.mean(epoch_loss)))
        gate_means.append(float(np.mean(epoch_gates)) if epoch_gates else 0.0)
    metadata = {'seed': seed, 'epochs': epochs, 'length': length,
                'hidden': hidden, 'learning_rate': lr, 'use_graph': model.use_graph,
                'association': model.association, 'rank': rank, 'sparsity': sparsity,
                'freeze_association': freeze_association, 'kind_count': KIND_COUNT,
                'kind_names': list(KIND_NAMES), 'device': device,
                'train_bins': len(matrix.data), 'train_node_count': len(matrix.nodes),
                'normalization': scaler, 'training_losses': losses,
                'mean_gate_per_epoch': gate_means,
                'max_steps_per_epoch': max_steps_per_epoch,
                'train_window': [matrix.start,
                                 matrix.start + len(matrix.data) * matrix.bin_seconds]}
    return model, metadata


def save_checkpoint(model: TemporalRelationModel, metadata: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({'weights': model.state_dict(), 'metadata': metadata}, path)
    path.with_suffix('.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


def load_checkpoint(path: Path, *, device: str | None = None):
    device = device or device_name()
    stored = torch.load(path, map_location=device, weights_only=True)
    meta = stored['metadata']
    model = TemporalRelationModel(
        meta['hidden'], meta.get('use_graph', True),
        association=meta.get('association', 'sparse'),
        rank=meta.get('rank', 8)).to(device)
    model.load_state_dict(stored['weights'])
    model.eval()
    return model, meta


def _permutation(nodes: int, seed: int, device) -> torch.Tensor:
    order = np.random.default_rng(seed).permutation(nodes)
    return torch.tensor(order, device=device)


@torch.no_grad()
def infer_graph(model: TemporalRelationModel, matrix: Matrix, meta: dict, *,
                shuffle_seed: int | None = None):
    features = normalize(matrix, meta['normalization'])
    length = meta['length']
    if len(features) <= length:
        raise ValueError('Not enough time bins to infer graph')
    device = next(model.parameters()).device
    kinds = kind_tensor(matrix, str(device))
    perm = None if shuffle_seed is None else _permutation(len(matrix.nodes), shuffle_seed, device)
    x = torch.from_numpy(features[-length:][None].transpose(0, 2, 1, 3).copy()).to(device)
    _pred, adj = model(x, kinds, source_permutation=perm)
    return adj.cpu().numpy()[0], kinds.cpu().numpy()


@torch.no_grad()
def evaluate_forecast(model: TemporalRelationModel, matrix: Matrix, meta: dict,
                      *, max_samples: int | None = None, shuffle_seed: int | None = None):
    features = normalize(matrix, meta['normalization'])
    samples = _samples(features, meta['length'])
    if max_samples is not None:
        samples = samples[:max_samples]
    device = next(model.parameters()).device
    kinds = kind_tensor(matrix, str(device))
    perm = None if shuffle_seed is None else _permutation(len(matrix.nodes), shuffle_seed, device)
    model.eval()
    losses = []
    for window, target in samples:
        x = torch.from_numpy(window[None].transpose(0, 2, 1, 3).copy()).to(device)
        pred, _adj = model(x, kinds, source_permutation=perm)
        losses.append(float(np.mean(np.abs(pred.cpu().numpy()[0] - target))))
    return {'mae_normalized': float(np.mean(losses)), 'n_samples': len(losses),
            'shuffled_graph': shuffle_seed is not None,
            'important': 'Forecast MAE is NOT relation edge accuracy'}


def gate_summary(adjacency: np.ndarray, kinds: np.ndarray) -> dict:
    size = adjacency.shape[0]
    off = ~np.eye(size, dtype=bool)
    values = adjacency[off]
    blocks = {}
    names = {0: 'N', 1: 'M', 2: 'C'}
    for src in range(KIND_COUNT):
        for dst in range(KIND_COUNT):
            mask = off & (kinds[:, None] == src) & (kinds[None, :] == dst)
            if not mask.any():
                continue
            chosen = adjacency[mask]
            blocks[f'{names[src]}-{names[dst]}'] = {
                'edges': int(mask.sum()),
                'mean': float(chosen.mean()),
                'frac_gt_0.2': float((chosen > 0.2).mean()),
            }
    return {'offdiag_median': float(np.median(values)) if values.size else None,
            'offdiag_frac_gt_0.2': float((values > 0.2).mean()) if values.size else None,
            'blocks': blocks}
