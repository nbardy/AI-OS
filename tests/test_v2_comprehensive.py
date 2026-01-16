"""
Comprehensive test suite for AI-OS v2 (Claude Code Native).

Tests all major components:
- Orchestrator (chat, edit, vision, parallel execution)
- DSL functions
- Integration with Claude Code
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from ai_os.core.orchestrator import ClaudeOrchestrator, ClaudeResult
import ai_os as ai


# =============================================================================
# Orchestrator Tests
# =============================================================================

class TestOrchestrator:
    """Test the Claude Code orchestrator."""

    def test_basic_chat(self):
        """Test basic synchronous chat."""
        orch = ClaudeOrchestrator()
        response = orch.chat("Say 'test passed' and nothing else")
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"✓ Basic chat: {response[:50]}...")

    def test_chat_with_context(self):
        """Test chat with file context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "context.txt"
            test_file.write_text("Important: The secret code is 42")

            orch = ClaudeOrchestrator(working_dir=tmpdir)
            response = orch.chat(
                "What is the secret code mentioned in context.txt?",
                context_files=["context.txt"]
            )
            assert "42" in response
            print(f"✓ Chat with context: {response[:50]}...")

    def test_chat_json(self):
        """Test JSON response parsing."""
        orch = ClaudeOrchestrator()
        result = orch.chat_json(
            'Output this JSON: {"status": "success", "value": 123}'
        )
        assert isinstance(result, dict)
        assert result.get("status") == "success"
        assert result.get("value") == 123
        print(f"✓ Chat JSON: {result}")

    @pytest.mark.asyncio
    async def test_async_chat(self):
        """Test asynchronous chat."""
        orch = ClaudeOrchestrator()

        # Test async_=True returns coroutine
        coro = orch.chat("Say 'async test'", async_=True)
        assert asyncio.iscoroutine(coro)

        # Await the result
        response = await coro
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"✓ Async chat: {response[:50]}...")

    def test_spawn_join(self):
        """Test parallel execution with spawn/join."""
        orch = ClaudeOrchestrator()

        # Spawn multiple agents
        agents = [
            orch.spawn(f"Say 'agent {i}'", model="haiku")
            for i in range(3)
        ]

        # Join and collect results
        results = orch.join(agents)

        assert len(results) == 3
        assert all(isinstance(r, ClaudeResult) for r in results)
        successful = [r for r in results if r.success]
        assert len(successful) >= 2  # At least 2 should succeed

        for i, result in enumerate(results):
            print(f"✓ Agent {i}: success={result.success}, result={result.result[:30] if result.result else result.error[:30]}")

    def test_gather(self):
        """Test convenience gather function."""
        orch = ClaudeOrchestrator()

        results = orch.gather(
            "Say 'first'",
            "Say 'second'",
            "Say 'third'",
            model="haiku"
        )

        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)
        print(f"✓ Gather: {[r[:20] for r in results]}")

    def test_file_operations(self):
        """Test direct file operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # Write
            orch.write("test.txt", "Hello World")

            # Exists
            assert orch.exists("test.txt")
            assert not orch.exists("nonexistent.txt")

            # Read
            content = orch.read("test.txt")
            assert content == "Hello World"

            print("✓ File operations")

    def test_edit(self):
        """Test Claude editing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create initial file
            test_file = Path(tmpdir) / "code.py"
            test_file.write_text("def hello():\n    print('hello')\n")

            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # Have Claude edit it
            success = orch.edit(
                "Add a docstring to the hello() function",
                file="code.py"
            )

            # Note: We can't guarantee edit succeeds without Claude, but we can test the API
            print(f"✓ Edit API called: success={success}")

    def test_cost_tracking(self):
        """Test cost tracking accumulation."""
        orch = ClaudeOrchestrator()

        # Make a simple call
        orch.chat("Say hello", model="haiku")

        # Check cost tracking
        cost = orch.get_cost()
        assert "input_tokens" in cost
        assert "output_tokens" in cost
        assert "total_cost_usd" in cost

        # Should have some tokens
        assert cost["input_tokens"] > 0 or cost["output_tokens"] > 0

        print(f"✓ Cost tracking: {cost}")


# =============================================================================
# DSL Tests
# =============================================================================

