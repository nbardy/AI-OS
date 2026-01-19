# Python DSL Design: AI-OS Macro Language v2

**Date:** 2026-01-17
**Status:** Design Phase
**Purpose:** Define the complete API for macro authors

---

## Design Philosophy

The AI-OS DSL should be:

1. **Pythonic** — Feels like normal Python, not a weird custom language
2. **Explicit** — No magic, every operation is visible
3. **Composable** — Small functions that combine well
4. **Safe by default** — Human checkpoints are encouraged, not optional
5. **Debuggable** — Easy to understand what went wrong

The guiding principle: **A macro should read like executable pseudocode.**

---

## Import Convention

```python
import ai_os as ai

# Or for explicit imports:
from ai_os import chat, spawn, join, shell, approve, log
```

The `ai` namespace is short, memorable, and clearly indicates AI operations.

**Alternative:** Keep `ah` for backwards compatibility:
```python
import ai_os as ah  # "AI Helper" - matches v1
```

---

## Core API Reference

### Output Functions

#### `ai.log(message: str) -> None`

Print a message to the console.

```python
ai.log("Starting shader generation...")
ai.log("[bold green]Success![/bold green]")  # Rich markup supported
```

**Implementation:** Direct print to console via Rich.

---

#### `ai.status(message: str) -> ContextManager`

Show a spinner/status indicator while code runs.

```python
with ai.status("Generating shaders..."):
    # Long-running operation
    shaders = generate_shaders()
```

**Implementation:** `rich.console.status` context manager.

---

### Human Interaction

#### `ai.approve(message: str) -> bool`

Ask the user for Y/N approval. **Essential for safe agentic workflows.**

```python
if ai.approve("Apply these changes to production?"):
    deploy()
else:
    ai.log("Deployment cancelled")
```

**Implementation:** `rich.prompt.Confirm.ask()`

---

#### `ai.ask(question: str, choices: list[str] = None) -> str`

Ask the user a question. Optionally provide choices.

```python
# Open-ended
name = ai.ask("What should we name this shader?")

# Multiple choice
approach = ai.ask(
    "Which technique should we try?",
    choices=["raymarching", "fractals", "noise", "all"]
)
```

**Implementation:** `rich.prompt.Prompt.ask()` with optional choices.

---

#### `ai.confirm_changes(files: list[str]) -> bool`

Show file diffs and ask for approval. **Use before destructive changes.**

```python
# After generating changes
if ai.confirm_changes(["src/auth.py", "tests/test_auth.py"]):
    ai.shell("git add -A && git commit -m 'Add auth'")
```

**Implementation:** Show git diff for each file, then prompt.

---

### LLM Operations

#### `ai.chat(prompt: str, **kwargs) -> str`

Send a prompt to Claude and get a text response.

```python
# Basic usage
response = ai.chat("Explain how raymarching works")

# With context files
response = ai.chat(
    "Review this code for bugs",
    context=["src/auth.py", "src/utils.py"]
)

# With specific model
response = ai.chat(
    "Complex architectural decision",
    model="opus"
)

# For quick tasks
response = ai.chat("Is this JSON valid?", model="haiku")
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | str | required | The prompt to send |
| `context` | list[str] | None | Files to include as context |
| `model` | str | "sonnet" | Model: "haiku", "sonnet", "opus" |
| `temperature` | float | None | Override temperature |

**Returns:** The assistant's response as a string.

**Implementation:** Calls `claude -p` with appropriate flags.

---

#### `ai.chat_json(prompt: str, schema: Type[BaseModel] = None, **kwargs) -> Any`

Get structured JSON output from Claude.

```python
from pydantic import BaseModel
from typing import List

class ShaderPlan(BaseModel):
    approaches: List[str]
    techniques: List[str]

# With Pydantic validation
plan = ai.chat_json(
    "Plan 5 shader approaches. Output as JSON with 'approaches' and 'techniques' arrays.",
    schema=ShaderPlan
)

# Without validation (returns dict)
data = ai.chat_json("Output a JSON object with name and score fields")
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | str | required | The prompt (should request JSON) |
| `schema` | Type[BaseModel] | None | Pydantic model for validation |
| `**kwargs` | | | Same as `ai.chat()` |

**Returns:** Parsed JSON as dict, or validated Pydantic model.

