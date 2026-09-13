"""Structural catalog validation that stays silent otherwise: a broken type/parent/label
reference on a proper individual never gets exercised at render time (its label is used
as-is), so without these checks a bad catalog can produce wrong-but-plausible output
instead of an error — exactly what §6 forbids."""
import json

import pytest

from amp.catalog import Catalog
from amp.errors import InvalidValue, MissingField, UnknownId


def _write(tmp_path, entries):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"version": "0.1", "entries": entries}), encoding="utf-8")
    return str(path)


def test_individual_missing_type(tmp_path):
    with pytest.raises(MissingField):
        Catalog.load(_write(tmp_path, [{"id": "entity:x", "kind": "individual", "proper": True, "label": {"en": "X"}}]))


def test_individual_unknown_type(tmp_path):
    with pytest.raises(UnknownId):
        Catalog.load(_write(tmp_path, [
            {"id": "entity:x", "kind": "individual", "type": "type:ghost", "proper": True, "label": {"en": "X"}},
        ]))


def test_proper_individual_missing_label(tmp_path):
    with pytest.raises(MissingField):
        Catalog.load(_write(tmp_path, [
            {"id": "type:t", "kind": "type", "generic_label": {"en": "thing"}},
            {"id": "entity:x", "kind": "individual", "type": "type:t", "proper": True},
        ]))


def test_type_unknown_parent(tmp_path):
    with pytest.raises(UnknownId):
        Catalog.load(_write(tmp_path, [{"id": "type:t", "kind": "type", "parent": "type:ghost"}]))


def test_bad_kind(tmp_path):
    with pytest.raises(InvalidValue):
        Catalog.load(_write(tmp_path, [{"id": "entity:x", "kind": "bogus"}]))


def test_valid_catalog_still_loads(tmp_path):
    Catalog.load(_write(tmp_path, [
        {"id": "type:t", "kind": "type", "generic_label": {"en": "thing"}},
        {"id": "entity:x", "kind": "individual", "type": "type:t", "proper": True, "label": {"en": "X"}},
        {"id": "entity:y", "kind": "individual", "type": "type:t"},
    ]))
