# examples/tdd_macro.py
"""
Test-Driven Development Macro

This macro implements a TDD workflow:
1. Generate a test file based on a goal
2. Loop: generate implementation until tests pass

Usage:
    /macro examples/tdd_macro.py test_goal="implement a function that checks if a number is prime"
"""

import ai_os.core.macro_helpers as ah
import re
import os

TEST_PROMPT_TEMPLATE = """
Generate a test file for the following goal:
{test_goal}

The test should test the test_goal and import a file and functions to test.
It should run tests and return a 0 exit code on success or non-zero on failure.
Keep the file simple.

The test file should be in the file: tests/test_{test_goal_snake}.py

IMPORTANT: The test will be run from the examples directory, so make sure imports work correctly.
Add this at the top of the test file to ensure imports work:
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""

IMPLEMENTATION_PROMPT_TEMPLATE = """
Given the user goal and test file contents, write the code to pass the test.

Goal:
{test_goal}

Test file:
{test_file_contents}

Implement the code in the appropriate file to make the tests pass.
"""


def main(ctx, **kwargs):
    """
    TDD macro - generate tests then implement until they pass.

    Args:
        test_goal: Description of what to implement
        max_attempts: Maximum implementation attempts (default: 5)
    """
    goal = kwargs.get("test_goal")
    if not goal:
        ah.log("[red]Error: test_goal argument is required.[/red]")
        ah.log("Usage: /macro examples/tdd_macro.py test_goal='...'")
        return

    max_attempts = int(kwargs.get("max_attempts", 5))
    test_goal_snake = re.sub(r'[^a-zA-Z0-9]+', '_', goal).strip('_').lower()

    ah.log(f"[bold]TDD Macro: {goal}[/bold]")

    # --- Phase 1: Generate Test File ---
    ah.log("\n[cyan]Phase 1: Generating test file...[/cyan]")

    test_prompt = TEST_PROMPT_TEMPLATE.format(
        test_goal=goal,
        test_goal_snake=test_goal_snake
    )

    # Have Claude create the test file using edit
    ah.edit(test_prompt)

    # Find the test file
    test_file = f"tests/test_{test_goal_snake}.py"

    if not ah.exists(test_file):
        ah.log(f"[red]Test file {test_file} was not created[/red]")
        return

    ah.log(f"[green]Test file created: {test_file}[/green]")

    # Show test content and get approval
    test_contents = ah.read(test_file)
    ah.log(f"[dim]Test contents:\n{test_contents[:500]}...[/dim]")

    if not ah.approve(f"Test file {test_file} created. Continue with implementation?"):
        ah.log("[yellow]Cancelled by user[/yellow]")
        return

    # --- Phase 2: Implementation Loop ---
    ah.log("\n[cyan]Phase 2: Implementation loop[/cyan]")

    test_command = f"pytest {test_file} -v"

    for attempt in range(1, max_attempts + 1):
        ah.log(f"\n[bold]Attempt {attempt}/{max_attempts}[/bold]")

        # Get current test file contents
        test_file_contents = ah.read(test_file)

        # Generate implementation
        impl_prompt = IMPLEMENTATION_PROMPT_TEMPLATE.format(
            test_goal=goal,
            test_file_contents=test_file_contents
        )

        ah.log("[dim]Generating implementation...[/dim]")
        ah.edit(impl_prompt)

        # Run tests
        ah.log(f"[dim]Running: {test_command}[/dim]")
        exit_code = ah.shell(test_command)

        if exit_code == 0:
            ah.log("\n[bold green]Tests passed! TDD cycle complete.[/bold green]")
            return

        ah.log(f"[yellow]Tests failed (exit code: {exit_code})[/yellow]")

        if attempt < max_attempts:
            if not ah.approve("Retry with another implementation?"):
                ah.log("[yellow]Cancelled by user[/yellow]")
                return
        else:
            ah.log(f"[red]Max attempts ({max_attempts}) reached. Tests still failing.[/red]")

    ah.log("[red]TDD macro completed without passing tests.[/red]")
