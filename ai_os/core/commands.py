from typing import List, Literal, Dict, Any, Callable, Optional
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
import uuid # Add this import

# Import error logging utility
from ai_os.utils.error_logging import log_parsing_error

# Note: File path tab completion is handled in cli.py using prompt_toolkit. No changes needed here for completion logic.

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
    
    # log to temp file

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

def patch(plan: str, strategy_name: str, console: Console, user_approval_override: Optional[bool] = None) -> Dict[str, Any] | None:
    """
    Orchestrates the patch generation and application workflow.
    Args:
        plan: A string describing the desired code change.
        strategy_name: The name of the patch strategy to use (e.g., "full_file").
        console: The Rich Console instance for user interaction and output.
        user_approval_override: If True/False, forces user approval on/off,
                                otherwise relies on apply_patch_with_approval default (True).

    Returns:
        A dictionary containing patch results if generated and processed (applied/rejected),
        or None if a critical error occurred during generation or application.
    """
    # 1. Validate strategy name
    if strategy_name not in PATCH_STRATEGIES:
        console.print(f"[bold red]Error:[/bold red] Unknown patch strategy '{strategy_name}'. Available strategies: {list(PATCH_STRATEGIES.keys())}")
        context_manager.add_message(role="system", content=f"Attempted patch with unknown strategy: {strategy_name}")
        return None # Indicate failure due to invalid input
    strategy_runner = PATCH_STRATEGIES[strategy_name]

    generated_patch: Optional[Patch] = None
    raw_llm_response: Optional[str] = None

    # 2. Run the selected strategy to generate the Patch object
    try:
        # Strategies should ideally return (Patch | None, str | None)
        # If a strategy fails to parse but has the raw response, it should return (None, raw_response_text)
        _patch_candidate, _raw_response_candidate = strategy_runner(plan=plan, console=console)
        generated_patch = _patch_candidate
        raw_llm_response = _raw_response_candidate
    except NotImplementedError as e:
        console.print(f"[bold red]Error:[/bold red] Strategy '{strategy_name}' is not yet implemented.")
        context_manager.add_message(role="system", content=f"Attempted unimplemented patch strategy: {strategy_name}")
        return None # Indicate failure
    except ValidationError as e: # Catch Pydantic validation errors if strategies raise them
        console.print(f"[bold red]Error parsing LLM response in strategy '{strategy_name}':[/bold red] {e}")
        context_manager.add_message(role="system", content=f"Patch strategy '{strategy_name}' parsing error: {e}")
        # raw_llm_response will be None here if the strategy raised before returning it.
        # The logging block below will handle this.
    except Exception as e: # Catch any other unexpected error from the strategy
        console.print(f"[bold red]An unexpected error occurred within strategy '{strategy_name}':[/bold red] {e}")
        context_manager.add_message(role="system", content=f"Unexpected error in patch strategy '{strategy_name}': {e}")
        # raw_llm_response will likely be None here as well.

    # --- Log raw LLM response to /tmp ---
    # This logging will now occur if raw_llm_response was successfully returned by the strategy,
    # or if the strategy call completed but returned raw_llm_response as None.
    if raw_llm_response:
        try:
            tmp_file_name = f"patch_llm_output_{uuid.uuid4()}.txt"
            tmp_file_path = os.path.join("/tmp", tmp_file_name)
            with open(tmp_file_path, "w") as f:
                f.write(raw_llm_response)
            console.print(f"[dim]Full LLM response saved to: {tmp_file_path}[/dim]")
        except Exception as log_e:
            console.print(f"[yellow]Warning:[/yellow] Could not save full LLM response to /tmp: {log_e}")
    else:
        # This means strategy_runner either didn't return a raw response,
        # or an exception occurred before raw_llm_response could be assigned from its return.
        console.print(f"[yellow]Warning:[/yellow] No raw LLM response was available from strategy '{strategy_name}' for logging. This might be due to an error during strategy execution before the response was obtained or returned.")

    # If generated_patch is None at this point, it means:
    # 1. Strategy returned (None, raw_response) -> raw_response was logged (if not None).
    # 2. Strategy raised an exception caught above -> raw_response might not have been logged (if it was None).
    #    In this case, generated_patch would still be its initial value (None).
    if generated_patch is None:
        # An error message would have already been printed by the exception handlers above if an exception occurred.
        # If we are here because the strategy returned (None, "text_response") without raising an exception,
        # this message clarifies that no valid patch object was produced.
        if raw_llm_response is not None: # Check if we had raw response but still no patch
             console.print(f"[bold red]Strategy Error:[/bold red] Strategy '{strategy_name}' did not produce a valid patch object, though a raw LLM response was received.")
        # else: an error message was already printed by an exception handler, or no raw response was ever available.

        context_manager.add_message(role="system", content=f"Strategy '{strategy_name}' failed to produce a patch. Raw response logged if it was available.")
        return None # Indicate failure in generation phase
    
    # Ensure generated_patch is indeed a Patch object if not None
    if not isinstance(generated_patch, Patch):
        console.print(f"[bold red]Internal Error:[/bold red] Strategy '{strategy_name}' returned an invalid object type instead of a Patch.")
        context_manager.add_message(role="system", content=f"Internal error: Strategy '{strategy_name}' returned invalid object type.")
        return None


    # 4. Apply the generated Patch object with approval
    console.print("[dim]Strategy complete. Proceeding to application.[/dim]")
    try:
        # apply_patch_with_approval needs to accept user_approval_override
        # It now returns the result dict
        application_result = apply_patch_with_approval(
            generated_patch,
            console=console,
            user_approval_override=user_approval_override # Pass the override
        )
        return application_result # Return the structured result from apply_patch_with_approval
    except Exception as e:
        # Catch any *unexpected* errors that bubble up from the apply logic (git errors etc.)
        # apply_patch_with_approval should ideally catch and log within, but this is a fallback.
        console.print(f"\n[bold red]A critical, unexpected error occurred during patch application:[/bold red] {e}")
        context_manager.add_message(role="system", content=f"Critical patch application error: {e}")
        # Return a failure structure or re-raise? Let's return None to signify critical failure in the workflow.
        # This should be distinct from user rejection.
        return None