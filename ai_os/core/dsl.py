# ai_os/core/dsl.py
"""
AI-OS DSL - Standalone API for agentic workflows.

This module provides a clean, standalone API that works both inside and outside
of macro contexts. It uses a global orchestrator instance for LLM operations.

Usage:
    import ai_os as ai

    response = ai.chat("Hello")
    ai.log(response)
"""

from __future__ import annotations

import time
import uuid
import subprocess
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union, Coroutine, TYPE_CHECKING
from datetime import datetime

from rich.console import Console
from rich.prompt import Confirm, Prompt

from ai_os.core.orchestrator import (
    ClaudeOrchestrator,
    get_orchestrator,
    configure_orchestrator,
    reset_orchestrator,
)

# Global console for output
_console: Console = Console()

# Global context for variables
_context: Dict[str, Any] = {
    "vars": {},
}


# =========================================================================
# Configuration
# =========================================================================


def config(
    working_dir: str = None,
    default_model: str = "sonnet",
    timeout: int = 600,
    skip_permissions: bool = True,
) -> ClaudeOrchestrator:
    """
    Configure the global orchestrator.

    Args:
        working_dir: Working directory for file operations
        default_model: Default model (haiku, sonnet, opus)
        timeout: Timeout in seconds
        skip_permissions: Skip permission prompts

    Returns:
        The configured orchestrator instance
    """
    return configure_orchestrator(
        working_dir=working_dir,
        default_model=default_model,
        timeout=timeout,
        skip_permissions=skip_permissions,
    )


def _set_context(ctx: Dict[str, Any]) -> None:
    """Set the context (used by macro runner)."""
    global _context
    _context = ctx


def _clear_context() -> None:
    """Clear the context."""
    global _context
    _context = {"vars": {}}


# =========================================================================
# Output Functions
# =========================================================================


def log(message: str) -> None:
    """
    Print a message to the console. Supports Rich markup.

    Args:
        message: The message to print (supports Rich markup like [bold], [red], etc.)
    """
    _console.print(message)


@contextmanager
def status(message: str):
    """
    Show a spinner/status indicator while code runs.

    Args:
        message: Status message to display

    Usage:
        with ai.status("Processing..."):
            do_work()
    """
    with _console.status(message):
        yield


# =========================================================================
# Human Interaction
# =========================================================================


def approve(message: str) -> bool:
    """
    Ask the user for Y/N approval.

    Args:
        message: The approval prompt

    Returns:
        True if user approves, False otherwise
    """
    return Confirm.ask(message, console=_console)


def ask(question: str, choices: List[str] = None) -> str:
    """
    Ask the user a question.

    Args:
        question: The question to ask
        choices: Optional list of choices

    Returns:
        User's response
    """
    if choices:
        return Prompt.ask(question, choices=choices, console=_console)
    return Prompt.ask(question, console=_console)


