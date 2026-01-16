# Implementation Roadmap: AI-OS v2 Build Plan

**Date:** 2026-01-17
**Status:** Planning Complete
**Purpose:** Phased implementation plan with concrete deliverables

---

## Overview

This document outlines the implementation plan for AI-OS v2, organized into phases with clear milestones, deliverables, and acceptance criteria.

**Total estimated effort:** 4-6 focused days
**Risk level:** Low-Medium (mostly deletion and simplification)

---

## Phase 0: Preparation (Day 0)

### Goals
- Verify Claude Code works as expected
- Set up clean development branch
- Establish testing baseline

### Tasks

#### 0.1 Environment Verification
```bash
# Verify Claude Code installation
claude --version
claude -p "Say hello" --output-format json

# Verify Python environment
python --version  # Should be 3.11+
uv --version      # Package manager
```

**Acceptance:** Claude Code responds, Python 3.11+ available.

#### 0.2 Create Development Branch
```bash
git checkout -b v2-claude-code-native
git push -u origin v2-claude-code-native
```

**Acceptance:** Branch created and pushed.

#### 0.3 Test Existing Macros
```bash
# Document current behavior
aios
/macro examples/tdd_macro.py test_goal="simple math function"
/macro examples/basic_macro_demo.py
```

**Acceptance:** Document which macros work, which fail, what the output looks like.

#### 0.4 Create Test Harness
```python
# tests/test_v2_integration.py
"""Integration tests for v2 functionality."""

def test_claude_code_basic():
    """Verify Claude Code subprocess works."""
    import subprocess
    result = subprocess.run(
        ["claude", "-p", "--output-format", "json"],
        input="Say 'test passed'",
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "test passed" in result.stdout.lower()
```

**Acceptance:** Test harness created, baseline tests pass.

---

## Phase 1: Core Orchestrator (Day 1)

### Goals
- Build the Claude Code subprocess wrapper
- Implement basic chat functionality
- Verify file operations work

### Deliverables

#### 1.1 Create Orchestrator Module

**File:** `ai_os/core/orchestrator.py`

```python
"""
Claude Code Orchestrator - manages subprocess communication with Claude Code CLI.
"""

import subprocess
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ClaudeResult:
    """Result from a Claude Code call."""
    success: bool
    result: str = ""
    error: str = ""
    cost: Dict[str, Any] = field(default_factory=dict)

class ClaudeOrchestrator:
    """Manages Claude Code subprocess invocations."""

    def __init__(
        self,
        working_dir: str = None,
        default_model: str = "sonnet",
        timeout: int = 600
    ):
        self.working_dir = working_dir or os.getcwd()
        self.default_model = default_model
        self.timeout = timeout
        self.total_cost = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost_usd": 0.0
        }

    def chat(
        self,
        prompt: str,
        model: str = None,
        context_files: List[str] = None
    ) -> str:
        """Send prompt to Claude Code and return response."""
        full_prompt = self._build_prompt(prompt, context_files)
        model = model or self.default_model

        result = subprocess.run(
            [
                "claude", "-p",
                "--model", model,
                "--dangerously-skip-permissions",
                "--output-format", "json"
            ],
            input=full_prompt,
            capture_output=True,
            text=True,
            cwd=self.working_dir,
            timeout=self.timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {result.stderr}")

        output = json.loads(result.stdout)
        self._track_cost(output.get("cost", {}))
        return output.get("result", "")

    def _build_prompt(self, prompt: str, context_files: List[str] = None) -> str:
        """Build prompt with optional file context."""
        if not context_files:
            return prompt

        parts = ["CONTEXT FILES:"]
        for file_path in context_files:
            path = Path(self.working_dir) / file_path
            if path.exists():
                parts.append(f"\n--- {file_path} ---\n{path.read_text()}")
        parts.append(f"\n\nTASK:\n{prompt}")
        return "\n".join(parts)

    def _track_cost(self, cost: Dict[str, Any]):
        """Accumulate cost tracking."""
        self.total_cost["input_tokens"] += cost.get("input_tokens", 0)
        self.total_cost["output_tokens"] += cost.get("output_tokens", 0)
        self.total_cost["total_cost_usd"] += cost.get("total_cost_usd", 0.0)

    def get_cost(self) -> Dict[str, Any]:
        """Return accumulated cost."""
        return self.total_cost.copy()
```

