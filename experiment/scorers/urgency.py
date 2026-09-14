"""Scorer for the urgency experiment.

Per the implementation instructions, this experiment does not test a new
`urgency` field — none exists. It tests whether *dropping* urgency
information (because current AMP has nowhere to put it, per
`reference/experiment-a-intent-roundtrip.md`'s finding that urgency was the
one thing lost in translation) causes a receiver to act on the wrong task
first when several competing tasks are pending. Gold is which task_id
should be handled first; correctness is whether the receiver's chosen
first task matches, not whether it used an urgency-sounding word.
"""
from __future__ import annotations

from typing import Any

from experiment.schema import ScoreResult
from experiment.scorers._common import extract_json_object


def parse_response(raw_output: str) -> dict[str, Any] | None:
    return extract_json_object(raw_output)


def score(parsed: dict[str, Any] | None, gold: dict[str, Any]) -> ScoreResult:
    if parsed is None:
        return ScoreResult(correct=None, detail={"reason": "unparseable_response"})

    first_task = parsed.get("first_task")
    if first_task is None:
        return ScoreResult(correct=None, detail={"reason": "missing_first_task"})

    correct = first_task == gold.get("first_task")
    return ScoreResult(
        correct=correct,
        detail={"first_task": first_task, "gold_first_task": gold.get("first_task")},
        self_report=parsed.get("reasoning"),
    )
