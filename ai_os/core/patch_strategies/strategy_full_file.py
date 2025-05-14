# ai_os/core/patch_strategies/strategy_full_file.py

from rich.console import Console
from ai_os.core.models import Patch
from ai_os.core.chat import chat_completion
from ai_os.utils.context import context_manager
import re
import os
import uuid
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# NOTE: The following prompt **must remain byte-for-byte identical**. Do NOT
# alter spacing, newlines, or wording – downstream logic relies on it.
# ---------------------------------------------------------------------------
STRATEGY_FORMAT_PROMPT = """
You MUST provide the complete, final code changes using the following format AND ONLY this format.

For each file output the entire the new file with changes.


For each file to be changed, output xml block  with the following format:
<code filename="foo.py" language="python">
<!--- This is the full content of foo.py -->
</code>
<code filename="bar.py" language="python">
<!--- This is the full content of bar.py -->
</code>
...

--- summaries ---
foo.py: Add new_helper function and Example class definition.
bar.py: Add comprehensive tests for new_helper including empty and negative cases.
...

Ensure there is no other text outside this specific structure.
"""

# ---------------------------------------------------------------------------
# State-machine XML-within-string parser
# ---------------------------------------------------------------------------


def _extract_code_blocks(xml_blob: str) -> Dict[str, str]:
    """
    Very small deterministic scanner that walks the blob once and
    yields {filename -> file_content}.  Assumes well-formed <code/> tags.
    """
    file_changes: Dict[str, str] = {}
    i, n = 0, len(xml_blob)

    while True:
        open_i = xml_blob.find("<code", i)
        if open_i == -1:
            break  # no more blocks
        tag_close = xml_blob.find(">", open_i)
        if tag_close == -1:
            raise ValueError("Unterminated <code …> tag")

        tag = xml_blob[open_i : tag_close + 1]  # include '>'
        m = re.search(r'filename="([^"]+)"', tag)
        if not m:
            raise ValueError("Missing filename attribute in <code> tag")
        filename = m.group(1).replace("\\", "/")

        close_tag = "</code>"
        close_i = xml_blob.find(close_tag, tag_close + 1)
        if close_i == -1:
            raise ValueError(f"Missing closing </code> tag for {filename}")

        content = xml_blob[tag_close + 1 : close_i]
        file_changes[filename] = content.strip()
        i = close_i + len(close_tag)

    return file_changes


def parse_xml_response(llm_response: str) -> Patch:
    """
    Parse an LLM response that embeds <code …></code> sections followed by
    a `--- summaries ---` list.  Raises on any structural error.
    """
    summary_marker = r"\n\s*---\s*summaries\s*---\s*\n"
    parts = re.split(summary_marker, llm_response, maxsplit=1, flags=re.DOTALL)
    xml_part = parts[0].strip()
    summary_part = parts[1].strip() if len(parts) > 1 else ""

    if not xml_part:
        raise ValueError("No <code> blocks detected before summary marker.")

    file_changes = _extract_code_blocks(xml_part)
    if not file_changes:
        raise ValueError("No valid <code/> blocks found.")

    # --- summaries ---
    summaries: Dict[str, str] = {}
    if summary_part:
        for line in summary_part.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            path, msg = (s.strip() for s in line.split(":", 1))
            path = path.replace("\\", "/")
            if path in file_changes:
                summaries[path] = msg

    for path in file_changes:
        summaries.setdefault(path, "[No summary provided]")

    return Patch(file_changes=file_changes, summaries=summaries)


# ---------------------------------------------------------------------------
# Strategy metadata & runner
# ---------------------------------------------------------------------------

STRATEGY_NAME = "full_file_xml"


def run_strategy(plan: str, console: Console) -> Tuple[Patch, str]:
    """Prompt the LLM for full-file XML patches and return the parsed Patch."""
    console.print(
        f"[dim]Strategy '{STRATEGY_NAME}': Asking LLM for full file XML patch...[/dim]"
    )

    llm_prompt_content = f"""[PLAN]
Goal: {plan}

{STRATEGY_FORMAT_PROMPT}"""
    context_manager.add_message(role="user", content=llm_prompt_content)
    messages = context_manager.get_llm_payload(llm_prompt_content)

    full_llm_response = ""
    with console.status("Thinking...", spinner="dots"):
        for chunk in chat_completion(messages=messages):
            full_llm_response += chunk
    console.print("[dim]LLM response received.[/dim]")

    # --- Log input and output trace to ./tmp ---
    try:
        log_dir = "./tmp"
        os.makedirs(log_dir, exist_ok=True)
        trace_file_name = f"strategy_trace_{STRATEGY_NAME}_{uuid.uuid4()}.log"
        trace_file_path = os.path.join(log_dir, trace_file_name)
        with open(trace_file_path, "w") as f:
            f.write("--- model input ---\n")
            f.write(llm_prompt_content)
            f.write("\n\n--- model output ---\n")
            f.write("[Full model output is logged to a file in /tmp by the patch command.]\n")
        # console.print(f"[dim]Strategy trace saved to: {trace_file_path}[/dim]") # Optional: print path to console
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not save strategy trace to {log_dir}: {e}")
    # -------------------------------------------

    stripped = full_llm_response.strip()
    if stripped.startswith("```diff") or stripped.startswith("--- a/"):
        snippet = stripped[:150].replace("\n", "\n")
        raise ValueError(
            f"LLM responded with diff format instead of requested XML. Response started with: '{snippet}...'"
        )

    console.print("[dim]Parsing LLM response (state-machine XML parser)...[/dim]")
    patch = parse_xml_response(stripped)
    console.print("[dim]Patch object generated.[/dim]")
    return patch, stripped


# ---------------------------------------------------------------------------
# Self-contained quick-check
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- Running self-contained parsing test (strategy_full_file) ---")

    TEST_LLM_RESPONSE_VALID = """
<code filename="src/my_module.py" language="python">
def my_function():
    pass  # initial function
</code>
<code filename="tests/test_my_module.py" language="python">
import unittest
from src.my_module import my_function

class TestMyModule(unittest.TestCase):
    def test_my_function(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
</code>

--- summaries ---
src/my_module.py: Add basic function.
tests/test_my_module.py: Add basic test.
"""

    TEST_LLM_RESPONSE_MALFORMED_XML = """
<code filename="src/bad.py" language="python">
# Missing closing tag
</code

--- summaries ---
src/bad.py: Should fail.
"""

    tests = {
        "Valid Response": TEST_LLM_RESPONSE_VALID,
        "Malformed XML": TEST_LLM_RESPONSE_MALFORMED_XML,
    }

    expected_failure = {"Malformed XML"}
    all_passed = True

    for name, response in tests.items():
        print(f"\n--- Testing: {name} ---")
        try:
            result = parse_xml_response(response)
            print("✅  Parsing Successful")
            print("Files parsed:", list(result.file_changes))
            if name in expected_failure:
                all_passed = False
                print("❌  Expected failure but succeeded.")
        except Exception as exc:
            print(f"❌  Parsing failed: {exc}")
            if name not in expected_failure:
                all_passed = False
            else:
                print("[Expected failure – OK]")

    print("\n--- Test Summary ---")
    if all_passed:
        print("✅  All tests behaved as expected.")
    else:
        print("❌  Unexpected test outcome(s).")
