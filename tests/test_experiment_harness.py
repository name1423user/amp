"""Tests for the symmetric-experiment harness (`experiment/`).

These tests do not call any live model — they exercise the harness's own
plumbing (scenario loading, hashing, scorers, the runner, and the
gold-status gate) using fixed/manual backends, per the harness's own design
(see experiment/backends/base.py).
"""
import json
from pathlib import Path

import pytest

from experiment.backends.fixed import FixedResponseBackend
from experiment.backends.manual import ManualTranscriptBackend
from experiment.runner import DriftError, run_trial, write_trial
from experiment.schema import Scenario
from experiment.scorers import condition, entity_reference, time_role, urgency
from experiment.scorers._common import extract_json_object

SCENARIOS_DIR = Path(__file__).parent.parent / "experiment" / "scenarios"


def all_scenario_paths():
    return sorted(SCENARIOS_DIR.glob("*/*.json"))


@pytest.mark.parametrize("path", all_scenario_paths(), ids=lambda p: p.stem)
def test_every_shipped_scenario_loads_and_hashes(path):
    scenario = Scenario.load(path)
    assert scenario.id == path.stem
    assert scenario.experiment in {"entity_reference", "condition", "urgency", "time_role"}
    assert scenario.gold_status in {"reused_validated", "draft_pending_review"}
    assert scenario.gold_source, "gold_source must explain where the gold answer came from"
    # hash is deterministic and stable across repeated computation
    assert scenario.content_hash() == scenario.content_hash()


def test_content_hash_changes_when_gold_changes():
    base = dict(
        id="x", experiment="entity_reference", case_id="x", condition="nl",
        prompt_version="v1", prompt="p", gold_status="draft_pending_review", gold_source="test",
    )
    a = Scenario(gold={"entity": "a"}, **base)
    b = Scenario(gold={"entity": "b"}, **base)
    assert a.content_hash() != b.content_hash()


def test_content_hash_stable_when_only_metadata_changes():
    base = dict(
        id="x", experiment="entity_reference", case_id="x", condition="nl",
        prompt_version="v1", prompt="p", gold={"entity": "a"},
        gold_status="draft_pending_review", gold_source="test",
    )
    a = Scenario(metadata={}, **base)
    b = Scenario(metadata={"note": "annotated later"}, **base)
    assert a.content_hash() == b.content_hash()


def test_scenario_rejects_unknown_experiment():
    with pytest.raises(ValueError):
        Scenario(
            id="x", experiment="not_a_real_experiment", case_id="x", condition="nl",
            prompt_version="v1", prompt="p", gold={}, gold_status="draft_pending_review",
            gold_source="test",
        )


def test_scenario_requires_gold_source():
    with pytest.raises(ValueError):
        Scenario(
            id="x", experiment="entity_reference", case_id="x", condition="nl",
            prompt_version="v1", prompt="p", gold={}, gold_status="draft_pending_review",
            gold_source="",
        )


def test_extract_json_object_prefers_last_balanced_block():
    text = 'Reasoning: consider {"example": 1} as a distractor.\nFinal answer: {"entity": "a.pdf", "recipient": "alex"}'
    assert extract_json_object(text) == {"entity": "a.pdf", "recipient": "alex"}


def test_extract_json_object_returns_none_when_absent():
    assert extract_json_object("I cannot answer in JSON.") is None


def test_extract_json_object_handles_braces_inside_strings():
    text = 'Some prose {not json}. Final: {"note": "a {weird} value", "entity": "x"}'
    assert extract_json_object(text) == {"note": "a {weird} value", "entity": "x"}


# --- scorer unit tests: objective scoring, not self-report ---

def test_entity_reference_scorer_correct():
    result = entity_reference.score({"entity": "a.pdf", "recipient": "alex"}, {"entity": "a.pdf", "recipient": "alex"})
    assert result.correct is True


def test_entity_reference_scorer_wrong_entity_scores_false_even_with_high_self_reported_confidence():
    parsed = {"entity": "wrong.pdf", "recipient": "alex", "confidence": "high"}
    result = entity_reference.score(parsed, {"entity": "a.pdf", "recipient": "alex"})
    assert result.correct is False
    assert result.self_report == "high"


def test_entity_reference_scorer_unparseable_is_none_not_false():
    result = entity_reference.score(None, {"entity": "a.pdf"})
    assert result.correct is None


def test_condition_scorer_flags_overconfident_guess():
    result = condition.score({"action": "send_now"}, {"action": "cannot_determine"})
    assert result.correct is False
    assert result.detail["overconfident_guess"] is True


def test_condition_scorer_rejects_out_of_taxonomy_action():
    result = condition.score({"action": "maybe"}, {"action": "send_now"})
    assert result.correct is None


def test_urgency_scorer_matches_first_task():
    assert urgency.score({"first_task": "task_1"}, {"first_task": "task_1"}).correct is True
    assert urgency.score({"first_task": "task_2"}, {"first_task": "task_1"}).correct is False


def test_time_role_scorer_flags_conflation_with_message_time():
    result = time_role.score(
        {"event_time": "15:00"},
        {"event_time": "unknown", "message_time": "15:00"},
    )
    assert result.correct is False
    assert result.detail["conflated_with_message_time"] is True


