# Final Document for new CLI Tool: AI-OS

## Overview and Philosophy  

**AI-OS** is a macro system—not an all-encompassing framework. Software is meant to be rewritten—AI-OS is explicitly designed as a small, core shell for tooling to rapidly grow, evolve, and be forked.

It's the dawn of AI: let us rewrite our code faster, making it smaller, simpler, and less complex. Certain words that describe the low quality of LLM code no longer need to apply. We can write LLM-assisted code that is **safe, tested, readable, and well-factored**—code whose quality is high by any metric and yields verifiable results.

LLM tooling can make us better engineers, not worse.

AI-OS is designed to avoid vibe coding and fully embrace tool-assisted engineering.

We develop macros to support structured workflows:

- Test-driven development cycles
- Chain-of-thought coding
- Critic-based refactors

We provide a minimalist terminal interface with clear `/chat`, `/patch`, and `/run` commands as the primary UI for AI-driven terminal development.

> **Philosophy**:  
> “Abandon vibe coding—embrace AI engineering.”

---

## Quick Install

```bash
pip install ai-os          # Python ≥ 3.11
export OPENROUTER_API_KEY=sk-...
aios                       # launch the terminal
