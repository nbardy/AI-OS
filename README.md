# AI-OS 😊🚀🎉

**"Abandon vibe coding—embrace AI engineering."**

AI-OS is an AI operating system—not a monolithic framework.  AI-OS is a tiny core lib and chat UI to allow you to quickly write small lean agentic macros.

Agents are for the common folk, macros are for the nerds.

LLM tooling can make us better engineers, not worse.


## What can you do with AI-OS
Some things that are easy to do with AI-OS.

1. Write an agentic flow for generating code that makes charts, then have a VLLM as a judge evaluate chart quality and run a loop until it passes a certain bar(https://github.com/nbardy/AI-OS/blob/main/examples/chart_judge_macro.py)
2. Write a Test driven development workflow that requires agents to write code that passes a given test.(https://github.com/nbardy/AI-OS/blob/main/examples/tdd_macro.py)
3. Impliment Test time search strategies from AI Research papers such as "Tree of Thought"(ttps://github.com/nbardy/AI-OS/blob/main/examples/tree_of_thought_macro.py)

### Core REPL commands

| Slash    | Alias | Purpose                                |
|----------|-------|----------------------------------------|
| `/chat`  | `>`   | Brainstorm, explain, iterate with LLM  |
| `/patch` | `+`   | Yield a `Patch` dict, preview & apply  |
| `/run`   | `!`   | Unix-style piping & safe shell exec    |
| `/macro` | `@`   | Run a Python macro workflow            |



## Why AI-OS?

AI-OS is a basic framework that impliments the core utilities for agentic macros. Agentic Macros all you to write python files that call llms and agent like agents, but also. We remove all the required boilerplate for manging context, result streaming, writing chat UI's, model selectors, etc... And allow you to write lean python programming for context engineering and control flow. 


AI-OS provides a REPL to interact with AI and a shared minimal language to write small macros that define your agentic workflows. Instead of writing separat isolated agentic setups you can't interact with. AI-OS macros simply run in the same Chat based repl. This allows you to use `+` (/patch) commands to write macros. `@` (/macro) comands to run macro, and . This allows previous agent runs to read each others results, and your chat commands to have previous failed or successful macro runs to be in context for further iteration. Running an AI agent workflow should not be a fire and forget experience, AI agents are perfect and are unpredictable, it requires iteration to get to your result and AI-OS allows you to do that. Mix your AI chat experience with your agents!

In the past each agentic workflow was an isolated. Some new paper comes out like Tree of Thought, the author impliments it in their own python repo. You can call it to solve your problem. But it fails, gets close almost solves your problem and You have no way to follow up. 

In the future AI-OS will have a growing standard lib that impliments inference time research techniques as macros. You can call each approach when neeeded and since results are stored in context, you can call another approach after! Chaining inference time techniques together for composability. No one inference time technique or process is the best for each problem. Instead have an array of composable tools to work together.



---

## Quick Install

```bash
pip install ai-os           # Python ≥ 3.11
export OPENROUTER_API_KEY=sk-…
aios                        # launch the AI-OS shell
```

---

## Test Driven Design Macro

```python
import ai_os.core.macro_helpers as ah
import re
import os

test_prompt_template = """
Generate a test file for the following goal:
{test_goal}

The test should test the test_goal and import a file and functions to test

It should run tests and return a 0 exit code on success or non-zero on failure.
Keep the file simple 

The test file should be in the file: tests/test_{test_goal_snake}.py

IMPORTANT: The test will be run from the examples directory, so make sure imports work correctly.
Add this at the top of the test file to ensure imports work:
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""

patch_prompt_template = """
Given the user goal and test file contents, write the code to pass the test.
Goal:
{test_goal}

Test file:
{test_file_contents}
"""

def main(ctx, **kwargs):
    goal = kwargs.get("test_goal")
    if not goal:
        ah.log("Error: test_goal argument is required.")
        ah.log("Usage: /macro examples/tdd_macro.py test_goal='...'")
        return

    test_goal_snake = re.sub(r'[^a-zA-Z0-9]+', '_', goal).strip('_').lower()

    # --- Test File Generation ---
    while True:
        patch = ah.patch(
            test_prompt_template.format(test_goal=goal, test_goal_snake=test_goal_snake)
        )
        files = patch.get("files") if patch else None
        test_file = files[0] if files else None

        if test_file and os.path.exists(test_file.path):
            if ah.approve(f"Is test file {test_file.path} ok?"):
                break
            ah.log(f"Test file {test_file.path} rejected. Retrying...")
        else:
            ah.log("No valid test file created. Retrying...")

    test_command = f"pytest {test_file.path}"

    # --- Implementation Loop ---
    while True:
        ah.log(f"Running test: {test_command}")
        patch = ah.patch(
            patch_prompt_template.format(
                test_goal=goal, test_file_contents=test_file.contents
            ),
            user_approval=True,
        )

        # Run test and check
        if ah.shell(test_command, capture=False) == 0:
            ah.log("[bold green]Tests passed![/bold green]")
            break

        ah.log("[bold yellow]Tests failed.[/bold yellow]")
        if not ah.approve("Retry with another implementation?"):
            ah.log("User cancelled implementation retry.")
            return

```
