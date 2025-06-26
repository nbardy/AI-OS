# examples/basic_macro_demo.py
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    """
    A basic macro demonstrating common ai_os.core.macro_helpers (ah) functions.
    You can run this macro with:
    /macro examples/basic_macro_demo.py name="AI-OS User" count=3
    """
    
    # ah.get_var: Retrieve arguments passed to the macro
    user_name = ah.get_var("name", "User")
    loop_count = int(ah.get_var("count", 2)) # Default to 2 loops if not provided

    ah.log(f"Hello, {user_name}! This macro will perform {loop_count} iterations.")
    ah.log(f"Current context variables: {ctx.get('vars')}")

    for i in range(1, loop_count + 1):
        ah.log(f"\n--- Iteration {i}/{loop_count} ---")

        # ah.chat: Interact with the LLM
        chat_prompt = f"Tell me a short, inspiring quote for the iteration number {i}."
        ah.log(f"Asking LLM: '{chat_prompt}'")
        llm_response = ah.chat(chat_prompt)
        ah.log(f"LLM said: \"{llm_response.strip()}\"")

        # ah.shell: Execute a shell command
        # Demonstrates capturing output and checking exit code
        shell_command = f"echo 'Hello from shell for iteration {i} of {user_name}!'"
        ah.log(f"Running shell command: '{shell_command}'")
        shell_output = ah.shell(shell_command, capture=True)
        ah.log(f"Shell output: \"{shell_output.strip()}\"")
        
        exit_code = ah.get_last_shell_exit_code()
        if exit_code != 0:
            ah.log(f"[bold red]Shell command failed with exit code: {exit_code}[/bold red]")
        else:
            ah.log("[bold green]Shell command succeeded.[/bold green]")

        # ah.approve: Ask for user confirmation
        if i < loop_count: # Don't ask on the very last iteration
            if not ah.approve(f"Continue to the next iteration ({i+1}/{loop_count})?"):
                ah.log("User chose to stop early. Exiting macro.")
                break
        else:
            ah.log("Last iteration completed.")

    ah.log("Macro execution finished.")