# ai_os/utils/error_logging.py
import traceback
import datetime
from pathlib import Path

# Ensure the tmp directory exists
TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def log_parsing_error(
    strategy_name: str,
    raw_response: str,
    exception: Exception,
    log_dir: Path = TMP_DIR,
    llm_input: str = "[Input not provided]"
) -> str:
    """
    Logs details of a parsing error to a timestamped file in the specified directory.

    Args:
        strategy_name: The name of the patch strategy being used.
        raw_response: The raw string response from the LLM that failed parsing.
        exception: The exception object caught during parsing (e.g., JSONDecodeError).
        log_dir: The directory to save the log file in (defaults to ./tmp).
        llm_input: The raw input sent to the LLM.

    Returns:
        The absolute path to the created log file as a string.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_filename = f"{strategy_name}_parsing_error_{timestamp}.log"
    log_filepath = log_dir / log_filename

    error_traceback = traceback.format_exc()

    log_content = f"""--- LLM INPUT ---
{llm_input}
--- RAW LLM RESPONSE ---
{raw_response}
--- PARSING ERROR TRACEBACK ---
{error_traceback}
--- END OF LOG ---
"""

    try:
        with open(log_filepath, "w", encoding="utf-8") as f:
            f.write(log_content)
        return str(log_filepath.resolve())
    except Exception as e:
        # If logging itself fails, return a failure message
        # (Could use console.print here if console object was passed, but keep it simple)
        print(f"[Error] Failed to write error log to {log_filepath}: {e}")
        return f"[Failed to create log file: {e}]" 