**Test:**
```python
def test_orchestrator_basic():
    orch = ClaudeOrchestrator()
    response = orch.chat("Say 'orchestrator works'")
    assert "orchestrator works" in response.lower()
```

**Acceptance:** `chat()` works, returns responses, tracks cost.

#### 1.2 Add JSON Parsing

Add to `orchestrator.py`:

```python
import re

def chat_json(self, prompt: str, **kwargs) -> Any:
    """Get JSON response from Claude."""
    full_prompt = f"{prompt}\n\nOutput valid JSON only."
    response = self.chat(full_prompt, **kwargs)
    return self._parse_json(response)

def _parse_json(self, response: str) -> Any:
    """Extract JSON from response."""
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"No valid JSON: {response[:200]}")
```

**Test:**
```python
def test_orchestrator_json():
    orch = ClaudeOrchestrator()
    result = orch.chat_json("Output JSON: {\"test\": true}")
    assert result.get("test") == True
```

**Acceptance:** `chat_json()` parses JSON correctly.

#### 1.3 File Operations

Add to `orchestrator.py`:

```python
def read(self, path: str) -> str:
    """Read file contents."""
    full_path = Path(self.working_dir) / path
    return full_path.read_text()

def write(self, path: str, content: str) -> None:
    """Write file contents."""
    full_path = Path(self.working_dir) / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)

def exists(self, path: str) -> bool:
    """Check if file exists."""
    full_path = Path(self.working_dir) / path
    return full_path.exists()

def edit(self, instruction: str, file: str = None) -> bool:
    """Have Claude edit files."""
    prompt = instruction
    if file:
        prompt = f"Edit {file}: {instruction}"
    try:
        self.chat(prompt)
        return True
    except Exception:
        return False
```

**Acceptance:** File operations work correctly.

---

## Phase 2: Parallel Execution (Day 2)

### Goals
- Add `async_=True` flag to chat functions
- Test parallel Claude Code processes with asyncio.gather
- Add timeout and error handling

### Deliverables

#### 2.1 Add async_=True Support

Add to `orchestrator.py`:

```python
import asyncio

class ClaudeOrchestrator:
    # ... existing code ...

    async def chat_async(
        self,
        prompt: str,
        model: str = None,
        context_files: List[str] = None
    ) -> str:
        """Async version - returns awaitable for use with asyncio.gather."""
        full_prompt = self._build_prompt(prompt, context_files)
        model = model or self.default_model

        proc = await asyncio.create_subprocess_exec(
            "claude", "-p",
            "--model", model,
            "--dangerously-skip-permissions",
            "--output-format", "json",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(full_prompt.encode()),
            timeout=self.timeout
        )

        if proc.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {stderr.decode()}")

        output = json.loads(stdout.decode())
        self._track_cost(output.get("cost", {}))
        return output.get("result", "")

    def chat(
        self,
        prompt: str,
        async_: bool = False,  # <-- The flag!
        **kwargs
    ):
        """
        Chat with Claude.

        If async_=True, returns a coroutine for use with asyncio.gather().
        Otherwise blocks and returns the response string.
        """
        if async_:
            return self.chat_async(prompt, **kwargs)
        else:
            # Sync version (existing code)
            return self._chat_sync(prompt, **kwargs)
```

**Test:**
```python
import asyncio

def test_chat_sync():
    orch = ClaudeOrchestrator()
    response = orch.chat("Say 'sync works'")
    assert "sync" in response.lower()

def test_chat_async():
    orch = ClaudeOrchestrator()

    async def run_parallel():
        results = await asyncio.gather(
            orch.chat("Say 'one'", async_=True),
            orch.chat("Say 'two'", async_=True),
            orch.chat("Say 'three'", async_=True),
        )
        return results

    results = asyncio.run(run_parallel())
    assert len(results) == 3
```

