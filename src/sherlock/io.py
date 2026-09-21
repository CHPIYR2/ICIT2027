"""Reproducible artifacts; no evaluator fields cross the feature boundary."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def opaque(prefix, text, length=16):
    return prefix + hashlib.sha256(text.encode()).hexdigest()[:length]


def read_json(path):
    return json.loads(Path(path).read_text())


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def verify_protocol(root=ROOT):
    lock = read_json(root/'configs/protocol.v1.lock.json')
    files = {**lock['files'],
             'data/manifests/sherlock_manifest.json': lock['dataset_manifest_sha256'],
             'data/evaluator/event_catalog.json': lock['event_catalog_sha256']}
    for path, digest in files.items():
        if sha256(root/path) != digest:
            raise ValueError(f'Frozen protocol changed: {path}')
    return read_json(root/'configs/split.v1.json'), read_json(root/'configs/evidence_contract.v1.json')
