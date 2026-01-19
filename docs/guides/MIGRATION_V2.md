# Migration Guide: AI-OS v1 to v2

**Date:** 2026-01-17  
**Purpose:** Guide for migrating from AI-OS v1 (OpenRouter-based) to v2 (Claude Code native)

---

## What's New in v2

AI-OS v2 is a complete rewrite that uses **Claude Code** as the execution substrate instead of calling OpenRouter directly. This provides:

1. **Native tool use** - Claude Code handles file operations, shell commands, etc.
2. **Better reliability** - No more XML patch parsing, uses Claude's Edit tool directly
3. **Parallel execution** - Run multiple Claude calls concurrently with `gather()`
4. **Simpler codebase** - Removed ~1800 lines of code
5. **Cost tracking** - Automatic tracking of API usage and costs

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

Claude Code requires an Anthropic API key, not OpenRouter.

### 2. Dependencies

**v1:** Required `aiohttp` for OpenRouter API calls

**v2:** Requires Claude Code CLI to be installed:
```bash
npm install -g @anthropic-ai/claude-code
# or
brew install claude-code
```

### 3. Patch System Removed

The old `ah.patch()` function that returned structured patch objects is gone.

**v1:**
```python
patch = ah.patch("Add user authentication")
if patch:
    for file in patch.get("files", []):
        ai.log(f"Modified: {file.path}")
```

**v2:**
```python
# Just use edit() directly
ai.edit("Add user authentication")
```

---

## API Changes

### Import Statement

**v1 and v2 (both work):**
```python
import ai_os.core.macro_helpers as ah
```

**v2 (recommended):**
```python
import ai_os as ai
```

The `ai` namespace is cleaner and more Pythonic.

### Core Functions

| v1 | v2 | Notes |
|----|-----|-------|
| `ah.log(msg)` | `ai.log(msg)` | Unchanged |
| `ah.chat(prompt)` | `ai.chat(prompt)` | Now uses Claude Code |
| `ah.patch(plan)` | `ai.edit(instruction)` | Different semantics |
| `ah.shell(cmd)` | `ai.shell(cmd)` | Unchanged |
| `ah.approve(msg)` | `ai.approve(msg)` | Unchanged |
| `ah.get_var(name)` | `ai.get_var(name)` | Unchanged |
| N/A | `ai.gather(*prompts)` | **New:** Parallel execution |
| N/A | `ai.vision(prompt, image)` | **New:** Image analysis |
| N/A | `ai.read(path)` | **New:** Direct file read |
| N/A | `ai.write(path, content)` | **New:** Direct file write |

### Parallel Execution

**v2 introduces parallel execution:**

```python
# Run 5 prompts in parallel
results = ai.gather(
    "Generate idea 1",
    "Generate idea 2", 
    "Generate idea 3",
    "Generate idea 4",
    "Generate idea 5",
    model="haiku"  # Optional: use haiku for speed
)

for i, result in enumerate(results):
    ai.log(f"Idea {i+1}: {result}")
```

This is much faster than sequential calls.

---

## Migration Examples

### Example 1: Simple TDD Macro

**v1:**
```python
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    goal = kwargs.get("goal")
    
    # Generate test
    patch = ah.patch(f"Create a pytest test for: {goal}")
    test_file = find_test_file()
    
    # Implementation loop
    for i in range(5):
        patch = ah.patch(f"Implement code to pass {test_file}")
        exit_code = ah.shell(f"pytest {test_file}")
        if exit_code == 0:
            ah.log("Tests pass!")
            break
```

**v2:**
```python
import ai_os as ai

def main(ctx, **kwargs):
    goal = kwargs.get("goal")
    
    # Generate test
    ai.edit(f"Create a pytest test for: {goal}")
    test_file = find_test_file()
    
    # Implementation loop
    for i in range(5):
        ai.edit(f"Implement code to pass {test_file}")
        exit_code = ai.shell(f"pytest {test_file}")
        if exit_code == 0:
            ai.log("Tests pass!")
            break
```

**Key changes:**
- `ah.patch()` → `ai.edit()`
- Import changed to `import ai_os as ai`

### Example 2: Parallel Idea Generation

**v1 (sequential):**
```python
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    ideas = []
    for i in range(5):
        idea = ah.chat(f"Generate creative idea #{i+1}")
        ideas.append(idea)
    
    # This is slow - 5 sequential API calls!
```

**v2 (parallel):**
```python
import ai_os as ai

def main(ctx, **kwargs):
    # All 5 prompts run in parallel!
    ideas = ai.gather(
        "Generate creative idea #1",
        "Generate creative idea #2",
        "Generate creative idea #3",
        "Generate creative idea #4",
        "Generate creative idea #5",
        model="haiku"
    )
    
    # Much faster - parallel execution
```

---

## Troubleshooting

### "claude: command not found"

Claude Code CLI is not installed. Install it:

```bash
npm install -g @anthropic-ai/claude-code
```

Or check installation:
```bash
which claude
claude --version
```

### "No module named 'anthropic'"

The Python SDK isn't needed for v2. Only the Claude Code CLI is required.

### Cost Tracking Not Working

Cost tracking only works when Claude Code returns JSON output. In v2, this is automatic for `chat()` and `chat_json()`, but not for streaming operations.

---

## Migration Checklist

- [ ] Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- [ ] Set `ANTHROPIC_API_KEY` environment variable
- [ ] Remove `OPENROUTER_API_KEY` (no longer needed)
- [ ] Update imports: `import ai_os as ai` (recommended)
- [ ] Replace `ah.patch()` with `ai.edit()`
- [ ] Test macros work with `aios`
- [ ] Verify parallel execution works if using `gather()`
- [ ] Check that file operations work

---

## Benefits of v2

1. **Simpler** - No XML patch parsing, just use Claude's Edit tool
2. **Faster** - Parallel execution with `gather()`
3. **More reliable** - Claude Code handles tool use natively
4. **Cheaper** - Can use haiku model for simple tasks
5. **Better errors** - Claude Code provides clearer error messages

---

## Getting Help

- Documentation: See `README.md`
- Examples: Check `examples/` directory
- Issues: https://github.com/nbardy/AI-OS/issues

---

## Summary

v2 is a major improvement that simplifies the codebase and improves reliability. The migration is straightforward:

1. Install Claude Code CLI
2. Update environment variable
3. Replace `ah.patch()` with `ai.edit()`
4. Optionally use `ai.gather()` for parallel execution

Most macros should work with minimal changes!
