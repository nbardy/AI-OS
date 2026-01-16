# examples/dummy_broken_macro.py
import ai_os as ai

def main(ctx, **kwargs):
    # Incorrect usage (causes AttributeError): ctx.log("...")
    # Corrected usage:
    ai.log("This is a log message that now works correctly")
    
    # You can still access variables from the 'ctx' dictionary if needed:
    # my_var = ai.get_var("some_arg_name", "default_value")
    # ai.log(f"My variable: {my_var}")
    
    print("This macro would work if ctx.log were ai.log")