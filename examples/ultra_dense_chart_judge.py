# examples/ultra_dense_chart_judge.py
"""
Ultra Dense Chart Judge - Generate chart from prompt, judge it.

V2: Uses Claude Code via ah.chat() and ah.vision() instead of OpenRouter.

Usage:
    /macro examples/ultra_dense_chart_judge.py prompt="Create a bar chart showing quarterly sales"
"""

import os
import re
import ai_os.core.macro_helpers as ah


def main(ctx, **kwargs):
    """
    Ultra dense chart judge macro.

    Args:
        prompt: Description of chart to create (default: quarterly sales bar chart)
    """
    prompt = kwargs.get('prompt', 'Create a bar chart showing quarterly sales growth')

    ah.log(f"[bold]Ultra Dense Chart Judge[/bold]")
    ah.log(f"[dim]Prompt: {prompt}[/dim]")

    # Step 1: Generate chart code using Claude
    ah.log("[cyan]Step 1: Generating chart code...[/cyan]")
    code_prompt = f"Write Python code to: {prompt}. Use matplotlib. Save as 'chart.png'. Just the code, no explanation."
    code = ah.chat(code_prompt, model="haiku")

    # Clean and save code
    code = code.strip().replace("```python", "").replace("```", "").strip()
    ah.write("chart_gen.py", code)
    ah.log("[green]Code generated and saved to chart_gen.py[/green]")

    # Step 2: Run the generated code
    ah.log("[cyan]Step 2: Running chart generation...[/cyan]")
    exit_code = ah.shell("python chart_gen.py")

    if exit_code != 0:
        ah.log("[red]Chart generation failed![/red]")
        return

    if not ah.exists("chart.png"):
        ah.log("[red]Chart file not created![/red]")
        return

    ah.log("[green]Chart generated: chart.png[/green]")

    # Step 3: Judge the chart using vision
    ah.log("[cyan]Step 3: Judging chart...[/cyan]")
    judge_prompt = f"Rate 1-10 how well this chart matches the request: '{prompt}'. Just give the number and a brief reason."
    response = ah.vision(judge_prompt, "chart.png", model="haiku")

    # Extract score
    score = re.search(r'\b([1-9]|10)\b', response)

    ah.log(f"\nChart: {os.path.abspath('chart.png')}")
    ah.log(f"Code: {os.path.abspath('chart_gen.py')}")
    if score:
        ah.log(f"[bold]Adherence Score: {score.group(0)}/10[/bold]")
    else:
        ah.log(f"Judge says: {response.strip()}")

    # Show cost
    cost = ah.get_cost()
    ah.log(f"[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")