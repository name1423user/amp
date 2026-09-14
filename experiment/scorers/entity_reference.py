"""Scorer for the entity-reference experiment.

Formalizes `reference/experiment-h-full-vs-minimal-vs-nl.md`'s blind-test
method: the receiver is asked which catalog entity a message refers to, and
correctness is which entity ID it actually names, not whether it *says* it
is confident. `self_report` keeps any confidence/ambiguity language the
model volunteered, for reference only — see the module-level policy in
`experiment/schema.py`.

Known limitation this scorer cannot address (carried over verbatim from
experiment-h's own "limits" section): it only measures whether the
*referent* (entity/recipient) was identified correctly. It says nothing
about whether the *act* (what should be done with that referent) was
conveyed — experiment-h found that every one of its scenarios let
surrounding NL context supply the act, so Minimal AMP's performance on
that axis is still untested. Do not read a high entity-reference score as
evidence that a minimal, entity-only representation is sufficient on its
own; it is evidence only about entity/recipient resolution.
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

    entity_ok = parsed.get("entity") == gold.get("entity")
    recipient_gold = gold.get("recipient")
    if recipient_gold is not None:
        recipient_ok = parsed.get("recipient") == recipient_gold
        correct = bool(entity_ok and recipient_ok)
        detail = {"entity_correct": entity_ok, "recipient_correct": recipient_ok}
    else:
        correct = bool(entity_ok)
        detail = {"entity_correct": entity_ok}

    return ScoreResult(correct=correct, detail=detail, self_report=parsed.get("confidence"))
