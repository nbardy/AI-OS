"""Global Learner prompt - compresses and refines learnings across runs.

NOTE: Placeholders used by this prompt:
  - {goal}               — the high-level visual goal
  - {existing_learnings}  — current global learnings (or "First run.")
  - {new_insights}        — summary of all attempts from this run
  - {best_score}          — score of the best result this run
  - {best_approach}       — title of the best approach this run
  - {output_path}         — file path to write updated learnings to
"""

GLOBAL_LEARNER_PROMPT = """
You are a meta-learning system that maintains compressed, evolving knowledge across multiple runs.

# Goal Being Pursued
{goal}

# Existing Global Learnings (from previous runs)
{existing_learnings}

# New Insights from This Run
{new_insights}

# This Run's Best Result
Score: {best_score}/10
Approach: {best_approach}

---

Your job: REWRITE (not append) the global learnings to integrate new insights while keeping it compressed.

Write to: {output_path}

# Global Learnings: {goal}

## What Works (proven patterns)
[Concrete techniques that consistently score well - max 5 bullets]

## What Fails (anti-patterns)
[Specific approaches to AVOID - max 5 bullets]

## Mathematical Reference
[The core equations, identities, and geometric principles that produce good results.
Write in plain math notation. Include: projection formulas, fiber parametrizations,
distance functions, key properties (conformal, circle-preserving, etc.).
This is the most important section — mathematical clarity produces correct code.]

## Visual Strategies
[Aesthetic/color/composition patterns that succeed - max 5 bullets]

## Theoretical Frontiers
[Mathematical ideas not yet tried that could break through the current score ceiling.
Frame as theory, not code: what geometric property could be exploited, what identity
could simplify the computation, what alternative mathematical representation might work.]

## Hall of Fame
[Top 3 approaches ever tried, with scores and one-line why]

## Current Best
Score: X/10 - [approach name]

---

IMPORTANT:
- Keep total length under 100 lines
- Merge/compress similar insights
- Drop outdated or contradicted learnings
- Mathematical Reference section is the highest priority — good math produces good shaders
- This gets fed to future goal-setters, so focus on theory and principles, not code
"""
