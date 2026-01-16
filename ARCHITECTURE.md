# AI-OS v2 Architecture

**Claude Code Native Implementation**

This document describes the technical architecture of AI-OS v2, its design decisions, and implementation details.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Design Decisions](#design-decisions)
5. [Data Flow](#data-flow)
6. [API Layers](#api-layers)
7. [Parallel Execution](#parallel-execution)
8. [Error Handling](#error-handling)
9. [Testing Strategy](#testing-strategy)
10. [Future Enhancements](#future-enhancements)

---

## Overview

AI-OS v2 is a thin Python DSL wrapper around Claude Code CLI. Instead of making direct API calls to LLMs, we invoke `claude -p` as a subprocess and let Claude Code handle:

- File operations (Read, Write, Edit)
- Shell commands (Bash)
- Web search (WebSearch, WebFetch)
- Vision (native image reading)
- Tool use orchestration

### Design Philosophy

1. **Minimalism**: Keep the core small (~2000 LOC)
2. **Composability**: Functions are building blocks, not frameworks
3. **Debuggability**: All operations are transparent Python code
4. **Human oversight**: Every macro can prompt for approval
5. **No magic**: Explicit is better than implicit

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User's Macro                          │
│  import ai_os as ai                                          │
│  def main(ctx, **kwargs):                                    │
│      ai.chat("Hello") → ai.edit("Fix bug") → ai.shell("test")│
└──────────────┬──────────────────────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────────────────────┐
│                         DSL Layer                             │
│  ai_os/__init__.py & ai_os/core/dsl.py                       │
│  - Standalone functions (work outside macros)                 │
│  - Simple, pythonic API                                       │
│  - No hidden state (except _orchestrator singleton)           │
└──────────────┬───────────────────────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                         │
│  ai_os/core/orchestrator.py                                  │
│  - ClaudeOrchestrator class                                   │
│  - Subprocess management                                      │
│  - Cost tracking                                              │
│  - Async/parallel execution                                   │
└──────────────┬───────────────────────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────────────────────┐
│                    Claude Code CLI                            │
│  claude -p --model sonnet --output-format json               │
│  - Native tool use (Edit, Bash, Read, Write)                 │
│  - Vision support                                             │
│  - Web search                                                 │
└──────────────┬───────────────────────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────────────────────┐
│                      Anthropic API                            │
│  Claude models (Sonnet 4.5, Opus, Haiku)                     │
└──────────────────────────────────────────────────────────────┘
```

### Auxiliary Components

```
┌─────────────────────────────┐    ┌──────────────────────────┐
│   MacroRunner               │    │   Terminal CLI           │
│   ai_os/core/macro_runner.py│    │   ai_os/cli.py           │
│   - Loads .py files         │    │   - REPL interface       │
│   - Injects context         │    │   - Commands: >, +, !, @ │
└─────────────────────────────┘    └──────────────────────────┘

┌─────────────────────────────┐    ┌──────────────────────────┐
│   Legacy Helpers            │    │   Context Manager        │
│   ai_os/core/macro_helpers  │    │   ai_os/utils/context.py │
│   - Backward compat (ah)    │    │   - Conversation history │
└─────────────────────────────┘    └──────────────────────────┘
```

---

## Core Components

### 1. ClaudeOrchestrator (`ai_os/core/orchestrator.py`)

The heart of v2. Manages all communication with Claude Code.

**Responsibilities:**
- Spawn `claude -p` subprocess
- Pass prompts via stdin
- Parse JSON responses
- Track costs (tokens, USD)
- Handle streaming output
- Manage parallel execution with asyncio

**Key Methods:**
```python
class ClaudeOrchestrator:
    def chat(prompt, model=None, context_files=None, async_=False) -> str
    def chat_json(prompt, model=None, async_=False) -> dict
    def chat_streaming(prompt, model=None) -> Generator[str, None, None]
    def edit(instruction, file=None, async_=False) -> bool
    def vision(prompt, image, model=None, async_=False) -> str
    def shell(command, capture=False, check=False) -> int | str
    def spawn(prompt, output_file=None, model=None) -> Future
    def join(agents, timeout=None) -> List[ClaudeResult]
```

**Implementation Details:**

1. **Subprocess invocation:**
```python
result = subprocess.run(
    ["claude", "-p", "--model", model, "--output-format", "json"],
    input=prompt,
    capture_output=True,
    text=True,
    cwd=self.working_dir,
    timeout=self.timeout
)
```

2. **Cost tracking:**
```python
output = json.loads(result.stdout)
self.total_cost["input_tokens"] += output["cost"]["input_tokens"]
self.total_cost["output_tokens"] += output["cost"]["output_tokens"]
```

3. **Async execution:**
```python
async def chat_async(self, prompt, model=None):
    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", "--model", model,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        ...
    )
    stdout, stderr = await proc.communicate(prompt.encode())
    return json.loads(stdout.decode())
```

### 2. DSL Layer (`ai_os/core/dsl.py`)

The user-facing API. Standalone functions that work outside macro context.

**Design:**
- Module-level `_orchestrator` singleton
- Lazy initialization on first use
- No required setup/teardown
- Works in Jupyter notebooks, scripts, REPL, macros

**Example:**
```python
import ai_os as ai

# Just works - no setup needed
result = ai.chat("Hello")
ai.log(result)
```

**Parallel Execution:**
```python
def gather(*prompts, model=None) -> List[str]:
    orch = _get_orchestrator()

    async def run_all():
        tasks = [
            orch.chat(prompt, model=model, async_=True)
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks)

    return asyncio.run(run_all())
```

### 3. MacroRunner (`ai_os/core/macro_runner.py`)

Executes Python files as macros.

**Workflow:**
1. Parse command line: `/macro path/to/macro.py key=value`
2. Import the .py file dynamically
3. Extract `main(ctx, **kwargs)` function
4. Inject context: `ctx = {"vars": {"key": "value"}}`
5. Call `main(ctx, key="value")`
6. Clean up context on exit

**Context Injection:**
```python
# In MacroRunner.run():
ctx = {"vars": kwargs}
dsl._set_context(ctx)  # Make vars accessible via ai.get_var()

try:
    main_func(ctx, **kwargs)
finally:
    dsl._clear_context()
```

### 4. Terminal CLI (`ai_os/cli.py`)

The interactive REPL.

**Commands:**
- `>` or `/chat` → Chat with Claude (read-only)
- `+` or `/patch` → Have Claude edit files
- `!` or `/run` → Run shell commands with piping
- `@` or `/macro` → Execute Python macros
- `/context` → Manage conversation context
- `/help` → Show help

**Implementation:**
```python
def handle_command(self, user_input: str):
    if user_input.startswith('>'):
        # Stream chat response
        for chunk in chat(prompt, self.console):
            print(chunk, end='', flush=True)

    elif user_input.startswith('+'):
        # Apply edits
        result = patch(instruction, console=self.console)

    elif user_input.startswith('@'):
        # Run macro
        runner = MacroRunner(self.console)
        runner.run(argline)
```

---

## Design Decisions

### Why Claude Code Instead of Direct API?

**Rationale:**
1. **Tool use is complex**: Building reliable file editing, shell execution, web search from scratch is hard
2. **Claude Code is battle-tested**: Anthropic maintains it, handles edge cases
3. **Future-proof**: New tools (PDFs, databases, etc.) automatically available
4. **Security**: Claude Code has built-in sandboxing and permission system

**Trade-offs:**
- ✅ Less code to maintain
- ✅ Better tool reliability
- ❌ Requires Node.js/npm
- ❌ Slightly higher latency (subprocess overhead ~50-100ms)

### Why Subprocess Instead of Python API?

**Rationale:**
1. Claude Code is a CLI tool, not a Python library
2. Subprocess is simple and works everywhere
3. Can easily switch to other backends later
4. Natural isolation between AI-OS and Claude Code

### Why asyncio.gather() Instead of spawn/join?

**Rationale:**
1. `asyncio.gather()` is Python-native, well-understood
2. Simpler implementation (no thread pools, no state tracking)
3. Better error handling (all-or-nothing)
4. `spawn/join` kept for API compatibility but discouraged

**Example:**
```python
# Preferred (v2)
results = ai.gather("Q1", "Q2", "Q3")

# Also works (but adds complexity)
agents = [ai.spawn("Q1"), ai.spawn("Q2"), ai.spawn("Q3")]
results = ai.join(agents)
```

### Why No Streaming in gather()?

**Rationale:**
1. Parallel streaming is complex (multiple stdout streams)
2. Most use cases don't need real-time feedback for parallel ops
3. Can add later if needed without breaking API

---

## Data Flow

### Synchronous Chat Flow

```
User macro
  ↓ ai.chat("Hello")
DSL Layer
  ↓ _get_orchestrator().chat("Hello")
Orchestrator
  ↓ subprocess.run(["claude", "-p", ...], input="Hello")
Claude Code
  ↓ Uses Read/Edit/Bash tools as needed
  ↓ Returns JSON: {"result": "Hello! How can I help?", "cost": {...}}
Orchestrator
  ↓ Parses JSON, tracks cost
  ↓ Returns result string
DSL Layer
  ↓ Returns to macro
User macro
  ↓ result = "Hello! How can I help?"
```

### Parallel Execution Flow

```
User macro
  ↓ results = ai.gather("Q1", "Q2", "Q3")
DSL Layer
  ↓ asyncio.run(run_all())
    ↓ async def run_all():
        tasks = [orch.chat(q, async_=True) for q in ["Q1","Q2","Q3"]]
        return await asyncio.gather(*tasks)
Orchestrator (x3 parallel)
  ↓ await asyncio.create_subprocess_exec("claude", "-p", ...)
  ↓ await proc.communicate(prompt.encode())
Claude Code (x3 parallel processes)
  ↓ Each runs independently
  ↓ Returns JSON responses
Orchestrator
  ↓ Collects all 3 results
DSL Layer
  ↓ Returns ["Answer 1", "Answer 2", "Answer 3"]
User macro
  ↓ results = ["Answer 1", "Answer 2", "Answer 3"]
```

### Edit Flow

```
User macro
  ↓ ai.edit("Add logging to main.py")
DSL Layer
  ↓ _get_orchestrator().edit("Add logging to main.py")
Orchestrator
  ↓ Builds system instruction: "Use the Edit tool..."
  ↓ subprocess.run(["claude", "-p"], input=full_prompt)
Claude Code
  ↓ Reads main.py
  ↓ Uses Edit tool to modify file
  ↓ Returns summary: "Added logging statements to main.py"
Orchestrator
  ↓ Returns True (success)
DSL Layer
  ↓ Returns True
User macro
  ↓ success = True
```

---

## API Layers

### Layer 1: Core Orchestrator (Low-Level)

Direct access to Claude Code subprocess.

```python
from ai_os.core.orchestrator import ClaudeOrchestrator

orch = ClaudeOrchestrator(working_dir="/tmp", default_model="haiku")
result = orch.chat("Hello", model="sonnet")
```

**Use when:**
- Need fine-grained control
- Custom working directory per operation
- Testing orchestrator in isolation

### Layer 2: DSL (High-Level)

User-friendly standalone functions.

```python
import ai_os as ai

result = ai.chat("Hello")
ai.log(result)
```

**Use when:**
- Writing macros (99% of the time)
- One-off scripts
- Interactive REPL usage

### Layer 3: Legacy Helpers (Compatibility)

Backward-compatible `ah` alias.

```python
from ai_os.core import macro_helpers as ah

result = ah.chat("Hello")
ah.log(result)
```

**Use when:**
- Migrating v1 macros
- Need exact v1 API compatibility

---

## Parallel Execution

### Implementation: asyncio.gather()

```python
async def run_all():
    tasks = [
        orch.chat(prompt, model=model, async_=True)
        for prompt in prompts
    ]
    return await asyncio.gather(*tasks)

return asyncio.run(run_all())
```

### Why asyncio Instead of Threads?

1. **Native Python**: No external dependencies
2. **Efficient**: Single event loop, no GIL contention
3. **Composable**: Easy to add timeouts, cancellation
4. **Debuggable**: Stack traces work correctly

### Performance

**Single operation:**
```
Think time: ~1.5s
Stream time: ~0.5s
Total: ~2s
```

**5 parallel operations:**
```
Think time: ~1.5s (same as single)
Stream time: ~0.5s (same as single)
Total: ~2s (not 10s!)
```

**Speedup:** ~5x for I/O-bound operations.

---

## Error Handling

### Orchestrator-Level Errors

```python
try:
    result = orch.chat(prompt)
except subprocess.CalledProcessError as e:
    # Claude Code returned non-zero exit
    print(f"Error: {e.stderr}")
except subprocess.TimeoutExpired:
    # Exceeded timeout (default 600s)
    print("Operation timed out")
except json.JSONDecodeError:
    # Failed to parse Claude Code output
    print("Invalid response format")
```

### DSL-Level Errors

DSL functions catch orchestrator errors and return safe defaults:

```python
def chat(prompt, **kwargs):
    try:
        return _get_orchestrator().chat(prompt, **kwargs)
    except Exception as e:
        log(f"[red]Chat error: {e}[/red]")
        return ""  # Safe default
```

### Macro-Level Errors

Macros can use standard Python error handling:

```python
def main(ctx, **kwargs):
    try:
        result = ai.chat("risky operation")
        if "error" in result.lower():
            raise ValueError("LLM reported an error")
    except Exception as e:
        ai.log(f"[red]Macro failed: {e}[/red]")
        return  # Early exit
```

---

## Testing Strategy

### Unit Tests (Fast, No API Calls)

Test orchestrator logic without calling Claude:

```python
def test_cost_tracking():
    orch = ClaudeOrchestrator()
    # Mock subprocess to return fake cost data
    ...
    assert orch.total_cost["input_tokens"] == 100
```

### Integration Tests (Slow, Real API Calls)

Test actual Claude Code interaction:

```python
@pytest.mark.slow
def test_basic_chat():
    orch = ClaudeOrchestrator()
    response = orch.chat("Say 'test passed'", model="haiku")
    assert "test" in response.lower()
```

### Macro Tests (End-to-End)

Test full macro workflows:

```python
def test_tdd_macro():
    runner = MacroRunner(console)
    runner.run("examples/tdd_macro.py goal='fibonacci function'")
    # Check that test file was created
    # Check that implementation passes tests
```

### Test Isolation

- Each test uses temporary directory
- Reset global orchestrator between tests
- Use `haiku` model to minimize cost
- Mark expensive tests with `@pytest.mark.slow`

---

## Future Enhancements

### Planned Features

1. **Caching layer**: Cache expensive LLM calls by prompt hash
2. **Cost budgets**: Fail-safe to prevent runaway costs
3. **Retry logic**: Auto-retry on transient errors
4. **Progress tracking**: Better visibility into long-running operations
5. **Remote execution**: Run macros on remote machines
6. **Multi-model**: Mix Claude, GPT, Llama in same macro
7. **Streaming gather()**: Real-time updates for parallel operations

### Architectural Improvements

1. **Plugin system**: Allow custom tools beyond Claude Code
2. **State persistence**: Save/restore macro state across runs
3. **Distributed execution**: Run gather() across multiple machines
4. **Better testing**: Mock Claude Code for faster unit tests
5. **Profiling**: Built-in performance analysis tools

### Research Directions

1. **Tree of Thought**: Built-in ToT macro primitive
2. **Self-healing**: Auto-fix errors using LLM
3. **Cost optimization**: Dynamic model selection based on task complexity
4. **Human-in-the-loop**: Better approval UX (show diffs, preview changes)

---

## Performance Characteristics

### Latency

| Operation | Time | Notes |
|-----------|------|-------|
| Orchestrator overhead | ~50ms | Subprocess spawn |
| Claude API (chat) | ~1.5s | Think time |
| Claude API (stream) | ~0.5s | Streaming response |
| File read (local) | <1ms | Direct Python I/O |
| File write (local) | <1ms | Direct Python I/O |
| Edit operation | ~3s | Claude reads → thinks → edits |
| Vision analysis | ~2s | Image upload + processing |

### Throughput

| Scenario | Sequential | Parallel (gather) | Speedup |
|----------|-----------|-------------------|---------|
| 5x chat | ~10s | ~2s | 5x |
| 10x haiku | ~15s | ~2s | 7.5x |
| 3x vision | ~6s | ~2.5s | 2.4x |

### Memory Usage

- Base: ~50MB (Python + dependencies)
- Per orchestrator: ~5MB
- Per Claude process: ~100MB (Node.js)
- Parallel (5 ops): ~550MB total

---

## Code Organization

```
ai-os_2/
├── ai_os/
│   ├── __init__.py           # Main API exports
│   ├── core/
│   │   ├── orchestrator.py   # Claude Code wrapper (500 LOC)
│   │   ├── dsl.py            # Standalone DSL (300 LOC)
│   │   ├── macro_runner.py   # Macro execution (350 LOC)
│   │   ├── macro_helpers.py  # Legacy compat (280 LOC)
│   │   ├── commands.py       # Terminal commands (290 LOC)
│   │   └── models.py         # Data models (30 LOC)
│   ├── ui/                   # Terminal UI components
│   └── utils/                # Context, logging, config
├── examples/                 # Example macros
├── tests/                    # Test suite
├── ARCHITECTURE.md          # This file
├── MIGRATION.md             # v1→v2 guide
└── README.md                # User documentation
```

### LOC Comparison

| Component | v1 | v2 | Change |
|-----------|----|----|--------|
| Core logic | 1800 | 1000 | -44% |
| Patch strategies | 800 | 0 | -100% |
| OpenRouter integration | 300 | 0 | -100% |
| Orchestrator | 0 | 500 | +500 |
| Tests | 400 | 600 | +50% |
| **Total** | **3300** | **2100** | **-36%**

---

## Conclusion

AI-OS v2 achieves its design goals:

✅ **Simpler codebase**: 36% reduction in core code
✅ **More reliable**: Claude Code handles edge cases
✅ **More powerful**: Parallel execution, native vision
✅ **More maintainable**: Less custom logic to debug
✅ **Backward compatible**: v1 macros still work

The architecture is designed to be:
- **Understandable**: Clear layers, minimal abstraction
- **Extensible**: Easy to add new DSL functions
- **Testable**: Unit tests don't need API calls
- **Debuggable**: Transparent subprocess communication

For questions or contributions, see:
- GitHub: https://github.com/nbardy/AI-OS
- Issues: https://github.com/nbardy/AI-OS/issues
