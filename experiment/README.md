# Symmetric-experiment harness

Infrastructure for running the four experiments fixed in
[`reference/experiment-plan-symmetric.md`](../reference/experiment-plan-symmetric.md)
(entity reference, condition, urgency, time role) the same way every time,
with objective scoring and full traceability. This directory contains no
AMP spec changes and defines no new AMP fields — see that plan document's
§0 for the guardrails this code enforces mechanically, not just by
convention.

## Pipeline

```
scenario (JSON, gold fixed in advance)
   -> backend.generate()        (model execution; see "Backends" below)
   -> raw_output                (stored verbatim, never edited)
   -> scorer.parse_response()   (extracts a judgeable answer, or None)
   -> scorer.score()            (objective compare against scenario.gold)
   -> TrialRecord                (fully traceable, written under results/)
   -> experiment/analysis/aggregate.py   (read-only summary, separate step)
```

Each step is a separate module so that scoring logic changes can't
retroactively alter which scenarios were run, and analysis can't feed back
into scenario/gold authoring (`aggregate.py` never writes into
`scenarios/`).

## Layout

```
experiment/
  schema.py            Scenario / ModelResponse / ScoreResult / TrialRecord
  runner.py             run_trial() + a CLI entry point
  backends/
    base.py             ModelBackend interface
    manual.py           reads a pre-recorded raw transcript from a file
    fixed.py             in-process fixed response, for tests/dry-runs only
  scorers/
    entity_reference.py, condition.py, urgency.py, time_role.py
    _common.py           extract_json_object() shared by all scorers
  scenarios/
    entity_reference/, condition/, urgency/, time_role/
      one JSON file per (case, condition) — see schema below
  results/               trial records land here at runtime (git-ignored
                          content; only .gitkeep is tracked)
  analysis/
    aggregate.py          groups results by condition, reports
                          correct/incorrect/unscoreable counts separately
```

## Scenario file schema

```json
{
  "id": "entity-case1-nl",
  "experiment": "entity_reference",
  "case_id": "entity-case1",
  "condition": "nl",
  "prompt_version": "v1",
  "prompt": "...",
  "gold": { "entity": "report-final.pdf", "recipient": "alex" },
  "gold_status": "reused_validated",
  "gold_source": "reference/experiment-h-full-vs-minimal-vs-nl.md, Round 2 (S4).",
  "metadata": { "...": "free-form, excluded from the content hash" }
}
```

- `case_id` groups the representation-variants (`condition` values) of one
  underlying situation, so analysis can compare them.
- `gold_status` is either `"reused_validated"` (the gold answer traces back
  to an already-run, independently-recorded experiment in `reference/`) or
  `"draft_pending_review"` (authored alongside this change — including
  scenarios Claude generated in this session — and not yet confirmed by a
  reviewer separate from the author). **`runner.run_trial` refuses to score
  a `draft_pending_review` scenario unless you pass `allow_draft_gold=True`
  (or `--allow-draft-gold` on the CLI)**, and `aggregate.py` prints a
  warning whenever a summarized condition includes draft trials. This is a
  hard gate, not a comment, precisely because "Claude generated the
  scenario, so Claude's gold answer for it must already be right" is the
  failure mode instruction #6 of the implementing task calls out by name.
- `Scenario.content_hash()` hashes `id`/`experiment`/`case_id`/`condition`/
  `prompt_version`/`prompt`/`gold` (not `metadata`, so annotating a
  scenario doesn't invalidate past trials against it). Every `TrialRecord`
  stores the hash of the scenario it was scored against; if you edit a
  scenario's prompt or gold after trials exist, `run_trial(...,
  expected_scenario_hash=...)` raises `DriftError` instead of silently
  scoring against a moved target.

## Backends: why there is no live-API backend yet

Every earlier experiment in `reference/` (F, F-2, G, H,
cross-model-verification, ...) was run by a human/orchestrating Claude
session spawning a blind sub-agent (told nothing about the hypothesis) and
transcribing its answer by hand. This environment also has no configured
model API credentials for a harness process to call on its own. Rather than
inventing a parallel execution path, `ManualTranscriptBackend` formalizes
that exact workflow:

1. Read `scenario.prompt` (e.g. `python -c "import json,sys;
   print(json.load(open(sys.argv[1]))['prompt'])" experiment/scenarios/.../x.json`).
2. Run it through a blind receiver (a fresh sub-agent session that is not
   told the experiment's purpose, matching the discipline in
   `experiment-h-full-vs-minimal-vs-nl.md` and its predecessors) or a
   Gemini session, etc.
3. Save exactly what it said to a text file.
4. `python -m experiment.runner --scenario <scenario.json> --response-file
   <that file> --model <name> --model-version <exact id/build>`.

Wiring a live `APIBackend` (Anthropic Messages API, Gemini API, ...) that
calls a model directly is explicitly out of scope for this change — see
`reference/experiment-plan-symmetric.md` §0 ("infrastructure and a fixed
plan only, this round"). Adding one later only requires implementing
`ModelBackend.generate()`; nothing else in the pipeline changes.

## Cross-model runs

Nothing in `runner.py` or the scorers is model-specific. To compare models,
run the same scenario file through each model's transcript and record a
`model`/`model_version` per trial — `aggregate.py` groups by `condition`,
so pass `--results-dir` per model (or read `TrialRecord.model` in a custom
analysis pass) to compare across models without changing the prompt or the
scoring code, per instruction #11 of the implementing task.

## Running the tests

```
pytest tests/test_experiment_harness.py
```

covers scenario loading/hashing for every shipped scenario file, each
scorer's objective-vs-unparseable behavior, the gold-status gate, drift
detection, and that `run_trial`/`write_trial`/`aggregate.py` never modify
`experiment/scenarios/`.
