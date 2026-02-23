# SHEC Improvement Plan

Based on analysis of 5 rounds of evolution, this plan addresses the core issues preventing improvement.

---

## Issue 1: Candidate Distribution Strategy

**Problem:** All candidates pursue novelty, no one preserves proven approaches.

**Solution:** Structured candidate distribution per round.

### Implementation

```python
# In shec.py - new constant
CANDIDATE_ROLES = {
    "baseline": 1,      # Minimal modification of best-ever shader
    "iterative": 2,     # Build on best parts from top-K attempts
    "exploratory": 2,   # Novel directions, higher risk tolerance
}
```

### New Prompt: `prompts/candidate_roles.py`

```python
BASELINE_GOAL_PROMPT = """
You are improving the PROVEN BEST shader from previous rounds.

# Current Best (Score: {best_score}/10)
{best_shader_code}

# What the Judge Loved
{best_judge_feedback}

# Your Task
Create a MINIMAL improvement. Change at most 2-3 things:
- Slightly tweak colors, radii, or camera angle
- Add one subtle effect (glow, reflection)
- Improve one parameter based on feedback

DO NOT:
- Change the core mathematical approach
- Rewrite the structure
- Add complex new features

Goal: 7/10 → 7.5/10, not 7/10 → attempt 10/10 and get 3/10
"""

ITERATIVE_GOAL_PROMPT = """
You are combining the BEST PARTS of multiple previous attempts.

# Top 3 Performers (Study These)
{top_k_attempts}

# Specific Strengths to Combine
{strengths_to_combine}

# Your Task
Create a shader that borrows:
- The rendering technique from the highest scorer
- The color scheme from the most visually praised
- The mathematical elegance from the most accurate

This is SYNTHESIS not invention. 80% proven, 20% improvement.
"""

EXPLORATORY_GOAL_PROMPT = """
You are exploring a NOVEL direction.

# What's Been Tried (Don't Repeat)
{tried_approaches}

# Proven Technical Constraints (MUST follow)
{mandatory_constraints}

# Your Task
Explore a genuinely new creative direction, BUT:
- Use proven rendering parameters (contribution ≥ 0.08, radius ≥ 0.12)
- Use proven GLSL patterns (no 2D arrays, external camera)
- Novel CONCEPT, proven EXECUTION

High risk is OK here. 1/5 exploratory candidates succeeding is fine.
"""
```

### Code Change: `shec.py` lines 189-213

```python
async def execute_candidate(cand_num: int, role: str):
    """Execute with role-specific prompting."""
    cand_dir = round_dir / f"candidate_{cand_num}"
    ai.shell(f"mkdir -p {cand_dir}")

    # Choose prompt based on role
    if role == "baseline":
        best = max(all_history, key=lambda x: x["score"]) if all_history else None
        if best:
            prompt = BASELINE_GOAL_PROMPT.format(
                best_score=best["score"],
                best_shader_code=read_file(best["shader_path"]),
                best_judge_feedback=best["judge_summary"]
            )
        else:
            prompt = extract_goal_section(goals_content, cand_num)

    elif role == "iterative":
        prompt = ITERATIVE_GOAL_PROMPT.format(
            top_k_attempts=format_top_k(all_history, k=3),
            strengths_to_combine=extract_strengths(all_history)  # New helper
        )

    else:  # exploratory
        prompt = EXPLORATORY_GOAL_PROMPT.format(
            tried_approaches=list_tried_approaches(all_history),
            mandatory_constraints=MANDATORY_CONSTRAINTS  # New constant
        )
```

---

## Issue 2: Overfitting to Last Failure

**Problem:** System fixes last failure, introduces new one. Learns specifics, not generals.

**Solution:** Two-part reflection structure + cumulative learnings with versioning.

### Implementation

**Change prompt structure to separate:**
1. **Raw Critique** (descriptive) - What happened, what worked, what failed
2. **Principle Extraction** (generalizing) - What GENERAL rule does this teach
3. **Guidance Generation** (prescriptive) - Specific instructions for next round