def confirm_changes(files: List[str]) -> bool:
    """
    Show file diffs and ask for approval.

    Args:
        files: List of file paths to show diffs for

    Returns:
        True if user approves
    """
    for file_path in files:
        result = subprocess.run(
            ["git", "diff", "--", file_path],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            _console.print(f"\n[bold]Changes in {file_path}:[/bold]")
            _console.print(result.stdout)

    return approve("Apply these changes?")


# =========================================================================
# LLM Operations
# =========================================================================


def chat(
    prompt: str,
    context: List[str] = None,
    model: str = None,
    async_: bool = False,
    **kwargs,
) -> Union[str, Coroutine[Any, Any, str]]:
    """
    Send a prompt to Claude and get a text response.

    Args:
        prompt: The prompt to send
        context: List of file paths to include as context
        model: Model override (haiku, sonnet, opus)
        async_: If True, returns a coroutine for asyncio.gather()

    Returns:
        Response string, or coroutine if async_=True
    """
    orch = get_orchestrator()
    return orch.chat(prompt, model=model, context_files=context, async_=async_)


def chat_json(
    prompt: str,
    model: str = None,
    async_: bool = False,
    **kwargs,
) -> Union[Any, Coroutine[Any, Any, Any]]:
    """
    Get structured JSON output from Claude.

    Args:
        prompt: The prompt (should request JSON)
        model: Model override
        async_: If True, returns coroutine

    Returns:
        Parsed JSON (dict or list), or coroutine if async_=True
    """
    orch = get_orchestrator()
    return orch.chat_json(prompt, model=model, async_=async_)


def vision(
    prompt: str,
    image: str,
    model: str = None,
    async_: bool = False,
    **kwargs,
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
    orch = get_orchestrator()
    return orch.vision(prompt, image, model=model, async_=async_)


# =========================================================================
# Parallel Execution
# =========================================================================


def spawn(
    prompt: str,
    output_file: str = None,
    model: str = None,
    **kwargs,
):
    """
    Spawn an async Claude process.

    Args:
        prompt: The prompt to send
        output_file: Optional file to write result to
        model: Model override

    Returns:
        SpawnedAgent that can be passed to join()
    """
    orch = get_orchestrator()
    return orch.spawn(prompt, output_file=output_file, model=model, **kwargs)


def join(agents, timeout: float = None):
    """
    Wait for spawned agents to complete.

    Args:
        agents: List of SpawnedAgent from spawn()
        timeout: Optional timeout in seconds

    Returns:
        List of ClaudeResult in the same order as agents
    """
    orch = get_orchestrator()
    return orch.join(agents, timeout=timeout)


def gather(*prompts: str, model: str = None, **kwargs) -> List[str]:
    """
    Run multiple prompts in parallel and return results.

    Args:
        *prompts: Variable number of prompts to run
        model: Model override (applies to all)

    Returns:
        List of response strings in the same order as prompts
    """
    orch = get_orchestrator()
    return orch.gather(*prompts, model=model, **kwargs)


async def gather_async(*prompts: str, model: str = None, **kwargs) -> List[str]:
    """
    Run multiple prompts in parallel using true asyncio (fastest option).

    Use this when you're already in an async context for maximum performance.

    Args:
        *prompts: Variable number of prompts to run
        model: Model override (applies to all)

    Returns:
        List of response strings in the same order as prompts

    Example:
        import asyncio
        results = asyncio.run(ai.gather_async("prompt1", "prompt2", "prompt3"))
    """
    orch = get_orchestrator()
    return await orch.gather_async(*prompts, model=model, **kwargs)


# =========================================================================
# File Operations
# =========================================================================


def read(path: str) -> str:
    """
    Read a file's contents.

    Args:
        path: Path to the file

    Returns:
        File contents as string
    """
    orch = get_orchestrator()
    return orch.read(path)


def write(path: str, content: str) -> None:
    """
    Write content to a file.

    Args:
        path: Path to the file
        content: Content to write
    """
    orch = get_orchestrator()
    orch.write(path, content)


def edit(
    instruction: str,
    file: str = None,
    async_: bool = False,
) -> Union[bool, Coroutine[Any, Any, bool]]:
    """
    Have Claude edit a file intelligently.

    Args:
        instruction: What to do
        file: Specific file to edit (optional)
        async_: If True, returns coroutine

    Returns:
        True if successful
    """
    orch = get_orchestrator()
    return orch.edit(instruction, file=file, async_=async_)


def exists(path: str) -> bool:
    """
    Check if a file exists.

    Args:
        path: Path to the file

    Returns:
        True if file exists
    """
    orch = get_orchestrator()
    return orch.exists(path)


def glob(pattern: str) -> List[str]:
    """
    Find files matching a pattern.

    Args:
        pattern: Glob pattern (e.g., "*.py", "**/*.glsl")

    Returns:
        List of matching file paths
    """
    orch = get_orchestrator()
    base_path = Path(orch.working_dir)
    return [str(p) for p in base_path.glob(pattern)]


# =========================================================================
# Shell Operations
# =========================================================================


def shell(
    command: str,
    capture: bool = False,
    check: bool = False,
) -> Union[int, str]:
    """
    Execute a shell command.

    Args:
        command: Shell command to run
        capture: If True, return stdout instead of exit code
        check: If True, raise on non-zero exit

    Returns:
        Exit code (int) or stdout (str) if capture=True
    """
    orch = get_orchestrator()
    return orch.shell(command, capture=capture, check=check)


def run(command: str, **kwargs) -> subprocess.CompletedProcess:
    """
    Low-level shell access with full control.

    Args:
        command: Shell command to run
        **kwargs: Passed to subprocess.run

    Returns:
        CompletedProcess object
    """
    orch = get_orchestrator()
    return subprocess.run(
        command,
        shell=True,
        cwd=orch.working_dir,
        capture_output=True,
        text=True,
        **kwargs,
    )


# =========================================================================
# Context and State
# =========================================================================


def get_var(name: str, default: Any = None) -> Any:
    """
    Get a variable from context.

    Args:
        name: Variable name
        default: Default value if not found

    Returns:
        Variable value or default
    """
    return _context.get("vars", {}).get(name, default)


def set_var(name: str, value: Any) -> None:
    """
    Set a context variable.

    Args:
        name: Variable name
        value: Value to set
    """
    if "vars" not in _context:
        _context["vars"] = {}
    _context["vars"][name] = value


def get_cost() -> Dict[str, Any]:
    """
    Get cumulative cost for this session.

    Returns:
        Dict with input_tokens, output_tokens, total_cost_usd
    """
    orch = get_orchestrator()
    return orch.get_cost()


# =========================================================================
# Utility Functions
# =========================================================================


def sleep(seconds: float) -> None:
    """
    Pause execution.

    Args:
        seconds: Number of seconds to sleep
    """
    time.sleep(seconds)


def timestamp() -> str:
    """
    Get current timestamp (useful for filenames).

    Returns:
        ISO format timestamp: 2026-01-17T14-30-45
    """
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def random_id(length: int = 8) -> str:
    """
    Generate a random ID (useful for unique filenames).

    Args:
        length: Length of the ID (default 8)

    Returns:
        Random hex string
    """
    return uuid.uuid4().hex[:length]


# =========================================================================
# Exports
# =========================================================================

__all__ = [
    # Configuration
    "config",
    "_set_context",
    "_clear_context",
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
    "spawn",
    "join",
    "gather",
    "gather_async",
    # File operations
    "read",
    "write",
    "edit",
    "exists",
    "glob",
    # Shell operations
    "shell",
    "run",
    # Context and state
    "get_var",
    "set_var",
    "get_cost",
    # Utilities
    "sleep",
    "timestamp",
    "random_id",
]
