# Self-Healing Evolutionary Critique (SHEC)

## Overview

An evolutionary shader generation algorithm where the **process itself evolves** alongside the outputs. Each round produces not just shaders, but also critiques of methodology that feed forward into improved goal-setting and execution strategies.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ROUND N                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │   GOAL SETTER   │────▶│    EXECUTOR     │────▶│     JUDGE       │       │
│  │                 │     │                 │     │   (blind)       │       │
│  │ Writes:         │     │ Writes:         │     │ Writes:         │       │
│  │ - goals.md      │     │ - plan.md       │     │ - judgement.md  │       │
│  │                 │     │ - shader.glsl   │     │ - scores.json   │       │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘       │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                         ARTIFACTS                                │       │
│  │  traces/round_N/                                                 │       │
│  │  ├── candidate_0/                                                │       │
│  │  │   ├── goals.md        (goal-setting reasoning)                │       │
│  │  │   ├── plan.md         (execution plan & key math)             │       │
│  │  │   ├── shader.glsl     (the actual shader)                     │       │
│  │  │   ├── render.png      (rendered output)                       │       │
│  │  │   ├── judgement.md    (blind critique of render only)         │       │
│  │  │   └── score.json      {score: N, reasoning: "..."}            │       │
│  │  └── ...                                                         │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      METHODOLOGY CRITIC                          │       │
│  │                                                                  │       │
│  │  Inputs: ALL artifacts from round (goals + plans + judgements)   │       │
│  │                                                                  │       │
│  │  Analyzes: What methodology patterns led to high/low scores?     │       │
│  │                                                                  │       │
│  │  Writes:                                                         │       │
│  │  - methodology_critique.md   (what succeeded/failed and why)     │       │
│  │  - process_updates.md        (concrete improvements for next)    │       │
│  │                                                                  │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                      │                                      │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
                                       ▼ FEEDS INTO
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                              ROUND N+1                                       │
│                                                                             │
│  Goal Setter receives:                                                      │
│  - Original user goal                                                       │
│  - methodology_critique.md (what patterns worked)                           │
│  - process_updates.md (how to improve)                                      │
│  - Best previous attempts (shader + score + judgement)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Per Round

```
                    ┌──────────────────────────────────────┐
                    │         INPUTS TO ROUND              │
                    │                                      │
                    │  • user_goal: str                    │
                    │  • process_updates.md (from N-1)     │
                    │  • methodology_critique.md (N-1)     │
                    │  • top_k_previous: [(shader,score)]  │
                    └──────────────────┬───────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Candidate 0    │         │  Candidate 1    │         │  Candidate 2    │
│                 │         │                 │         │                 │
│  1. GOAL_SET    │         │  1. GOAL_SET    │         │  1. GOAL_SET    │
│     ↓           │         │     ↓           │         │     ↓           │
│  2. EXECUTE     │         │  2. EXECUTE     │         │  2. EXECUTE     │
│     ↓           │         │     ↓           │         │     ↓           │
│  3. RENDER      │         │  3. RENDER      │         │  3. RENDER      │
│     ↓           │         │     ↓           │         │     ↓           │
│  4. JUDGE       │         │  4. JUDGE       │         │  4. JUDGE       │
│     (blind)     │         │     (blind)     │         │     (blind)     │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                    ┌──────────────────────────────────────┐
                    │       METHODOLOGY CRITIC             │
                    │                                      │
                    │  Sees: ALL goals, plans, judgements  │
                    │  Produces:                           │
                    │  • methodology_critique.md           │
                    │  • process_updates.md                │
                    └──────────────────────────────────────┘
```

---

## Pseudo-Code

