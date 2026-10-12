"""Canonical JSON and content hashes for EBRL artifacts."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical_dumps(obj))


def short_id(prefix: str, obj: Any, n: int = 20) -> str:
    return f"{prefix}_{sha256_obj(obj)[:n]}"
