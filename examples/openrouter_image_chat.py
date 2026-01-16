# examples/vision_demo.py
"""
Vision Demo Macro - Demonstrates image analysis with Claude Code.

V2: Uses Claude Code's native vision capability via ah.vision().

Usage:
    /macro examples/openrouter_image_chat.py
    /macro examples/openrouter_image_chat.py image_path="/path/to/image.png"
"""

from pathlib import Path
import ai_os.core.macro_helpers as ah


def main(ctx, **kwargs):
    """
    Vision demo macro - shows how to analyze images with Claude.

    Args:
        image_path: Optional path to an image file to analyze
    """
    ah.log("[bold]Vision Demo - Image Analysis with Claude Code[/bold]\n")

    image_path = kwargs.get("image_path")

    if image_path:
        # Analyze user-provided image
        ah.log(f"[cyan]Analyzing image: {image_path}[/cyan]")

        if not Path(image_path).exists():
            ah.log(f"[red]Image file not found: {image_path}[/red]")
            return

        response = ah.vision(
            "Please analyze this image in detail. Describe what you see.",
            image_path
        )
        ah.log(f"\n[green]Analysis:[/green]\n{response}")

    else:
        # Demo mode - create a simple test chart
        ah.log("[cyan]Demo mode: Creating a test chart to analyze...[/cyan]")

        # Generate a simple matplotlib chart
        chart_code = '''
import matplotlib.pyplot as plt

# Simple demo chart
fig, ax = plt.subplots(figsize=(8, 6))
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
values = [65, 70, 85, 80, 90, 95]
ax.bar(months, values, color='steelblue')
ax.set_title('Monthly Performance')
ax.set_ylabel('Score')
ax.set_xlabel('Month')
plt.savefig('demo_chart.png', dpi=100, bbox_inches='tight')
plt.close()
print('Chart saved to demo_chart.png')
'''

        ah.write("_chart_gen_temp.py", chart_code)
        exit_code = ah.shell("python _chart_gen_temp.py")

        if exit_code != 0:
            ah.log("[red]Failed to generate demo chart[/red]")
            return

        ah.log("[green]Demo chart created![/green]\n")

        # Analyze the chart
        ah.log("[cyan]Asking Claude to analyze the chart...[/cyan]\n")

        response = ah.vision(
            """Analyze this chart:
1. What type of chart is this?
2. What does it show?
3. What trends do you notice?
4. Rate the visual quality (1-10)""",
            "demo_chart.png"
        )

        ah.log(f"[green]Claude's Analysis:[/green]\n{response}")

        # Cleanup
        ah.shell("rm -f _chart_gen_temp.py")

    # Show cost
    cost = ah.get_cost()
    ah.log(f"\n[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")


# Note: This script is designed to be run as a macro:
#   /macro examples/openrouter_image_chat.py
#
# Claude Code natively supports vision - just pass an image path to ah.vision()
# Claude will read the image file directly using its Read tool.