"""Mercury Harness: the flywheel that embeds frontier agent operations into lesser models.

This package is the flywheel only: trace capture, distillation, the knowledge store,
retrieval, operating packs, grading and the CLI. It has no dependency on
the agent runtime (``mercury_runtime``) or the application forge (``mercury_forge``).
Names those packages own stay importable from here (``from mercury import
MercuryAgentRuntime``) and are loaded on first access, only if the package is installed.
"""

from __future__ import annotations

import importlib
from typing import Any

from mercury.embed import EmbedderProtocol, HashingEmbedder
from mercury.harness import MercuryHarness
from mercury.inject import OperatingPack
from mercury.models import AgentTrace, OperationalCard, TraceEvent, TraceOutcome
from mercury.tiers import ModelTier, classify_model

_LAZY: dict[str, tuple[str, str]] = {}
for _name in (
    "AgentRunResult",
    "IterationLimitExceededError",
    "MercuryAgentRuntime",
    "SoftTrajectoryPivotError",
):
    _LAZY[_name] = ("mercury_runtime.runtime", "mercury-runtime")
for _name in (
    "FRONTIER_MODELS",
    "FrontierModelSpec",
    "FrontierOnlyError",
    "NetworkDropError",
    "ProviderId",
    "get_frontier_model",
    "list_frontier_models",
):
    _LAZY[_name] = ("mercury_runtime.providers", "mercury-runtime")
for _name in (
    "APP_TEMPLATES",
    "AppTemplate",
    "BuiltAppArtifact",
    "build_app_from_template",
    "generate_or_load_spec_manifest",
    "get_build_template",
    "list_build_templates",
    "verify_code_against_spec",
):
    _LAZY[_name] = ("mercury_forge.templates", "mercury-forge")

__all__ = [
    "MercuryHarness",
    "OperatingPack",
    "EmbedderProtocol",
    "HashingEmbedder",
    "AgentTrace",
    "OperationalCard",
    "TraceEvent",
    "TraceOutcome",
    "ModelTier",
    "classify_model",
]


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module 'mercury' has no attribute {name!r}")
    module_name, dist = target
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name and module_name.startswith(exc.name):
            raise ImportError(f"`mercury.{name}` lives in {dist}; install it with `pip install {dist}`") from exc
        raise
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))


__version__ = "0.4.0"