### New Prompt: `prompts/principle_extractor.py`

```python
PRINCIPLE_EXTRACTOR_PROMPT = """
You are extracting GENERAL PRINCIPLES from specific observations.

# Raw Critique From This Round
{raw_critique}

# Existing Principles (Do NOT contradict unless you have strong evidence)
{existing_principles}

---

Your task: Extract 2-3 NEW general principles from this round's critique.

## Format for Each Principle

### Principle: [Short name]

**Observation:** [What specific thing happened this round]

**Generalization:** [What broader rule does this suggest]

**Confidence:** [High/Medium/Low] - High if multiple examples support it

**Example:**
- Specific: "2D arrays failed in GLSL"
- General: "Any GLSL feature not explicitly tested should be assumed risky"

**Counter-example check:** [Does this contradict any prior learning?]

---

IMPORTANT:
- Prior principles with HIGH confidence should NOT be overridden by single failures
- If a prior principle seems wrong, mark it for INVESTIGATION not deletion
- Principles should be TEACHABLE - explain WHY, not just WHAT
"""
```

### New File: `prompts/tiered_guidance.py`

```python
TIERED_GUIDANCE_TEMPLATE = """
# Process Guidance for Round {round_num}

## TIER 1: MANDATORY (Violating guarantees failure)
These are LOAD-BEARING constraints. Every shader MUST follow these.

{mandatory_items}

## TIER 2: PROVEN BENEFICIAL (All 6+/10 shaders used these)
Strong evidence these help. Follow unless you have specific reason not to.

{proven_items}

## TIER 3: EXPERIMENTAL (Untested, use with caution)
Novel ideas that MIGHT work. Only exploratory candidates should try these.

{experimental_items}

---

## HOW TO USE THIS GUIDANCE

**Baseline candidates:** Follow TIER 1 + TIER 2 strictly
**Iterative candidates:** Follow TIER 1, adapt TIER 2 thoughtfully
**Exploratory candidates:** Follow TIER 1 only, may ignore TIER 2, may try TIER 3
"""

# Tracked as lists with evidence
MANDATORY_CONSTRAINTS = [
    {
        "rule": "Use distanceToSegment() for fiber rendering, not point distance",
        "evidence": "Round 0: 4/5 failures used point distance, winner used segment",
        "since_round": 0
    },
    {
        "rule": "External camera perspective (camera outside geometry looking in)",
        "evidence": "Round 1: Interior camera produced invisible output (1/10)",
        "since_round": 1
    },
    {
        "rule": "No 2D arrays in GLSL (vec3 arr[N][M] fails to compile)",
        "evidence": "Round 3: 4/5 shaders failed compilation from this",
        "since_round": 3
    }
]
```

### Code Change: Cumulative learnings file

```python
# In shec.py - new structure for learnings.json
{
    "version": 4,  # Incremented each run
    "principles": [
        {
            "name": "Segment Distance",
            "rule": "Use distanceToSegment for curves",
            "evidence": [...],
            "confidence": "high",
            "added_version": 1,
            "last_validated_version": 4
        }
    ],
    "tiered_guidance": {
        "mandatory": [...],
        "proven": [...],
        "experimental": [...]
    },
    "tried_approaches": [
        {"name": "Interior camera", "best_score": 1, "verdict": "failed"}
    ]
}
```

---

## Issue 3: Compilation Errors vs Scores

**Problem:** Render failures get score 0, same as "ugly but compiled."

**Solution:** Track compilation status separately, pass to judge as context.

### Code Change: `shec.py` Phase 3

