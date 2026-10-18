"""Mercury Harness: embed frontier agent operations into lesser models."""

from mercury.embed import EmbedderProtocol, HashingEmbedder
from mercury.harness import MercuryHarness
from mercury.inject import OperatingPack
from mercury.models import AgentTrace, OperationalCard, TraceEvent, TraceOutcome
from mercury.providers import (
    FRONTIER_MODELS,
    FrontierModelSpec,
    FrontierOnlyError,
    NetworkDropError,
    ProviderId,
    get_frontier_model,
    list_frontier_models,
)
from mercury.runtime import (
    AgentRunResult,
    IterationLimitExceededError,
    MercuryAgentRuntime,
    SoftTrajectoryPivotError,
)
from mercury.templates import (
    APP_TEMPLATES,
    AppTemplate,
    BuiltAppArtifact,
    build_app_from_template,
    generate_or_load_spec_manifest,
    get_build_template,
    list_build_templates,
    verify_code_against_spec,
)
from mercury.tiers import ModelTier, classify_model

__all__ = [
    "MercuryHarness",
    "MercuryAgentRuntime",
    "AgentRunResult",
    "IterationLimitExceededError",
    "SoftTrajectoryPivotError",
    "NetworkDropError",
    "APP_TEMPLATES",
    "AppTemplate",
    "BuiltAppArtifact",
    "list_build_templates",
    "get_build_template",
    "build_app_from_template",
    "generate_or_load_spec_manifest",
    "verify_code_against_spec",
    "FRONTIER_MODELS",
    "FrontierModelSpec",
    "FrontierOnlyError",
    "ProviderId",
    "list_frontier_models",
    "get_frontier_model",
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

__version__ = "0.4.0"
