"""Stable evidence identifiers. The same source locator always maps to one id."""
from __future__ import annotations
import hashlib


def evidence_id(*parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return "EV-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
