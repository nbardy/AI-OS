# AI-OS v2 API Evolution

**Date:** 2026-01-17
**Status:** Final API Design Complete

---

## API Evolution Summary

The AI-OS v2 API has evolved through several improvements, culminating in a clean, ergonomic interface.

---

## Version History

### v1 (Old - OpenRouter)

```python
import ai_os.core.macro_helpers as ah

# Basic operations
response = ah.chat("prompt")
ah.patch("edit instructions")  # XML-based patches

# No parallel execution support
# No vision support
```

### v2-alpha (Initial Migration)

```python
import ai_os.core.macro_helpers as ah
import asyncio

# New capabilities
response = ah.chat("prompt")
ah.edit("instructions")  # Claude Code Edit tool
analysis = ah.vision("prompt", "image.png")

# Parallel execution (complex async/await)
async def run():
    results = await asyncio.gather(
        ah.chat("prompt 1", async_=True),
        ah.chat("prompt 2", async_=True),
    )
    return results

results = asyncio.run(run())
```

### v2-beta (Clean Import)

```python
import ai_os as ai

# Cleaner top-level import
response = ai.chat("prompt")
ai.edit("instructions")
analysis = ai.vision("prompt", "image.png")

# Still complex async pattern
async def run():
    results = await asyncio.gather(
        ai.chat("prompt 1", async_=True),
        ai.chat("prompt 2", async_=True),
    )
    return results
```

### v2-final (gather() Convenience)

```python
import ai_os.core.macro_helpers as ah

# Simple parallel execution - no async/await needed!
results = ah.gather(
    "prompt 1",
    "prompt 2",
    "prompt 3",
    model="haiku"
)

# Still supports the clean import for single calls
import ai_os as ai
response = ai.chat("prompt")
```

---

## The `gather()` Function

The biggest UX improvement is the `gather()` convenience function:

### Before (v2-beta):
```python
import asyncio

async def parallel_thoughts():
    return await asyncio.gather(
        ah.chat("thought 1", async_=True),
        ah.chat("thought 2", async_=True),
        ah.chat("thought 3", async_=True),
    )

results = asyncio.run(parallel_thoughts())
```

### After (v2-final):
```python
# Just one line - no async/await needed!
results = ah.gather("thought 1", "thought 2", "thought 3", model="haiku")
```

---

## Complete v2 API Reference

### Two Import Styles

**Style 1: Macro Helpers (for complex macros)**
```python
import ai_os.core.macro_helpers as ah

# Best for macros that need gather()
results = ah.gather("p1", "p2", "p3")
response = ah.chat("prompt")
ah.edit("instructions")
```

**Style 2: Clean Import (for simple macros)**
```python
import ai_os as ai

# Best for simple, single-call macros
response = ai.chat("prompt")
ai.edit("instructions")
analysis = ai.vision("prompt", "image.png")
```

### Core Functions

```python
# Chat operations
response = ah.chat("prompt")
response = ah.chat("prompt", model="haiku")
response = ah.chat("prompt", include_context=True)

# JSON parsing
data = ah.chat_json("return JSON: {...}")

# Vision
analysis = ah.vision("describe this", "image.png")
analysis = ah.vision("prompt", "image.png", model="sonnet")

# Parallel execution (NEW!)
results = ah.gather("p1", "p2", "p3", model="haiku")
# Returns: ["response 1", "response 2", "response 3"]

# File editing
ah.edit("add comment to main.py")
ah.edit("fix the bug in utils.py", file="utils.py")

# File operations
content = ah.read("file.txt")
ah.write("file.txt", "content")
exists = ah.exists("file.txt")

# Shell operations
exit_code = ah.shell("pytest tests/")
output = ah.shell("git status", capture=True)

# User interaction
if ah.approve("Continue?"):
    ah.log("Continuing...")

# Context and state
value = ah.get_var("key", default="default")
ah.set_var("key", "value")
exit_code = ah.get_last_shell_exit_code()

# Cost tracking
cost = ah.get_cost()
# Returns: {"input_tokens": X, "output_tokens": Y, "total_cost_usd": Z}
```

---

## Real-World Examples

### Tree of Thought (Parallel Brainstorming)

```python
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    problem = kwargs.get("question")

    # Phase 1: Generate 5 initial thoughts in parallel
    prompts = [f"Generate thought #{i+1} about: {problem}" for i in range(5)]
    initial_thoughts = ah.gather(*prompts, model="haiku")

    # Phase 2: Branch each thought (15 parallel calls)
    branch_prompts = []
    for thought in initial_thoughts:
        for i in range(3):
            branch_prompts.append(f"Extend this thought: {thought}")
    branch_thoughts = ah.gather(*branch_prompts, model="haiku")

    # Phase 3: Synthesize (single call)
    all_thoughts = initial_thoughts + branch_thoughts
    synthesis = ah.chat(f"Synthesize these thoughts: {all_thoughts}")

    ah.log(synthesis)
```

