#!/usr/bin/env python3
"""
Shader Evolution Macro - Evolutionary GLSL shader generation.

Demonstrates:
- Parallel execution with gather()
- Vision analysis
- Iterative improvement loop
- Human checkpoints

Usage:
    /macro examples/shader_evolution.py goal="aurora borealis" iterations=3
"""

import ai_os as ai


def main(ctx, **kwargs):
    """
    Evolutionary shader generation workflow.

    Generates multiple shader candidates in parallel, renders and scores them,
    keeps the best, and iterates to improve quality.

    Args:
        goal: Description of desired shader (default: "beautiful generative art")
        iterations: Number of evolution rounds (default: 3)
        candidates: Shaders per round (default: 5)
    """
    goal = kwargs.get("goal", "beautiful generative art")
    iterations = int(kwargs.get("iterations", 3))
    num_candidates = int(kwargs.get("candidates", 5))

    ai.log(f"[bold]Shader Evolution: {goal}[/bold]")
    ai.log(f"[dim]{iterations} rounds, {num_candidates} candidates per round[/dim]")

    best_shader = None
    best_score = 0
    history = []

    for round_num in range(iterations):
        ai.log(f"\n[bold cyan]═══ Round {round_num + 1}/{iterations} ═══[/bold cyan]")

        # Step 1: Plan diverse approaches
        with ai.status("Planning approaches..."):
            plan_prompt = f"""
            Goal: {goal}
            Best score so far: {best_score}
            Prior critiques: {history[-2:] if history else "None"}

            Plan {num_candidates} VERY DIFFERENT GLSL shader approaches.
            Each should use distinct mathematical techniques.

            Output JSON: {{"approaches": ["approach 1", "approach 2", ...]}}
            """

            plan = ai.chat_json(plan_prompt, model="sonnet")
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

            results = ai.gather(*shader_prompts, model="haiku")

        # Log results
        ai.log(f"[green]Generated {len(results)} shaders[/green]")

        # Step 3: Render shaders (if glslviewer available)
        ai.log("[dim]Rendering shaders...[/dim]")

        # Create renders directory
        ai.shell("mkdir -p renders")

        # Check if glslviewer is available
        glslviewer_available = ai.shell("which glslviewer", capture=True) != ""

        if not glslviewer_available:
            ai.log("[yellow]glslviewer not installed - skipping renders[/yellow]")
            ai.log("[dim]Install with: brew install glslviewer (macOS) or apt-get install glslviewer (Linux)[/dim]")
        else:
            for i in range(len(approaches)):
                shader_path = f"shaders/candidate_{i}.glsl"
                if ai.exists(shader_path):
                    # Try to render - ignore failures
                    ai.shell(
                        f"glslviewer {shader_path} -s 5 -o renders/candidate_{i}.png 2>/dev/null || true"
                    )

        # Step 4: Score renders with vision model (only if we have renders)
        ai.log("[cyan]Scoring renders...[/cyan]")
        scores = []

        for i in range(len(approaches)):
            render_path = f"renders/candidate_{i}.png"

            if not ai.exists(render_path):
                ai.log(f"[yellow]Skipping candidate_{i} (no render)[/yellow]")
                continue

            score_prompt = f"""Score this shader render 1-10:
- Visual complexity
- Mathematical elegance
- Aesthetic beauty
- How well it matches: {goal}

Be critical. Most are 4-6.

Output JSON: {{"score": N, "reason": "brief reason"}}
"""
            try:
                score_data = ai.vision(score_prompt, render_path, model="sonnet")
                # Parse JSON from response
                import json
                score_obj = json.loads(score_data) if isinstance(score_data, str) else score_data
                scores.append((i, score_obj.get("score", 0), score_obj.get("reason", "")))
            except Exception as e:
                ai.log(f"[yellow]Scoring failed for candidate_{i}: {e}[/yellow]")
                scores.append((i, 0, "scoring failed"))

        if not scores:
            ai.log("[red]No successful scores this round[/red]")
            continue

        # Step 5: Pick winner
        scores.sort(key=lambda x: x[1], reverse=True)
        winner_idx, winner_score, reason = scores[0]

        ai.log(f"[bold]Winner: candidate_{winner_idx} (score: {winner_score})[/bold]")
        ai.log(f"[dim]{reason}[/dim]")

        if winner_score > best_score:
            best_score = winner_score
            best_shader = ai.read(f"shaders/candidate_{winner_idx}.glsl")
            ai.shell(f"cp shaders/candidate_{winner_idx}.glsl shaders/best.glsl")
            ai.shell(f"cp renders/candidate_{winner_idx}.png renders/best.png 2>/dev/null || true")
            ai.log("[green]New best shader![/green]")

        # Step 6: Critique for next round
        if best_shader and (round_num + 1) < iterations:
            critique = ai.chat(
                f"""Analyze this shader critically:
- What works?
- What's missing?
- How to improve?

Shader:
{best_shader[:500]}
""",
                model="sonnet"
            )
            history.append({
                "round": round_num + 1,
                "score": best_score,
                "critique": critique[:300]
            })

        # Human checkpoint
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
    # Allow running standalone for testing
    main({}, goal="swirling colors", iterations=2, candidates=3)
