#!/usr/bin/env python3
"""Evolutionary GLSL shader generation - generates, renders, scores, iterates."""

import re, sys
from pathlib import Path
import ai_os as ai

# Add renderer
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from shader_renderer import render_shader

def main(ctx, **kwargs):
    goal = kwargs.get("goal", "beautiful generative art")
    rounds = int(kwargs.get("iterations", 3))
    n = int(kwargs.get("candidates", 3))

    ai.shell("mkdir -p shaders renders")
    best_score, best_img = 0, None

    for r in range(rounds):
        ai.log(f"\n[cyan]═══ Round {r+1}/{rounds} ═══[/cyan]")

        # Generate shaders in parallel
        prompts = [f"Write GLSL shader to shaders/c{i}.glsl for: {goal}. Use u_time, u_resolution, gl_FragColor." for i in range(n)]
        ai.gather(*prompts, model="haiku")

        # Render and score
        scores = []
        for i in range(n):
            if ai.exists(f"shaders/c{i}.glsl") and render_shader(f"shaders/c{i}.glsl", f"renders/c{i}.png"):
                resp = ai.vision(f"Score 1-10 for '{goal}'. Reply: score: N", f"renders/c{i}.png", model="sonnet")
                score = int(re.search(r'(\d+)', resp).group(1)) if re.search(r'(\d+)', resp) else 5
                scores.append((i, score))
                ai.log(f"  c{i}: {score}")

        if scores:
            winner = max(scores, key=lambda x: x[1])
            if winner[1] > best_score:
                best_score, best_img = winner[1], Path(f"renders/c{winner[0]}.png").resolve()
                ai.log(f"[green]Winner: c{winner[0]} ({best_score})[/green]")

    ai.log(f"\n[bold]Best: {best_score}[/bold]")
    if best_img:
        ai.log(f"[cyan]{best_img}[/cyan]")
        ai.shell(f"imgcat {best_img} 2>/dev/null || true")

if __name__ == "__main__":
    main({}, goal="swirling colors", iterations=2, candidates=2)
