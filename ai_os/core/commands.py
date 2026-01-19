"""
AI-OS Commands - CLI command implementations.

These functions are called by cli.py when the user runs commands like:
- > or /chat - Chat with Claude
- + or /patch - Have Claude edit files
- ! or /run - Run shell commands
- @ or /macro - Run macro scripts

V2: Now uses Claude Code via orchestrator instead of OpenRouter.
"""

from typing import List, Dict, Any, Optional, Generator, Tuple

# =============================================================================
# Command Parsing (shared between TUI and headless CLI)
# =============================================================================

# Canonical command names and their aliases
ALIASES = {
    '>': '/chat',
    '+': '/patch',
    '!': '/run',
    '@': '/macro',
    '?': '/search',
}

# All commands (for completion, help, etc.)
COMMANDS = ['/chat', '/macro', '/patch', '/run', '/context', '/model', '/exit', '/help', '/quit', '/history', '/search']


def parse_input(line: str) -> Tuple[str, str]:
    """
    Parse user input into (command, argument).

    Handles both aliases (>, @, +, !, ?) and full commands (/chat, /macro, etc.).

    Args:
        line: Raw user input string

    Returns:
        Tuple of (command, argument) where command is the canonical form like '/chat'

    Examples:
        parse_input("> hello") -> ('/chat', 'hello')
        parse_input("@ macro.py arg=val") -> ('/macro', 'macro.py arg=val')
        parse_input("/chat hello") -> ('/chat', 'hello')
        parse_input("just text") -> ('/chat', 'just text')  # default to chat
    """
    line = line.strip()
    if not line:
        return ('', '')

    # Check for alias prefix (single char like >, @, +, !, ?)
    if line[0] in ALIASES:
        cmd = ALIASES[line[0]]
        arg = line[1:].strip()
        return (cmd, arg)

    # Check for slash commands
    if line.startswith('/'):
        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ''
        return (cmd, arg)

    # Default: treat as chat
    return ('/chat', line)


from pathlib import Path
import time

# Import the new orchestrator
from ai_os.core.orchestrator import get_orchestrator

# Import context manager for history tracking
from ai_os.utils.context import context_manager

# Third-Party Imports
from rich.console import Console


# =============================================================================
# Streaming Helper (shared by chat and search)
# =============================================================================

def _stream_response(
    prompt: str,
    system_instruction: str,
    console: Console = None,
    status_msg: str = "Thinking...",
    timing_label: str = "Thinking",
    context_prefix: str = "",
    error_prefix: str = "Chat",
) -> Generator[str, None, None]:
    """
    Shared streaming logic for chat and search commands.

    Args:
        prompt: User prompt to send
        system_instruction: System instruction for Claude
        console: Optional console for status display
        status_msg: Message shown in spinner (e.g., "Thinking...", "Searching...")
        timing_label: Label for timing output (e.g., "Thinking", "Search")
        context_prefix: Prefix for context history (e.g., "[Search Result] ")
        error_prefix: Prefix for error messages (e.g., "Chat", "Search")
    """
    think_start = time.time()
    think_time = None
    stream_start = None
    full_response = ""

    orch = get_orchestrator()

    try:
        stream_gen = orch.chat_streaming(prompt, system_instruction=system_instruction)
        first_chunk = None

        if console:
            with console.status(status_msg, spinner="dots"):
                first_chunk = next(stream_gen, None)
                if first_chunk:
                    think_time = time.time() - think_start
                    stream_start = time.time()

            if first_chunk:
                yield first_chunk
                full_response += first_chunk

            for chunk in stream_gen:
                yield chunk
                full_response += chunk
        else:
            for chunk in stream_gen:
                if stream_start is None:
                    think_time = time.time() - think_start
                    stream_start = time.time()
                yield chunk
                full_response += chunk

        if stream_start and think_time:
            stream_time = time.time() - stream_start
            yield f"\n[dim]({timing_label}: {think_time:.1f}s, Streaming: {stream_time:.1f}s)[/dim]"

        if full_response:
            context_manager.add_message(role="assistant", content=f"{context_prefix}{full_response}")

    except Exception as e:
        error_msg = f"{error_prefix} error: {e}"
        context_manager.add_message(role="system", content=error_msg)
        yield f"[red]{error_msg}[/red]"


