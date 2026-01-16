"""
AI-OS: Agentic Macro Framework

A Python DSL for writing composable, debuggable agentic workflows with human oversight.
Built on Claude Code for native tool use capabilities.

Usage:
    import ai_os as ai

    def main(ctx, **kwargs):
        result = ai.chat("Hello")
        ai.log(result)

Version: 2.0.0 (Claude Code Native)
"""

from ai_os.core.dsl import (
    # Output
    log,
    status,

    # Human interaction
    approve,
    ask,
    confirm_changes,

    # LLM operations
    chat,
    chat_json,
    vision,

    # Parallel execution
    gather,

    # File operations
    read,
    write,
    edit,
    exists,
    glob,

    # Shell operations
    shell,
    run,

    # Context
    get_var,
    set_var,
    get_cost,

    # Utilities
    sleep,
    timestamp,
    random_id,

    # Configuration
    config,

    # Internal
    _set_context,
    _clear_context,
)

# Legacy compatibility - import macro_helpers as ah
from ai_os.core import macro_helpers as ah

__version__ = "2.0.0"

__all__ = [
    # Output
    "log",
    "status",

    # Human interaction
    "approve",
    "ask",
    "confirm_changes",

    # LLM operations
    "chat",
    "chat_json",
    "vision",

    # Parallel execution
    "gather",

    # File operations
    "read",
    "write",
    "edit",
    "exists",
    "glob",

    # Shell operations
    "shell",
    "run",

    # Context
    "get_var",
    "set_var",
    "get_cost",

    # Utilities
    "sleep",
    "timestamp",
    "random_id",

    # Configuration
    "config",

    # Legacy
    "ah",
]