**Acceptance:** Both sync and async modes work, asyncio.gather runs in parallel.

---

## Phase 3: DSL Facade (Day 3)

### Goals
- Create the `ai_os` module with clean API
- Implement all DSL functions
- Backwards compatibility shim

### Deliverables

#### 3.1 Create Main Module

**File:** `ai_os/__init__.py`

```python
"""
AI-OS: Agentic Macro Framework

Usage:
    import ai_os as ai

    def main(ctx, **kwargs):
        result = ai.chat("Hello")
        ai.log(result)
"""

from ai_os.core.dsl import (
    # Output
    log,
    status,

    # Human interaction
    approve,
    ask,
    confirm_changes,

    # LLM operations
    chat,
    chat_json,
    vision,

    # Parallel execution
    spawn,
    join,
    gather,

    # File operations
    read,
    write,
    edit,
    exists,
    glob,

    # Shell operations
    shell,
    run,

    # Context
    get_var,
    set_var,
    get_cost,

    # Utilities
    sleep,
    timestamp,
    random_id,

    # Configuration
    config,
)

# Legacy alias
from ai_os.core import macro_helpers as ah

__all__ = [
    "log", "status",
    "approve", "ask", "confirm_changes",
    "chat", "chat_json", "vision",
    "spawn", "join", "gather",
    "read", "write", "edit", "exists", "glob",
    "shell", "run",
    "get_var", "set_var", "get_cost",
    "sleep", "timestamp", "random_id",
    "config",
    "ah",  # Legacy
]
```

#### 3.2 Create DSL Module

**File:** `ai_os/core/dsl.py`

