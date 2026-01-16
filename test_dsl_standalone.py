#!/usr/bin/env python3
"""Test DSL functions can be used standalone (outside macros)."""

import ai_os as ai

def test_log():
    """Test logging works."""
    print("\n=== Testing ai.log ===")
    ai.log("This is a test log message")
    ai.log("[green]Green text[/green]")
    print("✓ Log test passed")

def test_chat():
    """Test chat works."""
    print("\n=== Testing ai.chat ===")
    response = ai.chat("Say 'standalone DSL works' and nothing else")
    print(f"Response: {response}")
    assert "standalone" in response.lower() or "dsl" in response.lower() or "works" in response.lower()
    print("✓ Chat test passed")

def test_file_ops():
    """Test file operations."""
    print("\n=== Testing file operations ===")
    
    # Write
    ai.write("test_dsl_file.txt", "Hello from DSL")
    
    # Check exists
    assert ai.exists("test_dsl_file.txt")
    
    # Read
    content = ai.read("test_dsl_file.txt")
    assert content == "Hello from DSL"
    
    # Clean up
    import os
    os.remove("test_dsl_file.txt")
    
    print("✓ File operations test passed")

if __name__ == "__main__":
    print("=" * 60)
    print("DSL Standalone Tests")
    print("=" * 60)
    
    test_log()
    test_chat()
    test_file_ops()
    
    print("\n" + "=" * 60)
    print("ALL DSL TESTS PASSED ✓")
    print("=" * 60)
