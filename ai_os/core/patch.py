# ai_os/core/patch.py - Applying the Patch object

# Standard Library Imports
import subprocess
from pathlib import Path
from typing import List, Dict

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

def apply_patch_with_approval(patch: Patch, console: Console) -> bool:
    """
    Presents patch details, asks Y/N, applies file changes, git add/commit.
    Relies on exceptions propagating for core errors.
    """
    if not isinstance(patch, Patch) or not patch.file_changes:
        console.print("[yellow]Invalid or empty patch.[/yellow]")
        context_manager.add_message(role="system", content="Handled invalid/empty patch.")
        return True # Treat as successful no-op

    console.print("\n[yellow]Proposed Patch:[/yellow]")
    summaries = patch.summaries or {}
    for file, summary in sorted(summaries.items()): # Sort for consistent display
        console.print(f"  [cyan]{file}:[/cyan] [dim]{summary}[/dim]")
    console.print("---")

    if not Prompt.ask("Apply? (y/N)", choices=["y", "n"], default="n").lower() == 'y':
        console.print("[red]Rejected.[/red]")
        context_manager.add_message(role="system", content="Patch rejected by user.")
        return False

    console.print("[green]Applying...[/green]")
    files_to_add = list(patch.file_changes.keys())
    files_to_add.sort() # Consistent order

    # Write Files
    for file_path_str in files_to_add:
        content = patch.file_changes[file_path_str]
        p = Path(file_path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        console.print(f"[dim]Wrote {p}[/dim]")

    # Git Add
    if files_to_add:
        _run_git(['add', '--'] + files_to_add)
        console.print(f"[dim]Staged {len(files_to_add)} files.[/dim]")
    else:
         console.print("[yellow]No files to stage.[/yellow]")


    # Git Commit Message
    commit_summary_lines = [
        f"- {f}: {summaries.get(f, 'Update')}" for f in sorted(files_to_add)
    ]
    commit_message = "Apply AI-OS patch\n\n" + "\n".join(commit_summary_lines)

    # Git Commit (Check returncode manually to handle 'nothing to commit')
    console.print("[dim]Committing...[/dim]")
    commit_result = _run_git(['commit', '-m', commit_message], check=False)

    if commit_result.returncode != 0:
        if "nothing to commit" in commit_result.stderr.lower() or "nothing added to commit" in commit_result.stderr.lower():
            console.print("[yellow]No effective changes; nothing committed.[/yellow]")
            context_manager.add_message(role="system", content="Applied patch: No changes detected.")
            # Still return True as the patch 'workflow' for this specific patch was completed without error
        else:
            # Actual commit error, print stderr and let caller handle the exception
            console.print(f"""[bold red]Commit failed:[/bold red]
{commit_result.stderr.strip()}""")
            commit_result.check_returncode() # Re-raise CalledProcessError
    else:
        # Commit successful, get SHA and log
        sha_result = _run_git(['rev-parse', 'HEAD'])
        commit_sha = sha_result.stdout.strip()
        console.print(f"[bold green]Applied. Commit: {commit_sha}[/bold green]")
        context_manager.add_message(role="system", content=f"""Applied patch: {commit_sha}
{commit_message}""")

    return True # Indicate successful application or successful 'nothing-to-commit'

# Note: This function *does not* handle LLM interaction or parsing.
# It only applies a pre-generated and approved Patch object. 