```python
def main(ctx, goal, rounds=3, candidates=3):
    """Self-Healing Evolutionary Critique algorithm."""

    shell("mkdir -p traces")

    # Accumulating context across rounds
    methodology_critique = ""  # What patterns succeeded/failed
    process_updates = ""       # Concrete improvements for next round
    all_history = []           # [(round, candidate, shader_path, score, judgement)]

    for round_num in range(rounds):
        round_dir = f"traces/round_{round_num}"
        shell(f"mkdir -p {round_dir}")

        round_results = []  # Collect this round's outputs for methodology critic

        # ════════════════════════════════════════════════════════════
        # PHASE 1: GENERATE CANDIDATES (parallel)
        # ════════════════════════════════════════════════════════════

        for candidate_num in parallel(range(candidates)):
            cand_dir = f"{round_dir}/candidate_{candidate_num}"
            shell(f"mkdir -p {cand_dir}")

            # ─────────────────────────────────────────────────────────
            # STEP 1A: GOAL SETTING
            # ─────────────────────────────────────────────────────────
            # The goal-setter interprets the user goal and creates a
            # specific, actionable goal with reasoning

            goal_prompt = f"""
            User goal: {goal}

            # Context from previous rounds:
            {methodology_critique if methodology_critique else "First round - no prior context"}

            # Process improvements to apply:
            {process_updates if process_updates else "None yet"}

            # Top previous attempts (shader + score):
            {format_top_k(all_history, k=3)}

            Write your goal-setting document with:
            1. <interpretation> How you interpret the user's goal
            2. <specific_goal> The concrete, measurable goal you'll pursue
            3. <approach> High-level approach and why
            4. <key_insights> What you learned from previous attempts (if any)

            Save to: {cand_dir}/goals.md
            """
            chat(goal_prompt, model="sonnet")

            # ─────────────────────────────────────────────────────────
            # STEP 1B: EXECUTION (Plan + Shader)
            # ─────────────────────────────────────────────────────────
            # The executor reads the goal and creates a detailed plan
            # plus the actual shader

            goals_content = read(f"{cand_dir}/goals.md")

            execute_prompt = f"""
            Your goal document:
            {goals_content}

            Write TWO files:

            FILE 1: {cand_dir}/plan.md
            Include:
            - <mathematical_foundation> Key equations and concepts
            - <implementation_plan> Step-by-step how you'll code it
            - <anticipated_challenges> What might go wrong
            - <visual_prediction> What you expect the output to look like

            FILE 2: {cand_dir}/shader.glsl
            A complete GLSL fragment shader using:
            - uniform float u_time;
            - uniform vec2 u_resolution;
            - gl_FragColor for output

            The shader should implement your plan.
            """
            chat(execute_prompt, model="sonnet")

        # ════════════════════════════════════════════════════════════
        # PHASE 2: RENDER SHADERS
        # ════════════════════════════════════════════════════════════

        for candidate_num in range(candidates):
            cand_dir = f"{round_dir}/candidate_{candidate_num}"
            shader_path = f"{cand_dir}/shader.glsl"
            render_path = f"{cand_dir}/render.png"

            if exists(shader_path):
                success = render_shader(shader_path, render_path)
                if not success:
                    write(f"{cand_dir}/render_error.txt", "Shader failed to compile")

        # ════════════════════════════════════════════════════════════
        # PHASE 3: BLIND JUDGEMENT (parallel)
        # ════════════════════════════════════════════════════════════
        # Judge ONLY sees the rendered image, not the shader or plan

        for candidate_num in parallel(range(candidates)):
            cand_dir = f"{round_dir}/candidate_{candidate_num}"
            render_path = f"{cand_dir}/render.png"

            if exists(render_path):
                judge_prompt = f"""
                You are judging a rendered image for the goal: "{goal}"

                Look at the image at: {render_path}

                You do NOT see the shader code or the plan.
                Judge ONLY what you see in the output.

                Write to {cand_dir}/judgement.md:
                - <first_impression> What do you see? (2-3 sentences)
                - <goal_alignment> How well does this match "{goal}"? (1-10)
                - <visual_quality> Aesthetic quality assessment
                - <uniqueness> Is this novel or generic?
                - <critique> What's wrong? What could be better?
                - <score> Final score 1-10

                Also write {cand_dir}/score.json:
                {{"score": N, "one_line_reason": "..."}}
                """
                chat(judge_prompt, model="sonnet", images=[render_path])
            else:
                # No render - score 0
                write(f"{cand_dir}/judgement.md", "# Failed to render\nScore: 0")
                write(f"{cand_dir}/score.json", '{"score": 0, "one_line_reason": "render failed"}')

        # ════════════════════════════════════════════════════════════
        # PHASE 4: COLLECT ROUND RESULTS
        # ════════════════════════════════════════════════════════════

        for candidate_num in range(candidates):
            cand_dir = f"{round_dir}/candidate_{candidate_num}"
            score = load_json(f"{cand_dir}/score.json").get("score", 0)

            round_results.append({
                "candidate": candidate_num,
                "goals": read(f"{cand_dir}/goals.md"),
                "plan": read(f"{cand_dir}/plan.md"),
                "shader": read(f"{cand_dir}/shader.glsl"),
                "judgement": read(f"{cand_dir}/judgement.md"),
                "score": score
            })

            all_history.append((round_num, candidate_num, f"{cand_dir}/shader.glsl", score, f"{cand_dir}/judgement.md"))

        # ════════════════════════════════════════════════════════════
        # PHASE 5: METHODOLOGY CRITIC
        # ════════════════════════════════════════════════════════════
        # Analyzes ALL candidates from this round to understand what
        # methodology patterns led to success/failure

        critic_prompt = f"""
        You are analyzing Round {round_num + 1} of an evolutionary shader generation process.

        Original goal: {goal}

        Below are ALL candidates from this round with their:
        - Goal-setting reasoning
        - Execution plan
        - Shader code
        - Blind judgement (judge only saw render, not code)
        - Score

        {format_round_results(round_results)}

        ═══════════════════════════════════════════════════════════════

        Write TWO files:

        FILE 1: {round_dir}/methodology_critique.md

        Analyze deeply:
        - <winning_patterns> What did high-scoring candidates do right?
        - <losing_patterns> What did low-scoring candidates do wrong?
        - <goal_setting_analysis> Were goals well-specified? Too vague? Too ambitious?
        - <execution_analysis> Did plans translate well to shaders?
        - <math_analysis> Which mathematical approaches worked?
        - <aesthetic_analysis> What visual strategies succeeded?
        - <process_gaps> Where did the methodology fail?

        FILE 2: {round_dir}/process_updates.md

        Concrete improvements for next round:
        - <goal_setting_rules> New rules for setting goals
        - <execution_rules> New rules for planning/coding
        - <avoid_list> Specific things to NOT do
        - <try_list> Specific new approaches to try
        - <math_suggestions> Mathematical techniques to explore
        """
        chat(critic_prompt, model="opus")

        # Load the new process updates for next round
        methodology_critique = read(f"{round_dir}/methodology_critique.md")
        process_updates = read(f"{round_dir}/process_updates.md")

        log(f"Round {round_num + 1} complete. Best score: {max(r['score'] for r in round_results)}")

    # ════════════════════════════════════════════════════════════════
    # FINAL: Report best result
    # ════════════════════════════════════════════════════════════════

    best = max(all_history, key=lambda x: x[3])
    log(f"Best overall: Round {best[0]}, Candidate {best[1]}, Score {best[3]}")
    shell(f"imgcat {best[2].replace('.glsl', '.png').replace('shader', 'render')}")


# ════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════

def format_top_k(history, k=3):
    """Format top k previous attempts for context."""
    if not history:
        return "No previous attempts"

    sorted_history = sorted(history, key=lambda x: x[3], reverse=True)[:k]
    result = []
    for round_num, cand_num, shader_path, score, judgement_path in sorted_history:
        judgement = read(judgement_path)
        result.append(f"""
        ### Score {score} (Round {round_num}, Candidate {cand_num})
        Judgement summary: {extract_summary(judgement)}
        """)
    return "\n".join(result)

def format_round_results(results):
    """Format all results from a round for the methodology critic."""
    output = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        output.append(f"""
        ═══ Candidate {r['candidate']} ═══ Score: {r['score']}

        ## Goal Setting:
        {r['goals']}

        ## Execution Plan:
        {r['plan']}

        ## Shader Code:
        ```glsl
        {r['shader']}
        ```

        ## Blind Judgement:
        {r['judgement']}
        """)
    return "\n".join(output)
```

