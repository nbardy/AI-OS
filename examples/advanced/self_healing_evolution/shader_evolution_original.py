#!/usr/bin/env python3
"""Evolutionary GLSL shader generation - generates, renders, scores, iterates."""

import asyncio, re, sys
from pathlib import Path
import ai_os as ai

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from shader_renderer import render_shader

async def parallel(*coros): return await asyncio.gather(*coros)

def main(ctx, **kwargs):
    goal, rounds, n = kwargs.get("goal", "beautiful generative art"), int(kwargs.get("iterations", 3)), int(kwargs.get("candidates", 3))
    ai.shell("mkdir -p shaders renders")
    history = []  # Track previous attempts: [(shader_path, render_path, score), ...]

    for r in range(rounds):
        ai.log(f"\n[cyan]═══ Round {r+1}/{rounds} ═══[/cyan]")

        # Build context from history
        ctx_str = "\n".join(f"- {s} (score {sc}): {Path(p).name}" for s, p, sc in history[-6:]) if history else "None yet"

        # Generate shaders in parallel (native asyncio)
        gen_prompts = [f"Write GLSL shader to shaders/r{r}_c{i}.glsl for: {goal}. Use u_time, u_resolution, gl_FragColor.\nPrevious attempts:\n{ctx_str}\nBe creative, learn from scores." for i in range(n)]
        asyncio.run(parallel(*[ai.chat(p, model="haiku", async_=True) for p in gen_prompts]))

        # Render valid shaders
        rendered = [(i, f"shaders/r{r}_c{i}.glsl", str(Path(f"renders/r{r}_c{i}.png").resolve()))
                    for i in range(n) if ai.exists(f"shaders/r{r}_c{i}.glsl") and render_shader(f"shaders/r{r}_c{i}.glsl", f"renders/r{r}_c{i}.png")]

        # Score in parallel (native asyncio)
        if rendered:
            score_prompts = [f"Read image at {img}. Score 1-10 for '{goal}'. Reply: score: N" for _, _, img in rendered]
            responses = asyncio.run(parallel(*[ai.chat(p, model="sonnet", async_=True) for p in score_prompts]))
            for (i, shader, img), resp in zip(rendered, responses):
                score = int(m.group(1)) if (m := re.search(r'(\d+)', str(resp))) else 5
                history.append((shader, img, score))
                ai.log(f"  r{r}_c{i}: {score} → {img}")

    best = max(history, key=lambda x: x[2]) if history else None
    ai.log(f"\n[bold]Best: {best[2] if best else 0}[/bold]")
    if best:
        ai.log(f"[cyan]{best[1]}[/cyan]")
        ai.shell(f"imgcat {best[1]} 2>/dev/null || true")

if __name__ == "__main__":
    main({}, goal="swirling colors", iterations=2, candidates=2)
