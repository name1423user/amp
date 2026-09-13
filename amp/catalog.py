"""§2: catalog loading, id validation, and generic_label chain resolution (ADR-012: parent field only, never string-split ids)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .errors import InvalidValue, MissingField, NoGenericLabel, UnknownId

ID_RE = re.compile(r"^(entity|type):[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")
SUPPORTED_CATALOG_VERSIONS = ("0.1",)


@dataclass
class Entry:
    id: str
    kind: str
    type: str | None = None
    parent: str | None = None
    label: str | None = None
    generic_label: str | None = None
    proper: bool = False


class Catalog:
    def __init__(self, entries: dict[str, Entry]):
        self._entries = entries

    @classmethod
    def load(cls, path: str) -> "Catalog":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version")
        if version is None:
            raise MissingField("catalog", "version", "version is required")
        if version not in SUPPORTED_CATALOG_VERSIONS:
            raise InvalidValue("catalog", "version", f"unsupported catalog version: {version!r}")
        entries: dict[str, Entry] = {}
        for raw in data["entries"]:
            entry_id = raw["id"]
            if not ID_RE.match(entry_id):
                raise InvalidValue("catalog", "id", f"malformed id: {entry_id!r}")
            entries[entry_id] = Entry(
                id=entry_id,
                kind=raw["kind"],
                type=raw.get("type"),
                parent=raw.get("parent"),
                label=(raw.get("label") or {}).get("en"),
                generic_label=(raw.get("generic_label") or {}).get("en"),
                proper=raw.get("proper", False),
            )
        return cls(entries)

    def get(self, ref_id: str, message_id: str, field_path: str) -> Entry:
        entry = self._entries.get(ref_id)
        if entry is None:
            raise UnknownId(message_id, field_path, f"unknown id: {ref_id!r}")
        return entry

    def generic_label_for_type(self, type_id: str, message_id: str, field_path: str) -> str:
        current, seen = type_id, set()
        while current is not None and current not in seen:
            seen.add(current)
            entry = self._entries.get(current)
            if entry is None:
                break
            if entry.generic_label is not None:
                return entry.generic_label
            current = entry.parent
        raise NoGenericLabel(message_id, field_path, f"no generic_label reachable from {type_id!r}")
