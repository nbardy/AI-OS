# Current State Analysis: AI-OS v1 Codebase Review

**Date:** 2026-01-17
**Status:** Analysis Complete
**Purpose:** Identify what to keep, modify, or discard in the v2 redesign

---

## Overview

This document provides a detailed analysis of the current AI-OS codebase. For each component, we assess:
- **What it does** — Functional description
- **How it works** — Implementation details
- **Pain points** — What's wrong with it
- **Verdict** — Keep, modify, or discard
- **Migration notes** — How to handle in v2

---

## Component Inventory

### 1. REPL Shell (`cli.py`)

**What it does:**
The main entry point. A terminal-based REPL (Read-Eval-Print Loop) that accepts slash commands and aliases:

| Command | Alias | Function |
|---------|-------|----------|
| `/chat` | `>` | Send prompt to LLM |
| `/patch` | `+` | Generate code and apply changes |
| `/run` | `!` | Execute shell command |
| `/macro` | `@` | Run a macro script |
| `/context` | — | View/edit context |
| `/model` | — | Select LLM model |
| `/search` | `?` | Web search |
| `/history` | — | View command history |

**How it works:**
- Built on `prompt_toolkit.PromptSession` for readline-style editing
- Uses `rich.Console` for styled output
- Parses input for command prefix, dispatches to handler functions
- Maintains persistent history via `PersistentHistory`
- Tab completion via `AIOSCompleter` class

**Pain points:**
1. Tightly coupled to the `commands` module
2. No clean separation between UI and logic
3. Some commands bypass the context manager inconsistently

**Verdict: KEEP with modifications**

The REPL is the right UX paradigm. Users should have an interactive terminal where they can:
- Run macros
- See output streaming
- Approve changes
- Inspect state

**Migration notes:**
- Simplify command set (remove `/patch`, `/chat` direct commands if macros become primary)
- Or keep them as "quick macro" shortcuts
- Decouple from `commands.py` internals
- Consider whether we need the full REPL or just macro execution mode

---

### 2. OpenRouter Integration (`chat.py`)

**What it does:**
HTTP client for the OpenRouter API. Sends chat completion requests and streams responses.

**How it works:**
```python
def chat_completion(messages: List[Message], model: str = None) -> Generator[str, None, None]:
    # 1. Build HTTP request with messages
    # 2. POST to https://openrouter.ai/api/v1/chat/completions
    # 3. Parse SSE stream
    # 4. Yield text chunks as they arrive
```

Key features:
- Server-Sent Events (SSE) parsing for streaming
- Support for vision models (base64 image encoding)
- Search-enabled model suffix (`:online`)
- 600-second timeout for long-running requests
- Error handling for API failures

**Pain points:**
1. **Duplicates Claude Code functionality** — Claude Code already handles LLM calls
2. **No function calling** — Uses raw text completion, not structured tool use
3. **Manual retry logic** — No exponential backoff
4. **Rate limiting not handled** — Can hit OpenRouter limits
5. **Model-specific quirks** — Different models need different handling

**Verdict: DISCARD entirely**

This is exactly what Claude Code replaces. When we call `claude -p "prompt"`, Claude Code handles:
- API authentication
- Streaming
- Error recovery
- Rate limiting
- Model selection

**Migration notes:**
- Delete `chat.py`
- Replace calls to `chat_completion()` with Claude Code subprocess calls
- Vision model support: `claude -p "prompt" --image path/to/image.png` (if supported) or pass image in prompt

---

### 3. Patch System (`patch.py`, `patch_strategies/`)

**What it does:**
Generates code changes from LLM responses and applies them to the filesystem.

**How it works:**

1. **Strategy selection** — Choose a patch format (currently only `full_file`)
2. **Prompt construction** — Include format instructions in LLM prompt
3. **Response parsing** — Extract file contents from XML-like format
4. **Preview** — Show user what will change
5. **Approval** — Ask Y/N
6. **Application** — Write files, git add, git commit

The XML format looks like:
```xml
<code filename="path/to/file.py" language="python">
def hello():
    print("Hello, world!")
</code>

--- summaries ---
path/to/file.py: Added hello function
```

**Pain points:**

1. **Custom format is fragile** — LLMs don't always emit valid XML
2. **State machine parsing** — Complex regex/state machine to extract blocks
3. **Full file replacement only** — No surgical edits, high token cost
4. **Git operations embedded** — Mixes concerns (patching vs. version control)
5. **No conflict detection** — Overwrites without checking for concurrent edits
6. **Duplicates Claude Code Edit tool** — Reimplements what already exists

