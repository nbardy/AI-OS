from pathlib import Path
import subprocess

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.styles import Style

from ai_os.utils.context import context_manager
from ai_os.utils.command_history import CommandHistoryManager, PersistentHistory
from ai_os.core import commands
from ai_os.core.commands import COMMANDS, ALIASES, parse_input
from ai_os.ui.context_editor import ContextEditorApp
from ai_os.core.macro_runner import MacroRunner

console = Console()

class AIOSCompleter(Completer):
    def __init__(self):
        self.command_completer = WordCompleter(COMMANDS + list(ALIASES.keys()), ignore_case=True)
        self.path_completer = PathCompleter(only_directories=False, expanduser=True)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        
        # Case 1: Empty text or command completion
        if not text:
            for c in self.command_completer.get_completions(document, complete_event):
                yield c
            return
        
        # Case 2: Command starting with '/' (but not followed by space yet)
        if text.startswith('/') and ' ' not in text:
            for c in self.command_completer.get_completions(document, complete_event):
                yield c
            return
        
        # Case 3: Single alias character - show command completions (except @)
        if len(text) == 1 and text[0] in ALIASES and text[0] != '@':
            for c in self.command_completer.get_completions(document, complete_event):
                yield c
            return
        
        # Case 4: @ followed by file path - THIS IS THE KEY CASE  
        if text.startswith('@'):
            path_part = text[1:]  # Remove the '@' character
            
            # Create a document for just the path part
            path_doc = Document(text=path_part, cursor_position=len(path_part))
            
            for c in self.path_completer.get_completions(path_doc, complete_event):
                # The completion text should be the full path starting with @
                # c.text is the part that would complete the path_part
                completed_text = '@' + path_part[:len(path_part) + c.start_position] + c.text
                
                # start_position should be relative to the original @ position
                # We want to replace from where the completion starts in the path part
                start_pos = c.start_position - len(path_part) - 1
                
                yield Completion(
                    text=completed_text,
                    start_position=start_pos
                )
            return
        
        # Case 5: /macro followed by space - complete file paths
        if text.startswith('/macro '):
            path_part = text[7:]  # Remove '/macro '
            path_doc = Document(text=path_part, cursor_position=len(path_part))
            for c in self.path_completer.get_completions(path_doc, complete_event):
                yield c
            return
        
        # Case 6: Other aliases followed by text
        if text and text[0] in ALIASES and text[0] != '@':
            # For other aliases, complete commands if no space yet
            if ' ' not in text:
                for c in self.command_completer.get_completions(document, complete_event):
                    yield c
            return

