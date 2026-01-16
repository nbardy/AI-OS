# ai_os/core/macro_runner.py
"""
Macro Runner - executes Python macro scripts.

V2: Uses Claude Code orchestrator instead of OpenRouter.
"""

import importlib.util
import inspect
import shlex
import sys
import types
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, Coroutine

from rich.console import Console
from rich.prompt import Confirm

from ai_os.core import macro_helpers
from ai_os.core.orchestrator import ClaudeOrchestrator
from ai_os.utils.context import context_manager


class MacroRunner:
    """
    Executes Python macro scripts with access to Claude Code via orchestrator.
    """

    def __init__(self, console: Console, cli_instance: Any = None):
        self.console = console
        self.cli_instance = cli_instance
        self.ctx: Dict[str, Any] = {
            "vars": {},
            "last_shell_exit_code": 0,
        }
        # Create orchestrator for this macro run
        self.orchestrator = ClaudeOrchestrator()

    # =========================================================================
    # Macro Execution
    # =========================================================================

    def run(self, argline: str) -> None:
        """Run a macro from command line."""
        original_cwd = Path.cwd()
        macro_path_resolved = None

        try:
            module_path_str, kwargs = self._parse_argline(argline)
            macro_path_resolved = Path(module_path_str)
            self.console.print(f"[dim]Running macro: {module_path_str} with args: {kwargs}[/dim]")

            # Change CWD to the macro's directory
            os.chdir(macro_path_resolved.parent)

            # Import the macro module
            module = self._import_module(str(macro_path_resolved.name))
            main_func = getattr(module, "main", None)

            if not (callable(main_func) and
                    len(inspect.signature(main_func).parameters) >= 1 and
                    list(inspect.signature(main_func).parameters.keys())[0] == 'ctx'):
                self.console.print(
                    f"[bold red]Error:[/bold red] Macro '{module_path_str}' must define a "
                    "function named 'main(ctx, **kwargs)'."
                )
                return

            # Setup context
            self.ctx['vars'] = kwargs.copy()
            self.ctx['last_shell_exit_code'] = 0

            # Install runner for macro_helpers
            macro_helpers.set_runner(self)

            try:
                main_func(self.ctx, **kwargs)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Macro interrupted by user.[/yellow]")
            except Exception as e:
                error_msg = f"Error during macro execution: {e}"
                self.console.print(f"[bold red]{error_msg}[/bold red]")
                import traceback
                traceback_str = traceback.format_exc()
                self.console.print(traceback_str)
                context_manager.add_message(
                    role="system",
                    content=f"[MACRO ERROR] {error_msg}\n{traceback_str}"
                )

        except (ValueError, ImportError) as e:
            error_msg = f"Macro Setup Error: {e}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            context_manager.add_message(role="system", content=f"[MACRO ERROR] {error_msg}")

        except Exception as e:
            error_msg = f"Unexpected Macro Runtime Error: {e}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            import traceback
            self.console.print(traceback.format_exc())

        finally:
            macro_helpers.set_runner(None)
            self.ctx.clear()
            if macro_path_resolved and Path.cwd() != original_cwd:
                os.chdir(original_cwd)

    def _parse_argline(self, argline: str) -> Tuple[str, Dict[str, Any]]:
        """Parse macro command line arguments."""
        parts = shlex.split(argline)
        if not parts:
            raise ValueError("Usage: /macro <module_path> [key=value ...]")

        module_path_str = parts[0]
        module_path = Path(module_path_str).resolve()

        if not module_path.is_file() or module_path.suffix.lower() != ".py":
            raise ValueError(f"Macro path '{module_path_str}' must be a valid .py file.")

        kwargs: Dict[str, Any] = {}
        for tok in parts[1:]:
            if "=" not in tok:
                raise ValueError(f"Macro argument '{tok}' is not in key=value format.")
            k, v = tok.split("=", 1)
            kwargs[k] = self._parse_value(v)

        return str(module_path), kwargs

    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def _import_module(self, module_path_str: str) -> types.ModuleType:
        """Dynamically import a Python module from a file path."""
        path = Path(module_path_str)
        module_name = f"aios_macro_{path.stem}_{os.urandom(4).hex()}"

        parent_dir = str(path.parent) if path.parent != Path('.') else '.'
        original_sys_path = list(sys.path)
        added_to_path = False

        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            added_to_path = True

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module
            else:
                raise ImportError(f"Could not load module spec for {module_path_str}")
        finally:
            if added_to_path and parent_dir in sys.path:
                sys.path.remove(parent_dir)

    # =========================================================================
    # Methods called by macro_helpers
    # =========================================================================

    def log(self, msg: str) -> None:
        """Log a message to the user console."""
        self.console.print(f"[cyan]{msg}[/cyan]")

    def log_to_context(self, msg: str) -> None:
        """Log a message to the AI-OS context history."""
        context_manager.add_message(role="system", content=f"[MACRO] {msg}")

    # -------------------------------------------------------------------------
    # LLM Operations (via orchestrator)
    # -------------------------------------------------------------------------

    def chat(
        self,
        prompt: str,
        include_context: bool = True,
        image_path: str = None,
        model: str = None,
        async_: bool = False
    ) -> Union[str, Coroutine[Any, Any, str]]:
        """Chat with Claude via orchestrator."""
        self.console.print(f"[dim]> {prompt[:80]}{'...' if len(prompt) > 80 else ''}[/dim]")

        # Handle vision requests
        if image_path and os.path.exists(image_path):
            full_prompt = f"Read the image at {image_path} and analyze it:\n{prompt}"
        else:
            full_prompt = prompt

        if async_:
            return self.orchestrator.chat(full_prompt, model=model, async_=True)

        # Sync version with streaming output
        full_response = ""
        for chunk in self.orchestrator.chat_streaming(full_prompt, model=model):
            print(chunk, end="", flush=True)
            full_response += chunk
        print()  # Newline after streaming

        # Add to context
        context_manager.add_message(role="user", content=prompt)
        context_manager.add_message(role="assistant", content=full_response)

        return full_response

    def chat_json(
        self,
        prompt: str,
        model: str = None,
        async_: bool = False
    ) -> Any:
        """Get JSON response from Claude."""
        return self.orchestrator.chat_json(prompt, model=model, async_=async_)

    def vision(
        self,
        prompt: str,
        image: str,
        model: str = None,
        async_: bool = False
    ) -> Union[str, Coroutine[Any, Any, str]]:
        """Analyze an image with Claude."""
        return self.orchestrator.vision(prompt, image, model=model, async_=async_)

    def edit(
        self,
        instruction: str,
        file: str = None,
        async_: bool = False
    ) -> Union[bool, Coroutine[Any, Any, bool]]:
        """Have Claude edit files."""
        self.console.print(f"[dim]Editing: {instruction[:80]}{'...' if len(instruction) > 80 else ''}[/dim]")
        return self.orchestrator.edit(instruction, file=file, async_=async_)

    # -------------------------------------------------------------------------
    # File Operations (direct, via orchestrator)
    # -------------------------------------------------------------------------

    def read(self, path: str) -> str:
        """Read file contents."""
        return self.orchestrator.read(path)

    def write(self, path: str, content: str) -> None:
        """Write file contents."""
        self.orchestrator.write(path, content)

    def exists(self, path: str) -> bool:
        """Check if file exists."""
        return self.orchestrator.exists(path)

    # -------------------------------------------------------------------------
    # Shell Operations
    # -------------------------------------------------------------------------

    def shell(self, cmd: str, capture: bool = False, check: bool = False) -> Any:
        """Execute a shell command."""
        self.console.print(f"[dim]$ {cmd}[/dim]")

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )

        if result.stdout and not capture:
            self.console.print(result.stdout.strip())
        if result.stderr:
            self.console.print(f"[red]{result.stderr.strip()}[/red]")

        self.ctx['last_shell_exit_code'] = result.returncode

        # Log to context
        context_manager.add_message(
            role="system",
            content=f"Shell: {cmd}\nExit: {result.returncode}"
        )

        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )

        return result.stdout.strip() if capture else result.returncode

    # -------------------------------------------------------------------------
    # Human Interaction
    # -------------------------------------------------------------------------

    def approve(self, msg: str) -> bool:
        """Prompt the user for Y/N approval."""
        self.console.print(f"[bold cyan]{msg}[/bold cyan]")
        try:
            response = Confirm.ask(msg)
            self.console.print(f"[dim]User: {'Yes' if response else 'No'}[/dim]")
            return response
        except Exception as e:
            self.console.print(f"[red]Approval error: {e}. Defaulting to No.[/red]")
            return False

    # -------------------------------------------------------------------------
    # Context and State
    # -------------------------------------------------------------------------

    def get_var(self, name: str, default: Any = None) -> Any:
        """Get a variable from the macro context."""
        return self.ctx['vars'].get(name, default)

    def set_var(self, name: str, value: Any) -> None:
        """Set a variable in the macro context."""
        self.ctx['vars'][name] = value

    def get_last_shell_exit_code(self) -> int:
        """Get the exit code of the last shell command."""
        return self.ctx.get('last_shell_exit_code', 0)

    def get_cost(self) -> Dict[str, Any]:
        """Get accumulated cost for this macro run."""
        return self.orchestrator.get_cost()