```python
# Phase 3: Render with explicit status tracking
rendered = []
for cand_num in range(n_candidates):
    cand_dir = round_dir / f"candidate_{cand_num}"
    shader_path = cand_dir / "shader.glsl"
    render_path = cand_dir / "render.png"
    status_path = cand_dir / "render_status.json"

    if not shader_path.exists():
        status = {"status": "NO_SHADER", "error": "Shader file not created"}
    else:
        success, error_msg = render_shader_with_error(str(shader_path), str(render_path))
        if success:
            status = {"status": "SUCCESS"}
            rendered.append(cand_num)
        else:
            status = {"status": "COMPILATION_ERROR", "error": error_msg}

    write_file(status_path, json.dumps(status))
```

### Code Change: Judge receives status

```python
async def judge_candidate(cand_num: int):
    cand_dir = round_dir / f"candidate_{cand_num}"
    status = load_json(cand_dir / "render_status.json")

    if status.get("status") == "COMPILATION_ERROR":
        # Don't judge - just record the error
        write_file(cand_dir / "judgement.md", f"""# Compilation Failed

**Status:** COMPILATION_ERROR
**Error:** {status.get('error', 'Unknown')}

This shader did not compile. No visual judgement possible.
""")
        write_file(cand_dir / "score.json", json.dumps({
            "score": "COMPILATION_ERROR",  # String, not number
            "one_line": f"Failed to compile: {status.get('error', '')[:50]}"
        }))
        return

    # ... normal judging for SUCCESS status
```

### Methodology Critic sees compilation status

```python
def format_round_results(results: list) -> str:
    parts = []
    for r in sorted(results, key=lambda x: x["score"] if isinstance(x["score"], int) else -1, reverse=True):
        status = "COMPILED" if isinstance(r["score"], int) else r["score"]
        parts.append(f"""
═══════════════════════════════════════════════════════════════
CANDIDATE {r['candidate_num']} — Status: {status}, Score: {r['score']}/10
═══════════════════════════════════════════════════════════════
""")
```

---

## Issue 4: K Inner Loop Iterations for Executors

**Problem:** Each candidate gets ONE attempt. No chance to fix obvious issues.

**Solution:** Add lightweight validation + retry loop.

### New Helper: `validate_shader.py`

```python
def validate_shader(shader_code: str) -> dict:
    """Quick validation before full render."""
    issues = []

    # Check for known-bad patterns
    if re.search(r'vec\d\s+\w+\[\d+\]\[\d+\]', shader_code):
        issues.append("2D arrays not supported in GLSL ES")

    if 'void main()' not in shader_code:
        issues.append("Missing main() function")

    if 'gl_FragColor' not in shader_code and 'fragColor' not in shader_code:
        issues.append("No fragment color output")

    # Try actual compilation with glslangValidator if available
    try:
        result = subprocess.run(
            ['glslangValidator', '--stdin', '-S', 'frag'],
            input=shader_code.encode(),
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            error = result.stderr.decode()[:200]
            issues.append(f"GLSL validation failed: {error}")
    except FileNotFoundError:
        pass  # glslangValidator not installed
    except subprocess.TimeoutExpired:
        pass

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }
```

### Code Change: Executor with retry loop

```python
async def execute_candidate_with_retry(cand_num: int, role: str, max_retries: int = 2):
    """Execute with validation and retry."""
    cand_dir = round_dir / f"candidate_{cand_num}"

    for attempt in range(max_retries + 1):
        # Generate shader
        await execute_candidate_inner(cand_num, role, attempt)

        shader_path = cand_dir / "shader.glsl"
        if not shader_path.exists():
            continue

        shader_code = read_file(shader_path)
        validation = validate_shader(shader_code)

        if validation["valid"]:
            break  # Success!

        if attempt < max_retries:
            # Give feedback and retry
            retry_prompt = f"""
Your shader has validation issues. Fix them and rewrite.

## Issues Found
{chr(10).join(f"- {issue}" for issue in validation["issues"])}

## Your Previous Code (with problems)
```glsl
{shader_code}
```

Fix these issues and write the corrected shader to: {shader_path}
"""
            await ai.chat(retry_prompt, model="sonnet", async_=True)
```

