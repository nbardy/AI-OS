import cmd
from typing import List
from pathlib import Path
from rich.console import Console
from rich.text import Text
# rich.table.Table is no longer used here
# rich.tree.Tree is no longer used here
import subprocess # Add subprocess import
import os # Needed for path completion
from rich.prompt import Prompt # Needed for _ask_approval
# Import the global context_manager instance
from ai_os.utils.context import context_manager
# Import commands which now operate on the context_manager
from ai_os.core import commands

# Import the Textual Context Editor App
from ai_os.ui.context_editor import ContextEditorApp
from ai_os.core.macro_runner import MacroRunner # Import the runner

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
        self.console = console
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
            arg_str_after_alias_char = line[1:].lstrip() 
            # If the arguments after the alias character themselves start with the command name
            # (e.g. user types "@macro actual_path.py" where "@" is alias for "macro"),
            # then the actual arguments for the command should be what follows that redundant command name.
            parts_of_arg_str = arg_str_after_alias_char.split(maxsplit=1)
            if len(parts_of_arg_str) > 1 and parts_of_arg_str[0] == cmd_name:
                arg_str = parts_of_arg_str[1]
            else:
                arg_str = arg_str_after_alias_char
        else:
            # Handles inputs that don't start with / or a known alias
            parts = line.split(maxsplit=1)
            first_part = parts[0] if parts else line
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
            full_response = "" # Keep track of full response for potential error logging if needed
            with console.status("Thinking...", spinner="dots"):
                # commands.chat yields chunks and handles context update internally
                for chunk in commands.chat(prompt=arg):
                    # Ensure each chunk is flushed immediately to avoid buffering issues
                    # interfering with the final output display before the prompt redraws.
                    # print("chunk >", chunk, "<")
                    console.print(chunk, end="", sep="")
                    full_response += chunk # Still useful to have the full response locally if needed later
            # Ensure a newline after the streaming is complete
            console.print()
        except Exception as e:
            # Ensure newline even if error occurs mid-stream
            console.print() # Add newline in case of error too
            console.print(f"\n[bold red]Error during chat:[/bold red] {e}")
            # Log the partial response if available? Maybe not necessary as context should have user msg.

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

    def do_macro(self, arg):
        """/macro <path/to/macro.py> [key=value ...] : Run a macro script."""
        if not arg:
            self.console.print("[yellow]Usage: /macro <path/to/macro.py> [key=value ...][/yellow]")
            return

        runner = MacroRunner(self.console, self)
        try:
            runner.run(arg)
        except Exception as e:
            self.console.print(f"[bold red]An error occurred while trying to run the macro: {e}[/bold red]")

    def complete_macro(self, text, line, begidx, endidx):
        """Completes macro paths and filenames."""
        arg_line = line[line.find('do_macro') + len('do_macro '):begidx]

        last_space_index = arg_line.rfind(' ')
        current_arg_prefix = arg_line[last_space_index + 1:]

        if '=' in current_arg_prefix:
            return []

        if '/' in current_arg_prefix:
            dirname, prefix = os.path.split(current_arg_prefix)
            search_path = Path(dirname)
        else:
            search_path = Path('.')
            prefix = current_arg_prefix

        completions = []
        try:
            for item in os.listdir(search_path):
                item_path = search_path / item
                item_name = item_path.name

                if item_name.startswith(prefix):
                    if item_path.is_dir():
                        completions.append(item_name + '/')
                    elif item_path.suffix == '.py':
                        completions.append(item_name)

            if not '/' in current_arg_prefix and ('examples'.startswith(prefix) or prefix == ''):
                 if Path('examples/').is_dir():
                      completions.append('examples/')

        except FileNotFoundError:
            return []
        except Exception as e:
            self.console.print(f"[yellow]Error during macro path completion: {e}[/yellow]", highlight=False)
            return []

        return sorted(completions)

    def _ask_approval(self, msg: str) -> bool:
        """Internal method called by macro_runner to ask the user for Y/N approval."""
        try:
             return Prompt.ask(f"[bold cyan]Macro asks:[/bold cyan] {msg}\nApprove? (y/N)", console=self.console, choices=["y", "n"], default="n").lower() == 'y'
        except EOFError:
             self.console.print("[yellow]Input stream closed during approval prompt. Denying approval.[/yellow]")
             return False
        except Exception as e:
             self.console.print(f"[bold red]Error during approval prompt: {e}. Denying approval.[/bold red]")
             return False

    def _run_patch_workflow(self, plan: str, user_approval: bool = True) -> dict | None:
        """Internal method called by macro_runner or macro_helpers.patch to execute the patch workflow."""
        if not plan:
             self.console.print("[yellow]Patch workflow requires a plan.[/yellow]")
             return None
        try:
            # commands.patch needs to accept user_approval_override and return the result dict
            patch_result = commands.patch(
                plan=plan,
                strategy_name=self.default_patch_strategy, # Use CLI's default strategy
                console=self.console,
                user_approval_override=user_approval # Pass the flag down
            )
            return patch_result # Return the result from commands.patch
        except Exception as e:
             self.console.print(f"[bold red]A critical error occurred during the patch workflow:[/bold red] {e}")

    @property
    def context_manager(self):
        return context_manager

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
            self.console.print(f"[yellow]Usage: /patch [strategy_name] <plan>[/yellow]")
            self.console.print(f"[yellow]Default strategy: '{self.default_patch_strategy}'. Available: {list(commands.PATCH_STRATEGIES.keys())}[/yellow]")
            return
        first_part = parts[0]
        if first_part in commands.PATCH_STRATEGIES:
            strategy_name = first_part
            plan = parts[1] if len(parts) > 1 else ""
        else:
            plan = arg.strip()
            strategy_name = self.default_patch_strategy
        if not plan:
            self.console.print(f"[yellow]Usage: /patch [strategy_name] <plan>[/yellow]")
            self.console.print(f"[yellow]Please provide a plan.[/yellow]")
            return
        self.console.print(f"[dim]Using strategy: '{strategy_name}'[/dim]")
        try:
            # Call the internal workflow method, CLI always asks for approval
            self._run_patch_workflow(plan=plan, user_approval=True)

        except Exception as e:
            # Catch any *unexpected* errors that bubble up from _run_patch_workflow
            self.console.print(f"\n[bold red]A critical, unexpected error occurred during the patch workflow:[/bold red] {e}")
            # Log to context history
            self.context_manager.add_message(role="system", content=f"Critical unexpected error during patch (CLI): {e}")

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