**Implementation:** Calls `ai.chat()`, then parses JSON from response.

---

#### `ai.vision(prompt: str, image: str, **kwargs) -> str`

Analyze an image with Claude.

```python
# Score a rendered shader
score = ai.vision(
    "Rate this shader render 1-10 on visual appeal. Output just the number.",
    image="renders/shader_01.png"
)

# Detailed analysis
analysis = ai.vision(
    "Describe what mathematical patterns you see in this fractal",
    image="renders/fractal.png",
    model="opus"  # Use opus for complex analysis
)
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | str | required | Analysis prompt |
| `image` | str | required | Path to image file |
| `**kwargs` | | | Same as `ai.chat()` |

**Returns:** Claude's analysis as a string.

**Implementation:** Claude Code's Read tool can read images directly.

---

### Parallel Execution

Use `async_=True` flag with `asyncio.gather()` for parallel execution. Simple and Pythonic.

#### Async Flag Pattern

```python
import asyncio

async def parallel_work():
    # Run 5 prompts in parallel
    results = await asyncio.gather(
        ah.chat("prompt 1", async_=True),
        ah.chat("prompt 2", async_=True),
        ah.chat("prompt 3", async_=True),
        ah.chat("prompt 4", async_=True),
        ah.chat("prompt 5", async_=True),
    )
    return results

# In your macro's main():
def main(ctx, **kwargs):
    results = asyncio.run(parallel_work())
```

#### Example: Parallel Shader Generation

```python
import asyncio
import ai_os.core.macro_helpers as ah

async def generate_shaders(techniques):
    """Generate multiple shaders in parallel."""
    tasks = [
        ah.chat(f"Write a GLSL shader using {tech}. Output only code.", async_=True)
        for tech in techniques
    ]
    return await asyncio.gather(*tasks)

def main(ctx, **kwargs):
    techniques = ["perlin noise", "voronoi", "fractals", "raymarching", "reaction-diffusion"]

    ah.log("Generating 5 shaders in parallel...")
    shaders = asyncio.run(generate_shaders(techniques))

    for i, shader in enumerate(shaders):
        ah.write(f"shaders/candidate_{i}.glsl", shader)
        ah.log(f"Wrote shader {i}")
```

**How it works:**
- `async_=True` makes `ah.chat()` return a coroutine instead of blocking
- `asyncio.gather()` runs them concurrently
- Under the hood: each call spawns a `claude -p` subprocess
- `asyncio.run()` in main() drives the event loop

**Works with all LLM functions:**
```python
# All of these support async_=True
await ah.chat(prompt, async_=True)
await ah.chat_json(prompt, async_=True)
await ah.vision(prompt, image, async_=True)
await ah.edit(instruction, async_=True)
```

---

### File Operations

#### `ai.read(path: str) -> str`

Read a file's contents.

```python
shader_code = ai.read("shaders/best.glsl")
config = ai.read("config.json")
```

**Implementation:** Direct file read (not through Claude).

---

#### `ai.write(path: str, content: str) -> None`

Write content to a file.

```python
ai.write("output/result.txt", "Final score: 9.5")
ai.write("shaders/final.glsl", shader_code)
```

**Implementation:** Direct file write, creates parent directories.

---

#### `ai.edit(instruction: str, file: str = None) -> bool`

Have Claude edit a file intelligently.

```python
# Edit specific file
ai.edit("Add error handling to the login function", file="src/auth.py")

# Let Claude decide what to edit
ai.edit("Fix all type errors in the codebase")
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `instruction` | str | required | What to do |
| `file` | str | None | Specific file to edit |

**Returns:** True if successful.

**Implementation:** Calls Claude Code with edit-focused prompt.

---

#### `ai.exists(path: str) -> bool`

Check if a file exists.

```python
if ai.exists("shaders/best.glsl"):
    best_shader = ai.read("shaders/best.glsl")
```

**Implementation:** `os.path.exists()`

---

#### `ai.glob(pattern: str) -> list[str]`

Find files matching a pattern.

```python
all_shaders = ai.glob("shaders/*.glsl")
all_tests = ai.glob("tests/**/test_*.py")
```

**Implementation:** `glob.glob()` with recursive support.

---

### Shell Operations