---

## Issue 5: Generalized Principles (Teaching, Not Just Rules)

**Problem:** Learning says "don't do X" but not "why X fails" or "what class X belongs to."

**Solution:** Require principles to include WHY and TEACHING.

### Prompt Change: `methodology_critic.py`

```python
METHODOLOGY_CRITIC_PROMPT = """
...existing content...

## NEW SECTION: Principle Teaching

For each major failure or success pattern, write a TEACHING explanation:

### Teaching: [Pattern Name]

**What happened:** [Specific observation]

**Why it happened:** [Root cause explanation - physics, math, or GLSL reason]

**General category:** [What class of mistakes/successes is this]

**How to recognize in advance:** [What should executor look for to avoid/replicate]

**Analogy:** [Compare to something familiar to build intuition]

---

Example:
### Teaching: The Visibility Trap

**What happened:** 4/5 shaders rendered invisible output despite correct math

**Why it happened:** Accumulation coefficient 0.03 × 60 steps × exp(-d²) ≈ 0.1 max brightness.
Tone mapping `color/(1+color)` then compresses this further. Human vision needs >0.2 to perceive.

**General category:** Signal chain attenuation - each stage reduces signal, compounding loss

**How to recognize:** Count multiplication factors. If product < 0.5, signal will be weak.

**Analogy:** Like whispering through 5 people - each reduces volume, end result is inaudible.
"""
```

### New: `prompts/knowledge_base.py`

```python
KNOWLEDGE_BASE_PROMPT = """
You are maintaining a KNOWLEDGE BASE of shader development principles.

# Existing Knowledge Base
{existing_knowledge}

# New Learnings This Round
{new_learnings}

---

Update the knowledge base:

## 1. Add new entries for genuinely new principles
## 2. Strengthen entries that got more evidence
## 3. Mark entries as DEPRECATED if contradicted (don't delete, annotate)
## 4. Add cross-references between related principles

Format each entry as:

### [Principle Name]
**Category:** [Math | Rendering | GLSL Syntax | Color | Composition | Camera]
**Confidence:** [High | Medium | Low]
**Evidence:** [List of rounds/candidates supporting this]

**Rule:** [One sentence]
**Explanation:** [2-3 sentences explaining WHY]
**Anti-pattern:** [What violation looks like]
**Example code:** [If applicable, working vs broken code]

**Related to:** [Other principle names]
"""
```

---

## Issue 6: Two-Step Critique → Guidance

**Problem:** Methodology critic does analysis AND prescription in one shot, conflating them.

**Solution:** Split into two separate calls.

### Code Change: `shec.py` Phase 6

```python
# ════════════════════════════════════════════════════════════
# PHASE 6A: PURE CRITIQUE (Descriptive analysis)
# ════════════════════════════════════════════════════════════

ai.log("  [dim]Phase 6A: Analyzing what happened...[/dim]")

critique_path = round_dir / "methodology_critique.md"

critique_prompt = PURE_CRITIQUE_PROMPT.format(
    main_goal=goal,
    round_results=format_round_results(round_results),
    output_path=critique_path
)

ai.chat(critique_prompt, model="opus")
critique_content = read_file(critique_path)

# ════════════════════════════════════════════════════════════
# PHASE 6B: GUIDANCE GENERATION (Prescriptive, informed by critique)
# ════════════════════════════════════════════════════════════

ai.log("  [dim]Phase 6B: Generating guidance from critique...[/dim]")

updates_path = round_dir / "process_updates.md"

guidance_prompt = GUIDANCE_FROM_CRITIQUE_PROMPT.format(
    main_goal=goal,
    critique=critique_content,
    existing_guidance=goal_setting_guidance,
    existing_principles=read_file(campaign_dir / "principles.md"),
    output_path=updates_path
)

ai.chat(guidance_prompt, model="opus")
```

