import cmd
import sys
from typing import List
from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.table import Table

# Import the global context_manager instance
from ai_os.utils.context import context_manager
# Import commands which now operate on the context_manager
from ai_os.core import commands

console = Console()

class AIOSShell(cmd.Cmd):
    intro = 'Welcome to AI-OS. Type /help or ? to list commands.\n'
    prompt = '➜ ' # AI-OS git:(main) ✗' # Simulate prompt style

    # Alias mappings - keeping minimal for now
    aliases = {
        '>': 'chat',
        # Add others later: '+', '!', '@'
    }

    def precmd(self, line):
        if line.startswith('/'):
            parts = line[1:].split(maxsplit=1)
            cmd_name = parts[0]
            arg_str = parts[1] if len(parts) > 1 else ''

            if cmd_name in self.aliases:
                cmd_name = self.aliases[cmd_name]

            return f"{cmd_name} {arg_str}".strip()
        
        if line.strip():
            console.print(f"Unknown command format: '{line}'. Commands must start with '/'.")
            return ""

        return line

    def default(self, line):
        pass

    def do_help(self, arg):
        """List available commands or get help on a specific command."""
        if arg:
            try:
                resolved_arg = self.aliases.get(arg, arg)
                func = getattr(self, 'do_' + resolved_arg, None)
                if func and func.__doc__:
                    console.print(func.__doc__.strip())
                    return
            except AttributeError:
                pass
            console.print(f"No help for command or alias '{arg}'")
        else:
            command_methods = [name[3:] for name in get_class_methods(self.__class__) if name.startswith('do_')]
            valid_commands = sorted([cmd for cmd in command_methods if cmd not in ['help', 'quit']])

            aliases_list = sorted([f"{alias} -> /{cmd}" for alias, cmd in self.aliases.items()])

            console.print("[bold]Available commands:[/bold]")
            console.print("  " + ", ".join([f"/{c}" for c in valid_commands] + ['/help', '/exit', '/quit']))
            if aliases_list:
                console.print("[bold]Aliases:[/bold]")
                console.print("  " + ", ".join(aliases_list))

    # --- Core Commands ---

    def do_chat(self, arg):
        """/chat or > <prompt> : Chat with LLM, includes context."""
        if not arg:
            console.print("Usage: /chat <prompt>")
            return

        console.print("[bold blue]assistant:[/bold blue] ", end="")
        try:
            for chunk in commands.chat(prompt=arg):
                console.print(chunk, end="", sep="")
        except Exception as e:
            console.print(f"\n[bold red]Error during chat:[/bold red] {e}")
        console.print()

    def do_context(self, arg):
        """/context : Launch the context editor UI."""
        console.print("[bold green]Entering Context Editor (type 'exit' to return)[/bold green]")

        while True:
            try:
                files = context_manager.get_known_files()
                paths = sorted(files.keys())

                table = Table(title="Context Files")
                table.add_column("#", style="dim")
                table.add_column("Path", style="bold")
                table.add_column("Include", justify="center")

                if not files:
                    table.add_row("", "No files added.", "[red]N/A[/red]")
                else:
                    for i, path in enumerate(paths):
                        data = files[path]
                        status_text = Text("ON", style="green bold") if data.include_in_prompt else Text("OFF", style="red bold")
                        table.add_row(str(i+1), str(path), status_text)

                console.print(table)
                console.print("Toggle file by # or path. Type 'exit' to return.")

                context_input = console.input("[bold cyan]Context Editor[/bold cyan] > ").strip()

                if context_input.lower() == "exit":
                    console.print("[bold green]Exiting Context Editor[/bold green]")
                    break

                if context_input.lower().startswith("toggle "):
                    toggle_arg = context_input[7:].strip()
                    if not toggle_arg:
                        console.print("Usage: toggle <# or filepath>")
                        continue

                    try:
                        idx = int(toggle_arg) - 1
                        if 0 <= idx < len(paths):
                            target_path = paths[idx]
                            commands.toggle_context_file(str(target_path))
                        else:
                            console.print(f"Invalid number: {toggle_arg}")
                    except ValueError:
                        target_path = Path(toggle_arg)
                        commands.toggle_context_file(str(target_path))
                    except Exception as e:
                        console.print(f"Error toggling {toggle_arg}: {e}")

                else:
                    console.print(f"Unknown command: '{context_input}'. Use 'toggle <# or filepath>' or 'exit'.")

            except Exception as e:
                console.print(f"[bold red]Error in Context Editor:[/bold red] {e}")

    # --- Utility Commands ---

    def do_exit(self, arg):
        """Exit the AI-OS shell."""
        console.print("Exiting AI-OS. Goodbye!")
        return True

    def do_quit(self, arg):
         """Exit the AI-OS shell."""
         return self.do_exit(arg)

# --- Helper function for help command introspection ---
def get_class_methods(cls):
    return [method_name for method_name in dir(cls) if callable(getattr(cls, method_name))]

# --- Initialization ---
def initialize_cli():
    """Initializes the CLI and context."""
    console.print("[bold green]Starting AI-OS Shell...[/bold green]")
    console.print("[bold green]Initializing context with git files...[/bold green]")

    files_added = context_manager.load_git_repo()

    if files_added:
        console.print(f"[bold green]Added {len(files_added)} files to context.[/bold green]")
    else:
        console.print("[bold yellow]No git files added.[/bold yellow]")

    console.print("[bold green]AI-OS Minimal Chat[/bold green]")
    console.print("Type /help for commands. Type /context to manage files.")
    AIOSShell().cmdloop()

if __name__ == '__main__':
    initialize_cli()
