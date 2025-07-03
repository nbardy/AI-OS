# ai_os/core/macro_runner.py
import inspect
import shlex
import sys
import types
import subprocess
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from rich.console import Console
# from rich.prompt import Prompt # No longer used directly here, cli_instance handles it
from . import macro_helpers # Import the helper module itself
# Import core commands used by runner methods
from ai_os.core import commands
from ai_os.utils.context import context_manager # Access context manager directly or via cli_instance
# from ai_os.utils.thinking_indicator import ThinkingIndicator  # Replaced with console.status


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
             error_msg = f"Error importing macro module {module_path_str}: {e}"
             self.console.print(f"[bold red]{error_msg}[/bold red]")
             # Add import error to context
             try:
                 context_manager.add_message(role="system", content=f"[MACRO ERROR] {error_msg}")
             except Exception as ctx_e:
                 self.console.print(f"[red]Error adding import error to context: {ctx_e}[/red]")
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

    def chat(self, prompt: str, include_context: bool = True, image_path: str = None) -> str:
        """Execute a chat prompt via commands.chat and return the full response."""
        if not isinstance(prompt, str) or not prompt.strip():
            self.console.print("[yellow]Macro chat action requires a non-empty prompt.[/yellow]")
            return f"CHAT_ERROR: Empty prompt"

        full_response = ""
        self.console.print(f"[dim]Macro Chat: > {prompt}[/dim]")
        
        # Handle image encoding if provided
        image_content = None
        if image_path and os.path.exists(image_path):
            try:
                import base64
                with open(image_path, 'rb') as img_file:
                    img_data = img_file.read()
                    base64_data = base64.b64encode(img_data).decode('utf-8')
                    ext = os.path.splitext(image_path)[1].lower()
                    mime_type = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg', 
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }.get(ext, 'image/png')
                    image_content = f"data:{mime_type};base64,{base64_data}"
                    self.console.print(f"[dim]Including image: {os.path.basename(image_path)}[/dim]")
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not encode image: {e}[/yellow]")
        
        if include_context:
            # For context mode with images, we need to handle this differently
            # since commands.chat doesn't support images directly
            if image_content:
                self.console.print("[yellow]Image support in context mode not yet implemented. Using text-only.[/yellow]")
            # Use the normal commands.chat function with context
            for chunk in commands.chat(prompt=prompt, console=self.console):
                print(chunk, end="", flush=True)
                full_response += chunk
        else:
            # Use direct chat_completion to bypass context
            from ai_os.core.chat import chat_completion
            from ai_os.core.models import Message, TextContent, ImageContent
            from ai_os.utils.config import config_manager
            
            # Create message content with or without image
            if image_content:
                content = [
                    TextContent(type="text", text=prompt),
                    ImageContent(type="image_url", image_url={"url": image_content})
                ]
            else:
                content = prompt
            
            # Create a pure message without context
            messages = [Message(role="user", content=content)]
            
            # Get the selected model from config
            selected_model = config_manager.get_current_model()
            
            # Use a vision model if image is provided
            if image_content and selected_model:
                # Check if current model supports vision, if not switch to a vision model
                if 'vision' not in selected_model and 'claude-3' not in selected_model:
                    self.console.print(f"[dim]Switching from {selected_model} to vision model[/dim]")
                    selected_model = "anthropic/claude-3-5-sonnet"  # Default vision model
            
            # Call chat_completion directly
            if selected_model:
                assistant_response_chunks = chat_completion(messages=messages, model=selected_model)
            else:
                assistant_response_chunks = chat_completion(messages=messages)
            
            # Stream the response
            for chunk in assistant_response_chunks:
                print(chunk, end="", flush=True)
                full_response += chunk
                
            # Still add the result to context for tracking
            if image_content:
                context_manager.add_message(role="user", content=f"[MACRO NO-CONTEXT WITH IMAGE] {prompt}")
            else:
                context_manager.add_message(role="user", content=f"[MACRO NO-CONTEXT] {prompt}")
            context_manager.add_message(role="assistant", content=full_response)
            
        print() 
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
            
            # Add command execution to context
            command_record = f"Shell command: {cmd}\n"
            if process.stdout:
                command_record += f"Output:\n{process.stdout.strip()}\n"
            if process.stderr:
                command_record += f"Error:\n{process.stderr.strip()}\n"
            command_record += f"Exit code: {process.returncode}"
            
            context_manager.add_message(role="system", content=command_record)
            
            return process.stdout.strip() if capture else process.returncode # Strip stdout

        except Exception as e:
            self.console.print(f"[bold red]Error running shell command '{cmd}': {e}[/bold red]")
            self.ctx['last_shell_exit_code'] = -1
            # Also add error to context
            context_manager.add_message(role="system", content=f"Shell command: {cmd}\nError: {e}")
            return f"SHELL_ERROR: {e}" if capture else -1

    def patch(self, plan: str, user_approval: bool = True) -> Dict[str, Any] | None:
        """Initiate the patch workflow via the CLI instance."""
        if not isinstance(plan, str) or not plan.strip():
            self.console.print("[yellow]Macro patch action requires a plan.[/yellow]")
            return None 

        self.console.print(f"[dim]Macro requests patch workflow for plan: '{plan}'[/dim]")
        try:
            # Use the commands.patch function directly with default strategy
            patch_result = commands.patch(
                plan=plan,
                strategy_name="full_file",
                console=self.console,
                user_approval_override=user_approval
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
            from rich.prompt import Confirm
            response = Confirm.ask(msg)
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
                error_msg = f"Error during macro execution: {e}"
                self.console.print(f"[bold red]{error_msg}[/bold red]")
                import traceback
                traceback_str = traceback.format_exc()
                self.console.print(traceback_str)
                # Add execution error to context
                try:
                    context_manager.add_message(role="system", content=f"[MACRO ERROR] {error_msg}\n{traceback_str}")
                except Exception as ctx_e:
                    self.console.print(f"[red]Error adding execution error to context: {ctx_e}[/red]")

        except (ValueError, ImportError) as e:
            error_msg = f"Macro Setup Error: {e}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            # Add setup error to context
            try:
                context_manager.add_message(role="system", content=f"[MACRO ERROR] {error_msg}")
            except Exception as ctx_e:
                self.console.print(f"[red]Error adding setup error to context: {ctx_e}[/red]")
        except Exception as e:
            error_msg = f"Unexpected Macro Runtime Error: {e}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            import traceback
            traceback_str = traceback.format_exc()
            self.console.print(traceback_str)
            # Add runtime error to context
            try:
                context_manager.add_message(role="system", content=f"[MACRO ERROR] {error_msg}\n{traceback_str}")
            except Exception as ctx_e:
                self.console.print(f"[red]Error adding runtime error to context: {ctx_e}[/red]")
        finally:
            macro_helpers.set_runner(None)
            self.ctx.clear() # Clear context for next run
            # Restore original CWD
            if macro_path_resolved and Path.cwd() != original_cwd:
                os.chdir(original_cwd)