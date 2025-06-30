# examples/dummy_broken_macro.py
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    # Incorrect usage (causes AttributeError): ctx.log("...")
    # Corrected usage:
    ah.log("This is a log message that now works correctly")
    
    # You can still access variables from the 'ctx' dictionary if needed:
    # my_var = ah.get_var("some_arg_name", "default_value")
    # ah.log(f"My variable: {my_var}")
    
    print("This macro would work if ctx.log were ah.log")