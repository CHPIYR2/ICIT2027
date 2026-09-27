"""Exact serialization, hashes and create-once artifacts."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]

def dumps(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def utc():
    return datetime.now(timezone.utc).isoformat()

def create_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return file_hash(path)

def binding(path):
    return {'path': str(Path(path).relative_to(ROOT)), 'sha256': file_hash(path)}