#### `ai.shell(command: str, capture: bool = False, check: bool = False) -> Any`

Execute a shell command.

```python
# Run and show output (returns exit code)
exit_code = ai.shell("pytest tests/")

# Capture output (returns stdout)
output = ai.shell("git status --short", capture=True)

# Check for errors (raises on non-zero exit)
ai.shell("npm run build", check=True)
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `command` | str | required | Shell command |
| `capture` | bool | False | If True, return stdout instead of exit code |
| `check` | bool | False | If True, raise on non-zero exit |

**Returns:** Exit code (int) or stdout (str) if capture=True.

**Implementation:** `subprocess.run()` with shell=True.

---

#### `ai.run(command: str, **kwargs) -> subprocess.CompletedProcess`

Low-level shell access with full control.

```python
result = ai.run("glslviewer shader.glsl -s 5", timeout=30)
if result.returncode != 0:
    ai.log(f"Render failed: {result.stderr}")
```

**Implementation:** `subprocess.run()` wrapper.

---

### Context and State

#### `ai.get_var(name: str, default: Any = None) -> Any`

Get a variable passed via command line.

```python
# Macro invoked as: /macro shader.py iterations=10 style="abstract"
iterations = ai.get_var("iterations", default=5)
style = ai.get_var("style", default="geometric")
```

**Implementation:** Access from `ctx['vars']` dict.

---

#### `ai.set_var(name: str, value: Any) -> None`

Set a context variable (accessible to subsequent operations).

```python
ai.set_var("best_score", 9.5)
# ... later ...
best = ai.get_var("best_score")
```

**Implementation:** Store in `ctx` dict.

---

#### `ai.get_cost() -> dict`

Get cumulative cost for this macro run.

```python
cost = ai.get_cost()
ai.log(f"Total cost so far: ${cost['total_cost_usd']:.4f}")
ai.log(f"Tokens used: {cost['input_tokens']} in, {cost['output_tokens']} out")
```

**Returns:** Dict with `input_tokens`, `output_tokens`, `total_cost_usd`.

---

### Utility Functions

#### `ai.sleep(seconds: float) -> None`

Pause execution.

```python
ai.log("Waiting for render to complete...")
ai.sleep(5)
```

**Implementation:** `time.sleep()`

---

#### `ai.timestamp() -> str`

Get current timestamp (useful for filenames).

```python
output_file = f"renders/shader_{ai.timestamp()}.png"
```

**Returns:** ISO format timestamp: `2026-01-17T14-30-45`

---

#### `ai.random_id(length: int = 8) -> str`

Generate a random ID (useful for unique filenames).

```python
shader_id = ai.random_id()
ai.write(f"shaders/{shader_id}.glsl", shader_code)
```

**Implementation:** `uuid.uuid4().hex[:length]`

---

## Complete API Summary

```python
# Output
ai.log(message)                    # Print to console
ai.status(message)                 # Context manager for spinner

# Human Interaction
ai.approve(message) -> bool        # Y/N prompt
ai.ask(question, choices?) -> str  # Text input or choice
ai.confirm_changes(files) -> bool  # Show diffs, ask approval

# LLM Operations
ai.chat(prompt, **kwargs) -> str           # Text completion
ai.chat_json(prompt, schema?, **kwargs)    # JSON completion
ai.vision(prompt, image, **kwargs) -> str  # Image analysis

# Parallel Execution (use async_=True with asyncio.gather)
ai.chat(prompt, async_=True) -> Coroutine  # Returns awaitable
# Then: await asyncio.gather(ai.chat(p1, async_=True), ai.chat(p2, async_=True), ...)

# File Operations
ai.read(path) -> str               # Read file
ai.write(path, content)            # Write file
ai.edit(instruction, file?)        # AI edit file
ai.exists(path) -> bool            # Check existence
ai.glob(pattern) -> list[str]      # Find files

# Shell Operations
ai.shell(command, capture?, check?) -> Any  # Run command
ai.run(command, **kwargs) -> CompletedProcess  # Low-level

# Context and State
ai.get_var(name, default?) -> Any  # Get CLI arg
ai.set_var(name, value)            # Set context var
ai.get_cost() -> dict              # Get cost info

