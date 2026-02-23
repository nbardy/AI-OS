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
from ai_os.core.dsl import flush_logs
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
            # Flush logs to context as single message
            logs = flush_logs()
            if logs.strip():
                context_manager.add_message(role="system", content=f"[MACRO OUTPUT]\n{logs}")

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

        # Clear cached submodules from this macro's directory to enable hot-reload
        self._clear_cached_modules(Path(parent_dir).resolve())

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

    def _clear_cached_modules(self, macro_dir: Path) -> None:
        """Clear any cached modules that live in the macro's directory tree.

        This enables hot-reload: when a macro is re-run, its submodules
        (like 'prompts.goal_setter') are reimported from disk.
        """
        to_remove = []
        for name, module in sys.modules.items():
            if module is None:
                continue
            try:
                module_file = getattr(module, '__file__', None)
                if module_file:
                    module_path = Path(module_file).resolve()
                    # Check if module lives under the macro's directory
                    if str(module_path).startswith(str(macro_dir)):
                        to_remove.append(name)
            except Exception:
                pass

        for name in to_remove:
            del sys.modules[name]

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
        images: list = None,
        model: str = None,
        harness: str = None,
        reasoning_effort: str = None,
        async_: bool = False
    ) -> Union[str, Coroutine[Any, Any, str]]:
        """Chat with Claude or Codex via orchestrator.

        Args:
            prompt: The prompt to send
            include_context: Whether to include conversation context
            images: List of image paths for Claude to read
            model: Model to use (haiku, sonnet, opus for claude; o4-mini etc for codex)
            harness: 'claude' or 'codex' (defaults to orchestrator's default)
            reasoning_effort: For codex only: 'low', 'medium', 'high'
            async_: If True, return coroutine for async execution
        """
        self.console.print(f"[dim]> {prompt[:80]}{'...' if len(prompt) > 80 else ''}[/dim]")

        # Handle vision requests - images is a list of paths
        if images:
            valid_paths = [p for p in images if os.path.exists(p)]
            if valid_paths:
                image_instructions = "\n".join([f"Read the image at {p}" for p in valid_paths])
                full_prompt = f"{image_instructions}\n\n{prompt}"
            else:
                full_prompt = prompt
        else:
            full_prompt = prompt

        if async_:
            return self.orchestrator.chat(
                full_prompt, model=model, harness=harness,
                reasoning_effort=reasoning_effort, async_=True
            )

        # Sync version: streaming only supported for claude harness
        resolved_harness = harness or self.orchestrator.default_harness
        if resolved_harness == "codex":
            full_response = self.orchestrator.chat(
                full_prompt, model=model, harness="codex",
                reasoning_effort=reasoning_effort
            )
            print(full_response)
        else:
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

    # -------------------------------------------------------------------------
    # Parallel Execution (spawn/join/gather)
    # -------------------------------------------------------------------------

    def spawn(self, prompt: str, output_file: str = None, model: str = None, **kwargs):
        """Spawn an async Claude process."""
        self.console.print(f"[dim]Spawning agent: {prompt[:60]}{'...' if len(prompt) > 60 else ''}[/dim]")
        return self.orchestrator.spawn(prompt, output_file=output_file, model=model, **kwargs)

    def join(self, agents, timeout: float = None):
        """Wait for spawned agents to complete."""
        self.console.print(f"[dim]Joining {len(agents)} agents...[/dim]")
        results = self.orchestrator.join(agents, timeout=timeout)
        successful = sum(1 for r in results if r.success)
        self.console.print(f"[dim]{successful}/{len(agents)} agents completed successfully[/dim]")
        return results

    def gather(self, *prompts: str, model: str = None, **kwargs):
        """Run multiple prompts in parallel."""
        self.console.print(f"[dim]Running {len(prompts)} prompts in parallel...[/dim]")
        results = self.orchestrator.gather(*prompts, model=model, **kwargs)
        self.console.print(f"[dim]Gathered {len(results)} results[/dim]")
        return results
