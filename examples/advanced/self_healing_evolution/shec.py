#!/usr/bin/env python3
"""
Self-Healing Evolutionary Critique (SHEC)

An evolutionary shader generation algorithm where the process itself evolves.
Each round produces shaders AND critiques of methodology that improve future rounds.

Usage:
    @self_healing_evolution/shec.py goal="hopf fibration art" rounds=3 candidates=5
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path

import ai_os as ai

# Add utils to path for shader renderer
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "utils"))
from shader_renderer import render_shader

# Import prompt templates
from prompts.goal_setter import GOAL_SETTER_PROMPT
from prompts.executor import EXECUTOR_PROMPT
from prompts.judge import JUDGE_PROMPT
from prompts.methodology_critic import METHODOLOGY_CRITIC_PROMPT
from prompts.global_learner import GLOBAL_LEARNER_PROMPT
from prompts.tiered_guidance import get_initial_guidance


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def read_file(path) -> str:
    p = Path(path) if not isinstance(path, Path) else path
    return p.read_text() if p.exists() else ""

def write_file(path, content: str):
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)

def load_json(path) -> dict:
    try:
        return json.loads(read_file(path))
    except:
        return {}

def slugify(text: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', text.lower())
    return slug.strip('_')[:50]

def extract_goal_section(goals_content: str, goal_num: int) -> str:
    pattern = rf"## Goal {goal_num}:.*?(?=## Goal \d+:|$)"
    match = re.search(pattern, goals_content, re.DOTALL)
    return match.group(0).strip() if match else f"Goal {goal_num} not found"

def format_top_k(history: list, k: int = 3) -> str:
    if not history:
        return "No previous attempts yet."
    valid = [h for h in history if isinstance(h.get("score"), (int, float))]
    sorted_hist = sorted(valid, key=lambda x: x["score"], reverse=True)[:k]
    parts = []
    for h in sorted_hist:
        parts.append(f"- **{h['score']}/10** {h['subgoal_title']}: {h['judge_summary']}")
    return "\n".join(parts) if parts else "No successful renders yet."

def format_round_results(results: list) -> str:
    parts = []
    for r in sorted(results, key=lambda x: x["score"] if isinstance(x["score"], (int, float)) else -1, reverse=True):
        score_display = f"{r['score']}/10" if isinstance(r["score"], (int, float)) else r["score"]
        parts.append(f"""
═══ CANDIDATE {r['candidate_num']} ({r.get('role', '?')}) — {score_display} ═══

**Goal:** {r['goal']}

**Shader Code:**
```glsl
{r['shader']}
```

**Judge Verdict:**
{r['judgement']}
""")
    return "\n".join(parts)

def extract_mandatory(guidance: str) -> str:
    """Extract just the MANDATORY section from tiered guidance."""
    # Try various header formats the critic might use
    for pattern in [
        r"## MANDATORY.*?(?=##|\Z)",
        r"## TIER 1:.*?(?=##|\Z)",
    ]:
        match = re.search(pattern, guidance, re.DOTALL)
        if match:
            return match.group(0).strip()
    # Fallback: return first 20 lines
    lines = guidance.strip().split("\n")
    return "\n".join(lines[:20])

def list_tried_approaches(history: list) -> str:
    """Format a simple list of what approaches have been tried."""
    if not history:
        return "No previous attempts."
    seen = []
    for h in history:
        role = h.get("role", "unknown")
        title = h.get("subgoal_title", "untitled")
        score = h.get("score", "?")
        score_str = f"{score}/10" if isinstance(score, (int, float)) else str(score)
        seen.append(f"- [{role}] {title} -> {score_str}")
    return "\n".join(seen)

def get_role_distribution(n: int, has_history: bool) -> list:
    """Assign roles: baseline (1), iterative (~40%), exploratory (~40%).
    Each entry is (role, harness) where harness is 'claude' or 'codex'.
    Alternates harnesses so ~half use codex."""
    if n <= 2:
        roles = ["iterative", "exploratory"][:n]
    else:
        roles = ["baseline"] if has_history else ["iterative"]
        remaining = n - 1
        roles.extend(["iterative"] * (remaining // 2))
        roles.extend(["exploratory"] * (remaining - remaining // 2))
    return roles


def get_executor_harnesses(n: int) -> list:
    """Assign harnesses to candidates: alternate claude/codex so ~half use each."""
    return ["claude" if i % 2 == 0 else "codex" for i in range(n)]

def get_role_context(role: str, history: list, best_shader: str = "") -> str:
    """Role context - ALL candidates get the best shader as starting point."""

    # Common reference: best shader code (if available)
    shader_ref = ""
    if best_shader:
        shader_ref = f"""
