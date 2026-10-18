"""Mercury Runtime: frontier agent runtime, provider adapters and the A/B control group.

Builds on the ``mercury`` flywheel (``mercury-harness``). Optionally picks up the
application forge (``mercury_forge``) at call time when it is installed.
"""

from mercury_runtime.providers import (
    FRONTIER_MODELS,
    FrontierModelSpec,
    FrontierOnlyError,
    ModelSpec,
    NetworkDropError,
    ProviderId,
    get_frontier_model,
    list_frontier_models,
)
from mercury_runtime.runtime import (
    AgentRunResult,
    IterationLimitExceededError,
    MercuryAgentRuntime,
    SoftTrajectoryPivotError,
)

__all__ = [
    "AgentRunResult",
    "FRONTIER_MODELS",
    "FrontierModelSpec",
    "FrontierOnlyError",
    "IterationLimitExceededError",
    "MercuryAgentRuntime",
    "ModelSpec",
    "NetworkDropError",
    "ProviderId",
    "SoftTrajectoryPivotError",
    "get_frontier_model",
    "list_frontier_models",
]

__version__ = "0.4.0"
