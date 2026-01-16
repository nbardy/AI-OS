# AI-OS v2 Migration Guide

**From OpenRouter to Claude Code Native**

This guide explains how to migrate from AI-OS v1 (OpenRouter-based) to AI-OS v2 (Claude Code native).

---

## Overview

AI-OS v2 represents a fundamental architectural shift:

- **v1**: Used OpenRouter API for LLM calls, custom XML-based patch strategies
- **v2**: Uses Claude Code CLI as a subprocess, leveraging its native tool use capabilities

### Key Benefits

1. **Native tool use**: Claude Code handles file editing, shell commands, web search
2. **Simpler codebase**: Removed ~800 lines of patch strategy code
3. **Better reliability**: Claude Code's Edit tool is more precise than XML parsing
4. **Cost tracking**: Built-in cost tracking per request
5. **Parallel execution**: True async support with `gather()`, `spawn()`, `join()`

---

## Breaking Changes

### 1. Environment Variables

**v1:**
```bash
export OPENROUTER_API_KEY=sk-or-...
```

**v2:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 2. API Changes

| v1 Function | v2 Function | Notes |
|-------------|-------------|-------|
| `ah.patch(plan)` | `ai.edit(instruction)` | No XML, just natural language |
| `ah.chat(prompt)` | `ai.chat(prompt)` | Same signature |
| N/A | `ai.gather(*prompts)` | New: parallel execution |
| N/A | `ai.spawn(prompt)` | New: background execution |
| N/A | `ai.join(agents)` | New: wait for spawned agents |
| `ah.chat_with_image()` | `ai.vision(prompt, image)` | Simplified vision API |

### 3. Import Changes

**v1:**
```python
from ai_os.core import macro_helpers as ah
```

**v2 (preferred):**
```python
import ai_os as ai
```

**v2 (legacy compatible):**
```python
from ai_os.core import macro_helpers as ah  # Still works
```

---

## Migration Examples

### Basic Chat

**v1:**
```python
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    response = ah.chat("What is 2+2?")
    ah.log(response)
```

**v2:**
```python
import ai_os as ai

def main(ctx, **kwargs):
    response = ai.chat("What is 2+2?")
    ai.log(response)
```

### File Editing

**v1:**
```python
patch = ah.patch("""
Add a function to calculate factorial in math_utils.py
""")
if patch and patch.get("applied"):
    ah.log("Patch applied!")
```

**v2:**
```python
success = ai.edit("Add a function to calculate factorial in math_utils.py")
if success:
    ai.log("Edit applied!")
```

### Parallel Execution

**v1:**
```python
# Not directly supported - had to manually thread
```

**v2:**
```python
# Simple parallel execution
results = ai.gather(
    "Question 1",
    "Question 2",
    "Question 3",
    model="haiku"
)

# Or with spawn/join for more control
agents = [ai.spawn(f"Task {i}") for i in range(5)]
results = ai.join(agents)
```

### Vision/Image Analysis

**v1:**
```python
# Had to use OpenRouter-specific image encoding
response = ah.chat_with_image(prompt, image_path)
```

**v2:**
```python
# Claude Code reads images natively
response = ai.vision("Describe this image", "chart.png")
```

---

## Full API Reference

### Output Functions
- `ai.log(message)` - Print to console with Rich formatting
- `ai.status(message)` - Context manager for spinner display

### LLM Operations
- `ai.chat(prompt, model=None, context=None)` - Send prompt to Claude
- `ai.chat_json(prompt, schema=None)` - Get structured JSON response
- `ai.vision(prompt, image, model=None)` - Analyze images

### Parallel Execution
- `ai.gather(*prompts, model=None)` - Execute prompts in parallel (recommended)
- `ai.spawn(prompt)` - Spawn background agent
- `ai.join(agents)` - Wait for spawned agents

### File Operations
- `ai.read(path)` - Read file contents
- `ai.write(path, content)` - Write file contents
- `ai.edit(instruction, file=None)` - Have Claude edit files
- `ai.exists(path)` - Check if file exists
- `ai.glob(pattern)` - Find files matching pattern

### Shell Operations
- `ai.shell(command, capture=False, check=False)` - Execute shell command
- `ai.run(command, **kwargs)` - Low-level subprocess access

### Human Interaction
- `ai.approve(message)` - Ask for Y/N approval
- `ai.ask(question, choices=None)` - Ask user a question
- `ai.confirm_changes(files)` - Show files and ask for approval

### Context & State
- `ai.get_var(name, default=None)` - Get macro argument
- `ai.set_var(name, value)` - Set context variable
- `ai.get_cost()` - Get accumulated cost for session

### Utilities
- `ai.sleep(seconds)` - Pause execution
- `ai.timestamp()` - Get current timestamp string
- `ai.random_id(length=8)` - Generate random ID

