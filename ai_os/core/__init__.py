"""
AI-OS Core - Core components for the agentic macro framework.

Contains:
- orchestrator: Claude Code subprocess wrapper
- macro_helpers: DSL functions (ah.chat, ah.edit, etc.)
- macro_runner: Executes Python macro scripts
- commands: CLI command implementations
- models: Data structures
"""

from ai_os.core.orchestrator import (
    ClaudeOrchestrator,
    ClaudeResult,
    get_orchestrator,
    reset_orchestrator,
    configure_orchestrator,
)

from ai_os.core.macro_helpers import (
    log,
    chat,
    chat_json,
    vision,
    edit,
    read,
    write,
    exists,
    shell,
    approve,
    get_var,
    set_var,
    get_cost,
)

__all__ = [
    # Orchestrator
    "ClaudeOrchestrator",
    "ClaudeResult",
    "get_orchestrator",
    "reset_orchestrator",
    "configure_orchestrator",
    # DSL functions
    "log",
    "chat",
    "chat_json",
    "vision",
    "edit",
    "read",
    "write",
    "exists",
    "shell",
    "approve",
    "get_var",
    "set_var",
    "get_cost",
]
