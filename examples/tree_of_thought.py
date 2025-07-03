# examples/tree_of_thought_macro.py

import ai_os.core.macro_helpers as ah
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
Given the following 25 thoughts (numbered), synthesize a clear, comprehensive, and actionable answer.
Thoughts:
{all_thoughts}

Your Synthesis:
"""

async def get_initial_thoughts(problem):
    tasks = [
        ah.llm(INITIAL_THOUGHT_PROMPT.format(problem=problem, n=i+1))
        for i in range(5)
    ]
    return await asyncio.gather(*tasks)

async def get_branch_thoughts(initial_thoughts):
    tasks = []
    for i, thought in enumerate(initial_thoughts):
        for j in range(5):
            tasks.append(
                ah.llm(BRANCH_PROMPT.format(thought=thought, n=j+1))
            )
    return await asyncio.gather(*tasks)

def main(ctx, **kwargs):
    problem = kwargs.get("prompt") or kwargs.get("problem") or kwargs.get("question")
    if not problem:
        ah.log("Error: You must provide a 'prompt' or 'problem' argument.")
        ah.log("Usage: /macro examples/tree_of_thought_macro.py prompt='...'")
        return

    # Use asyncio event loop for parallel calls
    async def tree_of_thoughts(problem):
        ah.log("[bold]Generating initial thoughts...[/bold]")
        initial_thoughts = await get_initial_thoughts(problem)

        ah.log("[bold]Branching to 25 parallel thoughts...[/bold]")
        branch_thoughts = await get_branch_thoughts(initial_thoughts)

        ah.log("[bold]Synthesizing a final answer...[/bold]")
        numbered = "\n".join(f"{i+1}. {t.strip()}" for i, t in enumerate(branch_thoughts))
        synthesis = await ah.llm(SYNTHESIS_PROMPT.format(all_thoughts=numbered))
        return synthesis

    answer = asyncio.run(tree_of_thoughts(problem))
    ah.log("\n[bold green]Final Synthesized Answer:[/bold green]\n")
    print(answer)
