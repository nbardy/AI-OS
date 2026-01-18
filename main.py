#!/usr/bin/env python3
"""
AI-OS - Agentic Macro Framework

Usage:
    aios                              # Launch interactive TUI
    aios "> chat prompt"              # Run chat prompt headlessly
    aios "@ macro.py arg=value"       # Run macro headlessly
    aios --help                       # Show help

Examples:
    aios "> What is 2+2?"
    aios "@ examples/hello_macro.py name=World loops=2"
    aios "> explain this code" --model haiku
"""

import argparse
import sys

# Import shared parsing from commands module
from ai_os.core.commands import parse_input


def run_chat(prompt: str, model: str = None):
    """Run a chat prompt headlessly and print the response."""
    from ai_os.core.orchestrator import ClaudeOrchestrator

    orch = ClaudeOrchestrator()
    if model:
        orch.default_model = model

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


def run_macro(argline: str):
    """Run a macro headlessly."""
    from rich.console import Console
    from ai_os.core.macro_runner import MacroRunner

    console = Console()
    runner = MacroRunner(console=console)

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
  aios "> Explain this code"              # Run chat prompt
  aios "@ examples/hello_macro.py"        # Run macro
  aios "@ examples/tdd_macro.py test_goal='implement fibonacci'"
  aios "> quick answer" --model haiku     # Use specific model
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        help='Command to run: "> prompt" for chat, "@ macro.py args" for macro'
    )

    parser.add_argument(
        '--model',
        type=str,
        choices=['sonnet', 'opus', 'haiku'],
        default=None,
        help='Model to use (default: sonnet)'
    )

    args = parser.parse_args()

    if args.command:
        # Headless mode - parse and execute command using shared parser
        cmd, arg = parse_input(args.command)

        if cmd == '/chat':
            run_chat(arg, model=args.model)
        elif cmd == '/macro':
            run_macro(arg)
        else:
            print(f"Unsupported command for headless mode: {cmd}", file=sys.stderr)
            print("Supported: > or /chat for prompts, @ or /macro for macros", file=sys.stderr)
            sys.exit(1)
    else:
        # Interactive TUI mode (default)
        from ai_os.cli import initialize_cli
        initialize_cli()


if __name__ == "__main__":
    main()
