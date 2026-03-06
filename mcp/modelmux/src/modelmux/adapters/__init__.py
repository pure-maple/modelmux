"""Model CLI adapters for modelmux."""

from modelmux.adapters.base import AdapterResult, BaseAdapter
from modelmux.adapters.claude import ClaudeAdapter
from modelmux.adapters.codex import CodexAdapter
from modelmux.adapters.gemini import GeminiAdapter
from modelmux.adapters.ollama import OllamaAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "codex": CodexAdapter,
    "gemini": GeminiAdapter,
    "claude": ClaudeAdapter,
    "ollama": OllamaAdapter,
}

__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "CodexAdapter",
    "GeminiAdapter",
    "ClaudeAdapter",
    "OllamaAdapter",
    "ADAPTERS",
]