# Utilities
ai.sleep(seconds)                  # Pause
ai.timestamp() -> str              # Current time
ai.random_id(length?) -> str       # Random ID
```

---

## Macro Contract

Every macro must:

1. Be a `.py` file
2. Define `main(ctx, **kwargs)`
3. Use the `ai` namespace for operations

```python
# examples/my_macro.py
import ai_os as ai

def main(ctx, **kwargs):
    """
    Macro docstring - shown when user runs /help macro_name
    """
    goal = kwargs.get("goal", "default goal")

    # ... macro logic ...

    ai.log("Done!")
```

**Invocation:**
```
/macro examples/my_macro.py goal="create something cool"
```

---

## Example Macros

### Example 1: Simple TDD Loop

```python
# examples/tdd.py
import ai_os as ai

def main(ctx, **kwargs):
    """Test-driven development loop."""
    goal = kwargs.get("goal")
    if not goal:
        ai.log("Usage: /macro examples/tdd.py goal='...'")
        return

    # Generate test
    ai.log("[bold]Phase 1: Generate test[/bold]")
    ai.chat(f"Write a pytest test file for: {goal}")

    test_file = ai.glob("tests/test_*.py")[-1]  # Most recent
    if not ai.approve(f"Test file created: {test_file}. Continue?"):
        return

    # Implementation loop
    ai.log("[bold]Phase 2: Implement until tests pass[/bold]")
    max_attempts = 5

    for attempt in range(max_attempts):
        ai.log(f"Attempt {attempt + 1}/{max_attempts}")

        # Generate implementation
        ai.edit(f"Implement code to pass the tests in {test_file}")

        # Run tests
        exit_code = ai.shell(f"pytest {test_file} -v")

        if exit_code == 0:
            ai.log("[bold green]Tests pass! Done.[/bold green]")
            return

        ai.log("[yellow]Tests failed. Retrying...[/yellow]")

        if not ai.approve("Continue trying?"):
            return

    ai.log("[bold red]Max attempts reached.[/bold red]")
```

---

### Example 2: Parallel Shader Evolution

```python
# examples/shader_evolution.py
import ai_os as ai
import json

def main(ctx, **kwargs):
    """
    Evolutionary shader generation with parallel exploration.

    Usage: /macro examples/shader_evolution.py goal="aurora borealis" iterations=5
    """
    goal = kwargs.get("goal", "beautiful generative shader")
    iterations = int(kwargs.get("iterations", 5))
    num_candidates = int(kwargs.get("candidates", 5))

    best_shader = None
    best_score = 0
    history = []

    for round_num in range(iterations):
        ai.log(f"\n[bold cyan]═══ Round {round_num + 1}/{iterations} ═══[/bold cyan]")

        # Step 1: Plan diverse approaches
        with ai.status("Planning approaches..."):
            plan = ai.chat_json(f"""
                Goal: {goal}
                Best score so far: {best_score}
                Previous critiques: {json.dumps(history[-3:])}

                Plan {num_candidates} VERY DIFFERENT shader approaches.
                Each should use a different mathematical technique.

                Output JSON: {{"approaches": ["approach 1 description", ...]}}
            """)

        approaches = plan.get("approaches", [f"Approach {i}" for i in range(num_candidates)])

        # Step 2: Spawn parallel shader writers
        ai.log(f"Spawning {len(approaches)} shader agents...")
        agents = []
        for i, approach in enumerate(approaches):
            agent = ai.spawn(
                f"""
                Write a GLSL fragment shader implementing:
                {approach}

                Requirements:
                - uniform float u_time for animation
                - uniform vec2 u_resolution for aspect ratio
                - Output to gl_FragColor
                - Be mathematically interesting

                Output ONLY the shader code, no explanation.
                """,
                output_file=f"shaders/candidate_{i}.glsl"
            )
            agents.append(agent)

        # Step 3: Wait for all shaders
        with ai.status("Generating shaders..."):
            results = ai.join(agents)

        successful = sum(1 for r in results if r.success)
        ai.log(f"Generated {successful}/{len(agents)} shaders")

        # Step 4: Render all shaders
        ai.log("Rendering...")
        for i in range(num_candidates):
            if ai.exists(f"shaders/candidate_{i}.glsl"):
                ai.shell(f"glslviewer shaders/candidate_{i}.glsl -s 5 -o renders/candidate_{i}.png")

        # Step 5: Score renders with vision
        ai.log("Scoring renders...")
        scores = []
        for i in range(num_candidates):
            render_path = f"renders/candidate_{i}.png"
            if not ai.exists(render_path):
                continue

            score_data = ai.chat_json(f"""
                Score this shader 1-10 on:
                - Visual complexity
                - Mathematical elegance
                - Aesthetic beauty
                - How well it matches: {goal}

                Be critical. Most are 4-6.

                Output JSON: {{"score": N, "reason": "brief"}}
            """, context=[render_path])

            scores.append((i, score_data.get("score", 0), score_data.get("reason", "")))

        if not scores:
            ai.log("[red]No successful renders this round[/red]")
            continue

        # Step 6: Pick winner
        scores.sort(key=lambda x: x[1], reverse=True)
        winner_idx, winner_score, reason = scores[0]

        ai.log(f"Winner: candidate_{winner_idx} (score: {winner_score})")
        ai.log(f"Reason: {reason}")

        if winner_score > best_score:
            best_score = winner_score
            best_shader = ai.read(f"shaders/candidate_{winner_idx}.glsl")
            ai.shell(f"cp shaders/candidate_{winner_idx}.glsl shaders/best.glsl")
            ai.shell(f"cp renders/candidate_{winner_idx}.png renders/best.png")

        # Step 7: Critique for next round
        critique = ai.chat(f"""
            Analyze this shader critically:
            - What works?
            - What's missing?
            - What could be improved?

            Shader code:
            {best_shader}
        """)
        history.append({"round": round_num + 1, "score": best_score, "critique": critique[:500]})

        # Checkpoint
        if (round_num + 1) % 2 == 0:
            cost = ai.get_cost()
            ai.log(f"Cost so far: ${cost['total_cost_usd']:.4f}")
            if not ai.approve(f"Continue? Best score: {best_score}"):
                break

    # Final report
    ai.log(f"\n[bold green]═══ Evolution Complete ═══[/bold green]")
    ai.log(f"Final best score: {best_score}")
    ai.log(f"Best shader: shaders/best.glsl")
    ai.log(f"Best render: renders/best.png")

    cost = ai.get_cost()
    ai.log(f"Total cost: ${cost['total_cost_usd']:.4f}")
