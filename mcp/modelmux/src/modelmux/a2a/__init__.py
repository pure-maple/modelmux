"""A2A (Agent-to-Agent) protocol implementation for modelmux.

Enables true multi-agent collaboration with iterative feedback loops,
going beyond single-prompt dispatch to real agent-to-agent negotiation.
"""

from modelmux.a2a.engine import CollaborationEngine, EngineConfig
from modelmux.a2a.http_server import A2AServer
from modelmux.a2a.patterns import (
    BUILTIN_PATTERNS,
    CollaborationPattern,
    get_pattern,
    list_patterns,
)
from modelmux.a2a.types import (
    AgentCard,
    Artifact,
    CollaborationTask,
    ConvergenceDecision,
    ConvergenceSignal,
    Message,
    Part,
    TaskState,
    Turn,
)

__all__ = [
    "A2AServer",
    "AgentCard",
    "Artifact",
    "BUILTIN_PATTERNS",
    "CollaborationEngine",
    "CollaborationPattern",
    "CollaborationTask",
    "ConvergenceDecision",
    "ConvergenceSignal",
    "EngineConfig",
    "Message",
    "Part",
    "TaskState",
    "Turn",
    "get_pattern",
    "list_patterns",
]
