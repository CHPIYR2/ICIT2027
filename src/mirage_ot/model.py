"""Small, shared-encoder temporal relation model.

Learn adjacency from context and optimize it through future-feature prediction;
NO attack-specific rule or event label is used in learning.
"""
from __future__ import annotations
import copy
import json
import math
import random
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import torch
from torch import nn
from .features import Matrix, F


class TemporalRelationModel(nn.Module):
    def __init__(self, hidden: int = 48, use_graph: bool = True):
        super().__init__()
        self.use_graph = use_graph
        self.hidden = hidden
        self.encoder = nn.GRU(F + 2, hidden, batch_first=True)
        self.query = nn.Linear(hidden, hidden, bias=False)
        self.key = nn.Linear(hidden, hidden, bias=False)
        self.predictor = nn.Sequential(nn.Linear(hidden * 2, hidden), nn.ReLU(),
                                       nn.Linear(hidden, F))

    def forward(self, x: torch.Tensor, kinds: torch.Tensor):
        # x: [batch,node,window,feature], kinds: [node] with 0=network,1=physical
        b, n, length, feat = x.shape
        if feat != F or len(kinds) != n:
            raise ValueError('Bad node/feature shape')
        one_hot = nn.functional.one_hot(kinds.long(), 2).to(x.dtype)
        z = torch.cat([x, one_hot[None, :, None, :].expand(b, n, length, 2)], dim=-1)
        _, state = self.encoder(z.reshape(b*n, length, F + 2))
        state = state[0].reshape(b, n, self.hidden)
        logits = self.query(state) @ self.key(state).transpose(-1, -2) / math.sqrt(self.hidden)
        if n > 1:
            logits = logits.masked_fill(torch.eye(n, dtype=torch.bool, device=x.device)[None], -1e4)
            adjacency = logits.softmax(dim=-1)
        else:
            adjacency = torch.zeros_like(logits)
        message = adjacency @ state if self.use_graph else torch.zeros_like(state)
        out = self.predictor(torch.cat([state, message], -1))
        return out, adjacency


def _samples(features: np.ndarray, length: int):
    if features.shape[0] <= length:
        raise ValueError(f'Need at least {length+1} bins, got {len(features)}')
    return [(features[t-length:t], features[t]) for t in range(length, len(features))]


def kind_tensor(matrix: Matrix, device: str):
    return torch.tensor([int(n.modality == 'physical') for n in matrix.nodes], device=device)


def device_name() -> str:
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _norm_fit(matrix: Matrix) -> dict:
    # Modality-specific, feature-specific global statistics from TRAIN ONLY.
    stats = {}
    for modality in ['network', 'physical']:
        idx = [i for i, n in enumerate(matrix.nodes) if n.modality == modality]
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
    for i, n in enumerate(matrix.nodes):
        center = np.asarray(stats[n.modality]['mean'], dtype=np.float32)
        scale = np.asarray(stats[n.modality]['std'], dtype=np.float32)
        result[:, i, :] = (result[:, i, :] - center) / scale
    return np.clip(result, -15, 15)  # numerical robustness, not an attack rule


def train_model(matrix: Matrix, *, epochs=8, length=12, hidden=48,
                lr=0.003, seed=20261014, use_graph=True, device=None,
                max_steps_per_epoch=256) -> tuple[TemporalRelationModel, dict]:
    set_seed(seed)
    device = device or device_name()
    scaler = _norm_fit(matrix)
    features = normalize(matrix, scaler)
    samples = _samples(features, length)
    kinds = kind_tensor(matrix, device)
    model = TemporalRelationModel(hidden=hidden, use_graph=use_graph).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    losses = []
    for epoch in range(epochs):
        model.train()
        indices = np.random.default_rng(seed + epoch).permutation(len(samples))[:max_steps_per_epoch]
        epoch_loss = []
        for idx in indices:
            window, target = samples[int(idx)]
            x = torch.from_numpy(window[None].transpose(0,2,1,3).copy()).to(device)
            y = torch.from_numpy(target[None].copy()).to(device)
            optimizer.zero_grad()
            predicted, _ = model(x, kinds)
            loss = nn.functional.smooth_l1_loss(predicted, y)
            if not torch.isfinite(loss):
                raise RuntimeError('Nonfinite training loss')
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss.append(float(loss.detach().cpu()))
        losses.append(float(np.mean(epoch_loss)))
    metadata = {'seed': seed, 'epochs': epochs, 'length': length,
                'hidden': hidden, 'learning_rate': lr, 'use_graph': use_graph,
                'device': device, 'train_bins': len(matrix.data),
                'train_node_count': len(matrix.nodes),
                'normalization': scaler, 'training_losses': losses,
                'max_steps_per_epoch': max_steps_per_epoch}
    return model, metadata


def save_checkpoint(model: TemporalRelationModel, metadata: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({'weights': model.state_dict(), 'metadata': metadata}, path)
    path.with_suffix('.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


def load_checkpoint(path: Path, *, device: str | None = None):
    device = device or device_name()
    # Only load checkpoints you produced/trust; torch deserialization is sensitive.
    stored = torch.load(path, map_location=device, weights_only=True)
    meta = stored['metadata']
    model = TemporalRelationModel(meta['hidden'], meta['use_graph']).to(device)
    model.load_state_dict(stored['weights'])
    model.eval()
    return model, meta


@torch.no_grad()
def infer_graph(model: TemporalRelationModel, matrix: Matrix, meta: dict):
    features = normalize(matrix, meta['normalization'])
    length = meta['length']
    if len(features) <= length:
        raise ValueError('Not enough time bins to infer graph')
    device = next(model.parameters()).device
    kinds = kind_tensor(matrix, str(device))
    x = torch.from_numpy(features[-length:][None].transpose(0,2,1,3).copy()).to(device)
    pred, adj = model(x, kinds)
    return adj.cpu().numpy()[0], pred.cpu().numpy()[0]


@torch.no_grad()
def evaluate_forecast(model: TemporalRelationModel, matrix: Matrix, meta: dict,
                      *, max_samples: int | None = None):
    features = normalize(matrix, meta['normalization'])
    samples = _samples(features, meta['length'])
    if max_samples is not None:
        samples = samples[:max_samples]
    device = next(model.parameters()).device
    kinds = kind_tensor(matrix, str(device))
    model.eval()
    losses = []
    for window, target in samples:
        x = torch.from_numpy(window[None].transpose(0,2,1,3).copy()).to(device)
        pred, _ = model(x, kinds)
        losses.append(float(np.mean(np.abs(pred.cpu().numpy()[0] - target))))
    return {'mae_normalized': float(np.mean(losses)), 'n_samples': len(losses),
            'important': 'Forecast MAE is NOT relation edge accuracy'}
