"""Methodology Critic - analyzes a round and produces TWO output files.

File 1 ({critique_path}): Full verbose analysis for human review and global learner.
File 2 ({updates_path}): Concise tiered guidance list only (~40 lines max).

NOTE: Placeholders used by this prompt:
  - {main_goal}          — the high-level visual goal
  - {round_results}      — formatted results from all candidates this round
  - {existing_guidance}  — current tiered guidance being maintained
  - {critique_path}      — output path for full verbose analysis
  - {updates_path}       — output path for concise updated tiered guidance
"""

METHODOLOGY_CRITIC_PROMPT = """
You are analyzing a round of shader evolution.

# Goal: {main_goal}

# Results
{round_results}

# Existing Guidance
{existing_guidance}

---

You must write TWO files. Read the instructions for BOTH before writing either.

## FILE 1: {critique_path}

Full verbose analysis. Be thorough and detailed — this is for human review and the global learner.

Structure:

# Round Analysis

## Mathematical Correctness
[For each candidate: is the math right? Does the projection preserve the structure it should? Are there algebraic errors in the quaternion/projection formulas? Cite specific equations.]

## What Worked (and WHY)
[For each success (score 6+), explain the mathematical reason it produced good visuals — what geometric property was preserved, what projection behavior created visual clarity]

## What Failed (and WHY)
[For each failure, diagnose the mathematical root cause. E.g.: "S³→S²→R³ projection collapses fibers to points because the Hopf map S³→S² sends each fiber circle to a single base point." Be precise about the math, not just "it didn't render."]

## Patterns
[Cross-cutting mathematical and rendering observations across all candidates]

## Theoretical Insights
[Deeper analysis: what mathematical properties of the target geometry (Hopf fibration, stereographic projection, fiber bundles) are being leveraged or missed? What theorems or identities could inform better approaches?]

---

## FILE 2: {updates_path}

Updated tiered guidance with MATHEMATICAL REFERENCE. This file replaces the existing guidance.
~60 lines maximum. Rules include equations and mathematical reasoning, not code.

Structure:

# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Rule name**: description | Evidence: which candidates/rounds

## TIER 2: PROVEN (used by high scorers)
- **Pattern name**: description | Evidence: which candidates/rounds

## TIER 3: EXPERIMENTAL (worth trying)
- **Idea**: description | Risk: what could go wrong

## DEPRECATED (don't retry)
- **Approach**: what it was | Failed because: one-line root cause

## MATHEMATICAL REFERENCE

Include the key equations, identities, and geometric principles the executor needs.
Write math in plain notation (not code). Focus on:

1. **Core geometry** — the mathematical structure being visualized (fiber parametrization, projection formulas, key identities)
2. **Why the best approach works** — which mathematical property produces visual clarity (e.g., "stereographic projection is conformal, preserving circle shape")
3. **Theoretical path forward** — mathematical reasoning for what to try next (e.g., "SDF for a torus knot: the distance from point p to the nearest fiber is minimized when...")

Example:
  Hopf fiber at shell angle α, rotation φ:
  q(θ) = (cos(α/2)·exp(iθ), sin(α/2)·exp(i(θ+φ)))
  Stereographic projection S³→R³: p = (2x, 2y, 2z) / (1 - w + ε)
  This is conformal ⟹ circles in S³ map to circles in R³.

Rules:
- Preserve all existing MANDATORY rules unless evidence contradicts them
- Promote PROVEN to MANDATORY if 3+ rounds of evidence
- Promote EXPERIMENTAL to PROVEN if a high scorer used it
- Move failed approaches to DEPRECATED with clear reason
- MATHEMATICAL REFERENCE is the most valuable section — give executors the theory they need to derive correct implementations
"""
