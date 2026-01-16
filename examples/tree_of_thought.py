# examples/tree_of_thought.py
"""
Tree of Thought Macro - Parallel brainstorming with synthesis.

This macro demonstrates the async_=True pattern for parallel LLM calls.
It generates multiple initial thoughts, branches each into sub-thoughts,
then synthesizes everything into a final answer.

Usage:
    /macro examples/tree_of_thought.py question="How should we architect auth?"
"""

import ai_os as ai
import asyncio

INITIAL_THOUGHT_PROMPT = """You are part of a brainstorming team. Based on the following problem, generate an insightful and creative approach, idea, or step.
Problem: {problem}
Thought #{n}
"""

BRANCH_PROMPT = """Given this prior thought, extend or branch off with a new, creative direction, detail, or solution. Be original.
Prior Thought: {thought}
Branch #{n}
"""

SYNTHESIS_PROMPT = """
You are the synthesizer for a brainstorming tree.
Given the following thoughts (numbered), synthesize a clear, comprehensive, and actionable answer.
Thoughts:
{all_thoughts}

Your Synthesis:
"""


async def get_initial_thoughts(problem: str, num_thoughts: int = 5) -> list:
    """Generate initial thoughts in parallel."""
    tasks = [
        ai.chat(
            INITIAL_THOUGHT_PROMPT.format(problem=problem, n=i+1),
            async_=True
        )
        for i in range(num_thoughts)
    ]
    return await asyncio.gather(*tasks)


async def get_branch_thoughts(initial_thoughts: list, branches_per: int = 3) -> list:
    """Branch each initial thought in parallel."""
    tasks = []
    for i, thought in enumerate(initial_thoughts):
        for j in range(branches_per):
            tasks.append(
                ai.chat(
                    BRANCH_PROMPT.format(thought=thought, n=j+1),
                    async_=True
                )
            )
    return await asyncio.gather(*tasks)


def main(ctx, **kwargs):
    """
    Tree of Thought reasoning macro.

    Args:
        question/problem/prompt: The question to reason about
        thoughts: Number of initial thoughts (default: 5)
        branches: Branches per thought (default: 3)
    """
    # Get the question from various possible arg names
    problem = (
        kwargs.get("question") or
        kwargs.get("problem") or
        kwargs.get("prompt")
    )

    if not problem:
        ai.log("[red]Error: You must provide a 'question', 'problem', or 'prompt' argument.[/red]")
        ai.log("Usage: /macro examples/tree_of_thought.py question='...'")
        return

    num_thoughts = int(kwargs.get("thoughts", 5))
    branches_per = int(kwargs.get("branches", 3))

    ai.log(f"[bold]Tree of Thought: {problem}[/bold]")
    ai.log(f"[dim]Config: {num_thoughts} initial thoughts, {branches_per} branches each[/dim]")

    async def run_tree_of_thought():
        # Phase 1: Generate initial thoughts in parallel
        ai.log(f"\n[cyan]Phase 1: Generating {num_thoughts} initial thoughts...[/cyan]")
        initial_thoughts = await get_initial_thoughts(problem, num_thoughts)
        ai.log(f"[green]Generated {len(initial_thoughts)} initial thoughts[/green]")

        for i, thought in enumerate(initial_thoughts):
            ai.log(f"[dim]Thought {i+1}: {thought[:100]}...[/dim]")

        # Phase 2: Branch each thought in parallel
        total_branches = num_thoughts * branches_per
        ai.log(f"\n[cyan]Phase 2: Branching into {total_branches} sub-thoughts...[/cyan]")
        branch_thoughts = await get_branch_thoughts(initial_thoughts, branches_per)
        ai.log(f"[green]Generated {len(branch_thoughts)} branch thoughts[/green]")

        # Phase 3: Synthesize all thoughts
        all_thoughts = initial_thoughts + branch_thoughts
        ai.log(f"\n[cyan]Phase 3: Synthesizing {len(all_thoughts)} thoughts...[/cyan]")

        numbered = "\n\n".join(
            f"{i+1}. {t.strip()[:500]}"
            for i, t in enumerate(all_thoughts)
        )

        synthesis = ai.chat(SYNTHESIS_PROMPT.format(all_thoughts=numbered))
        return synthesis

    # Run the async workflow
    answer = asyncio.run(run_tree_of_thought())

    ai.log("\n[bold green]═══ Final Synthesized Answer ═══[/bold green]\n")
    ai.log(answer)

    # Show cost
    cost = ai.get_cost()
    ai.log(f"\n[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")
