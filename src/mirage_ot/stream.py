"""Bounded-memory reading of JSON arrays, JSONL and JSON object streams.

Sherlock IPAL state files may be large. Do not load a complete ZIP or nested gzip
into RAM merely to parse the first event window.
"""
import json
from typing import Iterator, TextIO


def iter_json_records(handle: TextIO) -> Iterator[dict]:
    """Read JSONL or streamed JSON array, without retaining previously decoded rows.

    Raises on malformed content rather than silently dropping records. Very large
    single rows still require memory proportional to the row's size.
    """
    initial = handle.read(1)
    while initial and initial.isspace():
        initial = handle.read(1)
    if not initial:
        return
    if initial not in ('[', '{'):
        raise ValueError('Expected a JSON array or JSONL/JSON object stream')
    if initial == '[':
        yield from _iter_array(handle)
    else:
        first = initial + handle.readline()
        yield json.loads(first)
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _iter_array(handle: TextIO) -> Iterator[dict]:
    decoder = json.JSONDecoder()
    buffer = ''
    eof = False
    finished = False
    while not finished:
        buffer = buffer.lstrip()
        if buffer.startswith(','):
            buffer = buffer[1:].lstrip()
        if buffer.startswith(']'):
            finished = True
            buffer = buffer[1:]
            break
        try:
            obj, pos = decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            if eof:
                raise ValueError('Truncated/invalid JSON array') from None
            piece = handle.read(131072)
            if not piece:
                eof = True
            else:
                buffer += piece
            continue
        if not isinstance(obj, dict):
            raise ValueError('Expected array of JSON objects')
        yield obj
        buffer = buffer[pos:]
    if not finished:
        raise ValueError('Missing array terminator')
