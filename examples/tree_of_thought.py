# examples/tree_of_thought.py
"""
Tree of Thought Macro - Parallel brainstorming with synthesis.

This macro demonstrates the gather() pattern for parallel LLM calls.
It generates multiple initial thoughts, branches each into sub-thoughts,
then synthesizes everything into a final answer.

Usage:
    /macro examples/tree_of_thought.py question="How should we architect auth?"
"""

import ai_os.core.macro_helpers as ah

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


def get_initial_thoughts(problem: str, num_thoughts: int = 5) -> list:
    """Generate initial thoughts in parallel using gather()."""
    prompts = [
        INITIAL_THOUGHT_PROMPT.format(problem=problem, n=i+1)
        for i in range(num_thoughts)
    ]
    return ah.gather(*prompts, model="haiku")


def get_branch_thoughts(initial_thoughts: list, branches_per: int = 3) -> list:
    """Branch each initial thought in parallel using gather()."""
    prompts = []
    for i, thought in enumerate(initial_thoughts):
        for j in range(branches_per):
            prompts.append(
                BRANCH_PROMPT.format(thought=thought, n=j+1)
            )
    return ah.gather(*prompts, model="haiku")


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
        ah.log("[red]Error: You must provide a 'question', 'problem', or 'prompt' argument.[/red]")
        ah.log("Usage: /macro examples/tree_of_thought.py question='...'")
        return

    num_thoughts = int(kwargs.get("thoughts", 5))
    branches_per = int(kwargs.get("branches", 3))

    ah.log(f"[bold]Tree of Thought: {problem}[/bold]")
    ah.log(f"[dim]Config: {num_thoughts} initial thoughts, {branches_per} branches each[/dim]")

    # Phase 1: Generate initial thoughts in parallel
    ah.log(f"\n[cyan]Phase 1: Generating {num_thoughts} initial thoughts...[/cyan]")
    initial_thoughts = get_initial_thoughts(problem, num_thoughts)
    ah.log(f"[green]Generated {len(initial_thoughts)} initial thoughts[/green]")

    for i, thought in enumerate(initial_thoughts):
        ah.log(f"[dim]Thought {i+1}: {thought[:100]}...[/dim]")

    # Phase 2: Branch each thought in parallel
    total_branches = num_thoughts * branches_per
    ah.log(f"\n[cyan]Phase 2: Branching into {total_branches} sub-thoughts...[/cyan]")
    branch_thoughts = get_branch_thoughts(initial_thoughts, branches_per)
    ah.log(f"[green]Generated {len(branch_thoughts)} branch thoughts[/green]")

    # Phase 3: Synthesize all thoughts
    all_thoughts = initial_thoughts + branch_thoughts
    ah.log(f"\n[cyan]Phase 3: Synthesizing {len(all_thoughts)} thoughts...[/cyan]")

    numbered = "\n\n".join(
        f"{i+1}. {t.strip()[:500]}"
        for i, t in enumerate(all_thoughts)
    )

    synthesis = ah.chat(SYNTHESIS_PROMPT.format(all_thoughts=numbered))

    ah.log("\n[bold green]═══ Final Synthesized Answer ═══[/bold green]\n")
    ah.log(synthesis)

    # Show cost
    cost = ah.get_cost()
    ah.log(f"\n[dim]Total cost: ${cost['total_cost_usd']:.4f}[/dim]")