### Configuration
- `ai.config(model=None, timeout=None, working_dir=None)` - Configure orchestrator

---

## Common Migration Patterns

### Pattern 1: Test-Driven Development

**v1:**
```python
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    # Generate test
    test_patch = ah.patch("Create test file for user auth")

    # Implement
    impl_patch = ah.patch("Implement code to pass the test")

    # Run test
    ah.shell("pytest tests/")
```

**v2:**
```python
import ai_os as ai

def main(ctx, **kwargs):
    # Generate test
    ai.edit("Create test file for user auth")

    # Implement
    ai.edit("Implement code to pass the test")

    # Run test
    ai.shell("pytest tests/")
```

### Pattern 2: Tree of Thought

**v2 (new capability):**
```python
import ai_os as ai

def main(ctx, **kwargs):
    question = kwargs.get("question")

    # Generate 5 initial thoughts in parallel
    thoughts = ai.gather(
        f"Thought 1: {question}",
        f"Thought 2: {question}",
        f"Thought 3: {question}",
        f"Thought 4: {question}",
        f"Thought 5: {question}",
        model="haiku"
    )

    # Synthesize
    synthesis = ai.chat(f"""
    Question: {question}
    Thoughts: {thoughts}

    Synthesize into a comprehensive answer.
    """)

    ai.log(synthesis)
```

### Pattern 3: Iterative Refinement

**v1:**
```python
for attempt in range(max_attempts):
    patch = ah.patch(f"Attempt {attempt}: {instruction}")
    if test_passes():
        break
```

**v2:**
```python
for attempt in range(max_attempts):
    ai.edit(f"Attempt {attempt}: {instruction}")
    if ai.shell("pytest", capture=True) == 0:
        break
```

---

## Troubleshooting

### Issue: "Claude Code not found"

**Solution:**
```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Or use npx (no install needed)
# The orchestrator will automatically use npx if claude binary not found
```

### Issue: "Permission denied" errors

**Solution:**
The orchestrator uses `--dangerously-skip-permissions` by default for macro usage.
If you want stricter permission checking, configure the orchestrator:

```python
from ai_os.core.orchestrator import configure_orchestrator

configure_orchestrator(skip_permissions=False)
```

### Issue: Cost tracking shows $0.00

**Solution:**
Cost tracking only works when using `--output-format json` mode.
Streaming mode (used in interactive chat) doesn't provide cost data.

### Issue: "Context too large" errors

**Solution:**
```python
# Use haiku for large context operations
ai.chat(huge_prompt, model="haiku")

# Or split into smaller operations
results = ai.gather(
    chunk1, chunk2, chunk3,
    model="haiku"
)
```

---

## Performance Considerations

### v1 vs v2 Performance

| Operation | v1 (OpenRouter) | v2 (Claude Code) | Notes |
|-----------|-----------------|------------------|-------|
| Simple chat | ~2s | ~2s | Similar |
| File editing | ~5s | ~3s | Faster (no XML) |
| Parallel (5 ops) | N/A | ~2s | New capability |
| Vision analysis | ~3s | ~2s | Native support |

### Optimization Tips

1. **Use haiku for simple tasks**: `ai.chat(prompt, model="haiku")`
2. **Parallelize independent operations**: `ai.gather(*prompts)`
3. **Batch file operations**: Read/write multiple files before calling LLM
4. **Cache expensive operations**: Store results in `ai.set_var()`

---

## Backward Compatibility

AI-OS v2 maintains backward compatibility with v1 macros through the `ah` alias:

```python
from ai_os.core import macro_helpers as ah

# v1 macros still work
def main(ctx, **kwargs):
    ah.chat("Hello")  # Works
    ah.log("World")   # Works
```

However, v1's `ah.patch()` now wraps `ai.edit()` and returns a simplified result dict.

---

## What's Removed

These v1 features are removed in v2:

1. **Patch strategies** (`full_file`, `git_diff`, `step_by_step`) - Claude Code handles this
2. **XML schema parsing** - No longer needed
3. **OpenRouter integration** - Replaced with Claude Code
4. **Custom streaming protocols** - Use Claude Code's native streaming

---

## Next Steps

1. Update your `ANTHROPIC_API_KEY` environment variable
2. Install Claude Code: `npm install -g @anthropic-ai/claude-code`
3. Update macro imports from `ah` to `ai`
4. Replace `ah.patch()` calls with `ai.edit()`
5. Leverage new parallel execution capabilities with `ai.gather()`

For more examples, see:
- `examples/tdd_macro.py` - Test-driven development
- `examples/tree_of_thought.py` - Parallel reasoning
- `examples/shader_evolution.py` - Iterative generation with vision
- `examples/chart_judge_macro.py` - Vision-based evaluation

---

## Questions?

- Check `ARCHITECTURE.md` for technical details
- See `examples/` for working macro code
- File issues at: https://github.com/nbardy/AI-OS/issues