### TDD Macro (Iterative Development)

```python
import ai_os as ai

def main(ctx, **kwargs):
    goal = kwargs.get("test_goal")

    # Generate test
    ai.edit(f"Create a test for: {goal}")
    test_file = f"tests/test_{goal}.py"

    # Implementation loop
    for attempt in range(5):
        test_contents = ai.read(test_file)
        ai.edit(f"Implement code to pass this test: {test_contents}")

        if ai.shell(f"pytest {test_file}") == 0:
            ai.log("Tests passed!")
            break
```

### Chart Judge (Vision Analysis)

```python
import ai_os as ai

def main(ctx, **kwargs):
    # Generate chart
    code = ai.chat("Write matplotlib code for a bar chart")
    ai.write("chart.py", code)
    ai.shell("python chart.py")

    # Judge quality
    analysis = ai.vision("Rate this chart 1-10", "chart.png", model="haiku")
    ai.log(analysis)
```

---

## Design Principles

### 1. Simple Things Should Be Simple

**Good:**
```python
response = ai.chat("prompt")
```

**Bad (old v1):**
```python
from ai_os.core.chat import chat_with_llm
response = chat_with_llm(prompt="prompt", model="default", stream=False)
```

### 2. Complex Things Should Be Possible

**Good:**
```python
results = ah.gather("p1", "p2", "p3", model="haiku")
```

**Also Good (if you need more control):**
```python
import asyncio
results = await asyncio.gather(
    ah.chat("p1", async_=True, model="sonnet"),
    ah.chat("p2", async_=True, model="haiku"),
)
```

### 3. Two Import Styles for Different Use Cases

**For complex macros with parallel execution:**
```python
import ai_os.core.macro_helpers as ah
results = ah.gather(...)  # gather() only available in macro_helpers
```

**For simple linear macros:**
```python
import ai_os as ai
ai.chat(...)  # Cleaner, more intuitive
```

### 4. Backward Compatible

Old code still works:
```python
import ai_os.core.macro_helpers as ah
patch = ah.patch("instructions")  # Legacy, wraps edit()
```

---

## Migration Guide

### From v1 to v2

**v1 Code:**
```python
import ai_os.core.macro_helpers as ah

# Patch with XML
patch = ah.patch("""
<code filename="app.py">
# full file contents here
</code>
""")

# No parallel execution
response1 = ah.chat("prompt 1")
response2 = ah.chat("prompt 2")
```

**v2 Code:**
```python
import ai_os.core.macro_helpers as ah

# Edit with natural language
ah.edit("add a comment to app.py")

# Parallel execution
results = ah.gather("prompt 1", "prompt 2")
```

---

## Performance Comparison

### Sequential (v1 and v2)
```python
# Takes 15 seconds (5 seconds per call)
r1 = ah.chat("prompt 1")  # 5s
r2 = ah.chat("prompt 2")  # 5s
r3 = ah.chat("prompt 3")  # 5s
```

### Parallel (v2 only)
```python
# Takes 5 seconds (all run simultaneously)
results = ah.gather("prompt 1", "prompt 2", "prompt 3")  # 5s total
```

**Speedup:** 3x faster with `gather()`

---

## Best Practices

### 1. Use `gather()` for Independent Prompts

**Good:**
```python
# These can run in parallel
results = ah.gather(
    "Analyze approach A",
    "Analyze approach B",
    "Analyze approach C",
    model="haiku"
)
```

**Bad:**
```python
# Sequential - unnecessarily slow
a = ah.chat("Analyze approach A")
b = ah.chat("Analyze approach B")
c = ah.chat("Analyze approach C")
```

### 2. Use Sequential Calls for Dependent Operations

**Good:**
```python
# Second call depends on first
code = ah.chat("Generate a function")
review = ah.chat(f"Review this code: {code}")
```

**Bad:**
```python
# Won't work - second prompt doesn't have code yet
results = ah.gather(
    "Generate a function",
    f"Review this code: {code}"  # code doesn't exist yet!
)
```

### 3. Choose the Right Import Style

**Use `import ai_os as ai` for:**
- Simple linear workflows
- TDD macros
- Chart generation
- Single-threaded operations

**Use `import ai_os.core.macro_helpers as ah` for:**
- Tree of thought
- Parallel brainstorming
- Ensemble methods
- Any workflow needing `gather()`

---

## Summary

The v2 API evolution achieved:

✅ **Simplicity** - `import ai_os as ai` for basic use
✅ **Power** - `ah.gather()` for parallelism without async/await
✅ **Ergonomics** - Natural language edits, not XML
✅ **Performance** - 3x+ speedup with parallelism
✅ **Backward compatible** - Old code still works
✅ **Clean** - 75% less code, better abstractions

**The API is now stable and production-ready.**

---

*End of API Evolution Document*
