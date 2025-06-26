from ai_os.core import macro_helpers as ah # if you adjust sys.path or install as package

def main(ctx, **kwargs):
    target_name = kwargs.get("name", "World")
    loops = int(kwargs.get("loops", 1))

    ah.log(f"Macro started. Target: {target_name}, Loops: {loops}")
    ah.log(f"Initial variables: {ctx.get('vars')}")
    
    for i in range(loops):
        ah.log(f"Loop {i+1}/{loops}")
        ah.chat(f"Tell me a fun fact about the name {target_name} or the number {i+1}.")
        
        # Example shell command with capture
        hostname_output = ah.shell("hostname", capture=True)
        ah.log(f"Hostname was: {hostname_output.strip()}")
        
        # Check exit code
        exit_code = ah.get_last_shell_exit_code()
        if exit_code != 0:
            ah.log("Hostname command failed!")

    ah.log("Macro finished.")