```python
"""
DSL implementation - the public API for macro authors.
"""

import os
import time
import uuid
import subprocess
import glob as globlib
from typing import Any, List, Optional, Type
from contextlib import contextmanager
from datetime import datetime

from rich.console import Console
from rich.prompt import Confirm, Prompt

from ai_os.core.orchestrator import ClaudeOrchestrator, SpawnedAgent, ClaudeResult

# Global state
_console = Console()
_orchestrator: Optional[ClaudeOrchestrator] = None
_context: dict = {"vars": {}}

def _get_orchestrator() -> ClaudeOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ClaudeOrchestrator()
    return _orchestrator

# ============================================================
# Output Functions
# ============================================================

def log(message: str) -> None:
    """Print message to console."""
    _console.print(message)

@contextmanager
def status(message: str):
    """Show spinner while code runs."""
    with _console.status(message, spinner="dots"):
        yield

# ============================================================
# Human Interaction
# ============================================================

def approve(message: str) -> bool:
    """Ask for Y/N approval."""
    return Confirm.ask(message)

def ask(question: str, choices: List[str] = None) -> str:
    """Ask user a question."""
    if choices:
        return Prompt.ask(question, choices=choices)
    return Prompt.ask(question)

def confirm_changes(files: List[str]) -> bool:
    """Show file changes and ask for approval."""
    log("[bold]Changes to apply:[/bold]")
    for f in files:
        log(f"  - {f}")
        # Could show git diff here
    return approve("Apply these changes?")

# ============================================================
# LLM Operations
# ============================================================

def chat(
    prompt: str,
    context: List[str] = None,
    model: str = None,
    **kwargs
) -> str:
    """Send prompt to Claude."""
    orch = _get_orchestrator()
    return orch.chat(prompt, model=model, context_files=context)

def chat_json(
    prompt: str,
    schema: Type = None,
    **kwargs
) -> Any:
    """Get JSON response from Claude."""
    orch = _get_orchestrator()
    result = orch.chat_json(prompt, **kwargs)
    if schema:
        return schema.model_validate(result)
    return result

def vision(prompt: str, image: str, **kwargs) -> str:
    """Analyze image with Claude."""
    # Claude Code can read images directly
    full_prompt = f"Read the image at {image} and analyze it:\n{prompt}"
    return chat(full_prompt, **kwargs)

# ============================================================
# Parallel Execution
# ============================================================

def spawn(prompt: str, output_file: str = None, **kwargs) -> SpawnedAgent:
    """Spawn async Claude process."""
    orch = _get_orchestrator()
    return orch.spawn(prompt, output_file=output_file, **kwargs)

def join(agents: List[SpawnedAgent], timeout: float = None) -> List[ClaudeResult]:
    """Wait for spawned agents."""
    orch = _get_orchestrator()
    return orch.join(agents, timeout=timeout)

def gather(*prompts: str, **kwargs) -> List[str]:
    """Spawn and join multiple prompts."""
    orch = _get_orchestrator()
    return orch.gather(*prompts, **kwargs)

# ============================================================
# File Operations
# ============================================================

def read(path: str) -> str:
    """Read file contents."""
    orch = _get_orchestrator()
    return orch.read(path)

def write(path: str, content: str) -> None:
    """Write file contents."""
    orch = _get_orchestrator()
    orch.write(path, content)

def edit(instruction: str, file: str = None) -> bool:
    """Have Claude edit files."""
    orch = _get_orchestrator()
    return orch.edit(instruction, file=file)

def exists(path: str) -> bool:
    """Check if file exists."""
    orch = _get_orchestrator()
    return orch.exists(path)

def glob(pattern: str) -> List[str]:
    """Find files matching pattern."""
    orch = _get_orchestrator()
    return globlib.glob(
        os.path.join(orch.working_dir, pattern),
        recursive=True
    )

# ============================================================
# Shell Operations
# ============================================================

def shell(command: str, capture: bool = False, check: bool = False) -> Any:
    """Execute shell command."""
    orch = _get_orchestrator()
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=orch.working_dir
    )

    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, command, result.stdout, result.stderr
        )

    if not capture:
        if result.stdout:
            _console.print(result.stdout)
        if result.stderr:
            _console.print(f"[red]{result.stderr}[/red]")
        return result.returncode

    return result.stdout.strip()

def run(command: str, **kwargs) -> subprocess.CompletedProcess:
    """Low-level shell access."""
    orch = _get_orchestrator()
    return subprocess.run(
        command,
        shell=True,
        cwd=orch.working_dir,
        **kwargs
    )

# ============================================================
# Context and State
# ============================================================

def get_var(name: str, default: Any = None) -> Any:
    """Get context variable."""
    return _context.get("vars", {}).get(name, default)

def set_var(name: str, value: Any) -> None:
    """Set context variable."""
    if "vars" not in _context:
        _context["vars"] = {}
    _context["vars"][name] = value

def get_cost() -> dict:
    """Get accumulated cost."""
    orch = _get_orchestrator()
    return orch.get_cost()

# ============================================================
# Utilities
# ============================================================

def sleep(seconds: float) -> None:
    """Pause execution."""
    time.sleep(seconds)

def timestamp() -> str:
    """Get current timestamp."""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

def random_id(length: int = 8) -> str:
    """Generate random ID."""
    return uuid.uuid4().hex[:length]

# ============================================================
# Configuration
# ============================================================

def config(
    model: str = None,
    timeout: int = None,
    max_parallel: int = None,
    working_dir: str = None
) -> None:
    """Configure the orchestrator."""
    global _orchestrator
    _orchestrator = ClaudeOrchestrator(
        working_dir=working_dir or os.getcwd(),
        default_model=model or "sonnet",
        timeout=timeout or 600,
        max_parallel=max_parallel or 5
    )

# ============================================================
# Internal: Context management for macro runner
# ============================================================

def _set_context(ctx: dict) -> None:
    """Set context (called by macro runner)."""
    global _context
    _context = ctx

def _clear_context() -> None:
    """Clear context (called by macro runner)."""
    global _context, _orchestrator
    _context = {"vars": {}}
    if _orchestrator:
        _orchestrator.shutdown()
        _orchestrator = None
```

**Acceptance:** All DSL functions implemented and importable.

---

## Phase 4: Macro Runner Update (Day 4)

