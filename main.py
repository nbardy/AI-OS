#!/usr/bin/env python3
"""
AI-OS - Agentic Macro Framework

Usage:
    aios                              # Launch interactive TUI
    aios -p "chat prompt"             # Run chat prompt headlessly
    aios -m macro.py arg=value        # Run macro headlessly
    aios --help                       # Show help

Examples:
    aios -p "What is 2+2?"
    aios -m examples/hello_macro.py name="World" loops=2
    aios --macro examples/tree_of_thought.py question="How to design an API?"
"""

import argparse
import sys
from pathlib import Path


def run_prompt(prompt: str, model: str = None):
    """Run a chat prompt headlessly and print the response."""
    from ai_os.core.orchestrator import ClaudeOrchestrator

    orch = ClaudeOrchestrator()
    if model:
        orch.default_model = model

    print(f"Running prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}\n")

    try:
        # Use streaming for nicer output
        for chunk in orch.chat_streaming(prompt):
            print(chunk, end='', flush=True)
        print()  # Final newline

        cost = orch.get_cost()
        if cost['total_cost_usd'] > 0:
            print(f"\n[Cost: ${cost['total_cost_usd']:.4f}]")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def run_macro(macro_path: str, args: list):
    """Run a macro headlessly."""
    from rich.console import Console
    from ai_os.core.macro_runner import MacroRunner

    # Build argline: "path/to/macro.py key=value key2=value2"
    argline = macro_path
    if args:
        argline += " " + " ".join(args)

    console = Console()
    runner = MacroRunner(console=console)

    print(f"Running macro: {argline}\n")

    try:
        runner.run(argline)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AI-OS - Agentic Macro Framework built on Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aios                                    # Launch interactive TUI
  aios -p "Explain this code"             # Run chat prompt
  aios -m examples/hello_macro.py         # Run macro
  aios -m examples/tdd_macro.py test_goal="implement fibonacci"
        """
    )

    parser.add_argument(
        '-p', '--prompt',
        type=str,
        help='Run a chat prompt headlessly (no TUI)'
    )

    parser.add_argument(
        '-m', '--macro',
        type=str,
        help='Run a macro file headlessly (no TUI)'
    )

    parser.add_argument(
        '--model',
        type=str,
        choices=['sonnet', 'opus', 'haiku'],
        default=None,
        help='Model to use (default: sonnet)'
    )

    parser.add_argument(
        'args',
        nargs='*',
        help='Arguments for macro (key=value format)'
    )

    args = parser.parse_args()

    # Determine mode
    if args.prompt:
        # Headless chat mode
        run_prompt(args.prompt, model=args.model)

    elif args.macro:
        # Headless macro mode
        run_macro(args.macro, args.args)

    else:
        # Interactive TUI mode (default)
        from ai_os.cli import initialize_cli
        initialize_cli()


if __name__ == "__main__":
    main()
