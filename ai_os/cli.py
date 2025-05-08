import cmd
from typing import List
from pathlib import Path
from rich.console import Console
from rich.text import Text
# rich.table.Table is no longer used here
# rich.tree.Tree is no longer used here
import subprocess # Add subprocess import

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

    # Map aliases to command method names (without do_)
    aliases = {
        '>': 'chat',
        '+': 'patch', # Map '+' to 'patch' command
        '!': 'run',   # Add run alias (implementation needed)
        '@': 'macro', # Add macro alias (implementation needed)
    }

    # Default patch strategy to use if not specified
    default_patch_strategy = "full_file" # Use the name defined in patch_strategies/__init__.py

    def __init__(self):
        super().__init__()
        self.command_history: List[str] = []
        self.history_file_path = Path.home() / ".ai_os" / "history.txt"
        self._load_history()

    def _load_history(self):
        self.command_history = [] # Start fresh
        # Ensure directory exists before trying to read/write
        self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.history_file_path.exists():
            with open(self.history_file_path, "r") as f:
                self.command_history = [line.strip() for line in f.readlines() if line.strip()]
        else:
            # print "History file not found, creating..."

            self.history_file_path.touch()

    def _add_history(self, line):
        line = line.strip()
        if not line:
            return
        self.command_history.append(line)
        self.command_history = self.command_history[-20:]
        self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file_path, "w") as f:
            for cmd_line in self.command_history:
                f.write(cmd_line + "\n")

    def precmd(self, line):
        """Parse aliases and slash commands. Also saves command to history."""
        line = line.strip()
        if not line:
            return "" # Return empty string for precmd to ignore empty input lines

        self._add_history(line)

        cmd_name = None
        arg_str = ""

        if line.startswith('/'):
            parts = line.split(maxsplit=1)
            cmd_name = parts[0][1:]
            arg_str = parts[1] if len(parts) > 1 else ''
        elif line and line[0] in self.aliases: # Ensure line is not empty after strip
            cmd_name = self.aliases[line[0]]
            arg_str = line[1:].lstrip() # Get everything after the alias char
        else:
            # Handles inputs that don't start with / or a known alias
            parts = line.split(maxsplit=1)
            first_part = parts[0] if parts else line # Handle case where line is just empty spaces after strip (though already handled by !line check)
            console.print(f"[yellow]Command '{first_part}' not recognized.[/yellow] Commands must start with a slash '/' or an alias ({', '.join(f'{k} (/{v})' for k, v in self.aliases.items())}). For general chat, use `/chat` or `>`. Type `/help` for a list of commands.")
            return "" # Invalid format, prevent execution

        # Return the command name and the rest of the line as arguments string
        return f"{cmd_name} {arg_str}".strip()

    def default(self, line):
        """Handles unrecognized commands after precmd processing."""
        # This is called if precmd returns a valid command name, but no do_* method exists.
        # Our precmd now filters most invalid formats, so this handles valid format but unknown command.
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
            # Stream the response with a thinking spinner
            full_response = ""
            with console.status("Thinking...", spinner="dots"):
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

    def do_run(self, arg):
        """/run <command> or ! <command> : Execute a shell command."""
        if not arg:
            console.print("[yellow]Usage: /run <command>  or  ! <command>[/yellow]")
            return

        console.print(f"[dim]$ {arg}[/dim]") # Print the command being run
        try:
            # shell=True allows using shell features like pipes, but be mindful of security
            # if commands can come from untrusted sources. For a user CLI, it's usually acceptable.
            result = subprocess.run(arg, shell=True, capture_output=True, text=True, check=False)

            if result.stdout:
                console.print(result.stdout.strip())

            if result.stderr:
                console.print(f"[bold red]Error output:[/bold red]\n{result.stderr.strip()}")

            if result.returncode != 0:
                console.print(f"[yellow]Command exited with status {result.returncode}[/yellow]")

        except FileNotFoundError:
            console.print(f"[bold red]Error: Command not found: {arg.split()[0]}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred while trying to run the command:[/bold red] {e}")

    def do_patch(self, arg):
        """/patch [strategy] <plan> : Generate, preview, and apply a code patch.

        Usage: /patch <plan> (uses default strategy '{self.default_patch_strategy}')
               /patch <strategy_name> <plan> (optional: specify strategy)

        Uses the LLM and a chosen strategy to propose file changes,
        presents them for user approval, and applies them to the repo
        with a Git commit if approved.
        """
        parts = arg.strip().split(maxsplit=1)
        strategy_name = self.default_patch_strategy
        plan = ""

        if not parts:
             console.print(f"[yellow]Usage: /patch [strategy_name] <plan>[/yellow]")
             console.print(f"[yellow]Default strategy: '{self.default_patch_strategy}'. Available: {list(commands.PATCH_STRATEGIES.keys())}[/yellow]") # Need access to strategies here
             return

        # Check if the first part looks like a strategy name
        # A simple heuristic: check if it's a known strategy name.
        # This allows "/patch plan..." or "/patch strategy_name plan..."
        first_part = parts[0]
        if first_part in commands.PATCH_STRATEGIES: # Check against the imported registry
             strategy_name = first_part
             plan = parts[1] if len(parts) > 1 else ""
        else:
             # Assume the entire arg is the plan, use the default strategy
             plan = arg.strip()
             strategy_name = self.default_patch_strategy


        if not plan:
            console.print(f"[yellow]Usage: /patch [strategy_name] <plan>[/yellow]")
            console.print(f"[yellow]Please provide a plan.[/yellow]")
            return


        console.print(f"[dim]Using strategy: '{strategy_name}'[/dim]")
        try:
            # Call the orchestrator function in commands.py
            # Pass the console instance and the determined strategy name
            # commands.patch returns True/False indicating workflow success/failure (applied or rejected vs error)
            commands.patch(plan=plan, strategy_name=strategy_name, console=console)
            # Success/failure messages and logging are handled inside commands.patch/apply_patch_with_approval.
            # We don't need to print success/failure here unless commands.patch didn't already do it.

        except Exception as e:
            # Catch any *unexpected* errors that bubble up from the commands module
            # Specific operational errors (git, parsing, unimplemented strategy)
            # should ideally be caught and logged within commands.patch.
            # This catches truly unhandled exceptions.
            console.print(f"\n[bold red]A critical, unexpected error occurred during the patch workflow:[/bold red] {e}")
            # Potentially log this unexpected error as well if not already done
            context_manager.add_message(role="system", content=f"Critical unexpected error during patch: {e}")

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
    config_folder = Path.home() / ".ai_os"
    config_folder.mkdir(parents=True, exist_ok=True)
    config_file = config_folder / "config.json"
    if not config_file.exists():
        config_file.write_text("{}")

    # Command history file is now managed by AIOSShell
    # history_file = config_folder / "history.txt"
    # if not history_file.exists():
    #     history_file.write_text("")


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
    # Add strategy info to startup message
    console.print(f"[dim]Default patch strategy: '{shell.default_patch_strategy}'. Available strategies: {list(commands.PATCH_STRATEGIES.keys())}[/dim]")

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