# =============================================================================
# Chat Command (> or /chat)
# =============================================================================

def chat(prompt: str, console: Console = None) -> Generator[str, None, None]:
    """
    Sends a prompt to Claude via Claude Code.

    This is a READ-ONLY operation - Claude will not edit files.
    It can read files for context but won't make changes.

    Yields response chunks for streaming display.
    """
    context_manager.add_message(role="user", content=prompt)

    system_instruction = """This is a chat/question command.
You may read files for context if needed, but do NOT edit or write any files.
Just answer the user's question or discuss the topic."""

    yield from _stream_response(
        prompt=prompt,
        system_instruction=system_instruction,
        console=console,
        status_msg="Thinking...",
        timing_label="Thinking",
        error_prefix="Chat",
    )


# =============================================================================
# Patch Command (+ or /patch)
# =============================================================================

def patch(
    plan: str,
    strategy_name: str = "full_file",  # noqa: ARG001 - kept for v1 API compat
    console: Console = None,
    user_approval_override: Optional[bool] = None  # noqa: ARG001 - kept for v1 API compat
) -> Dict[str, Any]:
    """
    Have Claude edit files to implement the given plan.

    This tells Claude Code to use its Edit tool to make changes.

    Note: strategy_name and user_approval_override are kept for v1 API
    compatibility but are no longer used in v2 (Claude Code handles these).

    Args:
        plan: Description of what changes to make
        strategy_name: DEPRECATED - Ignored in v2 (was XML strategy selector)
        console: Console for output
        user_approval_override: DEPRECATED - Ignored in v2 (Claude Code handles approvals)

    Returns:
        Dict with 'applied' (bool) and 'summary' (str)
    """
    # Add to history
    context_manager.add_message(role="user", content=f"[Patch Request] {plan}")

    # Build instruction for Claude
    system_instruction = """This is an EDIT command. The user wants you to modify files.
Use the Edit tool to make surgical changes to files.
After making changes, briefly summarize what you did."""

    orch = get_orchestrator()

    try:
        if console:
            console.print(f"[dim]Generating patch for: {plan[:100]}...[/dim]")

        # Call Claude Code with edit instruction
        response = orch.chat(plan, system_instruction=system_instruction)

        # Log result
        context_manager.add_message(role="assistant", content=f"[Patch Applied] {response}")

        if console:
            console.print(f"\n[green]Changes applied.[/green]")
            console.print(response)

        return {
            "applied": True,
            "summary": response,
            "patch_obj": None  # No longer using Patch objects
        }

    except Exception as e:
        error_msg = f"Patch error: {e}"
        context_manager.add_message(role="system", content=error_msg)
        if console:
            console.print(f"[red]{error_msg}[/red]")
        return {
            "applied": False,
            "error": str(e),
            "summary": error_msg
        }


# =============================================================================
# Search Command (? or /search)
# =============================================================================

def search(query: str, console: Console = None) -> Generator[str, None, None]:
    """
    Web search using Claude's WebSearch capability.
    """
    context_manager.add_message(role="user", content=f"[Search Query] {query}")

    system_instruction = """The user wants to search the web.
Use the WebSearch tool to find relevant information.
Summarize the findings clearly."""

    yield from _stream_response(
        prompt=query,
        system_instruction=system_instruction,
        console=console,
        status_msg="Searching...",
        timing_label="Search",
        context_prefix="[Search Result] ",
        error_prefix="Search",
    )


# =============================================================================
# Context Management
# =============================================================================

def toggle_context_file(item: str):
    """Toggles inclusion of a known file in the LLM prompt context."""
    item_path = Path(item)
    if item_path not in context_manager.get_known_files():
        print(f"Error: File '{item_path}' not found in context. Use add_item() to add it.")
        return

    context_manager.toggle_path(item_path)
    status = "ON" if context_manager.get_known_files()[item_path].include_in_prompt else "OFF"
    print(f"Toggled {item_path} context {status}.")
