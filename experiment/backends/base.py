"""Backend interface: turns a Scenario's prompt into a ModelResponse.

No backend in this module calls a live model API. This environment has no
configured Anthropic/Gemini credentials for the harness to use on its own,
and — more importantly — every prior experiment in `reference/` (F, G, H,
cross-model-verification, ...) was actually run by a human/orchestrating
Claude session spawning a blind sub-agent and transcribing its response by
hand. `ManualTranscriptBackend` formalizes exactly that workflow so results
are stored and traced the same way regardless of how the raw text was
produced. Wiring a live `APIBackend` subclass (Anthropic Messages API,
Gemini API, ...) is future work explicitly out of scope for this change —
see `experiment/README.md`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from experiment.schema import ModelResponse, Scenario


class ModelBackend(ABC):
    name: str

    @abstractmethod
    def generate(self, scenario: Scenario) -> ModelResponse:
        raise NotImplementedError
