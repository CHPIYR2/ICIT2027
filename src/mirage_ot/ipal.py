"""Read Sherlock / IPAL state snapshots as *reported* process values.

Physical modality here means electrical quantity, NOT trusted out-of-band
physical ground truth. The values remain network-observed telemetry.
"""
import datetime as dt
import gzip
import io
import math
from pathlib import Path
from typing import Iterable, Iterator
from .stream import iter_json_records
from .types import Observation


def unix_seconds(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            d = dt.datetime.fromisoformat(v.replace('Z', '+00:00'))
            if d.tzinfo is None:
                raise ValueError('Ambiguous timezone in timestamp: ' + v)
            return d.timestamp()
    raise TypeError(f'Unsupported timestamp {v!r}')


_IGNORED_FIELDS = ('malicious', 'description', 'attack_point', 'label', 'labels', 'recovery')


def _numeric(value):
    if isinstance(value, dict):
        value = value.get('value')
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def _same(left: float, right: float) -> bool:
    scale = max(1.0, abs(left), abs(right))
    return abs(left - right) <= 1e-5 * scale


def iter_state(handle, *, source: str, start: float | None = None,
               end: float | None = None, max_rows: int | None = None,
               audit: dict | None = None, initial_state: dict | None = None,
               updates_only: bool = True) -> Iterator[Observation]:
    """Emit a physical value only when it changes.

    A repeated timeslice value is a hold, and a value that still equals the
    IPAL initial state is a fill. Neither is an independent measurement.
    Rows before `start` are still read so a later change can be recognized.
    The stream is assumed to be time-sorted. `malicious` is never a feature.
    """
    if source.endswith('.gz'):
        handle = gzip.GzipFile(fileobj=handle)
    initial = {}
    for key, value in (initial_state or {}).items():
        number = _numeric(value)
        if number is not None:
            initial[str(key)] = number
    last: dict[str, float] = {}
    stream = io.TextIOWrapper(handle, encoding='utf-8')
    for index, row in enumerate(iter_json_records(stream)):
        if max_rows is not None and index >= max_rows:
            break
        time_value = row.get('timestamp', row.get('time'))
        if time_value is None:
            raise ValueError(f'No timestamp at {source} row {index}')
        t = unix_seconds(time_value)
        if end is not None and t >= end:
            break
        in_window = start is None or t >= start
        if audit is not None:
            for field in _IGNORED_FIELDS:
                if field in row:
                    audit[field] = audit.get(field, 0) + 1
            if in_window and row.get('malicious') not in (None, False):
                audit['malicious_true'] = audit.get('malicious_true', 0) + 1
        values = row.get('values', row.get('state'))
        if not isinstance(values, dict):
            raise ValueError(f'No state/values dictionary at {source} row {index}')
        for key, value in values.items():
            name = str(key)
            if name in _IGNORED_FIELDS:
                continue
            number = _numeric(value)
            if number is None:
                continue
            previous = last.get(name)
            if previous is not None and _same(previous, number):
                status = 'hold'
            elif previous is None and name in initial and _same(initial[name], number):
                status = 'initial'
            else:
                status = 'new'
            last[name] = number
            if audit is not None and in_window:
                audit[status] = audit.get(status, 0) + 1
            if updates_only and status != 'new':
                continue
            if not in_window:
                continue
            yield Observation(t, 'physical', name, 'observed_telemetry', number,
                              f'{source}#row={index};key={name}',
                              {'trust': 'network-reported', 'update': status,
                               'physical_trust': 'network-reported-not-simulator-truth'})


def read_state(path: Path, **kwargs) -> Iterator[Observation]:
    with path.open('rb') as f:
        yield from iter_state(f, source=path.name, **kwargs)
