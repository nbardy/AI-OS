#!/usr/bin/env python3
"""
Chart Judge Macro - Draw chart, have Claude judge quality.

V2: Uses Claude Code via ah.vision() instead of OpenRouter.

Usage:
    /macro examples/chart_judge_macro.py
"""

import matplotlib.pyplot as plt
import ai_os.core.macro_helpers as ah


def draw_chart() -> str:
    """Generate sample chart and save to file."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Sales trend
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May']
    sales = [120, 135, 125, 145, 160]
    ax1.plot(months, sales, 'bo-', linewidth=2, markersize=8)
    ax1.set_title('Q1 Sales Trend', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Sales ($k)')
    ax1.grid(True, alpha=0.3)

    # Market share
    companies = ['Us', 'CompA', 'CompB', 'Other']
    shares = [35, 25, 20, 20]
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#95a5a6']
    ax2.pie(shares, labels=companies, colors=colors, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Market Share', fontsize=14, fontweight='bold')

    plt.tight_layout()

    # Save to file (Claude Code can read image files)
    chart_path = "chart_to_judge.png"
    plt.savefig(chart_path, format='png', dpi=150, bbox_inches='tight')
    plt.close()

    return chart_path


def main(ctx, **kwargs):
    """
    Chart Judge macro - generates a chart and has Claude judge it.
    """
    ah.log("[bold]Chart Judge Macro[/bold]")

    # Generate chart
    ah.log("[cyan]Generating sample chart...[/cyan]")
    chart_path = draw_chart()
    ah.log(f"[green]Chart saved: {chart_path}[/green]")

    # Have Claude judge the chart using vision
    ah.log("[cyan]Asking Claude to judge the chart...[/cyan]")

    judge_prompt = """Rate this business chart (1-10) on:
    - Clarity: Is the data easy to understand?
    - Professionalism: Does it look polished?
    - Insight value: Does it convey useful information?

    Be critical and explain your ratings."""

    response = ah.vision(judge_prompt, chart_path)

    ah.log("\n[bold green]Chart Judge Says:[/bold green]")
    ah.log(response)

    # Show cost
    cost = ah.get_cost()
    ah.log(f"\n[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")