```

---

### Example 3: Tree of Thought

```python
# examples/tree_of_thought.py
import ai_os as ai

def main(ctx, **kwargs):
    """
    Tree of Thought reasoning: Generate multiple thought branches,
    then synthesize into a final answer.

    Usage: /macro examples/tree_of_thought.py question="How should we architect the auth system?"
    """
    question = kwargs.get("question")
    if not question:
        ai.log("Usage: /macro examples/tree_of_thought.py question='...'")
        return

    num_initial = int(kwargs.get("thoughts", 5))
    branches_per = int(kwargs.get("branches", 3))

    ai.log(f"[bold]Question:[/bold] {question}\n")

    # Phase 1: Generate initial thoughts
    ai.log(f"[cyan]Phase 1: Generating {num_initial} initial thoughts...[/cyan]")

    initial_prompts = [
        f"Thought {i+1} on: {question}\nProvide a unique perspective or approach."
        for i in range(num_initial)
    ]

    with ai.status("Generating initial thoughts..."):
        initial_thoughts = ai.gather(*initial_prompts, model="haiku")

    for i, thought in enumerate(initial_thoughts):
        ai.log(f"\n[dim]Thought {i+1}:[/dim] {thought[:200]}...")

    # Phase 2: Branch each thought
    ai.log(f"\n[cyan]Phase 2: Branching into {num_initial * branches_per} sub-thoughts...[/cyan]")

    branch_agents = []
    for i, thought in enumerate(initial_thoughts):
        for j in range(branches_per):
            agent = ai.spawn(f"""
                Given this initial thought:
                {thought}

                Extend it in direction {j+1}/{branches_per}.
                Explore implications, refine details, or challenge assumptions.
            """, model="haiku")
            branch_agents.append((i, j, agent))

    with ai.status("Generating branches..."):
        all_agents = [a for _, _, a in branch_agents]
        branch_results = ai.join(all_agents)

    all_thoughts = initial_thoughts.copy()
    for (i, j, _), result in zip(branch_agents, branch_results):
        if result.success:
            all_thoughts.append(result.result)

    ai.log(f"Generated {len(all_thoughts)} total thoughts")

    # Phase 3: Synthesize
    ai.log(f"\n[cyan]Phase 3: Synthesizing final answer...[/cyan]")

    numbered_thoughts = "\n\n".join(
        f"[{i+1}] {t[:500]}" for i, t in enumerate(all_thoughts)
    )

    with ai.status("Synthesizing..."):
        synthesis = ai.chat(f"""
            Question: {question}

            Here are {len(all_thoughts)} different thoughts and perspectives:

            {numbered_thoughts}

            Synthesize these into a comprehensive, well-reasoned answer.
            Identify the strongest insights and address any contradictions.
            Be thorough but concise.
        """, model="sonnet")

    ai.log(f"\n[bold green]═══ Final Answer ═══[/bold green]\n")
    ai.log(synthesis)

    cost = ai.get_cost()
    ai.log(f"\n[dim]Cost: ${cost['total_cost_usd']:.4f}[/dim]")
