# examples/hello_macro.py
import ai_os as ai

def main(ctx, **kwargs):
    loops = kwargs.get("loops", 1)
    name = kwargs.get("name", "Test ")
    ai.log(f"Hello macro loops={loops}")
    for i in range(int(loops)):
        ai.log(f"Loop {i+1} of {loops}")
        chat_result = ai.chat(f"Say hello to {name} (loop {i+1})")
        ai.log(f"Chat result: {chat_result}")
        shell_result = ai.shell(f"echo 'Shell says hi to {name} (loop {i+1})'", capture=True)
        ai.log(f"Shell result: {shell_result}")
        approved = ai.approve(f"Continue after loop {i+1}?")
        if not approved:
            ai.log("User did not approve, stopping early.")
            break

    ai.log("Macro finished.")