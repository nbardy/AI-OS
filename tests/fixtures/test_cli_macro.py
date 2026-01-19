# examples/test_cli_macro.py
"""Simple macro to test CLI --macro mode."""

import ai_os as ai

def main(ctx, **kwargs):
    name = kwargs.get("name", "World")
    ai.log(f"[bold green]Hello, {name}![/bold green]")
    ai.log("CLI macro mode works!")