**Verdict: DISCARD entirely**

Claude Code's Edit tool:
- Uses unique string matching for surgical edits
- Has conflict detection (fails if old_string not found)
- Doesn't require custom format instructions
- Handles multi-file changes atomically

**Migration notes:**
- Delete `patch.py` and `patch_strategies/`
- Replace `ah.patch(plan)` with `ah.edit(prompt)` which calls Claude Code
- Let Claude Code handle git operations (or keep git operations separate in macro)

---

### 4. Context Manager (`context.py`)

**What it does:**
Maintains conversation history and file context for LLM calls.

**How it works:**
```python
class ContextManager:
    messages: List[Message]  # Rolling conversation history
    included_files: Dict[str, str]  # file_path -> contents

    def add_message(role, content): ...
    def get_messages_for_llm(): ...  # Returns last N messages + file context
    def load_git_tracked_files(): ...  # Auto-includes repo files
```

Features:
- Loads all git-tracked files on startup
- Allows toggling files in/out of context
- Injects file contents into LLM prompts as markdown blocks
- Rolling message history (configurable depth)

**Pain points:**

1. **Over-inclusion** — Loading all git files can be excessive
2. **No smart truncation** — Just cuts off at N messages
3. **Context leaks between macros** — One macro's messages visible to next
4. **Duplicates Claude Code context** — Claude Code manages its own context

**Verdict: PARTIALLY KEEP**

We need *some* context management for the REPL experience (showing history, tracking state). But we shouldn't try to manage LLM context ourselves.

**Migration notes:**
- Keep for REPL display purposes (show user what macros have done)
- Don't pass to Claude Code (let it manage its own context)
- Simplify: just log what commands were run, not full message history
- Consider making context per-macro rather than global

---

### 5. Macro System (`macro_runner.py`, `macro_helpers.py`)

**What it does:**
Executes Python macro scripts with a DSL for agentic operations.

**How it works:**

1. **Macro loading:**
   ```python
   # User runs: /macro examples/tdd_macro.py test_goal="auth"
   runner = MacroRunner(console, cli)
   runner.run("examples/tdd_macro.py test_goal='auth'")
   ```

2. **Dynamic import:**
   ```python
   def _import_module(self, path):
       spec = importlib.util.spec_from_file_location(name, path)
       module = importlib.util.module_from_spec(spec)
       spec.loader.exec_module(module)
       return module
   ```

3. **Global runner injection:**
   ```python
   macro_helpers.set_runner(self)  # Set global _runner
   main_func(self.ctx, **kwargs)   # Call macro's main()
   macro_helpers.set_runner(None)  # Clear after
   ```

4. **Helper functions delegate to runner:**
   ```python
   # In macro_helpers.py
   def chat(prompt):
       return _require_runner().chat(prompt)
   ```

**Pain points:**

1. **Global state** — `_runner` singleton is fragile
2. **No true parallelism** — Can't spawn concurrent macros
3. **CWD manipulation** — Changes working directory during execution
4. **Error handling could be better** — Exceptions sometimes leave state dirty
5. **Missing `ah.llm()`** — The tree_of_thought example references non-existent function

**Verdict: KEEP with significant modifications**

The macro model is correct. The implementation needs rework:
- Remove global runner singleton
- Pass runner instance to macro (or use dependency injection)
- Add real parallel execution
- Better error recovery