### Goals
- Update MacroRunner to use new DSL
- Simplify (remove old patch/chat code)
- Test with existing macros

### Deliverables

#### 4.1 Simplify Macro Runner

**File:** `ai_os/core/macro_runner.py` (simplified)

```python
"""
Macro Runner - executes Python macro scripts.
"""

import importlib.util
import inspect
import os
import shlex
import sys
import types
from pathlib import Path
from typing import Any, Dict, Tuple

from rich.console import Console

from ai_os.core import dsl


class MacroRunner:
    """Executes Python macro scripts."""

    def __init__(self, console: Console):
        self.console = console

    def run(self, argline: str) -> None:
        """Run a macro from command line."""
        original_cwd = Path.cwd()

        try:
            module_path, kwargs = self._parse_args(argline)
            self.console.print(f"[dim]Running: {module_path}[/dim]")

            # Change to macro directory
            macro_dir = Path(module_path).parent
            os.chdir(macro_dir)

            # Import macro
            module = self._import_module(module_path)
            main_func = getattr(module, "main", None)

            if not callable(main_func):
                self.console.print("[red]Macro must define main(ctx, **kwargs)[/red]")
                return

            # Set up context
            ctx = {"vars": kwargs}
            dsl._set_context(ctx)

            # Execute
            try:
                main_func(ctx, **kwargs)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Macro interrupted[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Macro error: {e}[/red]")
                import traceback
                traceback.print_exc()

        finally:
            dsl._clear_context()
            os.chdir(original_cwd)

    def _parse_args(self, argline: str) -> Tuple[str, Dict[str, Any]]:
        """Parse command line arguments."""
        parts = shlex.split(argline)
        if not parts:
            raise ValueError("Usage: /macro <path.py> [key=value ...]")

        module_path = Path(parts[0]).resolve()
        if not module_path.exists():
            raise ValueError(f"Macro not found: {parts[0]}")

        kwargs = {}
        for tok in parts[1:]:
            if "=" in tok:
                k, v = tok.split("=", 1)
                kwargs[k] = self._parse_value(v)

        return str(module_path), kwargs

    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _import_module(self, path: str) -> types.ModuleType:
        """Dynamically import a module."""
        module_name = f"aios_macro_{Path(path).stem}_{os.urandom(4).hex()}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
```

**Acceptance:** Macro runner simplified, uses new DSL.

#### 4.2 Update CLI

**File:** `ai_os/cli.py` (simplified relevant parts)

```python
# In handle_command method:
elif cmd == "/macro" or cmd == "@":
    from ai_os.core.macro_runner import MacroRunner
    runner = MacroRunner(self.console)
    runner.run(arg)
```

**Acceptance:** `/macro` command uses new runner.

---

## Phase 5: Cleanup and Testing (Day 5)

### Goals
- Delete obsolete code
- Port example macros
- Full integration testing

### Deliverables

#### 5.1 Delete Obsolete Files

```bash
# Files to delete
rm ai_os/core/chat.py              # OpenRouter integration (replaced by orchestrator)
rm ai_os/core/patch.py             # Patch system (replaced by Claude Code Edit)
rm -rf ai_os/core/patch_strategies # Patch strategies (no longer needed)

# Files to KEEP and rewire
# ai_os/core/commands.py           # KEEP - rewire to use orchestrator
# ai_os/cli.py                     # KEEP - terminal UI unchanged
```

**Acceptance:** OpenRouter/patch code removed, terminal commands still work.

#### 5.1b Rewire commands.py

The terminal commands (`>`, `+`, `!`, `@`) stay. We just change what they call:

