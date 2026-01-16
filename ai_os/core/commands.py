"""
AI-OS Commands - CLI command implementations.

These functions are called by cli.py when the user runs commands like:
- > or /chat - Chat with Claude
- + or /patch - Have Claude edit files
- ! or /run - Run shell commands
- @ or /macro - Run macro scripts

V2: Now uses Claude Code via orchestrator instead of OpenRouter.
"""

from typing import List, Dict, Any, Optional, Generator
from pathlib import Path
import time
import subprocess
import os

# Import the new orchestrator
from ai_os.core.orchestrator import get_orchestrator

# Import context manager for history tracking
from ai_os.utils.context import context_manager
from ai_os.utils.config import config_manager

# Third-Party Imports
from rich.console import Console


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
    # Add user prompt to history
    context_manager.add_message(role="user", content=prompt)

    # Build the instruction that tells Claude this is chat-only
    system_instruction = """This is a chat/question command.
You may read files for context if needed, but do NOT edit or write any files.
Just answer the user's question or discuss the topic."""

    # Track timing
    think_start = time.time()
    think_time = None
    stream_start = None
    full_response = ""

    # Get orchestrator and stream response
    orch = get_orchestrator()

    try:
        # Create generator once to avoid double execution
        stream_gen = orch.chat_streaming(prompt, system_instruction=system_instruction)
        first_chunk = None

        if console:
            with console.status("Thinking...", spinner="dots"):
                # Get first chunk to measure think time
                first_chunk = next(stream_gen, None)
                if first_chunk:
                    think_time = time.time() - think_start
                    stream_start = time.time()
                    context_manager.add_message(
                        role="system",
                        content=f"LLM thinking time: {think_time:.1f}s"
                    )

            # Yield first chunk outside status
            if first_chunk:
                yield first_chunk
                full_response += first_chunk

            # Continue streaming remaining chunks
            for chunk in stream_gen:
                yield chunk
                full_response += chunk
        else:
            # No console - simple streaming
            for chunk in stream_gen:
                if stream_start is None:
                    think_time = time.time() - think_start
                    stream_start = time.time()
                yield chunk
                full_response += chunk

        # Add timing info
        if stream_start and think_time:
            stream_time = time.time() - stream_start
            yield f"\n[dim](Thinking: {think_time:.1f}s, Streaming: {stream_time:.1f}s)[/dim]"

        # Add response to history
        if full_response:
            context_manager.add_message(role="assistant", content=full_response)

    except Exception as e:
        error_msg = f"Chat error: {e}"
        context_manager.add_message(role="system", content=error_msg)
        yield f"[red]{error_msg}[/red]"


# =============================================================================
# Patch Command (+ or /patch)
# =============================================================================

def patch(
    plan: str,
    strategy_name: str = "full_file",  # Ignored in v2, kept for API compat
    console: Console = None,
    user_approval_override: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Have Claude edit files to implement the given plan.

    This tells Claude Code to use its Edit tool to make changes.

    Args:
        plan: Description of what changes to make
        strategy_name: Ignored in v2 (was XML strategy selector)
        console: Console for output
        user_approval_override: If True, skip user approval (for macros)

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

    think_start = time.time()
    think_time = None
    stream_start = None
    full_response = ""

    orch = get_orchestrator()

    try:
        # Create generator once to avoid double execution
        stream_gen = orch.chat_streaming(query, system_instruction=system_instruction)
        first_chunk = None

        if console:
            with console.status("Searching...", spinner="dots"):
                # Get first chunk to measure think time
                first_chunk = next(stream_gen, None)
                if first_chunk:
                    think_time = time.time() - think_start
                    stream_start = time.time()

            # Yield first chunk outside status
            if first_chunk:
                yield first_chunk
                full_response += first_chunk

            # Continue streaming remaining chunks
            for chunk in stream_gen:
                yield chunk
                full_response += chunk
        else:
            # No console - simple streaming
            for chunk in stream_gen:
                if stream_start is None:
                    think_time = time.time() - think_start
                    stream_start = time.time()
                yield chunk
                full_response += chunk

        if stream_start and think_time:
            stream_time = time.time() - stream_start
            yield f"\n[dim](Search: {think_time:.1f}s, Streaming: {stream_time:.1f}s)[/dim]"

        if full_response:
            context_manager.add_message(role="assistant", content=f"[Search Result] {full_response}")

    except Exception as e:
        error_msg = f"Search error: {e}"
        context_manager.add_message(role="system", content=error_msg)
        yield f"[red]{error_msg}[/red]"


# =============================================================================
# Context Management (from v1, unchanged)
# =============================================================================

def add_item(item: str | Path, *, show_user: bool = False):
    """Adds text content or file content to the context's known items."""
    item_path = Path(item)
    if item_path.is_file():
        try:
            content = item_path.read_text()
            context_manager.add_known_file(path=item_path, content=content)
            if show_user:
                print(f"Added file {item_path} to known context.")
        except Exception:
            if show_user:
                print(f"Error reading file {item_path}")
    else:
        if show_user:
            print(f"Only files can be added to known context via add_item(). '{item}' is not a file.")


def list_context_files():
    """Lists files currently in the known context with their include status."""
    files = context_manager.get_known_files()
    if not files:
        print("No files added to context yet.")
        return

    print("Context Files (Toggle with /context toggle <path>):")
    for path in sorted(files.keys()):
        data = files[path]
        status = "[green]ON[/green]" if data.include_in_prompt else "[red]OFF[/red]"
        print(f"- {path} {status}")


def toggle_context_file(item: str):
    """Toggles inclusion of a known file in the LLM prompt context."""
    item_path = Path(item)
    if item_path not in context_manager.get_known_files():
        print(f"Error: File '{item_path}' not found in context. Use add_item() to add it.")
        return

    context_manager.toggle_path(item_path)
    status = "ON" if context_manager.get_known_files()[item_path].include_in_prompt else "OFF"
    print(f"Toggled {item_path} context {status}.")


def info(msg: str):
    """Logs an informational message to the user UI, but NOT to the context."""
    print(f"INFO: {msg}")
