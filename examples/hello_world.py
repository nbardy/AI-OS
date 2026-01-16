import ai_os as ai  # v2 API

def main(ctx, **kwargs):
    """
    Hello World macro - demonstrates basic AI-OS v2 API.

    Args:
        name: Target name (default: World)
        loops: Number of loops (default: 1)
    """
    target_name = kwargs.get("name", "World")
    loops = int(kwargs.get("loops", 1))

    ai.log(f"Macro started. Target: {target_name}, Loops: {loops}")
    ai.log(f"Initial variables: {ctx.get('vars')}")

    for i in range(loops):
        ai.log(f"Loop {i+1}/{loops}")
        response = ai.chat(f"Tell me a fun fact about the name {target_name} or the number {i+1}.")
        ai.log(f"AI says: {response[:100]}...")

        # Example shell command with capture
        hostname_output = ai.shell("hostname", capture=True)
        ai.log(f"Hostname: {hostname_output.strip()}")

    ai.log("Macro finished.")

# Legacy ah alias is still available if needed:
# from ai_os.core import macro_helpers as ah