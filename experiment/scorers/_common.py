"""Shared helpers for scorer modules.

All scenarios instruct the model to end its answer with a single JSON
object (see the `prompt` text in `experiment/scenarios/**`). Extraction is
deliberately tolerant of surrounding prose (models restate/explain before
answering) but does not attempt any semantic interpretation — that stays
each scorer's job, on the parsed fields only.
"""
from __future__ import annotations

import json
from typing import Any


def _find_balanced_objects(text: str) -> list[str]:
    """Return every substring that is a balanced `{...}` span, scanning
    left to right and respecting string literals (so a brace inside a
    quoted JSON string value doesn't unbalance the count)."""
    spans: list[str] = []
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append(text[start : i + 1])
                    start = None
    return spans


def extract_json_object(raw_output: str) -> dict[str, Any] | None:
    """Return the last balanced `{...}` block in `raw_output` that parses
    as a JSON object, or None. Last, not first, because models sometimes
    show a JSON *example* while reasoning before giving their real final
    answer at the end."""
    for candidate in reversed(_find_balanced_objects(raw_output)):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
