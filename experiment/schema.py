"""Data model for the symmetric-experiment harness.

This module has no dependency on the `amp` package. The harness exists to
measure whether AMP's structuring *helps* relative to natural language (and,
within AMP, which structural element does the work) — it is not part of the
shipped protocol and must never become a place where new AMP fields get
invented (see `reference/experiment-plan-symmetric.md` §0 for the guardrails
this module enforces mechanically).

Two things are enforced here, not just documented:

1. **Gold answers are separate from scenario generation, and are locked.**
   A `Scenario.gold_status` of `"draft_pending_review"` means the gold value
   was set by whoever authored the scenario file (including Claude, when it
   authored the file) and has not yet been confirmed by a separate reviewer.
   `Scenario.content_hash()` is recorded on every trial; if the scenario file
   changes after a trial was scored against it, that trial's stored hash
   no longer matches the file's current hash and analysis can detect the
   drift instead of silently re-scoring against a moved target.
2. **Objective scoring is the default currency.** `TrialRecord.score` always
   carries a `correct: bool | None` (`None` = the response could not be
   parsed into a judgeable answer at all — this must never be silently
   coerced to `False`) plus whatever self-report the raw output happened to
   contain, kept as `self_report` for reference only. Analysis code must
   never rank conditions by `self_report`.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

EXPERIMENTS = ("entity_reference", "condition", "urgency", "time_role")

GOLD_STATUSES = ("reused_validated", "draft_pending_review")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclasses.dataclass(frozen=True)
class Scenario:
    """One runnable prompt + its locked-in-advance gold answer.

    `case_id` groups the representation-variants of the same underlying
    situation (e.g. the NL / full_amp / minimal_structured renderings of one
    entity-reference scenario) so analysis can compare them; `condition` is
    the independent variable value for this particular file.
    """

    id: str
    experiment: str
    case_id: str
    condition: str
    prompt_version: str
    prompt: str
    gold: dict[str, Any]
    gold_status: str
    gold_source: str
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.experiment not in EXPERIMENTS:
            raise ValueError(f"unknown experiment {self.experiment!r} (scenario {self.id})")
        if self.gold_status not in GOLD_STATUSES:
            raise ValueError(f"unknown gold_status {self.gold_status!r} (scenario {self.id})")
        if not self.gold_source:
            raise ValueError(f"gold_source is required (scenario {self.id})")

    @classmethod
    def load(cls, path: str | Path) -> "Scenario":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            id=data["id"],
            experiment=data["experiment"],
            case_id=data["case_id"],
            condition=data["condition"],
            prompt_version=data["prompt_version"],
            prompt=data["prompt"],
            gold=data["gold"],
            gold_status=data["gold_status"],
            gold_source=data["gold_source"],
            metadata=data.get("metadata", {}),
        )

    def content_hash(self) -> str:
        """Hash of everything that must not silently change after trials are
        scored against it: the prompt text and the gold answer. `metadata`
        is deliberately excluded so annotating a scenario doesn't fault
        every past trial; `id`/`experiment`/`condition` are included so a
        copy-paste-and-rename doesn't collide with the original's hash."""
        payload = {
            "id": self.id,
            "experiment": self.experiment,
            "case_id": self.case_id,
            "condition": self.condition,
            "prompt_version": self.prompt_version,
            "prompt": self.prompt,
            "gold": self.gold,
        }
        return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True)
class ModelResponse:
    """What a backend hands back for one scenario."""

    raw_output: str
    model: str
    model_version: str


@dataclasses.dataclass(frozen=True)
class ScoreResult:
    """Output of a scorer. `correct=None` means "could not be judged" —
    a parse failure or a deliberately-uncertain gold target that the
    response didn't address — and must be counted separately from a wrong
    answer, never folded into `False` (see module docstring)."""

    correct: bool | None
    detail: dict[str, Any] = dataclasses.field(default_factory=dict)
    self_report: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {"correct": self.correct, "detail": self.detail, "self_report": self.self_report}


@dataclasses.dataclass(frozen=True)
class TrialRecord:
    """One fully-traceable experiment run, per the tracking fields the
    implementation instructions require (experiment id / scenario id / model
    / model version / prompt version / scenario hash / timestamp / input /
    raw output / parsed answer / gold answer / score)."""

    experiment_id: str
    scenario_id: str
    case_id: str
    condition: str
    model: str
    model_version: str
    prompt_version: str
    scenario_hash: str
    timestamp: str
    input: str
    raw_output: str
    parsed_answer: dict[str, Any] | None
    gold_answer: dict[str, Any]
    gold_status: str
    score: ScoreResult

    def to_json(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["score"] = self.score.to_json()
        return d

    def result_filename(self) -> str:
        safe_ts = self.timestamp.replace(":", "").replace("-", "")
        return f"{self.scenario_id}__{self.model}__{safe_ts}.json"
