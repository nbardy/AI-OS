import ai_os.core.macro_helpers as ah
import sys 
import os

# Ensure the macro is run from the project root or handle paths carefully.
# The MacroRunner sets the CWD to the macro's directory (e.g., examples/).
# Paths like tests/foo.py and src/foo.py provided as arguments are likely
# expected relative to the project root. We'll assume `pytest` is run
# in a way that finds these files, e.g., if pytest is configured correctly.

def main(ctx, **kwargs):
    """
    Implements a simple TDD (Test-Driven Development) workflow.

    Arguments:
        test_file (str): Path to the test file to create/update (relative to project root).
        code_file (str): Path to the production code file to create/update (relative to project root).
        test_command (str, optional): The command to run tests. Defaults to "pytest".
    """
    test_file = kwargs.get("test_file")
    code_file = kwargs.get("code_file")
    test_command = kwargs.get("test_command", "pytest") 

    if not test_file or not code_file:
        ah.log("Error: test_file and code_file arguments are required.")
        ah.log("Usage: /macro examples/tdd_macro.py test_file=<path> code_file=<path> [test_command='...']")
        return

    ah.log(f"Starting TDD Macro for test: {test_file}, code: {code_file}")

    # --- Stage 1: Write Test ---
    ah.log("\n--- Stage 1: Write Test ---")
    test_approved = False
    # Keep proposing and patching the test file until the user approves.
    while not test_approved:
        ah.log(f"Attempting to write or refine test in {test_file}...")
        # The plan asks the LLM to write the test first, aiming for a failing state
        patch_plan = (
            f"Write or update the test file '{test_file}'. "
            f"The purpose is to define the expected behavior for the code to be written in '{code_file}'. "
            f"Ensure the test is well-formed and should *fail* currently if '{code_file}' doesn't exist or is not implemented according to the plan."
        )

        # Call ah.patch which handles LLM call, parsing, preview, and user Y/N approval.
        # If user rejects, ah.patch returns applied=False.
        patch_result = ah.patch(patch_plan, user_approval=True)

        if patch_result and patch_result.get('applied'):
            ah.log(f"Test patch for {test_file} applied.")
            test_approved = True
        elif patch_result and 'error' in patch_result:
             ah.log(f"[Error] Failed to apply test patch for {test_file}: {patch_result['error']}")
             # Decide how to handle critical patch errors here. Maybe break the loop?
             # For now, print error and continue prompt loop, letting user decide to quit or refine.
        else:
            # User rejected the patch, the loop continues to propose again.
            ah.log(f"Test patch for {test_file} rejected by user. Retrying...")

    ah.log("[bold green]Test writing stage complete. Test patch approved.[/bold green]")


    # --- Stage 2: Write Code and Pass Test ---
    ah.log("\n--- Stage 2: Write Code and Pass Test ---")
    max_attempts = 5
    test_passed = False

    for attempt in range(1, max_attempts + 1):
        if test_passed:
            break # Exit loop early if test passes
            
        ah.log(f"Attempt {attempt} of {max_attempts} to write code and pass tests.")
        ah.log(f"Attempting to write or refine code in {code_file}...")
        # The plan asks the LLM to write the code that passes the test
        code_plan = (
            f"Write or update the code file '{code_file}'."
            f"The goal is to make the tests defined in '{test_file}' pass."
            f"Refer to the content of '{test_file}' (in context) to guide the implementation in '{code_file}'."
        )

        # Call ah.patch. It will again ask for user approval by default.
        # We continue the loop if rejected or an error occurs.
        patch_result = ah.patch(code_plan, user_approval=True) 

        if not patch_result or not patch_result.get('applied'):
             if patch_result and 'error' in patch_result:
                  ah.log(f"[Error] Failed to apply code patch for {code_file}: {patch_result['error']}")
             else:
                  ah.log(f"Code patch for {code_file} rejected by user.")
             # Continue to the next attempt if rejected or error, without running the test yet.
             continue 

        ah.log(f"Code patch for {code_file} applied via commit {patch_result.get('sha', 'N/A')}. Running tests...")
        
        # Run the test command. We expect `test_command {test_file}` to work
        # from the current working directory (which is the macro's parent dir, e.g. examples/).
        full_test_command = f"{test_command} {test_file}"
        ah.log(f"$ {full_test_command}")
        
        # Capture=False lets subprocess output directly, which is good for test runners
        shell_result = ah.shell(full_test_command, capture=False) 
        
        exit_code = ah.get_last_shell_exit_code()
        ah.log(f"Test command exited with code: {exit_code}")

        # Check if the test passed (standard exit code 0 indicates success)
        if isinstance(exit_code, int) and exit_code == 0:
            ah.log("[bold green]Tests passed![/bold green]")
            test_passed = True # Set flag to exit the loop
        else:
            ah.log("[bold yellow]Tests failed.[/bold yellow]")
            if attempt < max_attempts:
                ah.log(f"Tests failed. Retrying code patch generation (Attempt {attempt+1})...")
            else:
                ah.log("[bold red]Maximum code attempts reached. Tests still failing.[/bold red]")

    ah.log("\n--- TDD Macro Finished ---")
    if test_passed:
        ah.log("[bold green]TDD Cycle Complete: Tests passed successfully.[/bold green]")
    else:
        ah.log("[bold red]TDD Cycle Halted: Tests did not pass after maximum attempts.[/bold red]")