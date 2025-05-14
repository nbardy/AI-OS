# ai_os/core/macro_runner.py
import inspect
import shlex
import sys
import types
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from rich.console import Console
# from rich.prompt import Prompt # No longer used directly here, cli_instance handles it
from . import macro_helpers # Import the helper module itself
# Import core commands used by runner methods
from ai_os.core import commands
from ai_os.utils.context import context_manager # Access context manager directly or via cli_instance


class MacroRunner:
    def __init__(self, console: Console, cli_instance: Any):
        self.console = console
        self.cli_instance = cli_instance # Keep reference to the CLI shell instance
        self.ctx: Dict[str, Any] = {
            "vars": {},
            "last_shell_exit_code": 0,
            # CLI instance is NOT stored in ctx for direct macro access.
            # Macros interact via the explicit helper functions.
        }

    def _parse_argline(self, argline: str) -> Tuple[str, Dict[str, Any]]:
        """Parses macro command line arguments: module_path key=value args."""
        parts = shlex.split(argline)
        if not parts:
            raise ValueError("Usage: /macro <module_path> [key=value ...]")

        module_path_str = parts[0]
        # Resolve path relative to current working directory
        module_path = Path(module_path_str).resolve()

        if not module_path.is_file() or module_path.suffix.lower() != ".py":
             raise ValueError(f"Macro path '{module_path_str}' must be a valid .py file. Resolved: {module_path}")

        kwargs: Dict[str, Any] = {}
        for tok in parts[1:]:
            if "=" not in tok:
                raise ValueError(f"Macro argument '{tok}' is not in key=value format.")
            k, v = tok.split("=", 1)
            # Attempt type conversion for common types
            try:
                if v.lower() == 'true':
                    kwargs[k] = True
                elif v.lower() == 'false':
                    kwargs[k] = False
                elif '.' in v: # Check for float before int
                    kwargs[k] = float(v)
                else:
                    kwargs[k] = int(v)
            except ValueError:
                kwargs[k] = v # Keep as string if conversion fails
        return str(module_path), kwargs # Return resolved path string

    def _import_module(self, module_path_str: str) -> types.ModuleType:
        """Dynamically imports a Python module from a file path."""
        path = Path(module_path_str)
        # Create a more unique module name to avoid collisions if macros have same stem
        module_name = f"aios_macro_{path.stem}_{os.urandom(4).hex()}"

        parent_dir = str(path.parent)
        
        original_sys_path = list(sys.path)
        added_to_path = False
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            added_to_path = True

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec and spec.loader:
                 module = importlib.util.module_from_spec(spec)
                 sys.modules[module_name] = module 
                 spec.loader.exec_module(module)
                 return module
            else:
                 raise ImportError(f"Could not load module spec for {module_path_str}")

        except Exception as e:
             self.console.print(f"[bold red]Error importing macro module {module_path_str}:[/bold red] {e}")
             raise 
        finally:
            # Clean up sys.path
            if added_to_path and parent_dir in sys.path: # Only remove if we added it
                 sys.path.remove(parent_dir)
            # Optionally remove the module from sys.modules if it causes issues with re-runs,
            # though dynamic naming should largely prevent this.
            # if module_name in sys.modules:
            #     del sys.modules[module_name]


    # --- Methods called by macro_helpers ---

    def log(self, msg: str) -> None:
        """Log a message to the user console."""
        self.console.print(f"[cyan]Macro Log:[/cyan] {msg}")

    def log_to_context(self, msg: str) -> None:
        """Log a message to the AI-OS context history (as a system message from Macro)."""
        try:
             context_manager.add_message(role="system", content=f"[MACRO] {msg}")
        except Exception as e:
             self.console.print(f"[red]Error adding macro log to context: {e}[/red]")

    def chat(self, prompt: str) -> str:
        """Execute a chat prompt via commands.chat and return the full response."""
        if not isinstance(prompt, str) or not prompt.strip():
            self.console.print("[yellow]Macro chat action requires a non-empty prompt.[/yellow]")
            return f"CHAT_ERROR: Empty prompt"

        full_response = ""
        self.console.print(f"[dim]Macro Chat: > {prompt}[/dim]") 
        with self.console.status("Macro thinking...", spinner="dots"):
             # Use the commands.chat function directly, collect output
             for chunk in commands.chat(prompt=prompt): # Assumes commands.chat yields chunks
                 self.console.print(chunk, end="", sep="")
                 full_response += chunk
        self.console.print() 
        return full_response 

    def shell(self, cmd: str, capture: bool = False) -> Any:
        """Execute a shell command via subprocess.run."""
        if not isinstance(cmd, str) or not cmd.strip():
             self.console.print("[yellow]Macro shell action requires a command string.[/yellow]")
             self.ctx['last_shell_exit_code'] = -1 # Consistent error code
             return f"SHELL_ERROR: Empty command" if capture else -1

        self.console.print(f"[dim]$ {cmd}[/dim]")
        try:
            process = subprocess.run(
                cmd, shell=True, 
                capture_output=True,
                text=True,
                check=False 
            )

            if process.stdout and not capture: 
                self.console.print(process.stdout.strip())

            if process.stderr:
                self.console.print(f"[red]Stderr:[/red]\n{process.stderr.strip()}")

            self.ctx['last_shell_exit_code'] = process.returncode
            return process.stdout.strip() if capture else process.returncode # Strip stdout

        except Exception as e:
            self.console.print(f"[bold red]Error running shell command '{cmd}': {e}[/bold red]")
            self.ctx['last_shell_exit_code'] = -1
            return f"SHELL_ERROR: {e}" if capture else -1

    def patch(self, plan: str, user_approval: bool = True) -> Dict[str, Any] | None:
        """Initiate the patch workflow via the CLI instance."""
        if not isinstance(plan, str) or not plan.strip():
            self.console.print("[yellow]Macro patch action requires a plan.[/yellow]")
            return None 

        self.console.print(f"[dim]Macro requests patch workflow for plan: '{plan}'[/dim]")
        try:
            patch_result = self.cli_instance._run_patch_workflow(
                plan=plan,
                user_approval=user_approval 
            )
            return patch_result 
        except Exception as e:
             self.console.print(f"[bold red]Error during macro patch workflow: {e}[/bold red]")
             return {"applied": False, "error": str(e)} # Ensure a consistent error structure

    def approve(self, msg: str) -> bool:
        """Prompt the user for Y/N approval via the CLI instance."""
        if not isinstance(msg, str) or not msg.strip():
             self.console.print("[yellow]Macro approve action requires a message string.[/yellow]")
             return False 

        self.console.print(f"[bold cyan]Macro asks for approval:[/bold cyan] {msg}")
        try:
            response = self.cli_instance._ask_approval(msg)
            self.console.print(f"[dim]User responded: {'Yes' if response else 'No'}[/dim]")
            return response 
        except Exception as e:
             self.console.print(f"[bold red]Error during approval prompt: {e}. Denying approval.[/bold red]")
             return False 

    def get_var(self, name: str, default: Any = None) -> Any:
        """Get a variable from the macro context."""
        return self.ctx['vars'].get(name, default)

    def get_last_shell_exit_code(self) -> int:
        """Get the exit code of the last shell command."""
        return self.ctx.get('last_shell_exit_code', 0) # Default to 0 if not set


    def run(self, argline: str):
        """Runs a macro script from a file path."""
        original_cwd = Path.cwd() # Store original CWD
        macro_path_resolved = None
        try:
            module_path_str, kwargs = self._parse_argline(argline)
            macro_path_resolved = Path(module_path_str) # For CWD change
            self.console.print(f"[dim]Running macro: {module_path_str} with args: {kwargs}[/dim]")

            # Change CWD to the macro's directory before import and execution
            # This allows macros to use relative paths for their own resources/imports
            os.chdir(macro_path_resolved.parent)

            module = self._import_module(str(macro_path_resolved.name)) # Import using only filename

            main_func = getattr(module, "main", None)

            if not (callable(main_func) and
                    len(inspect.signature(main_func).parameters) >= 1 and
                    list(inspect.signature(main_func).parameters.keys())[0] == 'ctx'
                    # Consider checking for **kwargs if strict adherence is needed
                    # and any(param.kind == inspect.Parameter.VAR_KEYWORD 
                    #          for param in inspect.signature(main_func).parameters.values())
                    ):
                self.console.print(
                    f"[bold red]Error:[/bold red] Macro '{module_path_str}' must define a "
                    "function named 'main(ctx, **kwargs)' or 'main(ctx)' or 'main(ctx, some_arg, ...)'."
                )
                return

            self.ctx['vars'] = kwargs.copy()
            self.ctx['last_shell_exit_code'] = 0 

            macro_helpers.set_runner(self)

            try:
                main_func(self.ctx, **kwargs)

            except Exception as e:
                self.console.print(f"[bold red]Error during macro execution:[/bold red] {e}")
                import traceback
                self.console.print(traceback.format_exc())

        except (ValueError, ImportError) as e:
            self.console.print(f"[bold red]Macro Setup Error:[/bold red] {e}")
        except Exception as e:
            self.console.print(f"[bold red]Unexpected Macro Runtime Error:[/bold red] {e}")
            import traceback
            self.console.print(traceback.format_exc())
        finally:
            macro_helpers.set_runner(None)
            self.ctx.clear() # Clear context for next run
            # Restore original CWD
            if macro_path_resolved and Path.cwd() != original_cwd:
                os.chdir(original_cwd)