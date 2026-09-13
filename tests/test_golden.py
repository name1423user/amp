import json
from pathlib import Path

import pytest

from amp.catalog import Catalog
from amp.errors import AmpError
from amp.render import render_message

GOLDEN_PATH = Path(__file__).parent / "golden.jsonl"
CATALOG_PATH = Path(__file__).parent.parent / "examples" / "catalog.json"

CASES = [json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load(str(CATALOG_PATH))


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_golden(case, catalog):
    if "expected" in case:
        assert render_message(case["message"], catalog) == case["expected"]
    else:
        with pytest.raises(AmpError) as exc_info:
            render_message(case["message"], catalog)
        assert exc_info.value.kind == case["error"]
