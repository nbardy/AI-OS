# AI-OS v2 Migration Guide

## Overview

AI-OS v2 represents a fundamental architectural shift from OpenRouter-based execution to Claude Code native execution. This guide will help you migrate your macros and understand the new capabilities.

## What Changed

### Architecture
- **Before**: Custom XML patching on top of OpenRouter API
- **After**: Claude Code subprocess orchestration with native tool use

### Key Benefits
1. **Real parallel execution** - `gather()` and `async_=True` now work
2. **Better file editing** - Uses Claude Code's Edit tool instead of XML parsing
3. **Native tooling** - Inherits all Claude Code capabilities (WebSearch, Grep, etc.)
4. **Simpler codebase** - Removed ~1200 lines of infrastructure code
5. **More reliable** - Battle-tested Claude Code runtime

## Breaking Changes

### 1. No More OpenRouter

**Before (v1):**
```bash
export OPENROUTER_API_KEY=sk-or-...
```

**After (v2):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Also need Claude Code CLI installed:
```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Patch → Edit

The `ah.patch()` function is replaced by `ah.edit()`.

**Before (v1):**
```python
ah.patch("""
<plan>
  Add authentication to the app
</plan>
<code filename="auth.py">
...
</code>
""")
```

**After (v2):**
```python
ah.edit("Add authentication to the app")
# Claude Code decides what files to create/edit
```

The new API is more flexible - you describe what you want, Claude figures out how to do it.

### 3. Parallel Execution Now Works

**Before (v1):**
```python
# This didn't actually work - ah.llm() was not implemented
results = await asyncio.gather(
    ah.llm("prompt 1"),
    ah.llm("prompt 2")
)
```

**After (v2):**
```python
# Option 1: Use gather() (simplest)
results = ah.gather("prompt 1", "prompt 2", "prompt 3")

# Option 2: Use async_=True with asyncio
async def parallel():
    return await asyncio.gather(
        ah.chat("prompt 1", async_=True),
        ah.chat("prompt 2", async_=True)
    )

results = asyncio.run(parallel())
```

### 4. New DSL Functions

Several new functions are available:

```python
# New in v2
ah.status("Working...")  # Context manager for spinners
ah.ask("Choose:", choices=["A", "B"])  # Multiple choice prompts
ah.confirm_changes(files)  # Show diffs before applying
ah.glob("**/*.py")  # Find files
ah.timestamp()  # Get current timestamp
ah.random_id()  # Generate random ID
```

## Migration Steps

### Step 1: Update Environment

```bash
# Unset OpenRouter key
unset OPENROUTER_API_KEY

# Set Anthropic key
export ANTHROPIC_API_KEY=sk-ant-...

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

### Step 2: Update Dependencies

```bash
cd ai-os_2
uv sync  # or: pip install -e .
```

### Step 3: Update Your Macros

For each macro file:

1. **Replace patch with edit**:
   ```python
   # Before
   ah.patch(plan)

   # After
   ah.edit("Implement the plan: " + plan_description)
   ```

2. **Update parallel patterns**:
   ```python
   # Before (broken)
   results = await asyncio.gather(ah.llm(p) for p in prompts)

   # After (works!)
   results = ah.gather(*prompts)
   ```

3. **Add human checkpoints** (optional but recommended):
   ```python
   if not ah.approve("Continue with these changes?"):
       return
   ```

### Step 4: Test Your Macros

```bash
# Run your macro
/macro examples/your_macro.py

# Or from shell
uv run aios
> @examples/your_macro.py
```

## API Reference

### Unchanged Functions

These work exactly as before:

```python
ah.log(msg)              # Print to console
ah.chat(prompt)          # Chat with Claude
ah.shell(cmd)            # Run shell command
ah.approve(msg)          # Y/N prompt
ah.get_var(name)         # Get CLI argument
ah.set_var(name, value)  # Set context variable
ah.get_cost()            # Get token costs
ah.read(path)            # Read file
ah.write(path, content)  # Write file
ah.exists(path)          # Check file exists
```

### New Functions

