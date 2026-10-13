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


def iter_state(handle, *, source: str, start: float | None = None,
               end: float | None = None, max_rows: int | None = None
               ) -> Iterator[Observation]:
    """Works on a binary `.gz` stream or a plain binary JSON/JSONL stream.

    Only numeric/bool values are emitted. Context and measurement/setpoint identity
    are preserved in the channel key; the parser never equates a setpoint with truth.
    """
    if source.endswith('.gz'):
        handle = gzip.GzipFile(fileobj=handle)
    stream = io.TextIOWrapper(handle, encoding='utf-8')
    for index, row in enumerate(iter_json_records(stream)):
        if max_rows is not None and index >= max_rows:
            break
        time_value = row.get('timestamp', row.get('time'))
        if time_value is None:
            raise ValueError(f'No timestamp at {source} row {index}')
        t = unix_seconds(time_value)
        if start is not None and t < start:
            continue
        if end is not None and t >= end:
            continue
        values = row.get('values', row.get('state'))
        if not isinstance(values, dict):
            raise ValueError(f'No state/values dictionary at {source} row {index}')
        for key, value in values.items():
            if isinstance(value, dict):
                v = value.get('value')
            else:
                v = value
            if isinstance(v, bool):
                v = float(v)
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                continue
            yield Observation(t, 'physical', str(key), 'observed_telemetry', float(v),
                              f'{source}#row={index};key={key}',
                              {'trust': 'network-reported', 'context': str(key)})


def read_state(path: Path, **kwargs) -> Iterator[Observation]:
    with path.open('rb') as f:
        yield from iter_state(f, source=path.name, **kwargs)
