from typing import List, Literal, Dict, Any, Callable
from pathlib import Path
# Import the global context_manager instance
from ai_os.utils.context import context_manager
from ai_os.core.chat import chat_completion # Import the raw chat function
from ai_os.core.models import Message, KnownFileData

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