```python
# Parallel execution
ah.gather(*prompts, model="haiku")  # Run prompts in parallel

# Async pattern
ah.chat(prompt, async_=True)  # Returns coroutine
ah.chat_json(prompt, async_=True)
ah.vision(prompt, image, async_=True)
ah.edit(instruction, async_=True)

# UI improvements
ah.status(msg)            # Spinner context manager
ah.ask(question, choices) # Multiple choice prompt
ah.confirm_changes(files) # Show diffs

# Utilities
ah.glob(pattern)         # Find files
ah.timestamp()           # ISO timestamp
ah.random_id(length=8)   # Random hex ID
```

### Changed Functions

```python
# v1: ah.patch(xml_plan)
# v2: ah.edit(instruction, file=None)
ah.edit("Add error handling to auth.py")
ah.edit("Fix all type errors", file="src/main.py")
```

## Example Migration

### Before (v1)

```python
# examples/old_tdd.py
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    goal = kwargs.get("goal")

    # Generate test
    test_plan = ah.chat(f"Write a test for: {goal}")
    ah.patch(test_plan)

    # Generate implementation
    impl_plan = ah.chat("Write code to pass the test")
    ah.patch(impl_plan)

    # Run tests
    ah.shell("pytest")
```

### After (v2)

```python
# examples/new_tdd.py
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    goal = kwargs.get("goal")

    # Generate test (Claude Code creates the file directly)
    ah.edit(f"Create a pytest test file for: {goal}")

    test_files = ah.glob("tests/test_*.py")
    if not test_files:
        ah.log("[red]No test file created[/red]")
        return

    # Human checkpoint
    if not ah.approve("Test created. Continue with implementation?"):
        return

    # Implementation loop
    for attempt in range(5):
        ah.log(f"[cyan]Attempt {attempt + 1}/5[/cyan]")

        # Generate implementation
        ah.edit(f"Write code to pass tests in {test_files[-1]}")

        # Run tests
        exit_code = ah.shell(f"pytest {test_files[-1]} -v")

        if exit_code == 0:
            ah.log("[bold green]Tests pass![/bold green]")
            cost = ah.get_cost()
            ah.log(f"[dim]Cost: ${cost['total_cost_usd']:.4f}[/dim]")
            return

        if not ah.approve("Retry?"):
            break

    ah.log("[red]Max attempts reached[/red]")
```

### Key Improvements

1. **No XML parsing** - Just tell Claude what to do
2. **Human checkpoints** - User can abort at any point
3. **Better error handling** - Loop with retry logic
4. **Cost tracking** - Show final cost
5. **Simpler code** - Focus on logic, not format

## Troubleshooting

### "Claude Code not found"

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Or use npx (no install needed)
# The orchestrator will try this automatically
```

### "API key not set"

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Add to ~/.bashrc or ~/.zshrc for persistence
```

### "Imports not working"

Make sure you're importing from the right place:

```python
# Correct
import ai_os.core.macro_helpers as ah

# Also works (new style)
import ai_os as ai
ai.chat("hello")
```

### "async_=True not working"

Make sure you're using it correctly:

```python
# Wrong - returns coroutine, doesn't execute
result = ah.chat("hello", async_=True)
print(result)  # <coroutine object>

# Correct - use with asyncio.gather
async def run():
    results = await asyncio.gather(
        ah.chat("one", async_=True),
        ah.chat("two", async_=True)
    )
    return results

results = asyncio.run(run())

# Or use gather() (simpler)
results = ah.gather("one", "two")
```

## Getting Help

- GitHub Issues: https://github.com/yourusername/ai-os/issues
- Example macros: `examples/` directory
- Full DSL reference: See `agent_notes/04_python_dsl_design.md`

## Summary

The v2 migration is mostly straightforward:

1. ✅ Install Claude Code CLI
2. ✅ Set ANTHROPIC_API_KEY
3. ✅ Replace `ah.patch()` with `ah.edit()`
4. ✅ Use `ah.gather()` for parallel execution
5. ✅ Add human checkpoints with `ah.approve()`

Your macros will be more reliable, faster (true parallelism!), and easier to maintain.
