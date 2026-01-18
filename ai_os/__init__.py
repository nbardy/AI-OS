"""
AI-OS: Agentic Macro Framework

A Python DSL for writing composable, debuggable agentic workflows with human oversight.
Built on Claude Code for native tool use capabilities.

Usage:
    import ai_os as ai

    # Standalone DSL (works outside macros)
    response = ai.chat("Hello")
    ai.log(response)

    # Or within a macro with context
    def main(ctx, **kwargs):
        result = ai.chat("Hello")
        ai.log(result)

Version: 2.0.0 (Claude Code Native)
"""

# Primary API - DSL functions (work standalone)
from ai_os.core.dsl import (
    log, status,
    approve, ask, confirm_changes,
    chat, chat_json, vision,
    spawn, join, gather, gather_async,
    read, write, edit, exists, glob,
    shell, run,
    get_var, set_var, get_cost,
    sleep, timestamp, random_id,
    config,
    _set_context, _clear_context,
)

# Legacy compatibility - import macro_helpers as ah
from ai_os.core import macro_helpers as ah

__version__ = "2.0.0"

__all__ = [
    "log", "status",
    "approve", "ask", "confirm_changes",
    "chat", "chat_json", "vision",
    "spawn", "join", "gather", "gather_async",
    "read", "write", "edit", "exists", "glob",
    "shell", "run",
    "get_var", "set_var", "get_cost",
    "sleep", "timestamp", "random_id",
    "config",
    "ah",
]
