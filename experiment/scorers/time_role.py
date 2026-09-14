"""Scorer for the message_time vs event_time experiment.

Per the implementation instructions, this tests only the narrowest possible
slice of `time` — the exact cut gap-analysis proposed and the improvement
proposal's roadmap item 4 kept as the minimal first probe — not a general
`time` role. Gold is the correct event time; a receiver that reports the
message's envelope timestamp instead is the specific, objectively-checkable
failure mode this scorer flags via `detail.conflated_with_message_time`.
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

    event_time = parsed.get("event_time")
    if event_time is None:
        return ScoreResult(correct=None, detail={"reason": "missing_event_time"})

    gold_event_time = gold.get("event_time")
    message_time = gold.get("message_time")
    correct = event_time == gold_event_time
    detail = {"event_time": event_time, "gold_event_time": gold_event_time}
    if not correct and message_time is not None and event_time == message_time:
        detail["conflated_with_message_time"] = True

    return ScoreResult(correct=correct, detail=detail, self_report=parsed.get("reasoning"))
