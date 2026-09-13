import json

import pytest

from amp.catalog import Catalog
from amp.errors import InvalidValue, MissingField


def _write(tmp_path, data):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_missing_version(tmp_path):
    with pytest.raises(MissingField):
        Catalog.load(_write(tmp_path, {"entries": []}))


def test_unsupported_version(tmp_path):
    with pytest.raises(InvalidValue):
        Catalog.load(_write(tmp_path, {"version": "9.9", "entries": []}))


def test_supported_version(tmp_path):
    Catalog.load(_write(tmp_path, {"version": "0.1", "entries": []}))
