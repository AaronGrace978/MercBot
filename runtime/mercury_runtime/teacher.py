"""Teacher-model card validator: the real-model implementation of the validation gate."""

from __future__ import annotations

from typing import Callable

from mercury.validate import CompletionCardValidator
from mercury_runtime.providers import call_frontier_provider, get_frontier_model


class TeacherCardValidator(CompletionCardValidator):
    """One frontier-model call per card; the model must be frontier tier."""

    def __init__(
        self,
        model: str = "gemini-4-argon-high",
        *,
        api_keys: dict[str, str] | None = None,
        complete: Callable[[str], str] | None = None,
    ) -> None:
        if complete is None:
            get_frontier_model(model)
        self.model = model
        self.api_keys = api_keys
        super().__init__(complete or self._call_teacher)

    def _call_teacher(self, prompt: str) -> str:
        spec = get_frontier_model(self.model)
        turn = call_frontier_provider(
            spec,
            [{"role": "user", "content": prompt}],
            None,
            api_keys=self.api_keys,
            allow_offline_fallback=False,
        )
        return turn.content
