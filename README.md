# AI-OS 😊🚀🎉

**"Abandon vibe coding—embrace AI engineering."**

AI-OS is an AI operating system—not a monolithic framework. Software is meant to be rewritten: AI-OS is a tiny core shell you fork, extend, and discard without regret.


It's the dawn of AI—let us rewrite our code faster, making it smaller, simpler, and less complex. Low-quality LLM code is optional noise; with disciplined workflows we generate **safe, tested, readable, well-factored** code—quality verifiable by any metric.

Agents are for the common folk, macros are for the nerds.

LLM tooling can make us better engineers, not worse.

We follow a shared minimal language (think CRDT-style primitives) to orchestrate control loops via Python, sync results with users, and provide just the essentials:

| Slash    | Alias | Purpose                                |
|----------|-------|----------------------------------------|
| `/chat`  | `>`   | Brainstorm, explain, iterate with LLM  |
| `/patch` | `+`   | Yield a `Patch` dict, preview & apply  |
| `/run`   | `!`   | Unix-style piping & safe shell exec    |
| `/macro` | `@`   | Run a Python macro workflow            |

> We embrace Unix philosophy—even Unix tooling—by enabling string piping and `/run` execution. This allows composing small programs via clear, typed interfaces.

---

## Quick Install

```bash
pip install ai-os           # Python ≥ 3.11
export OPENROUTER_API_KEY=sk-…
aios                        # launch the AI-OS shell
```

---

## Tree-of-Thought Parallel Async Example

```python
# macros/tot_five_approaches.py

import re, xml.etree.ElementTree as ET
from ai_os.core import chat, spawn, gather, patch

R_INS = re.compile(r"\{insert ([^}]+)\}")

SYSTEM = """
You are AI-OS.Tree-Of-Thought.

1. [PLAN]   → emit FIVE <approach> XML blocks (title, rationale, files).
2. [CAND]   → for each <approach>, output code for each <file>, prefixed {insert path}.
3. [CRITIC] → discuss pros & cons of all CANDs in plain language.
4. [MERGE]  → emit a FINAL document with:
   • <Key Design and Data Model Planning and Decisions>…</…>
   • <FN Signatures>…</…>
   • <File list>…</…>
   • <code file="…">…
```
✨🚀
```