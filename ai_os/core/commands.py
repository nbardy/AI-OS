from typing import List, Literal, Dict, Any, Callable
from pathlib import Path
# Import the global context_manager instance
from ai_os.utils.context import context_manager
from ai_os.core.chat import chat_completion # Import the raw chat function
from ai_os.core.models import Message, KnownFileData, Patch

# Third-Party Imports
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

# Import apply_patch_with_approval from patch.py
from ai_os.core.patch import apply_patch_with_approval
# Import the strategies registry
from ai_os.core.patch_strategies import PATCH_STRATEGIES
# Import parsing errors if needed for specific error handling
from pydantic import ValidationError
import json # Needed for handling parsing errors if they involve json
import subprocess # Add this import
import os

# Import error logging utility
from ai_os.utils.error_logging import log_parsing_error

# --- Public API functions used by the CLI ---

def chat(prompt: str):
    """Sends a prompt to the LLM using configured context."""
    # Add user prompt to global history first
    context_manager.add_message(role="user", content=prompt)

    # Get the messages list formatted for the LLM (includes files and history)
    messages_for_llm = context_manager.get_llm_payload(user_prompt=prompt)

    # Call the core chat logic with the prepared messages
    assistant_response_chunks = chat_completion(messages=messages_for_llm)

    # Stream chunks and build full response
    full_response = ""
    for chunk in assistant_response_chunks:
        yield chunk # Yield chunks to the CLI for streaming display
        full_response += chunk

    # Add assistant response to global history after streaming is complete
    if full_response:
        context_manager.add_message(role="assistant", content=full_response)

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
    # Sort paths alphabetically for consistent display
    for path in sorted(files.keys()):
        data = files[path]
        status = "[green]ON[/green]" if data.include_in_prompt else "[red]OFF[/red]"
        # Using print directly for minimal output, Rich console in CLI handles colors
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

# Placeholder for info command
def info(msg: str):
    """Logs an informational message to the user UI, but NOT to the context."""
    print(f"INFO: {msg}") # Use basic print for minimal version

def patch(plan: str, strategy_name: str, console: Console) -> bool:
    """
    Orchestrates the patch generation (using a specific strategy) and application workflow.
    Calls the selected strategy to get a Patch object, then calls the application logic.

    Args:
        plan: A string describing the desired code change.
        strategy_name: The name of the patch strategy to use (e.g., "full_file").
        console: The Rich Console instance for user interaction and output.

    Returns:
        True if the entire patch workflow completed successfully (generated, applied,
        or rejected), False if a critical error occurred during generation or application.
    """
    # 1. Validate strategy name
    if strategy_name not in PATCH_STRATEGIES:
        console.print(f"[bold red]Error:[/bold red] Unknown patch strategy '{strategy_name}'. Available strategies: {list(PATCH_STRATEGIES.keys())}")
        context_manager.add_message(role="system", content=f"Attempted patch with unknown strategy: {strategy_name}")
        return False # Indicate failure due to invalid input

    strategy_runner = PATCH_STRATEGIES[strategy_name]

    # 2. Run the selected strategy to generate the Patch object
    generated_patch: Patch | None = None
    raw_llm_response: str | None = None # Store the raw response
    # The strategy_runner handles its own LLM calls and parsing based on formats
    # It now returns a tuple (Patch object, raw_response_str) or raises an exception
    generated_patch, raw_llm_response = strategy_runner(plan=plan, console=console)
    # If strategy_runner completes without raising, generated_patch should be a Patch object

    # If generated_patch is None here, it means the strategy function returned None
    # which is not the expected behavior. It should return a Patch or raise.
    if generated_patch is None or not isinstance(generated_patch, Patch):
         console.print(f"[bold red]Internal Error:[/bold red] Strategy '{strategy_name}' did not return a valid Patch object.")
         context_manager.add_message(role="system", content=f"Internal error: Strategy '{strategy_name}' returned invalid object.")
         return False # Indicate failure in generation phase

    # 4. Apply the generated Patch object with approval
    console.print("[dim]Strategy complete. Proceeding to application.[/dim]")
    # apply_patch_with_approval handles user prompt, file writes, git add/commit, and logging its outcome
    application_success = apply_patch_with_approval(generated_patch, console)
    # apply_patch_with_approval returns True if applied or successfully handled 'nothing to commit', False if rejected or failed application/commit
    return application_success # Return the result of the application step