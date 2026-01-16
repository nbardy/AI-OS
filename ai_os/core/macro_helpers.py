# File: ai_os/core/macro_helpers.py
# Description: Light-weight facade that macros import as `ah`.
# All public helpers forward to the *current* MacroRunner instance.
#
# V2: Added async_=True support, edit(), vision(), read(), write() functions.

from __future__ import annotations

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING, Coroutine

# Avoid circular import by only importing MacroRunner type for type checking
if TYPE_CHECKING:
    from ai_os.core.macro_runner import MacroRunner

__all__ = [
    # Internal
    "set_runner",
    # Output
    "log", "log_to_context",
    # LLM Operations
    "chat", "chat_json", "vision", "edit",
    # File Operations
    "read", "write", "exists",
    # Shell
    "shell",
    # Human Interaction
    "approve",
    # Context
    "get_var", "set_var", "get_last_shell_exit_code", "get_cost",
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
        raise RuntimeError(
            "AI-OS Macro helpers used outside an active MacroRunner run. "
            "Ensure you are calling these from within a macro's main() function."
        )
    return _runner


# ------------------------------------------------------------------ #
# Output Functions
# ------------------------------------------------------------------ #

def log(msg: str) -> None:
    """Log a message to the user console. Supports Rich markup."""
    _require_runner().log(msg)


def log_to_context(msg: str) -> None:
    """Log a message to the AI-OS context history (as a system message from Macro)."""
    _require_runner().log_to_context(msg)


# ------------------------------------------------------------------ #
# LLM Operations
# ------------------------------------------------------------------ #

def chat(
    prompt: str,
    include_context: bool = True,
    image_path: str = None,
    model: str = None,
    async_: bool = False
) -> Union[str, Coroutine[Any, Any, str]]:
    """
    Send a prompt to Claude via Claude Code.

    Args:
        prompt: The prompt to send
        include_context: If True (default), includes conversation history
        image_path: Optional path to an image file (for vision)
        model: Model override (sonnet, opus, haiku)
        async_: If True, returns a coroutine for use with asyncio.gather()

    Returns:
        Response string, or coroutine if async_=True

    Example:
        # Sync (default)
        response = ah.chat("What is 2+2?")

        # Async (for parallel execution)
        results = await asyncio.gather(
            ah.chat("prompt 1", async_=True),
            ah.chat("prompt 2", async_=True),
        )
    """
    return _require_runner().chat(
        prompt,
        include_context=include_context,
        image_path=image_path,
        model=model,
        async_=async_
    )


def chat_json(
    prompt: str,
    model: str = None,
    async_: bool = False
) -> Union[Any, Coroutine[Any, Any, Any]]:
    """
    Get structured JSON response from Claude.

    Args:
        prompt: Should request JSON output
        model: Model override
        async_: If True, returns coroutine

    Returns:
        Parsed JSON (dict or list), or coroutine if async_=True
    """
    return _require_runner().chat_json(prompt, model=model, async_=async_)


def vision(
    prompt: str,
    image: str,
    model: str = None,
    async_: bool = False
) -> Union[str, Coroutine[Any, Any, str]]:
    """
    Analyze an image with Claude.

    Args:
        prompt: Analysis prompt
        image: Path to image file
        model: Model override
        async_: If True, returns coroutine

    Returns:
        Analysis response, or coroutine if async_=True
    """
    return _require_runner().vision(prompt, image, model=model, async_=async_)


def edit(
    instruction: str,
    file: str = None,
    async_: bool = False
) -> Union[bool, Coroutine[Any, Any, bool]]:
    """
    Have Claude edit files.

    Args:
        instruction: What changes to make
        file: Specific file to edit (optional)
        async_: If True, returns coroutine

    Returns:
        True if successful, or coroutine if async_=True
    """
    return _require_runner().edit(instruction, file=file, async_=async_)


# Legacy alias for patch (maps to edit)
def patch(plan: str, user_approval: bool = True) -> Dict[str, Any] | None:
    """
    Legacy patch function - now wraps edit().

    For backwards compatibility with v1 macros.
    """
    success = _require_runner().edit(plan)
    return {
        "applied": success,
        "summary": "Edit completed" if success else "Edit failed",
        "files": []
    }


# ------------------------------------------------------------------ #
# File Operations (direct, not through Claude)
# ------------------------------------------------------------------ #

def read(path: str) -> str:
    """Read file contents directly."""
    return _require_runner().read(path)


def write(path: str, content: str) -> None:
    """Write file contents directly."""
    _require_runner().write(path, content)


def exists(path: str) -> bool:
    """Check if file exists."""
    return _require_runner().exists(path)


# ------------------------------------------------------------------ #
# Shell Operations
# ------------------------------------------------------------------ #

def shell(cmd: str, capture: bool = False, check: bool = False) -> Any:
    """
    Execute a shell command.

    Args:
        cmd: Shell command to run
        capture: If True, return stdout instead of exit code
        check: If True, raise on non-zero exit

    Returns:
        Exit code (int) or stdout (str) if capture=True
    """
    return _require_runner().shell(cmd, capture=capture, check=check)


# ------------------------------------------------------------------ #
# Human Interaction
# ------------------------------------------------------------------ #

def approve(msg: str) -> bool:
    """
    Prompt the user for Y/N approval.

    Args:
        msg: Message to display

    Returns:
        True for 'y', False for 'n'
    """
    return _require_runner().approve(msg)


# ------------------------------------------------------------------ #
# Context and State
# ------------------------------------------------------------------ #

def get_var(name: str, default: Any = None) -> Any:
    """Get a variable passed to the macro via key=value arguments."""
    return _require_runner().get_var(name, default)


def set_var(name: str, value: Any) -> None:
    """Set a context variable."""
    _require_runner().set_var(name, value)


def get_last_shell_exit_code() -> int:
    """Get the exit code of the last shell command run via ah.shell()."""
    return _require_runner().get_last_shell_exit_code()


def get_cost() -> Dict[str, Any]:
    """
    Get accumulated cost for this macro run.

    Returns:
        Dict with input_tokens, output_tokens, total_cost_usd
    """
    return _require_runner().get_cost()
