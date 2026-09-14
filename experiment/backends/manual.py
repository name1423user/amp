"""Ingests a raw model transcript that was produced outside this codebase.

Typical use: run the scenario's `prompt` through a blind sub-agent session
(same discipline as `reference/experiment-h-full-vs-minimal-vs-nl.md` and
earlier: the receiver is told nothing about the experiment's hypothesis),
save what it said verbatim to a text file, and point this backend at that
file. Nothing here edits or normalizes the transcript — normalization is
the scorer's `parse_response` job, kept separate so the stored `raw_output`
always stays the untouched source of truth.
"""
from __future__ import annotations

from pathlib import Path

from experiment.backends.base import ModelBackend
from experiment.schema import ModelResponse, Scenario


class ManualTranscriptBackend(ModelBackend):
    name = "manual"

    def __init__(self, response_file: str | Path, model: str, model_version: str) -> None:
        self.response_file = Path(response_file)
        self.model = model
        self.model_version = model_version

    def generate(self, scenario: Scenario) -> ModelResponse:
        raw_output = self.response_file.read_text(encoding="utf-8")
        return ModelResponse(raw_output=raw_output, model=self.model, model_version=self.model_version)
