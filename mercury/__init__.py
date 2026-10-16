"""Mercury Harness: embed frontier agent operations into lesser models."""

from mercury.embed import EmbedderProtocol, HashingEmbedder
from mercury.harness import MercuryHarness
from mercury.inject import OperatingPack
from mercury.models import AgentTrace, OperationalCard, TraceEvent, TraceOutcome
from mercury.providers import (
    FRONTIER_MODELS,
    FrontierModelSpec,
    FrontierOnlyError,
    ProviderId,
    get_frontier_model,
    list_frontier_models,
)
from mercury.runtime import AgentRunResult, MercuryAgentRuntime
from mercury.tiers import ModelTier, classify_model

__all__ = [
    "MercuryHarness",
    "MercuryAgentRuntime",
    "AgentRunResult",
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

__version__ = "0.1.0"