## Reference: Best Shader So Far
Start from this working code. It compiles, renders, and scored well.
```glsl
{best_shader[:2000]}
```
"""

    if role == "baseline":
        return f"""{shader_ref}
## Your Role: BASELINE (preserve what works)
Make only 1-2 minimal tweaks: color adjustment, camera angle, small parameter change.
DO NOT restructure, add features, or change the core approach.
Your job is to ensure we don't regress."""

    elif role == "iterative":
        top3 = format_top_k(history, 3)
        return f"""{shader_ref}
## Your Role: ITERATIVE (evolve the approach)
Modify the reference shader's rendering technique, colors, or geometry.
You can make structural changes (different glow model, better ray marching, new color palette).
Keep what works, improve one or two things that could be better.

What scored well previously:
{top3}"""

    else:  # exploratory
        return f"""{shader_ref}
## Your Role: EXPLORATORY (try something new)
Use the reference as a foundation for something creative.
You may radically restructure it, but start from working code rather than blank page.
Change the visual approach, try a new technique, explore a novel direction.
The reference ensures your camera, coordinates, and GPU budget start from a working baseline."""


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main(ctx, **kwargs):
    goal = kwargs.get("goal", "beautiful generative art")
    rounds = int(kwargs.get("rounds", 3))
    n_candidates = int(kwargs.get("candidates", 5))

    base_dir = Path(__file__).parent
    traces_dir = base_dir / "traces"

    # Campaign folder for persistence
    campaign_slug = slugify(goal)
    campaign_dir = base_dir / "campaigns" / campaign_slug
    ai.shell(f"mkdir -p {traces_dir} {campaign_dir}")

    learnings_path = campaign_dir / "learnings.md"
    guidance_path = campaign_dir / "tiered_guidance.md"

    global_learnings = read_file(learnings_path)
    tiered_guidance = read_file(guidance_path) or get_initial_guidance()

    ai.log(f"[bold cyan]═══ SHEC: Self-Healing Evolutionary Critique ═══[/bold cyan]")
    ai.log(f"Goal: {goal} | Rounds: {rounds} | Candidates: {n_candidates}")

    all_history = []

    for round_num in range(rounds):
        round_dir = traces_dir / f"round_{round_num}"
        ai.shell(f"mkdir -p {round_dir}")
        ai.log(f"\n[cyan]═══ Round {round_num + 1}/{rounds} ═══[/cyan]")

        # Assign roles and harnesses
        roles = get_role_distribution(n_candidates, bool(all_history))
        harnesses = get_executor_harnesses(n_candidates)
        ai.log(f"  Roles: {list(zip(roles, harnesses))}")

        # ════════════════════════════════════════════════════════════
        # PHASE 1: GOAL SETTING (for exploratory candidates)
        # ════════════════════════════════════════════════════════════

        goals_path = round_dir / "goals.md"
        n_exploratory = roles.count("exploratory")

        if n_exploratory > 0:
            ai.log("  [dim]Generating goals...[/dim]")
            goal_prompt = GOAL_SETTER_PROMPT.format(
                n=n_exploratory,
                main_goal=goal,
                global_learnings=global_learnings or "First run - no learnings yet.",
                tried_approaches=list_tried_approaches(all_history),
                mandatory_constraints=extract_mandatory(tiered_guidance),
                output_path=goals_path
            )
            ai.chat(goal_prompt, model="o4-mini", harness="codex", reasoning_effort="high")

        goals_content = read_file(goals_path)

        # ════════════════════════════════════════════════════════════
        # PHASE 2: EXECUTION (parallel)
        # ════════════════════════════════════════════════════════════

        ai.log("  [dim]Executing shaders...[/dim]")

        # Get best shader for baseline role
        valid_history = [h for h in all_history if isinstance(h.get("score"), (int, float))]
        best_shader = ""
        if valid_history:
            best = max(valid_history, key=lambda x: x["score"])
            best_shader = read_file(best["shader_path"])

        async def execute_candidate(cand_num: int, role: str, exploratory_idx: int, harness: str):
            cand_dir = round_dir / f"candidate_{cand_num}"
            ai.shell(f"mkdir -p {cand_dir}")

            plan_path = cand_dir / "plan.md"
            shader_path = cand_dir / "shader.glsl"

            # Build context based on role
            role_context = get_role_context(role, all_history, best_shader)

            if role == "exploratory":
                assigned_goal = extract_goal_section(goals_content, exploratory_idx)
                role_context += f"\n\n**Your creative direction:**\n{assigned_goal}"

            exec_prompt = EXECUTOR_PROMPT.format(
                assigned_goal=role_context,
                execution_guidance=tiered_guidance,
                plan_path=plan_path,
                shader_path=shader_path
            )

            # Use assigned harness: claude → sonnet, codex → o4-mini
            exec_model = "sonnet" if harness == "claude" else "o4-mini"
            await ai.chat(exec_prompt, model=exec_model, harness=harness, async_=True)

        async def run_executors():
            exploratory_idx = 0
            tasks = []
            for i, role in enumerate(roles):
                h = harnesses[i]
                if role == "exploratory":
                    tasks.append(execute_candidate(i, role, exploratory_idx, h))
                    exploratory_idx += 1
                else:
                    tasks.append(execute_candidate(i, role, -1, h))
            await asyncio.gather(*tasks)

        asyncio.run(run_executors())

        # ════════════════════════════════════════════════════════════
        # PHASE 3: RENDER
        # ════════════════════════════════════════════════════════════

        ai.log("  [dim]Rendering...[/dim]")

        for cand_num in range(n_candidates):
            cand_dir = round_dir / f"candidate_{cand_num}"
            shader_path = cand_dir / "shader.glsl"
            render_path = cand_dir / "render.png"
            status_path = cand_dir / "render_status.json"

            if not shader_path.exists():
                write_file(status_path, json.dumps({"status": "NO_SHADER"}))
                ai.log(f"    ✗ C{cand_num}: NO_SHADER")
                continue

            success = render_shader(str(shader_path), str(render_path))

            if success and render_path.exists():
                write_file(status_path, json.dumps({"status": "SUCCESS"}))
                ai.log(f"    ✓ C{cand_num}")
            else:
                write_file(status_path, json.dumps({"status": "COMPILATION_ERROR"}))
                ai.log(f"    ✗ C{cand_num}: COMPILATION_ERROR")
                time.sleep(0.3)

        # ════════════════════════════════════════════════════════════
        # PHASE 4: JUDGE (parallel)
        # ════════════════════════════════════════════════════════════

        ai.log("  [dim]Judging...[/dim]")

        async def judge_candidate(cand_num: int):
            cand_dir = round_dir / f"candidate_{cand_num}"
            render_path = cand_dir / "render.png"
            judgement_path = cand_dir / "judgement.md"
            score_path = cand_dir / "score.json"
            status = load_json(cand_dir / "render_status.json")

            if status.get("status") != "SUCCESS":
                write_file(judgement_path, f"# Render Failed\nStatus: {status.get('status')}")
                write_file(score_path, json.dumps({"score": status.get("status"), "one_line": "Render failed"}))
                return

            # Get subgoal title for judge
            if roles[cand_num] == "exploratory":
                exp_idx = sum(1 for i in range(cand_num) if roles[i] == "exploratory")
                subgoal = extract_goal_section(goals_content, exp_idx)
                title_match = re.search(r"## Goal \d+: (.+)", subgoal)
                subgoal_title = title_match.group(1) if title_match else f"Exploratory {cand_num}"
            else:
                subgoal_title = f"{roles[cand_num].capitalize()} approach"

            judge_prompt = JUDGE_PROMPT.format(
                main_goal=goal,
                subgoal=subgoal_title,
                render_path=str(render_path.resolve()),
                judgement_path=judgement_path,
                score_path=score_path
            )

            await ai.chat(judge_prompt, model="sonnet", images=[str(render_path.resolve())], async_=True)

        async def run_judges():
            await asyncio.gather(*[judge_candidate(i) for i in range(n_candidates)])

        asyncio.run(run_judges())

        # ════════════════════════════════════════════════════════════
        # PHASE 5: COLLECT RESULTS
        # ════════════════════════════════════════════════════════════

        round_results = []
        for cand_num in range(n_candidates):
            cand_dir = round_dir / f"candidate_{cand_num}"
            score_data = load_json(cand_dir / "score.json")
            score = score_data.get("score", 0)
            if isinstance(score, str) and score not in ("COMPILATION_ERROR", "NO_SHADER"):
                try: score = float(score)
                except: pass

            # Get subgoal title
            if roles[cand_num] == "exploratory":
                exp_idx = sum(1 for i in range(cand_num) if roles[i] == "exploratory")
                assigned_goal = extract_goal_section(goals_content, exp_idx)
                title_match = re.search(r"## Goal \d+: (.+)", assigned_goal)
                subgoal_title = title_match.group(1) if title_match else f"Exploratory {cand_num}"
            else:
                assigned_goal = f"[{roles[cand_num]}]"
                subgoal_title = f"{roles[cand_num].capitalize()} approach"

            result = {
                "candidate_num": cand_num,
                "role": roles[cand_num],
                "goal": assigned_goal,
                "plan": read_file(cand_dir / "plan.md"),
                "shader": read_file(cand_dir / "shader.glsl"),
                "judgement": read_file(cand_dir / "judgement.md"),
                "score": score
            }
            round_results.append(result)

            all_history.append({
                "round": round_num,
                "candidate": cand_num,
                "role": roles[cand_num],
                "subgoal_title": subgoal_title,
                "score": score,
                "judge_summary": score_data.get("one_line", ""),
                "shader_path": str(cand_dir / "shader.glsl"),
                "render_path": str(cand_dir / "render.png")
            })

            score_display = f"{score}/10" if isinstance(score, (int, float)) else score
            ai.log(f"    C{cand_num} ({roles[cand_num]}): {score_display} — {subgoal_title}")

        # ════════════════════════════════════════════════════════════
        # PHASE 6: METHODOLOGY CRITIQUE (single call)
        # ════════════════════════════════════════════════════════════

        ai.log("  [dim]Analyzing & updating guidance...[/dim]")

        critique_path = round_dir / "methodology_critique.md"
        updates_path = round_dir / "process_updates.md"

        critic_prompt = METHODOLOGY_CRITIC_PROMPT.format(
            main_goal=goal,
            round_results=format_round_results(round_results),
            existing_guidance=tiered_guidance,
            critique_path=critique_path,
            updates_path=updates_path
        )

        ai.chat(critic_prompt, model="opus")

        # Update guidance for next round
        tiered_guidance = read_file(updates_path)
        write_file(guidance_path, tiered_guidance)

        # Report best
        valid_results = [r for r in round_results if isinstance(r["score"], (int, float))]
        if valid_results:
            best = max(valid_results, key=lambda x: x["score"])
            ai.log(f"  [green]Best: {best['score']}/10 ({best['role']})[/green]")

    # ════════════════════════════════════════════════════════════════
    # GLOBAL LEARNINGS
    # ════════════════════════════════════════════════════════════════

    valid_history = [h for h in all_history if isinstance(h.get("score"), (int, float))]
    if valid_history:
        best = max(valid_history, key=lambda x: x["score"])

        # Build rich run summary with full critiques per round
        run_summary_parts = []
        run_summary_parts.append("## Score Summary")
        run_summary_parts.append("\n".join([
            f"- {h['score']}/10 [{h['role']}]: {h['subgoal_title']}"
            for h in sorted(all_history, key=lambda x: x["score"] if isinstance(x["score"], (int, float)) else -1, reverse=True)
        ]))

        # Include full critiques from each round
        for r in range(rounds):
            round_dir = traces_dir / f"round_{r}"
            critique = read_file(round_dir / "methodology_critique.md")
            if critique:
                run_summary_parts.append(f"\n### Round {r+1} Critique")
                run_summary_parts.append(critique)

        run_summary = "\n".join(run_summary_parts)

        learner_prompt = GLOBAL_LEARNER_PROMPT.format(
            goal=goal,
            existing_learnings=global_learnings or "First run.",
            new_insights=run_summary,
            best_score=best["score"],
            best_approach=best["subgoal_title"],
            output_path=learnings_path
        )
        ai.chat(learner_prompt, model="opus")

        ai.log(f"\n[bold green]═══ COMPLETE ═══[/bold green]")
        ai.log(f"Best: R{best['round']}C{best['candidate']} ({best['role']}) — {best['score']}/10")
        ai.log(f"[cyan]{best['render_path']}[/cyan]")
        ai.shell(f"imgcat {best['render_path']} 2>/dev/null || true")


if __name__ == "__main__":
    main({}, goal="hopf fibration", rounds=2, candidates=3)
