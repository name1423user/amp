"""Runs one scenario through a backend, scores it, and writes a TrialRecord.

This module deliberately does nothing else: it does not decide what a
"good" score is (that's `experiment/scorers/`), it does not aggregate
across trials (that's `experiment/analysis/`), and it never writes back
into `experiment/scenarios/` — scenarios and their gold answers are
read-only from the runner's point of view. See
`reference/experiment-plan-symmetric.md` §0 for why that separation is a
hard requirement, not a style preference.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from experiment.backends.base import ModelBackend
from experiment.backends.manual import ManualTranscriptBackend
from experiment.schema import Scenario, TrialRecord
from experiment.scorers import get_scorer

RESULTS_DIR = Path(__file__).parent / "results"


class DriftError(RuntimeError):
    """Raised when a scenario's on-disk content no longer matches the hash
    a caller expected — i.e. someone edited a prompt or gold answer after
    the fact. Refuse to score silently against a moved target."""


def run_trial(
    scenario: Scenario,
    backend: ModelBackend,
    *,
    allow_draft_gold: bool = False,
    expected_scenario_hash: str | None = None,
) -> TrialRecord:
    if scenario.gold_status == "draft_pending_review" and not allow_draft_gold:
        raise ValueError(
            f"scenario {scenario.id!r} has gold_status=draft_pending_review; "
            "its gold answer has not been confirmed by a reviewer separate from "
            "whoever authored the scenario. Pass allow_draft_gold=True to run it "
            "anyway (e.g. for a dry run), but do not report such trials as if the "
            "gold answer were established (see reference/experiment-plan-symmetric.md)."
        )

    actual_hash = scenario.content_hash()
    if expected_scenario_hash is not None and expected_scenario_hash != actual_hash:
        raise DriftError(
            f"scenario {scenario.id!r} content_hash is {actual_hash} but "
            f"{expected_scenario_hash} was expected — the prompt or gold answer "
            "changed since this was last referenced. Re-review before using it."
        )

    response = backend.generate(scenario)
    scorer = get_scorer(scenario.experiment)
    parsed = scorer.parse_response(response.raw_output)
    result = scorer.score(parsed, scenario.gold)

    return TrialRecord(
        experiment_id=scenario.experiment,
        scenario_id=scenario.id,
        case_id=scenario.case_id,
        condition=scenario.condition,
        model=response.model,
        model_version=response.model_version,
        prompt_version=scenario.prompt_version,
        scenario_hash=actual_hash,
        timestamp=datetime.now(timezone.utc).isoformat(),
        input=scenario.prompt,
        raw_output=response.raw_output,
        parsed_answer=parsed,
        gold_answer=scenario.gold,
        gold_status=scenario.gold_status,
        score=result,
    )


def write_trial(record: TrialRecord, results_dir: Path = RESULTS_DIR) -> Path:
    out_dir = results_dir / record.experiment_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / record.result_filename()
    out_path.write_text(json.dumps(record.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="path to a scenario JSON file")
    parser.add_argument("--response-file", required=True, help="path to a saved raw model transcript")
    parser.add_argument("--model", required=True, help="model name, e.g. claude-sonnet-5")
    parser.add_argument("--model-version", required=True, help="the exact model identifier/build used")
    parser.add_argument("--allow-draft-gold", action="store_true")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args(argv)

    scenario = Scenario.load(args.scenario)
    backend = ManualTranscriptBackend(args.response_file, args.model, args.model_version)
    record = run_trial(scenario, backend, allow_draft_gold=args.allow_draft_gold)
    out_path = write_trial(record, Path(args.results_dir))
    print(f"wrote {out_path} (correct={record.score.correct})")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
