"""Registry mapping an experiment name to its scorer module.

Every scorer module exposes the same two-function contract:

- `parse_response(raw_output: str) -> dict | None`
- `score(parsed: dict | None, gold: dict) -> ScoreResult`

The runner never hardcodes per-experiment scoring logic itself; it looks
the module up here by `Scenario.experiment`.
"""
from __future__ import annotations

from types import ModuleType

from experiment.scorers import condition, entity_reference, time_role, urgency

REGISTRY: dict[str, ModuleType] = {
    "entity_reference": entity_reference,
    "condition": condition,
    "urgency": urgency,
    "time_role": time_role,
}


def get_scorer(experiment: str) -> ModuleType:
    try:
        return REGISTRY[experiment]
    except KeyError as exc:
        raise ValueError(f"no scorer registered for experiment {experiment!r}") from exc
