import cmd
from typing import List
from pathlib import Path
from rich.console import Console
from rich.text import Text
# rich.table.Table is no longer used here
# rich.tree.Tree is no longer used here

# Import the global context_manager instance
from ai_os.utils.context import context_manager
# Import commands which now operate on the context_manager
from ai_os.core import commands

# Import the Textual Context Editor App
from ai_os.ui.context_editor import ContextEditorApp

# KnownFileData is no longer needed here

console = Console() # Keep Rich Console for the cmd.Cmd shell output

# --- Textual Context Editor App code is now removed ---

class AIOSShell(cmd.Cmd):
    intro = 'Welcome to AI-OS. Type /help or ? to list commands.\n'
    prompt = '➜ '

    aliases = {
        '>': 'chat',
    }

    def precmd(self, line):
        """Parse aliases and slash commands."""
        line = line.strip()
        if not line:
            return ""  # Handle empty line

        parts = line.split(maxsplit=1)
        first_part = parts[0]
        arg_str = parts[1] if len(parts) > 1 else ''

        # Check for aliases first (e.g., '>')
        if first_part in self.aliases:
            cmd_name = self.aliases[first_part]
            # arg_str is already defined above
            return f"{cmd_name} {arg_str}".strip()

        # If not an alias, check for explicit slash command (e.g., '/chat')
        # arg_str is already defined above
        if line.startswith('/'):
            return f"{first_part[1:]} {arg_str}".strip()  # Strip the '/'

        # Anything else is an unknown format unless it's meant for the default handler
        # If default should handle raw input, maybe don't print error here?
        # For now, assume commands MUST start with / or alias
        console.print(f"Unknown command format: '{line}'. Commands must start with '/' or use an alias ({', '.join(f'/{k}' for k in self.aliases.keys())}).")
        return "" # Prevent default handler execution for invalid format

    def default(self, line):
        """Handles unrecognized commands."""
        # This is called if precmd returns a non-empty string that doesn't match a do_* method
        # Because precmd now returns "" for invalid formats, this shouldn't be hit often
        # unless precmd logic changes or a valid command format (like /unknown) is used.
        console.print(f"Unknown command: '{line}'. Type /help for available commands.")


    def do_help(self, arg):
        """/help [cmd] : List commands or show help for a specific command."""
        if arg:
            try:
                # Resolve alias if the user asks for help on an alias
                resolved_arg = self.aliases.get(arg.lstrip('/'), arg.lstrip('/'))
                func = getattr(self, 'do_' + resolved_arg, None)
                if func and func.__doc__:
                    # Display command usage from docstring
                    doc_lines = func.__doc__.strip().split('\n')
                    usage = doc_lines[0] # First line is usually usage summary
                    console.print(f"[bold]Usage:[/bold] {usage}")
                    if len(doc_lines) > 1:
                         # Print the rest of the docstring as description
                         console.print("\n".join(line.strip() for line in doc_lines[1:]))
                    return
            except AttributeError:
                pass # Fall through to "No help" message
            console.print(f"No help available for command or alias: '{arg}'")
        else:
            # Dynamically get command methods, excluding internal/hidden ones
            command_methods = [name[3:] for name in dir(self) if name.startswith('do_') and callable(getattr(self, name))]
            # Exclude help, quit, exit, and any command that is only reachable via alias
            aliased_cmds = set(self.aliases.values())
            exclude_cmds = {'help', 'quit', 'exit'} # Don't list aliases directly as primary commands
            # Primary commands are those with do_* methods not exclusively behind an alias
            primary_commands = sorted([cmd for cmd in command_methods if cmd not in exclude_cmds and cmd not in aliased_cmds])
            # Explicitly add help/exit/quit
            system_commands = sorted([cmd for cmd in command_methods if cmd in exclude_cmds])

            console.print("[bold]Available commands:[/bold]")
            if primary_commands:
                console.print("  " + ", ".join([f"/{c}" for c in primary_commands]))
            if system_commands:
                console.print("  " + ", ".join([f"/{c}" for c in system_commands]))

            if self.aliases:
                console.print("\n[bold]Aliases:[/bold]")
                # Show aliases like: '> (/chat)'
                aliases_list = sorted([f"{alias} ({f'/{cmd}'}) " for alias, cmd in self.aliases.items()])
                console.print("  " + ", ".join(aliases_list))

    def do_chat(self, arg):
        """/chat or > <prompt> : Chat with LLM, includes context."""
        if not arg:
            console.print("[yellow]Usage: /chat <prompt>  or  > <prompt>[/yellow]")
            return

        console.print("[bold blue]assistant:[/bold blue] ", end="")
        try:
            # Stream the response
            full_response = ""
            for chunk in commands.chat(prompt=arg):
                console.print(chunk, end="", sep="")
                full_response += chunk
            # Ensure a newline after the streaming is complete
            console.print()
            # Update message history explicitly after full response (context_manager handles this internally now?)
            # No, chat command should add user and assistant messages
            # Let's assume context_manager.add_message is called within commands.chat
        except Exception as e:
            # Ensure newline even if error occurs mid-stream
            console.print(f"\n[bold red]Error during chat:[/bold red] {e}")
        # No need for extra console.print() if streaming handles final newline

    def do_context(self, arg):
        """/context : Launch the interactive context editor UI."""
        app = ContextEditorApp()
        app.run()
        # Re-initialize console might not be necessary, but good practice if TUI messed with it.
        # console = Console() # Re-create to ensure terminal state is okay? Maybe not needed.
        console.print("\n[bold green]Returned to AI-OS shell.[/bold green]")

    def do_exit(self, arg):
        """/exit : Exit the AI-OS shell."""
        console.print("Exiting AI-OS. Goodbye!")
        return True

    def do_quit(self, arg):
        """/quit : Alias for /exit."""
        return self.do_exit(arg)

