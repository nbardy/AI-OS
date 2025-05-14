# ai_os/core/patch.py - Applying the Patch object

# Standard Library Imports
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any

# Third-Party Imports
from rich.console import Console
from rich.prompt import Prompt

# --- AI-OS Imports ---
from ai_os.core.models import Message, Patch
from ai_os.utils.context import context_manager

def _run_git(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Runs git, raises CalledProcessError on failure if check=True."""
    return subprocess.run(
        ['git'] + cmd,
        check=check,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

def apply_patch_with_approval(
    patch: Patch,
    console: Console,
    user_approval_override: Optional[bool] = None
) -> Dict[str, Any] | None:
    """
    Presents patch details, asks Y/N (if user_approval_override is not False),
    applies file changes, git add/commit.
    Returns a dictionary describing the outcome or None on critical errors.
    """
    if not isinstance(patch, Patch) or not patch.file_changes:
        console.print("[yellow]Invalid or empty patch.[/yellow]")
        context_manager.add_message(role="system", content="Handled invalid/empty patch.")
        # Indicate no application happened, but wasn't a critical failure
        return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch}

    console.print("\n[yellow]Proposed Patch:[/yellow]")
    summaries = patch.summaries or {}
    for file, summary in sorted(summaries.items()): # Sort for consistent display
        console.print(f"  [cyan]{file}:[/cyan] [dim]{summary}[/dim]")
    console.print("---")

    # Determine if approval is needed
    ask_for_approval = user_approval_override if user_approval_override is not None else True

    applied = False
    commit_sha: str | None = None
    log_file_path: str | None = None # Currently no specific log file generated here

    if ask_for_approval:
        try:
            response = Prompt.ask("Apply? (y/N)", console=console, choices=["y", "n"], default="n").lower()
            if response != 'y':
                console.print("[red]Rejected by user.[/red]")
                context_manager.add_message(role="system", content="Patch rejected by user.")
                return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch} # Return rejection dict
            # else: continue to apply
        except EOFError: # Handle Ctrl+D or input stream closed
             console.print("[yellow]Input stream closed during approval prompt. Denying application.[/yellow]")
             context_manager.add_message(role="system", content="Patch denied due to closed input stream.")
             return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch} # Return denial dict
        except Exception as e:
             console.print(f"[bold red]Error during approval prompt: {e}. Denying application.[/bold red]")
             context_manager.add_message(role="system", content=f"Error during patch approval: {e}.")
             return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch, 'error': str(e)} # Return error dict

    # If we reach here, either approval was given or not required
    console.print("[green]Applying...[/green]")
    files_to_add = list(patch.file_changes.keys())
    files_to_add.sort() # Consistent order

    # Write Files
    try:
        for file_path_str in files_to_add:
            content = patch.file_changes[file_path_str]
            p = Path(file_path_str)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            console.print(f"[dim]Wrote {p}[/dim]")
    except Exception as e:
         console.print(f"[bold red]Error writing files:[/bold red] {e}")
         context_manager.add_message(role="system", content=f"Error writing patch files: {e}.")
         # This is a critical failure *before* git operations, return None?
         # Or return applied: False with error message? Let's return applied: False
         return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch, 'error': str(e)}

    # Git Add
    try:
        if files_to_add:
            _run_git(['add', '--'] + files_to_add)
            console.print(f"[dim]Staged {len(files_to_add)} files.[/dim]")
        else:
             console.print("[yellow]No files to stage.[/yellow]")
    except subprocess.CalledProcessError as e:
         console.print(f"""[bold red]Git Add failed:[/bold red]
{e.stderr.strip()}""")
         context_manager.add_message(role="system", content=f"Git add failed: {e.stderr.strip()}")
         return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch, 'error': e.stderr.strip()}

    # Git Commit Message
    commit_summary_lines = [
        f"- {f}: {summaries.get(f, 'Update')}" for f in sorted(files_to_add)
    ]
    commit_message = "Apply AI-OS patch\n\n" + "\n".join(commit_summary_lines)

    # Git Commit (Check returncode manually to handle 'nothing to commit')
    console.print("[dim]Committing...[/dim]") # Check returncode manually to handle 'nothing to commit'
    commit_result = _run_git(['commit', '-m', commit_message], check=False)

    if commit_result.returncode != 0: # Check returncode
        if "nothing to commit" in commit_result.stderr.lower() or "nothing added to commit" in commit_result.stderr.lower():
            console.print("[yellow]No effective changes; nothing committed.[/yellow]")
            context_manager.add_message(role="system", content="Applied patch: No changes detected.")
            # Still return True as the patch 'workflow' for this specific patch was completed without error
            return {'applied': True, 'sha': None, 'log_file': None, 'patch_obj': patch}
        else:
            # Actual commit error, print stderr and let caller handle the exception
            console.print(f"""[bold red]Commit failed:[/bold red]
{commit_result.stderr.strip()}""")
            context_manager.add_message(role="system", content=f"Commit failed: {commit_result.stderr.strip()}")
            return {'applied': False, 'sha': None, 'log_file': None, 'patch_obj': patch, 'error': commit_result.stderr.strip()}
    else:
        # Commit successful, get SHA and log
        try:
            sha_result = _run_git(['rev-parse', 'HEAD']) # Check=True, this should succeed after commit
            commit_sha = sha_result.stdout.strip()
            console.print(f"[bold green]Applied. Commit: {commit_sha}[/bold green]")
            context_manager.add_message(role="system", content=f"""Applied patch: {commit_sha}
{commit_message}""")
            applied = True
        except subprocess.CalledProcessError as e:
            # Handle errors specifically from the SHA lookup if commit succeeded but lookup failed? Unlikely.
            console.print(f"[bold red]Error getting commit SHA:[/bold red] {e}")
            context_manager.add_message(role="system", content=f"Error getting patch commit SHA: {e}.")
            # The commit might have happened, but we failed to get the SHA. This is a messy state.
            # Indicate potentially applied but with error getting details.
            applied = True # Assume applied if commit had returncode 0
            commit_sha = None

    # Currently no specific log file is generated *by this function*
    # Return the structured result
    return {'applied': applied, 'sha': commit_sha, 'log_file': log_file_path, 'patch_obj': patch}

# Note: This function *does not* handle LLM interaction or parsing.
# It only applies a pre-generated and approved Patch object. 