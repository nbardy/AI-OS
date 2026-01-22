#!/usr/bin/env python3
"""
Shader Evolution Macro - Evolutionary GLSL shader generation.

Demonstrates:
- Parallel execution with gather()
- Code-based scoring (no external dependencies)
- Iterative improvement loop
- Human checkpoints

Usage:
    /macro examples/shader_evolution.py goal="aurora borealis" iterations=3
"""

import ai_os as ai


def main(ctx, **kwargs):
    """
    Evolutionary shader generation workflow.

    Generates multiple shader candidates in parallel, scores them by code quality,
    keeps the best, and iterates to improve quality.
    """
    goal = kwargs.get("goal", "beautiful generative art")
    iterations = int(kwargs.get("iterations", 3))
    num_candidates = int(kwargs.get("candidates", 5))

    ai.log(f"[bold]Shader Evolution: {goal}[/bold]")
    ai.log(f"[dim]{iterations} rounds, {num_candidates} candidates per round[/dim]")

    best_shader = None
    best_score = 0
    history = []

    # Create shaders directory
    ai.shell("mkdir -p shaders")

    for round_num in range(iterations):
        ai.log(f"\n[bold cyan]═══ Round {round_num + 1}/{iterations} ═══[/bold cyan]")

        # Step 1: Plan diverse approaches
        with ai.status("Planning approaches..."):
            plan = ai.chat_json(f"""
Goal: {goal}
Best score so far: {best_score}
Prior critiques: {history[-2:] if history else "None"}

Plan {num_candidates} VERY DIFFERENT GLSL shader approaches.
Each should use distinct mathematical techniques.

Output JSON: {{"approaches": ["approach 1", "approach 2", ...]}}
""", model="sonnet")
            approaches = plan.get("approaches", [f"Approach {i}" for i in range(num_candidates)])

        ai.log(f"[green]Planned {len(approaches)} approaches[/green]")

        # Step 2: Generate shaders in parallel
        with ai.status(f"Generating {len(approaches)} shaders..."):
            shader_prompts = [
                f"""Write a GLSL fragment shader to shaders/candidate_{i}.glsl implementing: {approach}

Requirements:
- uniform float u_time for animation
- uniform vec2 u_resolution for aspect ratio
- Output to gl_FragColor
- Be mathematically interesting

Use the Write tool to save the shader code to the specified file."""
                for i, approach in enumerate(approaches)
            ]
            ai.gather(*shader_prompts, model="haiku")

        ai.log(f"[green]Generated shaders[/green]")

        # Step 3: Score shaders by code quality
        ai.log("[cyan]Scoring shaders...[/cyan]")
        scores = []

        for i in range(len(approaches)):
            shader_path = f"shaders/candidate_{i}.glsl"

            if not ai.exists(shader_path):
                ai.log(f"[yellow]Skipping candidate_{i} (not written)[/yellow]")
                continue

            shader_code = ai.read(shader_path)

            score = ai.chat_json(f"""Score this GLSL shader 1-10 for goal: {goal}

```glsl
{shader_code[:800]}
```

Criteria: correctness, relevance, mathematical sophistication, visual appeal.
Be critical. Most are 4-6.

Output JSON: {{"score": N, "reason": "brief reason"}}
""", model="sonnet")

            scores.append((i, score.get("score", 0), score.get("reason", "")))
            ai.log(f"[dim]  candidate_{i}: {score.get('score', 0)} - {score.get('reason', '')[:50]}[/dim]")

        if not scores:
            ai.log("[red]No successful scores this round[/red]")
            continue

        # Step 4: Pick winner
        scores.sort(key=lambda x: x[1], reverse=True)
        winner_idx, winner_score, reason = scores[0]

        ai.log(f"[bold]Winner: candidate_{winner_idx} (score: {winner_score})[/bold]")

        if winner_score > best_score:
            best_score = winner_score
            best_shader = ai.read(f"shaders/candidate_{winner_idx}.glsl")
            ai.shell(f"cp shaders/candidate_{winner_idx}.glsl shaders/best.glsl")
            ai.log("[green]New best shader![/green]")

        # Step 5: Critique for next round
        if best_shader and (round_num + 1) < iterations:
            critique = ai.chat(f"""Briefly critique this shader (2-3 sentences):
- What works?
- What's missing for "{goal}"?

```glsl
{best_shader[:500]}
```
""", model="sonnet")
            history.append({"round": round_num + 1, "score": best_score, "critique": critique[:200]})

        # Human checkpoint every 2 rounds
        if (round_num + 1) % 2 == 0 and (round_num + 1) < iterations:
            cost = ai.get_cost()
            ai.log(f"\n[dim]Cost so far: ${cost['total_cost_usd']:.4f}[/dim]")
            if not ai.approve(f"Continue? Best score: {best_score}"):
                break

    # Final report
    ai.log(f"\n[bold green]═══ Evolution Complete ═══[/bold green]")
    ai.log(f"Final best score: {best_score}")
    ai.log(f"Best shader: shaders/best.glsl")

    cost = ai.get_cost()
    ai.log(f"\n[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")


if __name__ == "__main__":
    main({}, goal="swirling colors", iterations=2, candidates=3)