---

## Key Design Decisions

### 1. Separation of Concerns
- **Goal Setter**: Interprets what to do (strategic)
- **Executor**: Plans and implements (tactical)
- **Judge**: Evaluates output ONLY (blind to process)
- **Methodology Critic**: Analyzes what worked (meta-learning)

### 2. Blind Judgement
The judge **never sees** the shader code or plan. This:
- Prevents bias from "looks like good code"
- Forces evaluation based purely on visual output
- Mimics how end-users experience the result

### 3. Explicit Trace Files
Every step writes to files, so we can:
- Debug what went wrong
- Feed traces into prompts
- Build a dataset of goal → plan → shader → result
- Resume from any point

### 4. Process Evolution
The methodology critic generates **concrete process updates** that modify how future rounds:
- Set goals (more/less specific?)
- Plan execution (different math?)
- Avoid failures (don't repeat mistakes)

### 5. Accumulating Context
Each round receives:
- Original goal (constant)
- Methodology critique (what patterns work)
- Process updates (concrete rules)
- Top K previous attempts (examples to learn from)

---

## File Structure After 2 Rounds

```
traces/
├── round_0/
│   ├── candidate_0/
│   │   ├── goals.md
│   │   ├── plan.md
│   │   ├── shader.glsl
│   │   ├── render.png
│   │   ├── judgement.md
│   │   └── score.json
│   ├── candidate_1/
│   │   └── ...
│   ├── candidate_2/
│   │   └── ...
│   ├── methodology_critique.md    # Analysis of round 0
│   └── process_updates.md         # Rules for round 1
│
├── round_1/
│   ├── candidate_0/
│   │   └── ...
│   ├── methodology_critique.md    # Analysis of rounds 0+1
│   └── process_updates.md         # Rules for round 2
│
└── final_report.md                # Summary of entire run
```

---

## Questions for Confirmation

1. **Parallelism**: Should goal-setting and execution be separate LLM calls, or combined? (Current: separate for clearer traces)

2. **Model choices**:
   - Goal/Execute: sonnet (good reasoning, fast)
   - Judge: sonnet (vision capable)
   - Methodology Critic: opus (needs deep analysis)

   Sound right?

3. **Cross-candidate learning within round**: Should candidate 1's goal-setter see candidate 0's goals? (Current: no, they're parallel/independent)

4. **How many top-K to show**: Currently showing top 3 from all history. More? Less?

5. **Judgment granularity**: Current scoring is 1-10. Want more dimensions (novelty, quality, goal-fit)?
