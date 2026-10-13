"""Train/eval isolation checks. These do not score attacks."""
from __future__ import annotations
from .features import Matrix


def matrix_bounds(matrix: Matrix) -> tuple[float, float]:
    return matrix.start, matrix.start + len(matrix.data) * matrix.bin_seconds


def ranges_overlap(left: tuple[float, float], right: tuple[float, float]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def assert_disjoint(train: Matrix, evaluation: Matrix) -> dict:
    train_bounds = matrix_bounds(train)
    eval_bounds = matrix_bounds(evaluation)
    if ranges_overlap(train_bounds, eval_bounds):
        raise ValueError(
            f'Train window {train_bounds} overlaps evaluation window {eval_bounds}')
    return {'train_window': list(train_bounds), 'eval_window': list(eval_bounds),
            'disjoint': True}


def normalization_is_train_only(metadata: dict, train: Matrix) -> dict:
    """The checkpoint scaler must be the one fit on this train matrix, not eval."""
    stored = metadata.get('normalization')
    if not stored:
        raise ValueError('Checkpoint has no train normalization')
    from .model import _norm_fit
    fresh = _norm_fit(train)
    same = stored == fresh
    return {'normalization_matches_train_matrix': same,
            'trained_on_path': metadata.get('trained_on_path')}
