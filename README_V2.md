# AI-OS v2: Claude Code Native Agentic Macros

**AI-OS** is a Python framework for writing composable, debuggable agentic workflows with human-in-the-loop control.

Version 2.0 is a complete architectural redesign - we now use Claude Code as our execution runtime, giving you battle-tested tooling infrastructure while maintaining the macro-based workflow model that makes AI-OS unique.

## Key Features

- **True Parallel Execution** - `gather()` runs multiple prompts concurrently
- **Native Tool Use** - Inherits all Claude Code capabilities (Edit, WebSearch, Grep, etc.)
- **Human Oversight** - Built-in approval checkpoints for safe agentic workflows
- **Clean Python DSL** - Write macros that read like executable pseudocode
- **Battle-Tested Runtime** - Leverages Claude Code's production-ready infrastructure

## Quick Start

```bash
# Install dependencies
npm install -g @anthropic-ai/claude-code
uv sync  # or: pip install -e .

# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Launch AI-OS shell
uv run aios

# Run a macro
/macro examples/tree_of_thought.py question="How should we architect auth?"
```

## Writing Your First Macro

```python
# my_macro.py
import ai_os as ai

def main(ctx, **kwargs):
    """Simple macro demonstrating parallel execution."""

    # Get user input
    topic = kwargs.get("topic", "AI agents")

    # Generate multiple perspectives in parallel
    ai.log(f"[bold]Analyzing: {topic}[/bold]")

    results = ai.gather(
        f"What are the pros of {topic}?",
        f"What are the cons of {topic}?",
        f"What are alternatives to {topic}?",
        model="haiku"  # Fast and cheap for simple tasks
    )

    # Display results
    ai.log("\n[green]Pros:[/green]")
    ai.log(results[0])

    ai.log("\n[red]Cons:[/red]")
    ai.log(results[1])

    ai.log("\n[cyan]Alternatives:[/cyan]")
    ai.log(results[2])

    # Show cost
    cost = ai.get_cost()
    ai.log(f"\n[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")
```

Run it:
```bash
/macro my_macro.py topic="microservices"
```

## DSL API Reference

### Output

```python
ai.log(message)              # Print to console
ai.status(message)           # Show spinner (context manager)
```

### LLM Operations

```python
ai.chat(prompt, model="sonnet")        # Chat with Claude
ai.chat_json(prompt)                   # Get JSON response
ai.vision(prompt, image)               # Analyze image
ai.edit(instruction, file=None)        # Have Claude edit files
```

### Parallel Execution

```python
# Simple parallel - use this most of the time
results = ai.gather("prompt 1", "prompt 2", "prompt 3")

# Advanced async pattern
async def parallel():
    return await asyncio.gather(
        ai.chat("one", async_=True),
        ai.chat("two", async_=True)
    )

results = asyncio.run(parallel())
```

### File Operations

```python
ai.read(path)                # Read file
ai.write(path, content)      # Write file
ai.exists(path)              # Check if exists
ai.glob(pattern)             # Find files
```

### Shell

```python
ai.shell(cmd)                       # Run and print output
exit_code = ai.shell(cmd)           # Get exit code
output = ai.shell(cmd, capture=True)  # Capture stdout
```

### Human Interaction

```python
ai.approve(message)                      # Y/N prompt
ai.ask(question, choices=["A", "B"])     # Multiple choice
ai.confirm_changes(files)                # Show diffs
```

### Context & Utilities

```python
ai.get_var(name, default=None)  # Get CLI argument
ai.set_var(name, value)         # Set context variable
ai.get_cost()                   # Get token costs
ai.timestamp()                  # ISO timestamp
ai.random_id()                  # Random hex ID
```

## Example Macros

### Test-Driven Development

```python
import ai_os as ai

def main(ctx, **kwargs):
    goal = kwargs.get("goal")

    # Generate test
    ai.edit(f"Create a pytest test for: {goal}")

    test_files = ai.glob("tests/test_*.py")
    if not test_files:
        ai.log("[red]No test created[/red]")
        return

    # Implementation loop
    for attempt in range(5):
        ai.edit(f"Write code to pass tests in {test_files[-1]}")

        if ai.shell(f"pytest {test_files[-1]}") == 0:
            ai.log("[green]Tests pass![/green]")
            return

        if not ai.approve("Retry?"):
            break
```

### Tree of Thought Reasoning

```python
import ai_os as ai

def main(ctx, **kwargs):
    question = kwargs.get("question")

    # Generate initial thoughts in parallel
    thoughts = ai.gather(
        f"Thought 1 on: {question}",
        f"Thought 2 on: {question}",
        f"Thought 3 on: {question}",
        f"Thought 4 on: {question}",
        f"Thought 5 on: {question}",
        model="haiku"
    )

    # Branch each thought
    branch_prompts = []
    for thought in thoughts:
        for i in range(3):
            branch_prompts.append(
                f"Extend this thought:\n{thought}\n\nDirection {i+1}:"
            )

    branches = ai.gather(*branch_prompts, model="haiku")

    # Synthesize
    all_thoughts = thoughts + branches
    numbered = "\n".join(f"{i+1}. {t[:300]}" for i, t in enumerate(all_thoughts))

    synthesis = ai.chat(f"""
        Question: {question}
        Thoughts:
        {numbered}

        Synthesize into a comprehensive answer:
    """, model="sonnet")

    ai.log("[bold green]Answer:[/bold green]")
    ai.log(synthesis)

    cost = ai.get_cost()
    ai.log(f"\n[dim]Cost: ${cost['total_cost_usd']:.4f}[/dim]")
```

## Migration from v1

If you have existing v1 macros, see [MIGRATION_V2.md](MIGRATION_V2.md) for a complete guide.

Key changes:
- ✅ Use Claude Code instead of OpenRouter
- ✅ Replace `ah.patch()` with `ah.edit()`
- ✅ Use `ah.gather()` for parallel execution (now works!)
- ✅ Add human checkpoints with `ah.approve()`

## Architecture

AI-OS v2 treats Claude Code as its execution substrate:

```
┌────────────────────────────────────────────┐
│          AI-OS Terminal (REPL)             │
│    > chat  + patch  ! shell  @ macro       │
└───────────────────┬────────────────────────┘
                    │
┌───────────────────┴────────────────────────┐
│         AI-OS Python DSL                   │
│    log() chat() gather() edit() approve()  │
└───────────────────┬────────────────────────┘
                    │
┌───────────────────┴────────────────────────┐
│      ClaudeOrchestrator                    │
│  Spawns & manages claude -p subprocesses   │
└───────────────────┬────────────────────────┘
                    │
┌───────────────────┴────────────────────────┐
│          Claude Code Runtime               │
│    Read Edit Write Bash Task Grep etc.     │
└────────────────────────────────────────────┘
```

We removed ~1200 lines of infrastructure code by delegating to Claude Code.

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest tests/

# Type checking
uv run pyright ai_os/

# Run a macro
uv run aios
> @examples/tree_of_thought.py question="test"
```

## Project Status

**v2.0.0** (January 2026)
- ✅ Core orchestrator complete
- ✅ DSL implementation complete
- ✅ Parallel execution working
- ✅ Example macros updated
- ✅ Migration guide written
- ⏳ Testing in progress
- ⏳ Documentation complete

## License

MIT

## Credits

Built on [Claude Code](https://github.com/anthropics/claude-code) by Anthropic.
