from ai_os.core import macro_helpers as ah # if you adjust sys.path or install as package

def main(ctx, **kwargs):
    target_name = kwargs.get("name", "World")
    loops = int(kwargs.get("loops", 1))

    yield ah.log(f"Macro started. Target: {target_name}, Loops: {loops}")
    yield ah.log(f"Initial registers: {ctx.get('registers')}")
    
    for i in range(loops):
        yield ah.log(f"Loop {i+1}/{loops}")
        yield ah.chat(f"Tell me a fun fact about the name {target_name} or the number {i+1}.")
        
        # Example shell command with capture
        hostname_output = yield from ah.shell("hostname", capture_to="my_hostname")
        yield ah.log(f"Hostname was: {hostname_output.strip()}")
        yield ah.log(f"Hostname from register: {ah.get_register(ctx, 'my_hostname').strip()}")

        if ctx['last_shell_exit_code'] != 0:
            yield ah.log("Hostname command failed!")

    yield ah.log("Macro finished.")