**Migration notes:**
- Rewrite MacroRunner to use Claude Code subprocess calls
- Add `spawn()` and `join()` primitives
- Keep the `main(ctx, **kwargs)` contract
- Keep `ah.` helper pattern (it's clean)

---

### 6. Macro Helpers (`macro_helpers.py`)

**What it does:**
Thin facade that macro scripts import. Provides the `ah.` namespace.

**Current API:**
```python
ah.log(msg)                         # Print to console
ah.chat(prompt, include_context, image_path)  # LLM completion
ah.shell(cmd, capture)              # Shell execution
ah.patch(plan, user_approval)       # Code generation workflow
ah.approve(msg)                     # Y/N prompt
ah.get_var(name, default)           # Access CLI args
ah.get_last_shell_exit_code()       # Exit code
```

**Pain points:**

1. **Delegates through global** — Uses `_require_runner()` pattern
2. **Incomplete** — Missing `ah.llm()` async version, `ah.spawn()`, `ah.join()`
3. **No type hints** — Return types unclear to macro authors

**Verdict: KEEP, significantly expand**

This is the right pattern — a clean, simple API for macro authors. But we need to:
- Add parallelism primitives (`spawn`, `join`)
- Add file operations (`read`, `write`, `edit`)
- Remove patch (replaced by edit)
- Add JSON parsing helpers
- Add better type hints

**Migration notes:**
- New API design in 04_python_dsl_design.md
- Keep backwards compatibility where possible
- Add async versions of core functions

---

### 7. Example Macros (`examples/`)

**Current examples:**

| Macro | Purpose | Status |
|-------|---------|--------|
| `tdd_macro.py` | Test-driven development loop | Working |
| `tree_of_thought.py` | Parallel thought generation | Broken (uses `ah.llm()`) |
| `basic_macro_demo.py` | Shows all helper functions | Working |
| `chart_judge_macro.py` | Generate charts, judge quality | Unknown |
| `shader_macro.py` | Generate shaders | Unknown |

**Pain points:**

1. **tree_of_thought uses non-existent API** — References `ah.llm()` which doesn't exist
2. **asyncio integration unclear** — How should async work with macro runner?
3. **No standard patterns** — Each macro invents its own loop structure

**Verdict: REWRITE examples for v2**

Examples should demonstrate:
- Basic sequential workflow
- Parallel execution with spawn/join
- Vision model integration
- Error handling patterns
- Human checkpoint patterns

**Migration notes:**
- Port tdd_macro to new API
- Fix tree_of_thought to use actual parallelism
- Add shader evolution example from architecture doc

---

### 8. Models (`models.py`)

**What it does:**
Pydantic models for data structures.

**Current models:**
```python
class TextContent(BaseModel):
    type: Literal["text"]
    text: str

class ImageContent(BaseModel):
    type: Literal["image_url"]
    image_url: dict  # {"url": "data:image/png;base64,..."}

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: Union[str, List[Union[TextContent, ImageContent]]]

class Patch(BaseModel):
    file_changes: Dict[str, str]
    summaries: Dict[str, str]
```

**Pain points:**
- Patch model won't be needed
- Message model is OpenRouter-specific

**Verdict: SIMPLIFY or DISCARD**

We might not need custom models if Claude Code handles message formatting.

**Migration notes:**
- Remove Patch model
- Keep Message model only if we track history for display
- Consider using simple dicts instead of Pydantic

---

### 9. Configuration (`config.py` / `config_manager`)

**What it does:**
Manages user preferences (selected model, etc.).

**Pain points:**
- Model selection won't matter (Claude Code uses its own)
- Configuration might still be useful for macro defaults

**Verdict: SIMPLIFY**

**Migration notes:**
- Remove model selection (or repurpose for Claude Code model flag)
- Keep for macro-specific configuration
- Consider environment variables instead

---

## Summary Table

| Component | Lines | Verdict | Action |
|-----------|-------|---------|--------|
| `cli.py` | ~400 | KEEP | Simplify, decouple |
| `chat.py` | ~150 | DISCARD | Delete entirely |
| `patch.py` | ~200 | DISCARD | Delete entirely |
| `patch_strategies/` | ~100 | DISCARD | Delete entirely |
| `context.py` | ~200 | PARTIAL | Simplify for display only |
| `macro_runner.py` | ~370 | REWRITE | New orchestration model |
| `macro_helpers.py` | ~100 | EXPAND | New DSL API |
| `models.py` | ~50 | SIMPLIFY | Remove most models |
| `commands.py` | ~200 | KEEP/REWIRE | Rewire to use Claude Code subprocess instead of OpenRouter |
| `config.py` | ~50 | SIMPLIFY | Remove model selection |

**Total lines to remove:** ~1100
**Total lines to rewrite:** ~500
**Total lines to keep/modify:** ~350

---

## What Works Well (Keep These Patterns)

### 1. The Macro Contract

```python
def main(ctx, **kwargs):
    """Every macro has this signature."""
    pass
```

This is simple, Pythonic, and easy to understand. Keep it.

### 2. The `ah.` Namespace

```python
import ai_os as ah  # or: import ai_os.core.macro_helpers as ah

ah.log("message")
ah.chat("prompt")
ah.approve("Continue?")
```

Clean, memorable API. Keep it.

### 3. Human Checkpoints

```python
if ah.approve("Apply these changes?"):
    # proceed
else:
    # abort or retry
```

Essential for safe agentic workflows. Keep it.

### 4. The REPL Experience

```
> /macro examples/tdd_macro.py test_goal="implement auth"
[macro output streams here]
Macro asks for approval: Is test file ok? [y/N]
```

Interactive terminal is the right UX. Keep it.

### 5. Argument Passing

```bash
/macro script.py key=value another_key="quoted value"
```

Simple key=value args with type coercion. Keep it.

---

## What Doesn't Work (Fix These)

### 1. XML Patch Format

**Problem:** Fragile custom parsing
**Solution:** Use Claude Code's native Edit tool

### 2. Global Runner Singleton

**Problem:** Can't have concurrent macros
**Solution:** Pass runner instance or use proper DI

### 3. No Real Parallelism

**Problem:** `asyncio.gather` doesn't work with current API
**Solution:** `ah.spawn()` launches real subprocess

### 4. Context Management Complexity

**Problem:** Over-engineered for simple use case
**Solution:** Let Claude Code manage LLM context

### 5. OpenRouter Lock-in

**Problem:** Custom API integration
**Solution:** Use Claude Code (which supports multiple models)

---

## Migration Risk Assessment

### Low Risk (Safe to Change)

- `chat.py` — Pure I/O, no state
- `patch.py` — Self-contained
- `models.py` — Just data structures

### Medium Risk (Test Carefully)

- `cli.py` — User-facing, needs UX testing
- `context.py` — Shared state, need to ensure display still works
- `commands.py` — Entry points, need to route to new code

### High Risk (Plan Carefully)

- `macro_runner.py` — Core execution model, fundamental change
- `macro_helpers.py` — API contract, affects all macros

---

## Dependency Analysis

### External Dependencies (Keep)

- `rich` — Console output, prompts, styling
- `prompt_toolkit` — REPL input handling
- `pydantic` — Data validation (maybe optional)
- `httpx` — Only needed if we keep web features

### External Dependencies (Remove)

- None directly, but OpenRouter API key no longer needed

### New Dependencies

- `claude` CLI tool must be installed
- Python subprocess management

---

## Code Quality Observations

### Good

1. Clear separation of concerns (mostly)
2. Type hints in some places
3. Error messages are helpful
4. Rich output is readable

### Needs Improvement

1. Inconsistent error handling (some swallow, some raise)
2. Missing docstrings in many places
3. Some functions do too much
4. Test coverage appears minimal

---

## Recommendations

### Immediate (Before Starting v2)

1. Write tests for existing macros (tdd_macro, etc.)
2. Document the exact current behavior
3. Create a "compatibility matrix" of what macros use what features

### Short-term (During v2 Development)

1. Keep v1 running in parallel until v2 proven
2. Create adapter layer if needed for gradual migration
3. Port examples one at a time

### Long-term (After v2 Stable)

1. Remove all v1 code
2. Simplify further based on usage patterns
3. Consider packaging for pip install

---

## Appendix: File-by-File Notes

### `ai_os/cli.py`

**Keep:**
- REPL loop structure
- Alias expansion (`>` → `/chat`)
- History persistence
- Tab completion framework

**Change:**
- Route commands through new orchestrator
- Simplify command set
- Better error display

### `ai_os/core/chat.py`

**Delete entirely.** Claude Code handles this.

### `ai_os/core/patch.py`

**Delete entirely.** Claude Code's Edit tool handles this.

### `ai_os/core/patch_strategies/strategy_full_file.py`

**Delete entirely.** No custom format needed.

### `ai_os/core/macro_runner.py`

**Rewrite to:**
- Call Claude Code subprocess
- Support spawn/join
- Better error recovery
- No global state

### `ai_os/core/macro_helpers.py`

**Expand to:**
- `spawn()`, `join()` for parallelism
- `read()`, `write()`, `edit()` for files
- `chat()` that calls Claude Code
- Remove `patch()` (use `edit()`)

### `ai_os/core/models.py`

**Simplify to:**
- Remove Patch (not needed)
- Maybe remove all models if we use dicts

### `ai_os/core/commands.py`

**Probably delete.** Commands become thin wrappers around macro_helpers.

### `ai_os/utils/context.py`

**Simplify to:**
- Just track command history for display
- Don't try to manage LLM context

---

## Conclusion

The current AI-OS has the right ideas but the wrong plumbing. The macro model, REPL UX, and `ah.` API are good. The OpenRouter integration, XML parsing, and context management are unnecessary complexity.

By using Claude Code as the execution substrate, we can:
1. Delete ~1100 lines of code
2. Get real parallelism
3. Inherit a battle-tested tool ecosystem
4. Focus on what AI-OS does best: orchestration and human oversight

Next document (03_claude_code_integration.md) will detail exactly how to interface with Claude Code.
