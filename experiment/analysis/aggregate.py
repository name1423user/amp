"""Reads scored trial records and summarizes them. Read-only: this module
must never write into `experiment/scenarios/` or otherwise feed conclusions
back into the scenarios/gold answers it is analyzing (see the "no
auto-changing scope/spec from results" rule in
`reference/experiment-plan-symmetric.md` §0). It writes its own report
under `experiment/results/reports/`, never overwriting a raw trial record.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).parent.parent / "results"


def load_trials(experiment: str, results_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    exp_dir = results_dir / experiment
    if not exp_dir.is_dir():
        return []
    trials = []
    for path in sorted(exp_dir.glob("*.json")):
        trials.append(json.loads(path.read_text(encoding="utf-8")))
    return trials


def summarize(trials: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Groups by `condition` and reports three separate counts per the
    priority order the instructions require: correct / incorrect /
    unparseable-or-undeterminable (score.correct is None). Never collapses
    the last bucket into "incorrect" — an unscoreable trial is a fact about
    the harness or the response, not evidence against the condition."""
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        by_condition[trial["condition"]].append(trial)

    summary: dict[str, dict[str, Any]] = {}
    for condition, group in by_condition.items():
        correct = sum(1 for t in group if t["score"]["correct"] is True)
        incorrect = sum(1 for t in group if t["score"]["correct"] is False)
        unscoreable = sum(1 for t in group if t["score"]["correct"] is None)
        n = len(group)
        summary[condition] = {
            "n": n,
            "correct": correct,
            "incorrect": incorrect,
            "unscoreable": unscoreable,
            "accuracy_of_scored": (correct / (correct + incorrect)) if (correct + incorrect) else None,
            "gold_statuses": sorted({t["gold_status"] for t in group}),
        }
    return summary


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, choices=["entity_reference", "condition", "urgency", "time_role"])
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--out", default=None, help="optional path to also write the summary JSON to")
    args = parser.parse_args(argv)

    trials = load_trials(args.experiment, Path(args.results_dir))
    summary = summarize(trials)
    draft_conditions = [c for c, s in summary.items() if "draft_pending_review" in s["gold_statuses"]]

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if draft_conditions:
        print(
            f"NOTE: condition(s) {draft_conditions} include trials scored against "
            "draft_pending_review gold answers — treat as illustrative only, not "
            "as a finding, until a separate reviewer confirms the gold.",
            file=sys.stderr,
        )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
