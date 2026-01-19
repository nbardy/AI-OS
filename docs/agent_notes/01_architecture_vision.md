# Architecture Vision: AI-OS v2 — Claude Code Native

**Date:** 2026-01-17
**Status:** Design Phase
**Author:** Architecture Planning Session

---

## Executive Summary

AI-OS v2 represents a fundamental architectural shift: instead of building custom tool-calling infrastructure on top of OpenRouter, we leverage Claude Code's battle-tested tooling infrastructure as our execution substrate. This document outlines the vision, rationale, and high-level architecture for this redesign.

The core insight is simple: **Claude Code already solved the hard problems** (file editing, shell execution, context management, streaming, error handling). We should use that, not rebuild it. Our value-add is the **orchestration layer** — the Python DSL that lets engineers write composable, debuggable agentic workflows with human-in-the-loop control.

---

## The Problem Space

### What AI-OS Does (And Should Keep Doing)

AI-OS exists because existing agent frameworks have a fundamental flaw: they're fire-and-forget black boxes. When Claude, Devin, or any "AI agent" runs a complex workflow:

1. **No visibility** — You can't see what it's thinking mid-execution
2. **No intervention** — If it goes off-track, you can't course-correct
3. **No composability** — One agent's output can't feed another's input cleanly
4. **No iteration** — Failed runs leave no useful state for retry

AI-OS solves this with the **macro model**: small, readable Python scripts that define agentic workflows with explicit human checkpoints. The macro runs in a REPL where you can see everything, approve changes, and intervene.

This is the right model. Keep it.

### What AI-OS Currently Does Wrong

The current implementation rebuilds infrastructure that already exists:

1. **Custom XML patch format** — We parse `<code filename="...">` blocks from LLM responses and apply them as full-file replacements. Claude Code already has `Edit` and `Write` tools with proper diff handling, conflict detection, and error recovery.

2. **OpenRouter HTTP/SSE streaming** — We wrote custom streaming, chunking, and error handling. Claude Code handles all of this with proper retry logic and rate limiting.

3. **Tool calling simulation** — We don't use function calling at all. We ask the LLM to emit XML and parse it. This is fragile and loses the structured output guarantees modern LLMs provide.

4. **Context management** — We manually track messages, file content, and conversation history. Claude Code manages context automatically with intelligent truncation.

5. **No parallel execution** — The `tree_of_thought.py` example uses `asyncio.gather` with a non-existent `ah.llm()` function. True parallelism isn't implemented.

### The Opportunity

Claude Code provides:
- Native file Read/Edit/Write tools
- Bash execution with proper sandboxing
- Sub-agent spawning via the Task tool
- Context management that survives long conversations
- Streaming with timing indicators
- LSP integration for code intelligence

If we use Claude Code as our execution runtime, we get all of this for free. We only need to build:
1. A thin Python DSL for macro authors
2. An orchestration layer that spawns and joins Claude Code processes
3. A REPL for human interaction

---

## Architecture Vision

### Core Principle: Claude Code as Syscall Interface

Think of Claude Code like the operating system kernel, and our Python DSL as the shell scripting language. You don't rewrite the kernel to write a bash script. You call into it.

