# AI-OS

**“Abandon vibe coding—embrace AI engineering.”**

AI-OS is a macro system—not a monolithic framework. Software is meant to be rewritten: AI-OS is a tiny core shell you fork, extend, and discard without regret.

It’s the dawn of AI—let us rewrite our code faster, making it smaller, simpler, and less complex. Low-quality LLM code is optional noise; with disciplined workflows we generate **safe, tested, readable, well-factored** code—quality verifiable by any metric.


LLM tooling can make us better engineers, not worse.

We follow a shared minimal language (think CRDT-style primitives) to orchestrate control loops via Python, sync results with users, and provide just the essentials:

| Slash    | Alias | Purpose                                |
|----------|-------|----------------------------------------|
| `/chat`  | `>`   | Brainstorm, explain, iterate with LLM  |
| `/patch` | `+`   | Yield a `Patch` dict, preview & apply  |
| `/run`   | `!`   | Unix-style piping & safe shell exec    |
| `/macro` | `@`   | Run a Python macro workflow            |

> We share Unix philosophy—even Unix tooling—through string piping and `/run`:  
> think small programs composed via clear, typed interfaces.

All UI flows through **Rich** with a solarized palette, autocomplete, streaming output, and a blocking spinner during `.gather()`. Yielded patches pause for human approval and are logged in the chat history.

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
   • <code file="…">…</code> blocks.

No extra text.
"""

def parse(xml_txt):
    root = ET.fromstring(f"<all>{xml_txt}</all>")
    return [
        {
            "title": a.findtext("title"),
            "why":   a.findtext("rationale"),
            "files": [f.text for f in a.find("files")]
        }
        for a in root.findall("approach")
    ]

def run_macro(goal: str):
    # PLAN
    plan = chat(f"[PLAN]\nGoal: {goal}\n{SYSTEM}")
    approaches = parse(plan.content)

    # CAND (parallel)
    futs = [
        spawn(patch,
              f"[CAND]\nApproach: {ap['title']}\n{ap['why']}\nFiles:\n"
              + "\n".join(ap['files']),
              async_=True)
        for ap in approaches
    ]
    code_sets = gather(futs)   # UI shows blocking spinner until all done

    # CRITIC
    critique = chat(
        "[CRITIC]\nDiscuss pros & cons of each approach:\n\n"
        + "\n---\n".join(f"## {ap['title']}\n{c}"
                        for ap, c in zip(approaches, code_sets))
    )

    # MERGE
    final = chat(f"[MERGE]\n{critique.content}")
    patches = patch(final.content)   # yield dict; UI prompts Y/N

    return patches
```

---

## Macro API Reference

```python
chat(prompt:str, *, ctx:list[Message]=[], async_:bool=False, search:bool=False)
patch(plan:str, files:list[str]=[], *, ctx:list[Message]=[], async_:bool=False)
spawn(fn:Callable, *args, **kwargs) -> Future
gather(futures:list[Future]) -> list[Any]
run(command:str, *, async_:bool=False) -> str | Future
add(item:str|Path, *, show_user:bool=False) -> None
info(msg:str) -> None
```

- **`.gather()`** blocks the UI with a spinner until all threads finish.  
- **`patch(...)`** returns a `Patch` dict; yielding it invokes a Y/N approval dialog and logs to chat.  
- **`/run`** lets you pipe strings between macros and Unix commands.  
- **`add(..., show_user=True)`** both shows and saves to context.  
- **`info(...)`** logs to UI only.