def test_time_role_scorer_correct_when_unknown_reported_honestly():
    result = time_role.score(
        {"event_time": "unknown"},
        {"event_time": "unknown", "message_time": "15:00"},
    )
    assert result.correct is True


# --- runner integration ---

ENTITY_SCENARIO = SCENARIOS_DIR / "entity_reference" / "entity-case1-nl.json"
DRAFT_SCENARIO = SCENARIOS_DIR / "entity_reference" / "entity-case2-nl.json"


def test_run_trial_end_to_end_with_fixed_backend():
    scenario = Scenario.load(ENTITY_SCENARIO)
    backend = FixedResponseBackend(
        raw_output='I think the file is a.pdf. Final: {"entity": "report-final.pdf", "recipient": "alex", "confidence": "high"}',
        model="test-model",
        model_version="test-model-2026-01-01",
    )
    record = run_trial(scenario, backend)
    assert record.score.correct is True
    assert record.model == "test-model"
    assert record.scenario_id == scenario.id
    assert record.gold_status == "reused_validated"
    assert record.scenario_hash == scenario.content_hash()

    # every field the tracking requirement asks for is present
    payload = record.to_json()
    for field in (
        "experiment_id", "scenario_id", "model", "model_version", "prompt_version",
        "scenario_hash", "timestamp", "input", "raw_output", "parsed_answer",
        "gold_answer", "score",
    ):
        assert field in payload


def test_run_trial_refuses_draft_gold_by_default():
    scenario = Scenario.load(DRAFT_SCENARIO)
    backend = FixedResponseBackend('{"entity": "invoice-march.pdf", "recipient": "priya"}', "m", "v1")
    with pytest.raises(ValueError, match="draft_pending_review"):
        run_trial(scenario, backend)


def test_run_trial_allows_draft_gold_when_explicitly_requested():
    scenario = Scenario.load(DRAFT_SCENARIO)
    backend = FixedResponseBackend('{"entity": "invoice-march.pdf", "recipient": "priya"}', "m", "v1")
    record = run_trial(scenario, backend, allow_draft_gold=True)
    assert record.score.correct is True


def test_run_trial_detects_scenario_drift():
    scenario = Scenario.load(ENTITY_SCENARIO)
    backend = FixedResponseBackend('{"entity": "report-final.pdf", "recipient": "alex"}', "m", "v1")
    with pytest.raises(DriftError):
        run_trial(scenario, backend, expected_scenario_hash="not-the-real-hash")


def test_manual_transcript_backend_reads_file(tmp_path):
    response_file = tmp_path / "response.txt"
    response_file.write_text('{"entity": "report-final.pdf", "recipient": "alex"}', encoding="utf-8")
    scenario = Scenario.load(ENTITY_SCENARIO)
    backend = ManualTranscriptBackend(response_file, model="claude-sonnet-5", model_version="claude-sonnet-5-2026")
    response = backend.generate(scenario)
    assert response.raw_output == response_file.read_text(encoding="utf-8")
    assert response.model == "claude-sonnet-5"


def test_write_trial_writes_traceable_json(tmp_path):
    scenario = Scenario.load(ENTITY_SCENARIO)
    backend = FixedResponseBackend('{"entity": "report-final.pdf", "recipient": "alex"}', "m", "v1")
    record = run_trial(scenario, backend)
    out_path = write_trial(record, results_dir=tmp_path)
    assert out_path.exists()
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["scenario_id"] == "entity-case1-nl"
    assert saved["score"]["correct"] is True


def test_aggregate_summarize_separates_unscoreable_from_incorrect():
    from experiment.analysis.aggregate import summarize

    trials = [
        {"condition": "nl", "score": {"correct": True}, "gold_status": "reused_validated"},
        {"condition": "nl", "score": {"correct": False}, "gold_status": "reused_validated"},
        {"condition": "nl", "score": {"correct": None}, "gold_status": "reused_validated"},
        {"condition": "full_amp", "score": {"correct": True}, "gold_status": "draft_pending_review"},
    ]
    summary = summarize(trials)
    assert summary["nl"] == {
        "n": 3,
        "correct": 1,
        "incorrect": 1,
        "unscoreable": 1,
        "accuracy_of_scored": 0.5,
        "gold_statuses": ["reused_validated"],
    }
    assert summary["full_amp"]["gold_statuses"] == ["draft_pending_review"]


def test_write_trial_never_touches_scenarios_dir(tmp_path, monkeypatch):
    """Guards the hard requirement that the runner/analysis layer is
    read-only with respect to experiment/scenarios/."""
    scenario_mtime_before = ENTITY_SCENARIO.stat().st_mtime
    scenario = Scenario.load(ENTITY_SCENARIO)
    backend = FixedResponseBackend('{"entity": "report-final.pdf", "recipient": "alex"}', "m", "v1")
    record = run_trial(scenario, backend)
    write_trial(record, results_dir=tmp_path)
    assert ENTITY_SCENARIO.stat().st_mtime == scenario_mtime_before