```
┌────────────────────────────────────────────────────────────────┐
│                     AI-OS v2 Architecture                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Human Interface Layer                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │   REPL      │  │  Progress   │  │   Approval      │   │  │
│  │  │  Terminal   │  │  Display    │  │   Prompts       │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Orchestration Layer                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │   Macro     │  │  Agent      │  │   Result        │   │  │
│  │  │   Parser    │  │  Spawner    │  │   Aggregator    │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │              Python DSL (macro_helpers v2)           │ │  │
│  │  │  spawn() | join() | chat() | edit() | approve()     │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Claude Code Runtime                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │  │
│  │  │  Read   │ │  Edit   │ │  Bash   │ │  Task (agents)  │ │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘ │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────────────────────┐ │  │
│  │  │  Write  │ │  Grep   │ │  WebFetch | WebSearch       │ │  │
│  │  └─────────┘ └─────────┘ └─────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Filesystem / Git / Shell                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Execution Model

When a macro runs:

1. **Macro loads** — Python imports the macro file, just like today
2. **Helper calls translate to Claude Code invocations** — When the macro calls `ah.edit("fix the bug in auth.py")`, we spawn `claude -p "fix the bug in auth.py" --dangerously-skip-permissions`
3. **Results flow back** — Claude Code's stdout is captured and returned to the macro
4. **State persists** — File changes Claude Code makes are visible to subsequent operations
5. **Parallelism is real** — `ah.spawn()` launches actual parallel Claude Code processes

### The Critical Insight: Prompt Files as Interface

Claude Code accepts prompts from files or stdin:
```bash
claude -p "do something"                    # Direct prompt
claude -p < prompt.txt                      # From file
echo "do something" | claude -p             # From stdin
claude -p --dangerously-skip-permissions    # Skip approval dialogs
```

This means our DSL can:
1. Construct prompts programmatically in Python
2. Pipe them to Claude Code
3. Capture the results
4. Use those results to construct the next prompt

This is exactly how shell scripting works — and that's why it's powerful.

---

## The Shader Loop Example

Let's trace through the shader generation example you described to validate the architecture:

```python
# examples/shader_evolution.py
import ai_os as ah

def main(ctx, **kwargs):
    """
    Evolutionary shader generation with parallel exploration and critique.

    1. Look at prior shaders and critiques
    2. Plan 5 mathematically different approaches
    3. Launch 5 sub-agents to write shaders in parallel
    4. Render all 5
    5. Score them with vision model
    6. Pick best, discard others
    7. Critique the best one
    8. Loop 10 times
    """

    goal = kwargs.get("goal", "create a beautiful generative shader")
    iterations = kwargs.get("iterations", 10)

    best_shader = None
    best_score = 0
    history = []

    for round_num in range(iterations):
        ah.log(f"[bold]Round {round_num + 1}/{iterations}[/bold]")

        # Step 1: Plan 5 different mathematical approaches
        plan_prompt = f"""
        Goal: {goal}

        Prior best shader (score {best_score}):
        {best_shader or "None yet"}

        Prior critiques:
        {history[-3:] if history else "None yet"}

        Plan 5 VERY DIFFERENT mathematical approaches for shaders.
        Each should explore a different technique:
        - Raymarching / SDFs
        - Noise functions (Perlin, Simplex, Worley)
        - Fractals (Mandelbrot, Julia, IFS)
        - Wave interference patterns
        - Cellular automata / reaction-diffusion

        Output a JSON array of 5 approach descriptions.
        """

        approaches = ah.chat(plan_prompt, parse_json=True)

        # Step 2: Spawn 5 parallel agents to write shaders
        shader_agents = []
        for i, approach in enumerate(approaches):
            agent = ah.spawn(
                f"""
                Write a GLSL fragment shader implementing this approach:
                {approach}

                Requirements:
                - Must be a complete, runnable shader
                - Use uniform float u_time for animation
                - Use uniform vec2 u_resolution for aspect ratio
                - Output to gl_FragColor
                - Be mathematically interesting and visually striking

                Output ONLY the shader code, no explanation.
                """,
                output_file=f"shaders/candidate_{i}.glsl"
            )
            shader_agents.append(agent)

        # Step 3: Wait for all shaders to complete
        shader_results = ah.join(shader_agents)

        # Step 4: Render all shaders to images
        for i in range(5):
            ah.shell(f"glslviewer shaders/candidate_{i}.glsl -s 5 -o renders/candidate_{i}.png")

        # Step 5: Score all renders with vision model
        scores = []
        for i in range(5):
            score_result = ah.chat(
                f"""
                Score this shader render from 1-10 on:
                - Visual interest and complexity
                - Mathematical elegance
                - Aesthetic beauty
                - Animation quality (if visible)

                Be harsh. Most shaders are mediocre.
                Output JSON: {{"score": N, "reason": "..."}}
                """,
                image=f"renders/candidate_{i}.png",
                parse_json=True
            )
            scores.append((i, score_result["score"], score_result["reason"]))

        # Step 6: Pick best
        scores.sort(key=lambda x: x[1], reverse=True)
        winner_idx, winner_score, winner_reason = scores[0]

        if winner_score > best_score:
            best_score = winner_score
            best_shader = ah.read(f"shaders/candidate_{winner_idx}.glsl")
            ah.shell(f"cp shaders/candidate_{winner_idx}.glsl shaders/best.glsl")
            ah.shell(f"cp renders/candidate_{winner_idx}.png renders/best.png")

        ah.log(f"Round {round_num + 1} winner: candidate_{winner_idx} (score: {winner_score})")
        ah.log(f"Reason: {winner_reason}")

        # Step 7: Critique for next round
        critique = ah.chat(
            f"""
            Analyze this shader critically. What makes it work or not work?
            What mathematical principles could be explored further?
            What visual elements are missing?

            Shader code:
            {best_shader}
            """,
            image="renders/best.png"
        )

        history.append({
            "round": round_num + 1,
            "score": best_score,
            "critique": critique
        })

        # Human checkpoint every 3 rounds
        if (round_num + 1) % 3 == 0:
            if not ah.approve(f"Continue evolution? Current best score: {best_score}"):
                break

    ah.log(f"[bold green]Evolution complete! Final score: {best_score}[/bold green]")
    return best_shader
