"""A backend that returns a response given in-process rather than on disk.

Not used for real trials (a real trial's raw output should always be a file
someone can point back to). Exists for the harness's own tests and for
quick dry-runs of scoring logic without round-tripping through a file.
"""
from __future__ import annotations

from experiment.backends.base import ModelBackend
from experiment.schema import ModelResponse, Scenario


class FixedResponseBackend(ModelBackend):
    name = "fixed"

    def __init__(self, raw_output: str, model: str, model_version: str) -> None:
        self.raw_output = raw_output
        self.model = model
        self.model_version = model_version

    def generate(self, scenario: Scenario) -> ModelResponse:
        return ModelResponse(raw_output=self.raw_output, model=self.model, model_version=self.model_version)
