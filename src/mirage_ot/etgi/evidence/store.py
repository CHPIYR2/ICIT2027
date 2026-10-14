"""SQLite evidence store.

The investigation tools only read this database. Indexing is a separate
write phase. Nothing here accepts SQL from the model.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

FORBIDDEN_KEYS = frozenset({
    "malicious", "attack_point", "label", "labels", "event_description",
    "recovery", "attack_type", "description", "family_description", "event_truth",
})

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  timestamp REAL NOT NULL,
  modality TEXT NOT NULL,
  entity TEXT NOT NULL,
  kind TEXT NOT NULL,
  value REAL,
  value_present INTEGER NOT NULL,
  source_ref TEXT NOT NULL,
  archive_member TEXT,
  vantage TEXT,
  update_status TEXT,
  trust TEXT,
  ca TEXT,
  ioa TEXT,
  ca_ioa TEXT,
  ipal_context TEXT,
  fingerprint TEXT,
  parent_evidence_id TEXT,
  src_ip TEXT,
  dst_ip TEXT,
  src_port INTEGER,
  dst_port INTEGER,
  protocol_class TEXT,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_time ON evidence(timestamp);
CREATE INDEX IF NOT EXISTS idx_evidence_entity ON evidence(entity);
CREATE INDEX IF NOT EXISTS idx_evidence_kind ON evidence(kind);
CREATE INDEX IF NOT EXISTS idx_evidence_fp ON evidence(fingerprint);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

COLUMNS = (
    "evidence_id", "timestamp", "modality", "entity", "kind", "value", "value_present",
    "source_ref", "archive_member", "vantage", "update_status", "trust", "ca", "ioa",
    "ca_ioa", "ipal_context", "fingerprint", "parent_evidence_id", "src_ip", "dst_ip",
    "src_port", "dst_port", "protocol_class", "payload_json",
)


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    path = Path(path)
    if readonly:
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def create(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _clean_payload(payload: dict) -> dict:
    found = FORBIDDEN_KEYS & set(payload)
    if found:
        raise ValueError("Evaluator-only field cannot be stored as evidence: " + ", ".join(sorted(found)))
    return payload


def insert_evidence(conn: sqlite3.Connection, row: dict) -> None:
    payload = _clean_payload(dict(row.get("payload") or {}))
    present = 1 if row.get("value_present", row.get("value") is not None) else 0
    values = (
        row["evidence_id"], float(row["timestamp"]), row["modality"], row["entity"], row["kind"],
        None if not present else float(row["value"]), present,
        row["source_ref"], row.get("archive_member"), row.get("vantage"), row.get("update_status"),
        row.get("trust"), row.get("ca"), row.get("ioa"), row.get("ca_ioa"), row.get("ipal_context"),
        row.get("fingerprint"), row.get("parent_evidence_id"), row.get("src_ip"), row.get("dst_ip"),
        row.get("src_port"), row.get("dst_port"), row.get("protocol_class"),
        json.dumps(payload, sort_keys=True, default=str),
    )
    conn.execute(
        f"INSERT OR REPLACE INTO evidence ({', '.join(COLUMNS)}) VALUES ({', '.join('?' for _ in COLUMNS)})",
        values,
    )


def set_meta(conn: sqlite3.Connection, key: str, value) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (key, json.dumps(value, sort_keys=True, default=str)),
    )


def get_meta(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return json.loads(row["value"])


def expand_blocked(conn: sqlite3.Connection, seeds: Iterable[str]) -> set[str]:
    """Evidence that must stay hidden, including same-frame and derived rows.

    Ablation removes the cited record and any row that is the same frame,
    its parent packet, or a child decoded from that packet. A later tool
    call cannot hand the same observation back under another id.
    """
    blocked = {item for item in seeds if item}
    if not blocked:
        return set()
    for _ in range(6):
        marks = ",".join("?" for _ in blocked)
        params = tuple(blocked)
        rows = conn.execute(
            f"""SELECT evidence_id, parent_evidence_id, fingerprint FROM evidence
                WHERE evidence_id IN ({marks})
                   OR parent_evidence_id IN ({marks})
                   OR fingerprint IN (
                        SELECT fingerprint FROM evidence
                        WHERE evidence_id IN ({marks}) AND fingerprint IS NOT NULL
                   )""",
            params * 3,
        ).fetchall()
        grown = set(blocked)
        for row in rows:
            grown.add(row["evidence_id"])
            if row["parent_evidence_id"]:
                grown.add(row["parent_evidence_id"])
        if grown == blocked:
            break
        blocked = grown
    return blocked


def public_row(row: sqlite3.Row) -> dict:
    payload = json.loads(row["payload_json"])
    present = bool(row["value_present"])
    return {
        "evidence_id": row["evidence_id"],
        "timestamp": row["timestamp"],
        "modality": row["modality"],
        "entity": row["entity"],
        "kind": row["kind"],
        "value": row["value"] if present else None,
        "value_present": present,
        "source_ref": row["source_ref"],
        "archive_member": row["archive_member"],
        "vantage": row["vantage"],
        "update_status": row["update_status"],
        "trust": row["trust"],
        "ca": row["ca"],
        "ioa": row["ioa"],
        "ca_ioa": row["ca_ioa"],
        "ipal_context": row["ipal_context"],
        "fingerprint": row["fingerprint"],
        "parent_evidence_id": row["parent_evidence_id"],
        "src_ip": row["src_ip"],
        "dst_ip": row["dst_ip"],
        "src_port": row["src_port"],
        "dst_port": row["dst_port"],
        "protocol_class": row["protocol_class"],
        "payload": payload,
    }


def rows_by_ids(conn: sqlite3.Connection, ids: Sequence[str]) -> list[dict]:
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    found = conn.execute(
        f"SELECT * FROM evidence WHERE evidence_id IN ({marks})", tuple(ids)
    ).fetchall()
    order = {item: index for index, item in enumerate(ids)}
    return [public_row(row) for row in sorted(found, key=lambda item: order.get(item["evidence_id"], 10**9))]
