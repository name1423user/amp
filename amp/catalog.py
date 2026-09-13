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
            kind = raw["kind"]
            if kind not in ("individual", "type"):
                raise InvalidValue("catalog", f"entries[{entry_id}].kind", f"got {kind!r}")
            entries[entry_id] = Entry(
                id=entry_id,
                kind=kind,
                type=raw.get("type"),
                parent=raw.get("parent"),
                label=(raw.get("label") or {}).get("en"),
                generic_label=(raw.get("generic_label") or {}).get("en"),
                proper=raw.get("proper", False),
            )

        # Structural checks that stay silent otherwise: an individual whose
        # `type`/`parent` chain never gets consulted (a proper noun's label
        # is used as-is, never its type) can carry a broken reference
        # forever without ever raising — until, worse, a missing `label` on
        # a proper individual doesn't error at all, it renders "None" into
        # the sentence. §6 forbids exactly that: a wrong-looking-plausible
        # sentence is worse than refusing to generate one.
        for entry in entries.values():
            if entry.kind == "individual":
                if not entry.type:
                    raise MissingField("catalog", f"entries[{entry.id}].type", "type is required for individuals")
                type_entry = entries.get(entry.type)
                if type_entry is None or type_entry.kind != "type":
                    raise UnknownId("catalog", f"entries[{entry.id}].type", f"unknown type: {entry.type!r}")
                if entry.proper and not entry.label:
                    raise MissingField("catalog", f"entries[{entry.id}].label", "label is required when proper is true")
            elif entry.parent is not None:
                parent_entry = entries.get(entry.parent)
                if parent_entry is None or parent_entry.kind != "type":
                    raise UnknownId("catalog", f"entries[{entry.id}].parent", f"unknown parent: {entry.parent!r}")

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