```python
# ai_os/core/commands.py (updated)

from ai_os.core.orchestrator import ClaudeOrchestrator

_orchestrator = None

def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ClaudeOrchestrator()
    return _orchestrator

def chat(prompt: str, console: Console) -> Generator[str, None, None]:
    """
    /chat command - now uses Claude Code.
    Still streams output to console.
    """
    orch = _get_orchestrator()
    # For streaming, we don't use --output-format json
    process = subprocess.Popen(
        ["claude", "-p", "--dangerously-skip-permissions"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    process.stdin.write(prompt)
    process.stdin.close()

    for line in iter(process.stdout.readline, ''):
        yield line

    process.wait()

def patch(plan: str, console: Console, **kwargs) -> dict:
    """
    /patch command - now uses Claude Code's Edit tool.
    """
    orch = _get_orchestrator()
    prompt = f"""
    Implement this plan by editing the necessary files:
    {plan}

    Use the Edit tool for surgical changes.
    After making changes, briefly summarize what you changed.
    """
    result = orch.chat(prompt)
    return {"applied": True, "summary": result}
```

**Acceptance:** `> hello` and `+ add feature` work via Claude Code.

#### 5.2 Port Example Macros

**tdd_macro.py (ported):**
```python
import ai_os as ai

def main(ctx, **kwargs):
    """Test-driven development macro."""
    goal = kwargs.get("goal")
    if not goal:
        ai.log("Usage: /macro tdd.py goal='...'")
        return

    # Generate test
    ai.log("[bold]Generating test...[/bold]")
    ai.edit(f"Create a pytest test file for: {goal}")

    test_files = ai.glob("tests/test_*.py")
    if not test_files:
        ai.log("[red]No test file created[/red]")
        return

    test_file = test_files[-1]
    if not ai.approve(f"Test created: {test_file}. Continue?"):
        return

    # Implementation loop
    for attempt in range(5):
        ai.log(f"[cyan]Attempt {attempt + 1}/5[/cyan]")
        ai.edit(f"Write code to pass the tests in {test_file}")

        exit_code = ai.shell(f"pytest {test_file} -v")
        if exit_code == 0:
            ai.log("[bold green]Tests pass![/bold green]")
            return

        if not ai.approve("Retry?"):
            return

    ai.log("[red]Max attempts reached[/red]")
```

**tree_of_thought.py (ported):**
```python
import ai_os as ai

def main(ctx, **kwargs):
    """Tree of thought reasoning."""
    question = kwargs.get("question")
    if not question:
        ai.log("Usage: /macro tot.py question='...'")
        return

    # Initial thoughts in parallel
    ai.log("[cyan]Generating initial thoughts...[/cyan]")
    prompts = [
        f"Thought {i+1} on: {question}\nProvide a unique perspective."
        for i in range(5)
    ]

    with ai.status("Thinking..."):
        thoughts = ai.gather(*prompts, model="haiku")

    # Branch each thought
    ai.log("[cyan]Branching thoughts...[/cyan]")
    branch_prompts = []
    for thought in thoughts:
        for j in range(3):
            branch_prompts.append(
                f"Extend this thought:\n{thought}\n\nExplore direction {j+1}."
            )

    with ai.status("Branching..."):
        branches = ai.gather(*branch_prompts, model="haiku")

    all_thoughts = thoughts + branches

    # Synthesize
    ai.log("[cyan]Synthesizing...[/cyan]")
    numbered = "\n".join(f"{i+1}. {t[:300]}" for i, t in enumerate(all_thoughts))
    synthesis = ai.chat(f"""
        Question: {question}
        Thoughts:
        {numbered}

        Synthesize into a comprehensive answer.
    """, model="sonnet")

    ai.log("[bold green]Answer:[/bold green]")
    ai.log(synthesis)

    cost = ai.get_cost()
    ai.log(f"\n[dim]Cost: ${cost['total_cost_usd']:.4f}[/dim]")
```

**Acceptance:** Both macros run successfully.

#### 5.3 Integration Test Suite

