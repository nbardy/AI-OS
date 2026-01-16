"""Quick test to verify gather() works for parallel execution."""
import ai_os as ai

# Test with 3 simple prompts in parallel
print("[bold]Testing parallel gather()...[/bold]")
results = ai.gather(
    "Say 'alpha'",
    "Say 'beta'",
    "Say 'gamma'",
    model="haiku"
)

print(f"\n[green]Got {len(results)} results:[/green]")
for i, r in enumerate(results):
    print(f"{i+1}. {r[:100]}")

print("\n[bold green]gather() test passed![/bold green]")