class AIOSPromptShell:
    def __init__(self):
        self.console = console
        
        # Initialize command history
        self.history_manager = CommandHistoryManager(max_history=100)
        self.persistent_history = PersistentHistory(self.history_manager)
        
        self.session = PromptSession(
            completer=AIOSCompleter(), 
            style=Style.from_dict({
                'prompt': 'ansicyan bold',
            }),
            history=self.persistent_history
        )
        self.running = True

    def run(self):
        self.console.print("[bold green]Starting AI-OS Shell (prompt_toolkit mode)...[/bold green]")
        self.console.print("\n[bold italic yellow]“Abandon vibe coding—embrace AI engineering.”[/bold italic yellow]\n")
        self.console.print("[bold green]Initializing context with git files...[/bold green]")
        files_added = context_manager.load_git_repo()
        if files_added:
            self.console.print(f"[bold green]Added {len(files_added)} files to context.[/bold green]")
        else:
            self.console.print("[bold yellow]No git files found or added to context.[/bold yellow]")
        self.console.print("\n[bold green]AI-OS Shell Ready[/bold green]")
        self.console.print("[dim]Tab completion: commands, files, and directories. Type /help for commands.[/dim]")
        while self.running:
            try:
                user_input = self.session.prompt("➜ ", include_default_pygments_style=False)
                self.handle_command(user_input.strip())
            except (EOFError, KeyboardInterrupt):
                self.console.print("\nExiting AI-OS. Goodbye!")
                break

    def handle_command(self, line):
        if not line:
            return
        # Use shared parse_input from commands module
        cmd, arg = parse_input(line)
        if cmd in ['/exit', '/quit']:
            self.running = False
            self.console.print("Exiting AI-OS. Goodbye!")
        elif cmd in ['/help']:
            self.console.print("[bold]Available commands:[/bold] " + ", ".join(COMMANDS))
            self.console.print("[bold]Aliases:[/bold] " + ", ".join(f"{k} ({ALIASES[k]})" for k in ALIASES))
            self.console.print("\n[dim]Use arrow keys (↑/↓) to navigate command history from previous sessions.[/dim]")
        elif cmd in ['/history']:
            if arg == 'clear':
                self.history_manager.clear_history()
                self.console.print("[green]Command history cleared.[/green]")
            else:
                history = self.history_manager.get_commands()
                if history:
                    self.console.print(f"[bold]Command History ({len(history)}/100):[/bold]")
                    for i, cmd in enumerate(history[-20:], 1):  # Show last 20
                        self.console.print(f"  {i:2d}. {cmd}")
                    if len(history) > 20:
                        self.console.print(f"  ... and {len(history) - 20} more")
                    self.console.print("\n[dim]Use '/history clear' to clear history[/dim]")
                else:
                    self.console.print("[yellow]No command history found.[/yellow]")
        elif cmd in ['/macro', '@']:
            if not arg:
                self.console.print("[yellow]Usage: /macro <path/to/macro.py> [key=value ...][/yellow]")
                return
            runner = MacroRunner(self.console, self)
            try:
                runner.run(arg)
            except Exception as e:
                self.console.print(f"[bold red]An error occurred while trying to run the macro: {e}[/bold red]")
        elif cmd in ['/run', '!']:
            if not arg:
                self.console.print("[yellow]Usage: /run <command>  or  ! <command>[/yellow]")
                return
            self.console.print(f"[dim]$ {arg}[/dim]")
            try:
                result = subprocess.run(arg, shell=True, capture_output=True, text=True, check=False)
                if result.stdout:
                    self.console.print(result.stdout.strip())
                if result.stderr:
                    self.console.print(f"[bold red]Error output:[/bold red]\n{result.stderr.strip()}")
                if result.returncode != 0:
                    self.console.print(f"[yellow]Command exited with status {result.returncode}[/yellow]")
                
                # Add command and its output to context
                command_record = f"Command: {arg}\n"
                if result.stdout:
                    command_record += f"Output:\n{result.stdout.strip()}\n"
                if result.stderr:
                    command_record += f"Error output:\n{result.stderr.strip()}\n"
                command_record += f"Exit code: {result.returncode}"
                
                context_manager.add_message(role="system", content=command_record)
            except FileNotFoundError:
                self.console.print(f"[bold red]Error: Command not found: {arg.split()[0]}[/bold red]")
                # Also add error to context
                context_manager.add_message(role="system", content=f"Command: {arg}\nError: Command not found: {arg.split()[0]}")
            except Exception as e:
                self.console.print(f"[bold red]An unexpected error occurred while trying to run the command:[/bold red] {e}")
                # Also add error to context
                context_manager.add_message(role="system", content=f"Command: {arg}\nError: Unexpected error: {e}")
        elif cmd in ['/context']:
            app = ContextEditorApp()
            app.run()
            self.console.print("\n[bold green]Returned to AI-OS shell.[/bold green]")
        elif cmd in ['/model']:
            from ai_os.core.orchestrator import get_orchestrator

            if not arg:
                orch = get_orchestrator()
                self.console.print(f"[bold]Current:[/bold] {orch.default_harness} + {orch.default_model}")
                self.console.print("[dim]Usage: /model <opus|sonnet|haiku>[/dim]")
                return

            model = arg.strip().lower()
            if model not in ['opus', 'sonnet', 'haiku']:
                self.console.print(f"[red]Invalid model: {model}[/red]")
                self.console.print("[dim]Valid options: opus, sonnet, haiku[/dim]")
                return

            orch = get_orchestrator()
            orch.default_model = model
            self.console.print(f"[green]✓ Model set to: {model}[/green]")

        elif cmd in ['/harness']:
            from ai_os.core.orchestrator import get_orchestrator

            if not arg:
                orch = get_orchestrator()
                self.console.print(f"[bold]Current harness:[/bold] {orch.default_harness}")
                self.console.print("[dim]Usage: /harness <claude|codex>[/dim]")
                return

            harness = arg.strip().lower()
            if harness not in ['claude', 'codex']:
                self.console.print(f"[red]Invalid harness: {harness}[/red]")
                self.console.print("[dim]Valid options: claude, codex[/dim]")
                return

            orch = get_orchestrator()
            orch.default_harness = harness
            self.console.print(f"[green]✓ Harness set to: {harness}[/green]")
        elif cmd in ['/patch', '+']:
            if not arg:
                self.console.print("[yellow]Usage: /patch <plan> [strategy][/yellow]")
                return
            # Parse the arguments for patch: plan and optional strategy
            parts = arg.split(' strategy=', 1)
            plan = parts[0].strip()
            strategy_name = parts[1].strip() if len(parts) > 1 else "full_file"
            
            try:
                result = commands.patch(plan, strategy_name, self.console)
                if result:
                    self.console.print(f"[green]Patch operation completed successfully![/green]")
                else:
                    self.console.print(f"[yellow]Patch operation was not completed.[/yellow]")
            except Exception as e:
                self.console.print(f"[bold red]An error occurred while running patch: {e}[/bold red]")
        elif cmd in ['/chat', '>']:
            if not arg:
                self.console.print("[yellow]Usage: /chat <prompt>  or  > <prompt>[/yellow]")
                return
            try:
                # Stream the response chunks with console for status indicator
                for chunk in commands.chat(arg, console=self.console):
                    print(chunk, end='', flush=True)
                print()  # Add newline at the end
            except Exception as e:
                self.console.print(f"[bold red]An error occurred while chatting: {e}[/bold red]")
        elif cmd in ['/search', '?']:
            if not arg:
                self.console.print("[yellow]Usage: /search <query>  or  ? <query>[/yellow]")
                return
            try:
                # Stream the search response chunks with console for status indicator
                for chunk in commands.search(arg, console=self.console):
                    print(chunk, end='', flush=True)
                print()  # Add newline at the end
            except Exception as e:
                self.console.print(f"[bold red]An error occurred while searching: {e}[/bold red]")
        else:
            self.console.print(f"[yellow]Unknown command: '{line}'. Type /help for available commands.[/yellow]")

# Entrypoints

def initialize_cli():
    """Initialize and run the AI-OS CLI shell."""
    # Ensure config folder exists
    config_folder = Path.home() / ".ai_os"
    config_folder.mkdir(parents=True, exist_ok=True)
    config_file = config_folder / "config.json"
    if not config_file.exists():
        config_file.write_text("{}")

    # Run the shell (handles all initialization and welcome messages)
    shell = AIOSPromptShell()
    shell.run()


# Alias for backwards compatibility
main = initialize_cli

if __name__ == "__main__":
    initialize_cli()