```python
# tests/test_v2_full.py
import pytest
import ai_os as ai
import tempfile
import os

class TestDSL:
    def test_log(self, capsys):
        ai.log("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_chat(self):
        response = ai.chat("Say 'integration test passed'")
        assert "integration" in response.lower() or "test" in response.lower()

    def test_chat_json(self):
        result = ai.chat_json("Output: {\"value\": 42}")
        assert result.get("value") == 42

    def test_file_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ai.config(working_dir=tmpdir)
            ai.write("test.txt", "hello")
            assert ai.exists("test.txt")
            content = ai.read("test.txt")
            assert content == "hello"

    def test_shell(self):
        output = ai.shell("echo 'shell test'", capture=True)
        assert "shell test" in output

    def test_gather(self):
        results = ai.gather(
            "Say 'a'",
            "Say 'b'",
            model="haiku"
        )
        assert len(results) == 2

    def test_spawn_join(self):
        agents = [ai.spawn(f"Say '{i}'", model="haiku") for i in range(2)]
        results = ai.join(agents)
        assert len(results) == 2
        assert all(r.success for r in results)
```

**Acceptance:** All tests pass.

---

## Phase 6: Documentation and Release (Day 6)

### Goals
- Update README
- Document migration path
- Tag release

### Deliverables

#### 6.1 Update README

```markdown
# AI-OS v2

**Claude Code Native Agentic Macros**

AI-OS lets you write Python scripts that orchestrate Claude Code
for complex, multi-step AI workflows with human oversight.

## Quick Start

```bash
pip install ai-os
export ANTHROPIC_API_KEY=sk-...
aios
/macro examples/tdd.py goal="implement user auth"
```

## Writing Macros

```python
import ai_os as ai

def main(ctx, **kwargs):
    # Parallel execution
    agents = [ai.spawn(f"Generate idea {i}") for i in range(5)]
    results = ai.join(agents)

    # Human checkpoint
    if ai.approve("Continue with these ideas?"):
        for r in results:
            ai.log(r.result)
```

See [DSL Reference](docs/dsl.md) for full API.
```

#### 6.2 Migration Guide

```markdown
# Migrating from AI-OS v1 to v2

## Breaking Changes

1. **No more `ah.patch()`** - Use `ai.edit()` instead
2. **No more OpenRouter** - Now uses Claude Code directly
3. **Parallel execution** - Use `ai.spawn()` / `ai.join()`

## API Changes

| v1 | v2 |
|----|-----|
| `ah.patch(plan)` | `ai.edit(instruction)` |
| `ah.chat(prompt)` | `ai.chat(prompt)` |
| N/A | `ai.spawn()`, `ai.join()`, `ai.gather()` |

## Environment

v1:
```bash
export OPENROUTER_API_KEY=...
```

v2:
```bash
export ANTHROPIC_API_KEY=...
```
```

#### 6.3 Tag Release

```bash
git add -A
git commit -m "AI-OS v2: Claude Code native"
git tag v2.0.0
git push origin main --tags
```

---

## Summary

| Phase | Duration | Key Deliverables |
|-------|----------|-----------------|
| 0: Prep | 0.5 day | Environment verified, tests baseline |
| 1: Orchestrator | 1 day | Claude Code subprocess wrapper |
| 2: Parallelism | 1 day | spawn/join/gather |
| 3: DSL | 1 day | Full Python API |
| 4: Runner | 0.5 day | Updated macro execution |
| 5: Cleanup | 1 day | Delete old code, port examples |
| 6: Release | 0.5 day | Docs, migration guide, tag |

**Total: 5-6 days**

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Claude Code API changes | Pin version, test thoroughly |
| Parallel execution race conditions | Use ThreadPoolExecutor, not manual threads |
| Backward compatibility breaks | Keep `ah` alias, gradual migration |
| Cost overruns in testing | Use haiku model, small prompts |

## Success Metrics

1. **LOC reduced** - Target: <1000 lines core code (from ~1800)
2. **Test coverage** - Target: >80% on core modules
3. **Example macros work** - Both TDD and ToT macros pass
4. **Parallel execution verified** - 5+ concurrent agents work
5. **Cost tracking accurate** - Matches Claude usage

---

## Next Actions

1. **Approve this plan** - Review with stakeholders
2. **Set up dev environment** - Branch, deps, Claude Code
3. **Start Phase 1** - Build orchestrator
4. **Iterate** - One phase at a time

This roadmap provides a clear path from current state to v2. Each phase has testable deliverables, making progress visible and risks manageable.
