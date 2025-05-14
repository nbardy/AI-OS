# examples/hello_macro.py
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    loops = kwargs.get("loops", 1)
    name = kwargs.get("name", "Test ")
    ah.log(f"Hello macro loops={loops}")
    for i in range(int(loops)):
        ah.log(f"Loop {i+1} of {loops}")
        chat_result = ah.chat(f"Say hello to {name} (loop {i+1})")
        ah.log(f"Chat result: {chat_result}")
        shell_result = ah.shell(f"echo 'Shell says hi to {name} (loop {i+1})'", capture=True)
        ah.log(f"Shell result: {shell_result}")
        approved = ah.approve(f"Continue after loop {i+1}?")
        if not approved:
            ah.log("User did not approve, stopping early.")
            break

    ah.log("Macro finished.")