```

### What This Requires From The DSL

Looking at this example, the DSL needs to support:

| Function | Behavior | Implementation Strategy |
|----------|----------|------------------------|
| `ah.log(msg)` | Print to console | Direct print, same as today |
| `ah.chat(prompt, image=None, parse_json=False)` | LLM completion | `claude -p "prompt" [--image path]` |
| `ah.spawn(prompt, output_file=None)` | Start parallel agent | `claude -p "prompt" &` (background) |
| `ah.join(agents)` | Wait for all agents | `wait` on PIDs, collect results |
| `ah.shell(cmd)` | Run shell command | Direct subprocess |
| `ah.read(path)` | Read file contents | Direct file read |
| `ah.approve(msg)` | Human Y/N prompt | Rich Confirm prompt |
| `ah.edit(prompt)` | Have Claude edit files | `claude -p "edit X" --dangerously-skip-permissions` |

---

## Why This Architecture Is Better

### 1. No More XML Parsing

Currently:
```python
# Current: We ask LLM to emit XML and parse it ourselves
response = llm.chat("Write code for X")
# Response: <code filename="foo.py">content</code>
# We parse this manually with regex/state machine
```

New:
```python
# New: Claude Code handles structured output natively
claude -p "Write code for X in foo.py"
# Claude Code uses Edit tool internally, file is written
```

### 2. Real Parallelism

Currently:
```python
# Current: asyncio.gather with non-existent ah.llm()
# This doesn't actually work
tasks = [ah.llm(prompt) for prompt in prompts]
results = await asyncio.gather(*tasks)
```

New:
```python
# New: Actual parallel processes
agents = [ah.spawn(prompt) for prompt in prompts]
results = ah.join(agents)  # Real parallel execution
```

### 3. Inherited Tool Ecosystem

Claude Code has:
- WebFetch for reading URLs
- WebSearch for web search
- Grep/Glob for code search
- LSP integration for go-to-definition
- Git integration

Our macros get all of this for free.

### 4. Battle-Tested Infrastructure

Claude Code is used by thousands of developers daily. Its:
- Error handling is robust
- Rate limiting is handled
- Context management works at scale
- Streaming is reliable

We don't need to rebuild any of this.

### 5. Simpler Codebase

Current ai-os core:
- `chat.py` — OpenRouter API wrapper (150 lines)
- `patch.py` — Patch parsing and application (200 lines)
- `patch_strategies/` — XML format definitions (100 lines)
- `models.py` — Pydantic models (50 lines)
- `context.py` — Message history (200 lines)
- `macro_runner.py` — Macro execution (370 lines)
- `macro_helpers.py` — DSL facade (100 lines)
- `commands.py` — CLI command handlers (200 lines)
- `cli.py` — REPL (400 lines)

**Total: ~1800 lines**

New ai-os core:
- `orchestrator.py` — Spawn/join Claude Code processes (200 lines)
- `macro_helpers.py` — DSL facade (150 lines)
- `cli.py` — REPL (300 lines)

**Total: ~650 lines**

We're removing 1200 lines of code by delegating to Claude Code.

---

## Critical Clarification: The Terminal IS The Product

**We are NOT removing the terminal UI.** The REPL with `>`, `+`, `!`, `@` commands stays exactly as-is from the user's perspective.

What changes:
```
BEFORE:  > hello        →  commands.chat()  →  OpenRouter API  →  response
AFTER:   > hello        →  commands.chat()  →  claude -p       →  response
```

The user still types `> what is 2+2` and gets an answer. They still type `+ add auth` and get a patch. They still type `! pytest` and run tests.

The **terminal commands stay**:
- `>` / `/chat` — Chat with LLM (now via Claude Code)
- `+` / `/patch` — Generate code changes (now via Claude Code's Edit tool)
- `!` / `/run` — Shell commands (unchanged)
- `@` / `/macro` — Run macro scripts (same contract, new internals)

The **macro model stays identical**:
```python
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    ah.log("Hello")
    response = ah.chat("prompt")
    ah.patch("plan")
    ah.approve("Continue?")
