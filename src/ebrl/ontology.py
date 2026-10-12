"""Versioned command–variable compatibility. Compatibility is not causation."""
from __future__ import annotations


class Ontology:
    def __init__(self, document: dict, scopes: list[str] | None = None):
        self.document = document
        self.scopes = set(scopes or ["sherlock_attributes"])
        self._table: dict[tuple[str, str], dict] = {}
        for entry in document.get("entries", []):
            if entry.get("scope", "sherlock_attributes") not in self.scopes:
                continue
            self._table[(entry["command"], entry["variable"])] = entry

    def lookup(self, command: str | None, variable: str | None) -> dict | None:
        if not command or not variable:
            return None
        return self._table.get((command, variable))

    def relation(self, command: str | None, variable: str | None) -> str:
        entry = self.lookup(command, variable)
        if entry is None:
            return "unknown"
        return entry.get("relation", "unknown")

    def expected(self, command: str | None, variable: str | None) -> str | None:
        entry = self.lookup(command, variable)
        if entry is None:
            return None
        return entry.get("expected")
