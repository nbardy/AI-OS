# File: ai_os/core/macro_helpers.py
# Description: Light-weight facade that macros import as `ah`.
# All public helpers forward to the *current* MacroRunner instance.

from __future__ import annotations # Allows forward references like "MacroRunner"
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

# Avoid circular import by only importing MacroRunner type for type checking
if TYPE_CHECKING:
    from ai_os.core.macro_runner import MacroRunner

__all__ = [
    "set_runner", # Internal helper for the runner
    "log", "log_to_context", "chat", "shell", "patch", "approve",
    "get_var", "get_last_shell_exit_code" # Context accessors
]

# ------------------------------------------------------------------ #
# Runner plumbing (internal)                                         #
# ------------------------------------------------------------------ #

_runner: "MacroRunner | None" = None


def set_runner(runner: "MacroRunner | None") -> None:
    """Installed by MacroRunner at start/end of a /macro run."""
    global _runner
    _runner = runner


def _require_runner() -> "MacroRunner":
    """Ensures a MacroRunner instance is active."""
    if _runner is None:
        # Provide a clearer error message specific to this module
        raise RuntimeError("AI-OS Macro helpers used outside an active MacroRunner run. "
                           "Ensure you are calling these from within a macro's main() function.")
    return _runner


# ------------------------------------------------------------------ #
# Public helper API (called by macro scripts)                        #
# ------------------------------------------------------------------ #

def log(msg: str) -> None:
    """Log a message to the user console."""
    _require_runner().log(msg)

def log_to_context(msg: str) -> None:
    """Log a message to the AI-OS context history (as a system message from Macro)."""
    _require_runner().log_to_context(msg)

def chat(prompt: str) -> str:
    """
    Send a prompt to the LLM via the chat command.
    Streams the reply to the console and returns the full assistant response string.
    """
    return _require_runner().chat(prompt)

def shell(cmd: str, capture: bool = False) -> Any:
    """
    Execute a shell command via the run command.
    Returns the shell execution result (stdout string if capture=True, returncode integer otherwise).
    """
    return _require_runner().shell(cmd, capture)

def patch(plan: str, user_approval: bool = True) -> Dict[str, Any] | None:
    """
    Initiate the patch workflow (generate, preview, apply).
    Returns the result dictionary from the patch application workflow or None on critical failure.
    """
    return _require_runner().patch(plan, user_approval)

def approve(msg: str) -> bool:
    """
    Prompt the user for Y/N approval via the CLI's prompt mechanism.
    Returns the boolean user response (True for 'y', False for 'n').
    """
    return _require_runner().approve(msg)

def get_var(name: str, default: Any = None) -> Any:
    """Get a variable passed to the macro via key=value arguments."""
    # Access context directly via runner
    return _require_runner().get_var(name, default)

def get_last_shell_exit_code() -> int:
    """Get the exit code of the last shell command run via ah.shell()."""
    # Access context directly via runner
    return _require_runner().get_last_shell_exit_code() 