```

We're just swapping the engine, not the car.

### Visual: What Changes vs What Stays

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI-OS TERMINAL                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  > what is 2+2                                            │  │
│  │  + add user authentication                                │  │
│  │  ! pytest tests/                                          │  │
│  │  @ examples/tdd_macro.py goal="auth"                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                     [UNCHANGED - cli.py]                        │
│                              │                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    commands.py                             │  │
│  │   chat() | patch() | run() | macro()                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                     [KEEP - just rewire]                        │
│                              │                                  │
├──────────────────────────────┼──────────────────────────────────┤
│         BEFORE (delete)      │         AFTER (new)              │
│  ┌─────────────────────┐     │     ┌─────────────────────┐      │
│  │     chat.py         │     │     │   orchestrator.py   │      │
│  │   OpenRouter API    │ ──► │     │   Claude Code CLI   │      │
│  │   HTTP/SSE stream   │     │     │   subprocess mgmt   │      │
│  └─────────────────────┘     │     └─────────────────────┘      │
│  ┌─────────────────────┐     │              │                   │
│  │     patch.py        │     │              ▼                   │
│  │   XML parsing       │ ──► │     ┌─────────────────────┐      │
│  │   patch_strategies/ │     │     │   claude -p "..."   │      │
│  └─────────────────────┘     │     │   (uses Edit tool)  │      │
│                              │     └─────────────────────┘      │
├──────────────────────────────┴──────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    macro_runner.py                         │  │
│  │   main(ctx, **kwargs) contract stays identical            │  │
│  │   ah.chat() | ah.patch() | ah.shell() | ah.approve()      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                     [KEEP - same API]                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    NEW: spawn/join                         │  │
│  │   ah.spawn() | ah.join() | ah.gather()                    │  │
│  │   (parallel Claude Code processes)                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                     [ADD - new capability]                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Summary:**
- Terminal UI: **UNCHANGED**
- Commands (`>`, `+`, `!`, `@`): **UNCHANGED** (just rewired internally)
- Macro contract (`main(ctx, **kwargs)`): **UNCHANGED**
- Macro helpers (`ah.chat`, `ah.patch`, etc.): **UNCHANGED API** (new implementation)
- OpenRouter integration: **DELETED** (replaced by Claude Code subprocess)
- XML patch parsing: **DELETED** (replaced by Claude Code Edit tool)
- Parallel execution: **NEW** (`ah.spawn()`, `ah.join()`, `ah.gather()`)

---

## Design Decisions

### Decision 1: Keep the Macro Model

The macro model is AI-OS's core value proposition. A macro is:
- A Python file with `main(ctx, **kwargs)`
- Imports `ai_os as ah` (or similar)
- Has explicit human checkpoints via `ah.approve()`
- Runs in a visible REPL

This stays.

### Decision 2: Claude Code as Black Box

We treat Claude Code as an opaque executor. We don't:
- Intercept its internal tool calls
- Try to share context between parent and child Claude sessions
- Depend on its internal state

This keeps the interface clean and stable.

### Decision 3: File System as Shared State

When Claude Code edits a file, subsequent macro operations see that edit. The file system is our coordination mechanism:
- Agents write to files
- Other agents read those files
- No complex message passing needed

### Decision 4: Explicit Over Implicit Parallelism

We don't try to auto-parallelize. The macro author explicitly calls:
```python
agents = [ah.spawn(...) for ...]
results = ah.join(agents)
```

This makes the parallelism visible and debuggable.

### Decision 5: Human Checkpoints Are Required

Every macro must have approval checkpoints. This isn't optional. The whole point is human oversight.

---

## Open Questions

### Q1: Context Sharing

When we spawn a Claude Code sub-agent, should it see the parent conversation? Options:

1. **No sharing** — Each agent starts fresh. Simple but loses context.
2. **File-based context** — Write conversation to a file, tell agent to read it. Explicit but verbose.
3. **Prompt injection** — Include relevant context in the spawn prompt. Flexible but requires macro author effort.

**Current leaning:** Option 3. The macro author knows what context matters.

### Q2: Error Handling

When a spawned Claude Code process fails, what happens?

1. **Propagate exception** — Macro crashes. Simple but harsh.
2. **Return error object** — Macro can handle. More flexible.
3. **Retry logic** — Automatic retry with backoff. Most robust.

**Current leaning:** Option 2 with optional retry wrapper.

### Q3: Output Parsing

Claude Code outputs text. How do we structure that for the macro?

1. **Raw text** — Macro parses itself. Maximum flexibility.
2. **JSON mode** — Ask Claude to output JSON, we parse. Structured but can fail.
3. **File-based** — Tell Claude to write to a file, we read it. Most reliable.

**Current leaning:** All three, with helpers for each pattern.

### Q4: Resource Limits

How many parallel agents can we spawn?

- API rate limits
- Local CPU/memory
- Cost considerations

**Current leaning:** Configurable limit, default to 5.

---

## Success Criteria

AI-OS v2 is successful if:

1. **Simpler codebase** — Under 1000 lines of core code
2. **Real parallelism** — `spawn()` actually runs in parallel
3. **No XML parsing** — Zero custom format parsing
4. **Existing macros port easily** — TDD macro works with minimal changes
5. **New patterns enabled** — Shader evolution example works
6. **Human oversight preserved** — Approval checkpoints still required
7. **REPL works** — Interactive terminal experience maintained

---

## Next Steps

1. **Analyze current state** — Document what to keep, what to discard (02_current_state_analysis.md)
2. **Design Claude Code integration** — Detailed interface spec (03_claude_code_integration.md)
3. **Design the DSL** — Full API specification (04_python_dsl_design.md)
4. **Implementation roadmap** — Phased build plan (05_implementation_roadmap.md)

---

## Appendix: The Ralph Loop

The user mentioned a "ralph loop" pattern:

```bash
#!/bin/bash
cd "$(dirname "$0")"
for i in {1..20}; do
  claude -p --model opus --dangerously-skip-permissions < agent_drive.txt
done
```

This is a simple driver that:
1. Runs Claude Code with a prompt from `agent_drive.txt`
2. Loops 20 times
3. Each iteration sees the file system state from prior iterations

This is essentially a primitive agentic loop. Our macro system generalizes this with:
- Programmatic prompt construction
- Conditional branching
- Parallel execution
- Human checkpoints
- Structured output handling

The ralph loop pattern validates that "just calling Claude Code repeatedly" is a viable execution model.
