# ai_os/core/patch_strategies/strategy_git_diff.py

from rich.console import Console
from ai_os.core.models import Patch
from ai_os.core.chat import chat_completion # For LLM interaction
from ai_os.utils.context import context_manager # For getting LLM payload
# Needed for error logging if parsing were implemented
# from ai_os.utils.error_logging import log_parsing_error
# import json # Needed for parsing if implemented
# from pydantic import ValidationError # Needed for parsing if implemented

# --- Strategy Definition ---

# Define the specific prompt fragment for this strategy
# Migrated from patch_formats.py
FORMAT_PROMPT = """
Provide the code changes as a standard unified git diff format. Include necessary context lines ('---', '+++', '@@', +,- lines). Do not include any extra text outside the diff.
"""

# Define the parsing function specific to this strategy's format
# Migrated from patch_formats.py (parse_git_diff) - still TBD
def parse_response(llm_response: str) -> Patch:
    """
    Parses LLM response assumed to be a git diff string into a Patch object.
    This is complex as it needs to reconstruct the *new full file content*.
    """
    # This requires logic to:
    # 1. Identify affected files from the diff header.
    # 2. Get the *current* content of those files from the working directory.
    # 3. Apply the diff hunks to the current content to reconstruct the *new* content.
    # 4. Generate summaries (maybe ask LLM in a follow-up or try to parse from diff comments).
    # This is where diff libraries (like diff_match_patch or git apply) would be useful,
    # but integrating them to reconstruct the *new content* for our Patch model requires careful implementation.
    # Add logging potential failure here if implemented
    raise NotImplementedError("Parsing standard git diff format is complex and not yet implemented.")

# --- Strategy Execution Function ---

# Define the strategy name for logging/identification
STRATEGY_NAME = "git_diff"

def run_strategy(plan: str, console: Console) -> Patch:
    """
    Runs the 'git diff' patch strategy. Prompts LLM for changes in git diff
    format and attempts to parse the response.

    NOTE: Parsing git diff into the Patch model (full new content) is not yet implemented.
    """
    console.print(f"[dim]Strategy '{STRATEGY_NAME}': Asking LLM for git diff patch...[/dim]")

    # Prepare LLM Prompt using the local FORMAT_PROMPT
    llm_prompt_content = f"[PLAN]\nGoal: {plan}\n\n{FORMAT_PROMPT}"
    messages_for_llm = context_manager.get_llm_payload(user_prompt=llm_prompt_content)

    # Call LLM (Capture full response)
    full_llm_response = ""
    with console.status("Thinking...", spinner="dots"):
        for chunk in chat_completion(messages=messages_for_llm):
            full_llm_response += chunk
    console.print("[dim]LLM response received.[/dim]")

    # Parse LLM Response using the local PARSE_FN
    console.print("[dim]Parsing LLM response (git diff format)...[/dim]")

    # For now, just call and let the NotImplementedError propagate
    generated_patch = parse_response(full_llm_response.strip())
    return generated_patch # This line won't be reached until parse_response is implemented

# Note: Error handling expected in commands.py 