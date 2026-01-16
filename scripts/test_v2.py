#!/usr/bin/env python3
"""
Test script for AI-OS v2 - Run this outside a Claude session to verify integration.

Usage:
    cd /path/to/ai-os_2
    source .venv/bin/activate
    python scripts/test_v2.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test all imports work."""
    print("Testing imports...")

    # Core imports
    from ai_os.core.orchestrator import ClaudeOrchestrator, get_orchestrator
    print("  ✓ orchestrator")

    from ai_os.core.macro_helpers import chat, edit, vision, log
    print("  ✓ macro_helpers")

    from ai_os.core.macro_runner import MacroRunner
    print("  ✓ macro_runner")

    from ai_os.core.commands import chat as chat_cmd, patch, search
    print("  ✓ commands")

    # Top-level import
    import ai_os as ai
    print("  ✓ ai_os")

    print("All imports successful!\n")
    return True


def test_orchestrator_init():
    """Test orchestrator initialization."""
    print("Testing orchestrator initialization...")

    from ai_os.core.orchestrator import ClaudeOrchestrator

    orch = ClaudeOrchestrator()
    print(f"  Working dir: {orch.working_dir}")
    print(f"  Default model: {orch.default_model}")
    print(f"  Claude command: {orch._claude_cmd}")
    print("  ✓ Orchestrator initialized\n")
    return True


def test_file_operations():
    """Test direct file operations."""
    print("Testing file operations...")

    from ai_os.core.orchestrator import ClaudeOrchestrator
    import tempfile

    orch = ClaudeOrchestrator(working_dir=tempfile.gettempdir())

    # Write
    test_file = "ai_os_test_file.txt"
    test_content = "Hello from AI-OS v2!"
    orch.write(test_file, test_content)
    print(f"  ✓ write({test_file})")

    # Exists
    assert orch.exists(test_file), f"{test_file} should exist"
    print(f"  ✓ exists({test_file})")

    # Read
    content = orch.read(test_file)
    assert content == test_content, f"Content mismatch: {content}"
    print(f"  ✓ read({test_file})")

    # Cleanup
    os.remove(os.path.join(tempfile.gettempdir(), test_file))
    print("File operations successful!\n")
    return True


def test_shell():
    """Test shell command execution."""
    print("Testing shell execution...")

    from ai_os.core.orchestrator import ClaudeOrchestrator

    orch = ClaudeOrchestrator()

    # Simple command
    exit_code = orch.shell("echo 'Hello from shell'")
    assert exit_code == 0, f"Expected 0, got {exit_code}"
    print("  ✓ shell() exit code")

    # Capture output
    output = orch.shell("echo 'captured'", capture=True)
    assert "captured" in output, f"Expected 'captured' in output: {output}"
    print("  ✓ shell(capture=True)")

    print("Shell operations successful!\n")
    return True


def test_claude_chat(skip_if_no_claude=True):
    """Test actual Claude Code chat (requires Claude CLI)."""
    print("Testing Claude Code chat...")

    import shutil
    if not shutil.which("claude") and not shutil.which("npx"):
        if skip_if_no_claude:
            print("  ⏭ Skipped (Claude CLI not found)\n")
            return True
        else:
            print("  ✗ Claude CLI not found")
            return False

    from ai_os.core.orchestrator import ClaudeOrchestrator

    orch = ClaudeOrchestrator(timeout=60)

    try:
        response = orch.chat("Say 'test passed' and nothing else.", model="haiku")
        print(f"  Response: {response[:100]}...")
        print("  ✓ Claude chat successful")

        cost = orch.get_cost()
        print(f"  Cost: ${cost['total_cost_usd']:.4f}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    print("Claude chat successful!\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("AI-OS v2 Integration Test")
    print("=" * 60 + "\n")

    tests = [
        ("Imports", test_imports),
        ("Orchestrator Init", test_orchestrator_init),
        ("File Operations", test_file_operations),
        ("Shell Operations", test_shell),
        ("Claude Chat", lambda: test_claude_chat(skip_if_no_claude=True)),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ {name} failed with exception: {e}\n")
            results.append((name, False))

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