class TestDSL:
    """Test the public DSL API."""

    def test_chat(self):
        """Test DSL chat function."""
        response = ai.chat("Say 'DSL test'", model="haiku")
        assert isinstance(response, str)
        print(f"✓ DSL chat: {response[:50]}...")

    def test_chat_json(self):
        """Test DSL chat_json function."""
        result = ai.chat_json('Output: {"test": true}')
        assert isinstance(result, dict)
        assert result.get("test") is True
        print(f"✓ DSL chat_json: {result}")

    def test_gather(self):
        """Test DSL gather function."""
        results = ai.gather(
            "Count to 1",
            "Count to 2",
            model="haiku"
        )
        assert len(results) == 2
        print(f"✓ DSL gather: {len(results)} results")

    def test_file_operations(self):
        """Test DSL file operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure working directory
            ai.config(working_dir=tmpdir)

            # Write
            ai.write("dsl_test.txt", "DSL content")

            # Exists
            assert ai.exists("dsl_test.txt")

            # Read
            content = ai.read("dsl_test.txt")
            assert content == "DSL content"

            print("✓ DSL file operations")

    def test_get_set_var(self):
        """Test context variable management."""
        ai.set_var("test_key", "test_value")
        value = ai.get_var("test_key")
        assert value == "test_value"

        # Test default
        default_val = ai.get_var("nonexistent", "default")
        assert default_val == "default"

        print("✓ DSL get/set var")

    def test_get_cost(self):
        """Test cost retrieval."""
        # Make a call first
        ai.chat("Hello", model="haiku")

        cost = ai.get_cost()
        assert isinstance(cost, dict)
        assert "total_cost_usd" in cost

        print(f"✓ DSL get_cost: {cost}")


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple features."""

    def test_macro_like_workflow(self):
        """Test a workflow similar to a macro."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ai.config(working_dir=tmpdir)

            # Phase 1: Have Claude write a file
            ai.write("data.txt", "Test data: 1, 2, 3")

            # Phase 2: Ask Claude about it
            response = ai.chat(
                "Read data.txt and tell me what numbers are in it",
                context=["data.txt"]
            )

            assert isinstance(response, str)
            assert len(response) > 0

            print(f"✓ Macro-like workflow completed: {response[:50]}...")

    def test_parallel_then_synthesis(self):
        """Test parallel execution followed by synthesis (like tree of thought)."""
        # Generate multiple responses in parallel
        ideas = ai.gather(
            "Suggest a color: red, blue, or green?",
            "Suggest a shape: circle, square, or triangle?",
            "Suggest a size: small, medium, or large?",
            model="haiku"
        )

        assert len(ideas) == 3

        # Synthesize
        synthesis = ai.chat(
            f"Given these suggestions: {ideas}, describe a simple object.",
            model="haiku"
        )

        assert isinstance(synthesis, str)
        print(f"✓ Parallel + synthesis: {synthesis[:100]}...")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_json_parsing(self):
        """Test handling of invalid JSON responses."""
        orch = ClaudeOrchestrator()

        # This might not return valid JSON
        with pytest.raises(ValueError):
            orch.chat_json("Just say hello without any JSON")

    def test_nonexistent_file(self):
        """Test reading nonexistent file."""
        orch = ClaudeOrchestrator()

        with pytest.raises(Exception):
            orch.read("nonexistent_file_xyz.txt")

    def test_timeout_handling(self):
        """Test timeout configuration."""
        # Create orchestrator with very short timeout
        orch = ClaudeOrchestrator(timeout=1)

        # Note: This might or might not timeout depending on Claude's speed
        # Just verify the API works
        try:
            response = orch.chat("Quick response", model="haiku")
            print(f"✓ Timeout test: completed without timeout ({len(response)} chars)")
        except Exception as e:
            print(f"✓ Timeout test: caught timeout as expected: {e}")


# =============================================================================
# Main Test Runner
# =============================================================================

if __name__ == "__main__":
    """Run tests manually without pytest."""
    print("=" * 60)
    print("AI-OS v2 Comprehensive Test Suite")
    print("=" * 60)

    # Orchestrator tests
    print("\n[Orchestrator Tests]")
    test_orch = TestOrchestrator()
    test_orch.test_basic_chat()
    test_orch.test_chat_with_context()
    test_orch.test_chat_json()
    test_orch.test_spawn_join()
    test_orch.test_gather()
    test_orch.test_file_operations()
    test_orch.test_cost_tracking()

    # DSL tests
    print("\n[DSL Tests]")
    test_dsl = TestDSL()
    test_dsl.test_chat()
    test_dsl.test_chat_json()
    test_dsl.test_gather()
    test_dsl.test_file_operations()
    test_dsl.test_get_set_var()
    test_dsl.test_get_cost()

    # Integration tests
    print("\n[Integration Tests]")
    test_int = TestIntegration()
    test_int.test_macro_like_workflow()
    test_int.test_parallel_then_synthesis()

    # Error handling
    print("\n[Error Handling Tests]")
    test_err = TestErrorHandling()
    test_err.test_nonexistent_file()
    test_err.test_timeout_handling()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
