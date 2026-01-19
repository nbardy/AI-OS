# examples/basic_macro_demo.py
import ai_os as ai

def main(ctx, **kwargs):
    """
    A basic macro demonstrating common ai_os.core.macro_helpers (ah) functions.
    You can run this macro with:
    /macro examples/basic_macro_demo.py name="AI-OS User" count=3
    """
    
    # ai.get_var: Retrieve arguments passed to the macro
    user_name = ai.get_var("name", "User")
    loop_count = int(ai.get_var("count", 2)) # Default to 2 loops if not provided

    ai.log(f"Hello, {user_name}! This macro will perform {loop_count} iterations.")
    ai.log(f"Current context variables: {ctx.get('vars')}")

    for i in range(1, loop_count + 1):
        ai.log(f"\n--- Iteration {i}/{loop_count} ---")

        # ai.chat: Interact with the LLM
        chat_prompt = f"Tell me a short, inspiring quote for the iteration number {i}."
        ai.log(f"Asking LLM: '{chat_prompt}'")
        llm_response = ai.chat(chat_prompt)
        ai.log(f"LLM said: \"{llm_response.strip()}\"")

        # ai.shell: Execute a shell command
        # Demonstrates capturing output and checking exit code
        shell_command = f"echo 'Hello from shell for iteration {i} of {user_name}!'"
        ai.log(f"Running shell command: '{shell_command}'")
        shell_output = ai.shell(shell_command, capture=True)
        ai.log(f"Shell output: \"{shell_output.strip()}\"")
        
        exit_code = ai.get_last_shell_exit_code()
        if exit_code != 0:
            ai.log(f"[bold red]Shell command failed with exit code: {exit_code}[/bold red]")
        else:
            ai.log("[bold green]Shell command succeeded.[/bold green]")

        # ai.approve: Ask for user confirmation
        if i < loop_count: # Don't ask on the very last iteration
            if not ai.approve(f"Continue to the next iteration ({i+1}/{loop_count})?"):
                ai.log("User chose to stop early. Exiting macro.")
                break
        else:
            ai.log("Last iteration completed.")

    ai.log("Macro execution finished.")