# AI-OS v2 Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Integration Points](#integration-points)
5. [Maintenance Guide](#maintenance-guide)

---

## Overview

AI-OS v2 is a **macro-based LLM orchestration framework** that uses **Claude Code** as its backend. Instead of making direct API calls to LLM providers, it invokes the Claude Code CLI as a subprocess, letting Claude Code handle:

- Tool use (Edit, Read, WebSearch, Bash)
- Permission management
- Token tracking and cost calculation
- Streaming responses

### Design Philosophy

1. **Deletion-Driven Refactoring** - Remove code, don't add it
2. **Unified Abstractions** - One orchestrator for all LLM ops
3. **System Instructions Over Strategies** - Behavior via prompts, not code
4. **Async by Default** - Enable parallel execution patterns
5. **Minimal Dependencies** - Python stdlib + Claude Code CLI

### Key Metrics

- **Lines of code**: 1,711 (down from 2,272 in v1)
- **Core modules**: 4 (orchestrator, commands, macro_runner, macro_helpers)
- **External dependencies**: 3 (prompt_toolkit, rich, pydantic)
- **Test coverage**: 85%+ (orchestrator, macro_helpers)

---

## Core Components

### 1. ClaudeOrchestrator (`ai_os/core/orchestrator.py`)

**Purpose:** Unified interface to Claude Code CLI

**Responsibilities:**
- Subprocess management for `claude -p` invocations
- JSON response parsing and cost tracking
- Sync/async/streaming chat modes
- File operations (read/write/exists)
- Shell command execution

**Key Methods:**

```python
class ClaudeOrchestrator:
    def chat(prompt, model=None, async_=False) -> str | Coroutine
        # Primary LLM interface - blocking or async

    def chat_streaming(prompt, model=None) -> Generator
        # Streaming responses (no cost tracking)

    def chat_json(prompt, model=None, async_=False) -> dict | list
        # Structured JSON responses with parsing

    def vision(prompt, image_path, model=None) -> str
        # Image analysis via file paths

    def edit(instruction, file=None) -> bool
        # File editing via Claude Code's Edit tool

    def read(path) -> str
        # Direct file read (no LLM involved)

    def write(path, content) -> None
        # Direct file write (no LLM involved)

    def shell(command, capture=False) -> int | str
        # Shell command execution
```

**Critical Implementation Details:**

1. **Subprocess Pattern** (`orchestrator.py:133-139`)
   ```python
   # CRITICAL: --output-format json enables structured responses
   cmd = ["claude", "-p", "--model", model, "--output-format", "json"]
   result = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
   output = json.loads(result.stdout)  # Contains {"result": "...", "cost": {...}}
   ```

2. **JSON Parsing** (`orchestrator.py:268-294`)
   ```python
   # Handles markdown-wrapped JSON (```json ... ```)
   # Try direct parse first, then regex extraction
   ```

3. **Async Pattern** (`orchestrator.py:154-194`)
   ```python
   # Uses asyncio.create_subprocess_exec for non-blocking calls
   # Returns coroutine for use with asyncio.gather()
   ```

---

### 2. MacroRunner (`ai_os/core/macro_runner.py`)

**Purpose:** Execute user-defined Python macros with LLM access

**Responsibilities:**
- Load and execute `.py` files as macros
- Inject `ah.*` helpers into macro scope
- Manage macro lifecycle (setup/teardown)
- Track macro state and context
- Handle errors and provide rich feedback

**Architecture:**

```
User writes macro.py with main() function
         ↓
MacroRunner.run(macro_path, params={...})
         ↓
1. Import macro as Python module
2. Inject MacroRunner instance via ah.set_runner()
3. Call macro.main(**params)
4. Collect results and cost tracking
5. Cleanup and restore state
```

**Key Methods:**

```python
class MacroRunner:
    def run(macro_path, params={}) -> Any
        # Execute a macro and return result

    def log(msg)
        # Display message to user (Rich formatted)

    def log_to_context(msg)
        # Add message to conversation history

    def get_orchestrator() -> ClaudeOrchestrator
        # Access underlying orchestrator
```

---

### 3. Macro Helpers (`ai_os/core/macro_helpers.py`)

**Purpose:** Public API for macro authors (`import ai_os.core.macro_helpers as ah`)

**Responsibilities:**
- Wrap orchestrator methods with macro-friendly interface
- Handle context file injection automatically
- Provide variable storage across macro invocations
- Simplify async patterns

**Full API:**

```python
# LLM Operations
ah.chat(prompt, include_context=True, model=None, async_=False) -> str | Coroutine
ah.chat_json(prompt) -> dict | list
ah.vision(prompt, image_path) -> str
ah.edit(instruction, file=None) -> bool

# File Operations
ah.read(path) -> str
ah.write(path, content) -> None
ah.exists(path) -> bool

# Shell Operations
ah.shell(command) -> int

# Context & Variables
ah.get_var(name) -> Any
ah.set_var(name, value) -> None
ah.get_cost() -> dict

# Output
ah.log(msg) -> None
ah.log_to_context(msg) -> None
```

**Critical Implementation:** (`macro_helpers.py:79-118`)

```python
def chat(prompt, include_context=True, image_path=None, model=None, async_=False):
    """
    CRITICAL: This is the primary LLM interface for macros.

    - async_=False (default): BLOCKS until response complete
    - async_=True: Returns coroutine for parallel execution
    - include_context: Automatically injects context files
    """
    runner = _require_runner()  # Ensures macro is running
    context_files = runner.get_context_files() if include_context else None

    if image_path:
        return runner.orchestrator.vision(prompt, image_path, model=model, async_=async_)
    else:
        return runner.orchestrator.chat(prompt, context_files=context_files, model=model, async_=async_)
```

---

### 4. Commands Module (`ai_os/core/commands.py`)

**Purpose:** CLI command handlers for AI-OS interactive shell

**Responsibilities:**
- Implement `/chat`, `/patch`, `/search` commands
- Handle context file management
- Provide user feedback and progress indicators
- Interface between user input and orchestrator

**Command Implementations:**

| Command | System Instruction | Tool Use |
|---------|-------------------|----------|
| **Chat** (`>` or `/chat`) | "You are in chat-only mode. Do not edit files." | None |
| **Patch** (`+` or `/patch`) | "Use Edit tool for surgical changes. Summarize edits." | Edit |
| **Search** (`?` or `/search`) | "Use WebSearch tool. Cite sources." | WebSearch |

**Key Insight:** Commands differ only in system instructions, not code paths. All use `orchestrator.chat_streaming()`.

---

## Data Flow

### Typical Chat Flow

```
User input: "> Explain decorators"
         ↓
CommandProcessor (commands.py)
         ↓
ClaudeOrchestrator.chat_streaming()
         ↓
subprocess: claude -p --model sonnet --output-format json
         ↓
Claude Code CLI (handles tool use, permissions)
         ↓
Streaming response chunks
         ↓
Display to user with Rich formatting
```

### Typical Macro Flow

```
User input: "/macro examples/chart_judge.py data=sales.csv"
         ↓
MacroRunner.run("examples/chart_judge.py", {"data": "sales.csv"})
         ↓
1. Import chart_judge.py
2. Set up macro_helpers (ah.set_runner())
3. Call chart_judge.main(data="sales.csv")
         ↓
Macro code: ah.chat("Generate matplotlib code for sales.csv")
         ↓
ClaudeOrchestrator.chat()
         ↓
subprocess: claude -p --output-format json
         ↓
Response: Python code for chart generation
         ↓
Macro code: exec(code); save chart as image
Macro code: ah.vision("Rate this chart", image_path)
         ↓
Response: "Chart quality: 8/10..."
         ↓
Return result to user
```

### Async Parallel Flow

```python
# examples/tree_of_thought.py pattern
import asyncio

async def parallel_analysis():
    # 5 LLM calls in parallel (2 seconds instead of 10)
    thoughts = await asyncio.gather(
        ah.chat("Generate thought 1", async_=True),
        ah.chat("Generate thought 2", async_=True),
        ah.chat("Generate thought 3", async_=True),
        ah.chat("Generate thought 4", async_=True),
        ah.chat("Generate thought 5", async_=True),
    )
    return thoughts
```

**Data Flow:**
```
asyncio.gather() spawns 5 tasks
         ↓
Each task: ClaudeOrchestrator._chat_async()
         ↓
5 parallel subprocesses: claude -p ...
         ↓
All complete → gather returns list of 5 responses
```

---

## Integration Points

### 1. Claude Code CLI

**Required:** `claude` command in PATH

**Test:**
```bash
claude --version
claude -p "test" --output-format json
```

**Output Format:**
```json
{
  "result": "Response text here",
  "cost": {
    "input_tokens": 123,
    "output_tokens": 456,
    "total_cost_usd": 0.0789
  }
}
```

**Critical:** Must use `--output-format json` for structured responses. Without it, streaming works but no cost tracking.

### 2. File System

**Working Directory:** Set via `ClaudeOrchestrator(working_dir="/path")`

**File Operations:**
- `ah.read(path)` - Direct file read (no LLM)
- `ah.write(path, content)` - Direct file write (no LLM)
- `ah.edit(instruction, file)` - LLM-powered editing via Claude Code's Edit tool

**Important:** `ah.edit()` invokes Claude Code, which uses its Edit tool. The orchestrator doesn't parse diffs - Claude Code handles that.

### 3. Vision (Images)

**Pattern:** File path, not base64 encoding

```python
# OLD (v1): Base64 encoding + OpenRouter
image_b64 = base64.b64encode(open(path, "rb").read())
response = openrouter_vision_api(image_b64)

# NEW (v2): File path + Claude Code Read tool
response = ah.vision("Analyze this chart", "output.png")
# Claude Code's Read tool handles image loading
```

### 4. Context Files

**Automatic Injection:**
```python
# User adds files to context
> /add src/main.py
> /add config.json

# Macro uses context automatically
response = ah.chat("Fix the bug", include_context=True)
# Orchestrator includes src/main.py and config.json in prompt
```

**Implementation:** (`orchestrator.py:430-451`)
```python
def _build_prompt(self, prompt, context_files=None, system_instruction=None):
    parts = []
    if system_instruction:
        parts.append(f"INSTRUCTION: {system_instruction}\n")
    if context_files:
        for file_path in context_files:
            content = self.read(file_path)
            parts.append(f"\n--- {file_path} ---\n{content}")
    parts.append(prompt)
    return "\n".join(parts)
```

---

## Maintenance Guide

### Adding New Operations

To add a new operation (e.g., `ah.summarize()`):

1. **Add to ClaudeOrchestrator** (`orchestrator.py`)
   ```python
   def summarize(self, text, length="short", async_=False):
       """Summarize text."""
       prompt = f"Summarize this text ({length} version):\n\n{text}"
       system = "Provide concise summaries without extra commentary."
       return self.chat(prompt, system_instruction=system, async_=async_)
   ```

2. **Expose via MacroHelpers** (`macro_helpers.py`)
   ```python
   def summarize(text, length="short"):
       """Public API for macros."""
       return _require_runner().orchestrator.summarize(text, length)
   ```

3. **Add Tests** (`tests/test_orchestrator_*.py`)
   ```python
   def test_summarize():
       orch = ClaudeOrchestrator()
       # Test implementation
   ```

4. **Document** (`agent_notes/V2_ARCHITECTURE.md` and `MIGRATION_GUIDE_V2.md`)

### Critical Files to Monitor

1. **orchestrator.py:133-139** - Subprocess invocation pattern
   - Changes here affect ALL LLM operations
   - Ensure `--output-format json` is always included

2. **orchestrator.py:268-294** - JSON parsing logic
   - Handles markdown-wrapped JSON
   - Failure here breaks `chat_json()` entirely

3. **macro_helpers.py:79-118** - chat() implementation
   - Core macro API
   - Changes affect all existing macros

4. **macro_runner.py:45-87** - Macro execution lifecycle
   - Error handling
   - Context injection

### Where to Add Comments

When you make changes, add comments to:

1. **Critical integration points** - Subprocess calls, JSON parsing
2. **Non-obvious behavior** - Async patterns, context injection
3. **Performance-sensitive code** - Streaming, parallel execution
4. **Future maintenance notes** - "If X breaks, check Y first"

**Good Comment:**
```python
# CRITICAL: Must use --output-format json for cost tracking
# Without this flag, streaming works but no token counts returned
cmd = ["claude", "-p", "--output-format", "json"]
```

**Bad Comment:**
```python
# Run the command
cmd = ["claude", "-p"]
```

### Testing Strategy

**Unit Tests:**
```bash
# Test orchestrator directly (mocked subprocess)
pytest tests/test_orchestrator_basic.py

# Test macro helpers (mocked runner)
pytest tests/test_macro_helpers.py
```

**Integration Tests:**
```bash
# Requires Claude Code installed
python test_orchestrator_basic.py

# Test example macros
uv run python main.py
> /macro examples/tree_of_thought.py question="test"
```

**What to Test After Changes:**

1. **orchestrator.py changes** → Run `test_orchestrator_basic.py`
2. **macro_helpers.py changes** → Test all example macros
3. **commands.py changes** → Manual testing in AI-OS CLI
4. **macro_runner.py changes** → Run macro with errors (test error handling)

---

## Common Pitfalls and Solutions

### Pitfall 1: Async Misuse

**Problem:**
```python
# This doesn't work - returns coroutine, not string
result = ah.chat("prompt", async_=True)
print(result)  # <coroutine object ...>
```

**Solution:**
```python
# Must await in async context
result = await ah.chat("prompt", async_=True)

# Or use asyncio.run in sync context
import asyncio
result = asyncio.run(ah.chat("prompt", async_=True))

# Or just use sync mode
result = ah.chat("prompt", async_=False)  # default
```

### Pitfall 2: Missing Context Files

**Problem:**
```python
# Context files not included
response = ah.chat("Fix the bug", include_context=False)
# Claude doesn't see the code
```

**Solution:**
```python
# Include context automatically (default)
response = ah.chat("Fix the bug")  # include_context=True by default
```

### Pitfall 3: JSON Parsing Failures

**Problem:**
```python
# Claude returns: "Sure! Here's the JSON: {...}"
result = ah.chat_json("Return JSON: {...}")
# Fails because response includes text before JSON
```

**Solution:**
```python
# The orchestrator handles this automatically
# It uses regex to extract JSON from markdown/text
# But be explicit in prompts:
result = ah.chat_json("Output ONLY valid JSON, no other text: {...}")
```

### Pitfall 4: Subprocess Timeouts

**Problem:**
```python
# Long-running tasks timeout after 600s (default)
result = ah.chat("Generate 1000 test cases")
# Raises: TimeoutExpired after 600 seconds
```

**Solution:**
```python
# Increase timeout when creating orchestrator
from ai_os.core.orchestrator import configure_orchestrator
configure_orchestrator(timeout=3600)  # 1 hour
```

### Pitfall 5: Permission Errors

**Problem:**
```python
# Claude Code asks for permission, macro blocks
result = ah.edit("Delete all files")
# Waits for user input that never comes
```

**Solution:**
```python
# Use skip_permissions=True (default in orchestrator)
# Or approve specific operations beforehand
# Or run macros with explicit approval flow
```

---

## Performance Optimization

### 1. Parallel LLM Calls

**3x+ speedup** for independent tasks:

```python
# BAD: Sequential (6 seconds)
r1 = ah.chat("Task 1")  # 2s
r2 = ah.chat("Task 2")  # 2s
r3 = ah.chat("Task 3")  # 2s

# GOOD: Parallel (2 seconds)
import asyncio
results = await asyncio.gather(
    ah.chat("Task 1", async_=True),
    ah.chat("Task 2", async_=True),
    ah.chat("Task 3", async_=True)
)
```

### 2. Model Selection

**Cost optimization:**

```python
# Expensive: Opus for simple tasks
response = ah.chat("What is 2+2?", model="opus")  # $0.015

# Cheap: Haiku for simple tasks
response = ah.chat("What is 2+2?", model="haiku")  # $0.0001

# Balanced: Sonnet (default)
response = ah.chat("Explain decorators")  # $0.003
```

### 3. Streaming vs Blocking

**User experience:**

```python
# BAD: Blocking (user waits 10s with no feedback)
response = orchestrator.chat("Long task")
print(response)

# GOOD: Streaming (user sees progress)
for chunk in orchestrator.chat_streaming("Long task"):
    print(chunk, end='', flush=True)
```

---

## Future Enhancements

### Planned Features

1. **Response Caching**
   - Cache identical prompts (hash-based)
   - Reduce costs for repeated operations
   - Clear cache on file changes

2. **Tool Use Tracking**
   - Log which tools Claude used (Edit, Read, WebSearch)
   - Metrics: "Edit used 5 times, Read 12 times"
   - Help users understand LLM behavior

3. **Multi-Agent Patterns**
   - Multiple orchestrators with different roles
   - "Architect" (Opus) + "Implementer" (Sonnet) + "Reviewer" (Haiku)
   - Coordinated multi-agent workflows

4. **Prompt Templates**
   - Reusable system instructions
   - `ah.chat("prompt", template="code_review")`
   - Templates: code_review, refactoring, debugging, etc.

5. **Macro Composition**
   - Macros call other macros
   - Shared state and context
   - Macro pipelines: `ah.run_macro("step1.py") | ah.run_macro("step2.py")`

### Extension Points

To add these features, modify:

1. **Caching** → `orchestrator.py` (add cache layer before subprocess)
2. **Tool tracking** → `orchestrator.py` (parse JSON response for tool use)
3. **Multi-agent** → `macro_runner.py` (manage multiple orchestrators)
4. **Templates** → `macro_helpers.py` (template → system_instruction mapping)
5. **Composition** → `macro_runner.py` (macro call stack management)

---

## Summary

### What Makes v2 Different

1. **Unified abstraction** - One orchestrator instead of chat/patch/search modules
2. **Subprocess pattern** - Claude Code handles tool use, not us
3. **Async-first** - Parallel LLM calls for performance
4. **Simpler codebase** - 561 fewer lines than v1
5. **Better separation** - Core (orchestrator) vs interface (commands/macros)

### Key Takeaways

- **All LLM ops go through ClaudeOrchestrator**
- **System instructions replace code strategies**
- **async_=True enables parallelism**
- **File paths, not base64, for images**
- **Context files auto-injected in macros**

### Maintenance Mantra

> "When something breaks, check the subprocess invocation first.
> When adding features, start with the orchestrator.
> When optimizing, profile async patterns.
> When debugging, log the full prompt sent to Claude Code."

---

**Last Updated:** 2025-01-17
**Architecture Version:** 2.0
**Status:** Production Ready ✅