```

---

## Backwards Compatibility

### Migration from v1

| v1 API | v2 API | Notes |
|--------|--------|-------|
| `ah.log(msg)` | `ah.log(msg)` | Same |
| `ah.chat(prompt)` | `ah.chat(prompt)` | Same (now calls Claude Code) |
| `ah.llm(prompt)` (broken) | `ah.chat(prompt, async_=True)` | Now works! |
| `ah.patch(plan)` | `ah.edit(instruction)` | Different semantics |
| `ah.shell(cmd)` | `ah.shell(cmd)` | Same |
| `ah.approve(msg)` | `ah.approve(msg)` | Same |
| `ah.get_var(name)` | `ah.get_var(name)` | Same |
| N/A | `ah.vision(prompt, image)` | New |
| N/A | `ah.read(path)` | New (direct file read) |
| N/A | `ah.write(path, content)` | New (direct file write) |

### Compatibility Shim

For gradual migration, provide an `ah` alias:

```python
# ai_os/__init__.py
from ai_os import macro_helpers as ah  # Legacy alias
```

---

## Error Handling

### Recommended Patterns

```python
# Pattern 1: Check return values
if not ai.edit("fix the bug"):
    ai.log("[red]Edit failed[/red]")
    return

# Pattern 2: Use check=True for shell
try:
    ai.shell("npm run build", check=True)
except subprocess.CalledProcessError as e:
    ai.log(f"Build failed: {e}")
    return

# Pattern 3: Handle agent failures
results = ai.join(agents)
failures = [r for r in results if not r.success]
if failures:
    ai.log(f"[yellow]{len(failures)} agents failed[/yellow]")
    for f in failures:
        ai.log(f"  Error: {f.error}")
```

### Built-in Safeguards

1. **Timeout on all Claude calls** — Default 600s, configurable
2. **Cost tracking** — Always know how much you're spending
3. **Human checkpoints** — `approve()` for critical operations
4. **File existence checks** — Before reading/writing

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIOS_MODEL` | "sonnet" | Default model |
| `AIOS_TIMEOUT` | 600 | Default timeout (seconds) |
| `AIOS_MAX_PARALLEL` | 5 | Max parallel agents |
| `AIOS_WORKING_DIR` | cwd | Working directory |

### Per-Macro Configuration

```python
# At start of macro
ai.config(
    model="opus",       # Default model for this macro
    timeout=1200,       # Longer timeout
    max_parallel=10     # More parallelism
)
```

---

## Testing Macros

### Unit Testing Pattern

```python
# tests/test_my_macro.py
import pytest
from unittest.mock import patch
import ai_os as ai

def test_my_macro_basic():
    """Test macro with mocked AI calls."""
    with patch.object(ai, 'chat', return_value="mocked response"):
        with patch.object(ai, 'approve', return_value=True):
            from examples.my_macro import main
            ctx = {'vars': {'goal': 'test goal'}}
            main(ctx, goal='test goal')
            # Assert expected behavior
```

### Integration Testing

```python
# Run with small model and limited iterations
/macro examples/shader_evolution.py goal="simple test" iterations=1 candidates=2
```

---

## Next Steps

This DSL design is complete. The final document (05_implementation_roadmap.md) will detail the phased implementation plan.