### New Prompt: `prompts/pure_critique.py`

```python
PURE_CRITIQUE_PROMPT = """
You are analyzing a round of shader evolution. Your job is PURE ANALYSIS -
describe what happened, identify patterns, diagnose causes.

DO NOT give advice or suggestions - that comes in the next phase.

# Original Goal
{main_goal}

# This Round's Results
{round_results}

---

Write a detailed critique to: {output_path}

## What Worked (be specific about WHY)
[For each success, explain the chain of causation]

## What Failed (diagnose root causes)
[For each failure, trace back to the actual cause - not symptoms]

## Patterns Observed
[Cross-cutting observations across multiple candidates]

## Surprises
[Anything unexpected - good code that failed, bad code that worked]

## Open Questions
[Things we'd need more data to understand]

---

Be DESCRIPTIVE not PRESCRIPTIVE. Say "X happened because Y" not "you should do Z."
"""
```

### New Prompt: `prompts/guidance_from_critique.py`

```python
GUIDANCE_FROM_CRITIQUE_PROMPT = """
You are converting analysis into actionable guidance.

# The Critique (What Happened)
{critique}

# Existing Guidance (Don't Contradict Without Reason)
{existing_guidance}

# Established Principles (Treat as Constraints)
{existing_principles}

---

Write updated guidance to: {output_path}

Use this TIERED STRUCTURE:

## TIER 1: MANDATORY
[Rules that MUST be followed - add any new ones from this round's failures]
[Format: "RULE: X | EVIDENCE: Y | SINCE: Round Z"]

## TIER 2: PROVEN BENEFICIAL
[Patterns that helped in 6+/10 shaders]
[Can demote from TIER 2 if evidence weakens]

## TIER 3: EXPERIMENTAL
[Novel ideas from this round worth trying]
[Move to TIER 2 if they work, delete if they fail]

## DEPRECATED
[Ideas that were tried and definitively failed - don't retry]

---

IMPORTANT:
- New MANDATORY rules need strong evidence (multiple failures from same cause)
- Don't demote existing MANDATORY unless you have counter-evidence
- EXPERIMENTAL items should be clearly marked as "untested, at own risk"
"""
```

---

## Summary: Changes by Location

### New Files to Create
- `prompts/candidate_roles.py` - Role-specific prompts for baseline/iterative/exploratory
- `prompts/pure_critique.py` - Descriptive-only critique
- `prompts/guidance_from_critique.py` - Prescriptive guidance from critique
- `prompts/principle_extractor.py` - Generalizing specific learnings
- `prompts/knowledge_base.py` - Cumulative teaching knowledge
- `prompts/tiered_guidance.py` - Structured guidance template
- `utils/validate_shader.py` - Pre-render validation

### Files to Modify
- `shec.py`:
  - Add candidate role assignment (baseline/iterative/exploratory distribution)
  - Split Phase 6 into 6A (critique) and 6B (guidance)
  - Add compilation error tracking in Phase 3
  - Add executor retry loop with validation
  - Track principles in structured JSON, not just markdown

- `prompts/methodology_critic.py`:
  - Add "Teaching" section requiring WHY explanations
  - Remove prescriptive guidance (moved to separate prompt)

- `prompts/goal_setter.py`:
  - Receive tiered guidance structure
  - Different prompts for different candidate roles

### Data Structure Changes
- `campaigns/{goal}/learnings.json` - Structured cumulative knowledge
- `campaigns/{goal}/principles.md` - Human-readable principle list
- `traces/round_N/candidate_M/render_status.json` - Compilation status

---

## Implementation Order

1. **Compilation error tracking** (quick win, minimal change)
2. **Two-step critique → guidance** (improves learning quality)
3. **Tiered guidance structure** (better executor instructions)
4. **Candidate role distribution** (prevents novelty-only failure)
5. **Executor retry loop** (catches simple errors early)
6. **Principle extraction + teaching** (longer-term knowledge building)
