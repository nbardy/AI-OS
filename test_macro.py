#!/usr/bin/env python3
"""Test macro to verify patch functionality works"""

from ai_os.core import macro_helpers

def main(ctx, **kwargs):
    """Test macro that generates a factorial function"""
    macro_helpers.log("Starting factorial function generation test")
    
    # Request patch to create factorial function
    plan = """
Generate a test file for the following goal:
write a factorial fn

The test should test the test_goal and import a file and functions to test

It should run tests and return a 0 exit code on success or non-zero on failure.
Keep the file simple

The test file should be in the file: test_factorial.py
"""
    
    macro_helpers.log("Requesting patch workflow...")
    result = macro_helpers.patch(plan, user_approval=True)
    
    if result and result.get("applied"):
        macro_helpers.log("Patch was successfully applied!")
    else:
        macro_helpers.log(f"Patch failed or was rejected: {result}")
    
    return result