def get_class_methods(cls):
    # This helper is no longer used by do_help
    return [method_name for method_name in dir(cls) if callable(getattr(cls, method_name))]

def initialize_cli():
    """Initializes the CLI and context."""
    console.print("[bold green]Starting AI-OS Shell...[/bold green]")

    # Print the quote
    console.print("\n[bold italic yellow]“Abandon vibe coding—embrace AI engineering.”[/bold italic yellow]\n")

    # Context initialization
    console.print("[bold green]Initializing context with git files...[/bold green]")
    files_added = context_manager.load_git_repo()
    if files_added:
        console.print(f"[bold green]Added {len(files_added)} files to context.[/bold green]")
    else:
        console.print("[bold yellow]No git files found or added to context.[/bold yellow]")

    # Instantiate the shell early to access commands/aliases
    shell = AIOSShell()

    # --- Print available commands and aliases (adapted from do_help) ---
    # Dynamically get command methods, excluding internal/hidden ones
    command_methods = [name[3:] for name in dir(shell) if name.startswith('do_') and callable(getattr(shell, name))]
    # Exclude help, quit, exit, and any command that is only reachable via alias
    aliased_cmds = set(shell.aliases.values())
    exclude_cmds = {'help', 'quit', 'exit'} # Don't list aliases directly as primary commands
    # Primary commands are those with do_* methods not exclusively behind an alias
    primary_commands = sorted([cmd for cmd in command_methods if cmd not in exclude_cmds and cmd not in aliased_cmds])
    # Explicitly add help/exit/quit
    system_commands = sorted([cmd for cmd in command_methods if cmd in exclude_cmds])

    console.print("\n[bold green]AI-OS Shell Ready[/bold green]")

    console.print("[bold]Available commands:[/bold]")
    if primary_commands:
        console.print("  " + ", ".join([f"/{c}" for c in primary_commands]))
    if system_commands:
        console.print("  " + ", ".join([f"/{c}" for c in system_commands]))

    if shell.aliases:
        console.print("\n[bold]Aliases:[/bold]")
        # Show aliases like: '> (/chat)'
        aliases_list = sorted([f"{alias} ({f'/{cmd}'}) " for alias, cmd in shell.aliases.items()])
        console.print("  " + ", ".join(aliases_list))
    # --- End command/alias printing ---

    console.print("\nType /help for details on a command.")
    # Use the existing shell instance
    shell.cmdloop()

# The main entry point should be managed elsewhere (e.g., in __main__.py or main.py)
# if __name__ == '__main__':
#    initialize_cli()
