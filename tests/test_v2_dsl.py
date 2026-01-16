#!/usr/bin/env python3
"""
Comprehensive test suite for AI-OS v2 DSL and orchestrator.
"""

import pytest
import tempfile
import os
from pathlib import Path

import ai_os as ai
from ai_os.core.orchestrator import ClaudeOrchestrator


class TestOrchestrator:
    """Test the Claude Code orchestrator."""

    def test_basic_chat(self):
        """Test basic chat functionality."""
        orch = ClaudeOrchestrator()
        response = orch.chat("Say 'test passed' and nothing else")
        assert "test" in response.lower() or "passed" in response.lower()

    def test_chat_json(self):
        """Test JSON parsing."""
        orch = ClaudeOrchestrator()
        result = orch.chat_json('Output this exact JSON: {"value": 42, "status": "ok"}')
        assert isinstance(result, dict)
        assert "value" in result or "status" in result

    def test_file_operations(self):
        """Test file read/write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # Write
            orch.write("test.txt", "hello world")

            # Check exists
            assert orch.exists("test.txt")

            # Read
            content = orch.read("test.txt")
            assert content == "hello world"

    def test_shell(self):
        """Test shell execution."""
        orch = ClaudeOrchestrator()
        output = orch.shell("echo 'test'", capture=True)
        assert "test" in output

    def test_gather(self):
        """Test parallel execution."""
        orch = ClaudeOrchestrator()
        results = orch.gather(
            "Say 'one'",
            "Say 'two'",
            model="haiku"
        )
        assert len(results) == 2
        assert any("one" in r.lower() for r in results)
        assert any("two" in r.lower() for r in results)


class TestDSL:
    """Test the DSL API."""

    def setup_method(self):
        """Reset orchestrator before each test."""
        from ai_os.core.orchestrator import reset_orchestrator
        reset_orchestrator()

    def test_log(self, capsys):
        """Test logging."""
        ai.log("test message")
        # Rich outputs to stderr usually, so we just check no errors

    def test_chat(self):
        """Test chat function."""
        response = ai.chat("Say 'dsl test' briefly")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_file_ops(self):
        """Test file operations via DSL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ai.config(working_dir=tmpdir)

            # Write
            ai.write("test.txt", "content")

            # Exists
            assert ai.exists("test.txt")

            # Read
            content = ai.read("test.txt")
            assert content == "content"

    def test_shell_capture(self):
        """Test shell with capture."""
        output = ai.shell("echo hello", capture=True)
        assert "hello" in output

    def test_get_set_var(self):
        """Test context variables."""
        ai.set_var("test_key", "test_value")
        value = ai.get_var("test_key")
        assert value == "test_value"

    def test_timestamp(self):
        """Test timestamp utility."""
        ts = ai.timestamp()
        assert isinstance(ts, str)
        assert len(ts) > 0

    def test_random_id(self):
        """Test random ID generation."""
        id1 = ai.random_id()
        id2 = ai.random_id()
        assert id1 != id2
        assert len(id1) == 8

    def test_gather_parallel(self):
        """Test parallel gather."""
        results = ai.gather(
            "Say 'alpha'",
            "Say 'beta'",
            "Say 'gamma'",
            model="haiku"
        )
        assert len(results) == 3


class TestIntegration:
    """Integration tests simulating macro usage."""

    def setup_method(self):
        """Reset orchestrator before each test."""
        from ai_os.core.orchestrator import reset_orchestrator
        reset_orchestrator()

    def test_simple_macro_flow(self):
        """Test a simple macro-like flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ai.config(working_dir=tmpdir)

            # Simulate a simple workflow
            ai.write("data.txt", "initial data")
            assert ai.exists("data.txt")

            content = ai.read("data.txt")
            assert content == "initial data"

            # Use shell
            exit_code = ai.shell("echo 'processed' > output.txt")
            assert exit_code == 0

            # Check result
            output = ai.shell("cat output.txt", capture=True)
            assert "processed" in output

    def test_cost_tracking(self):
        """Test that cost tracking works."""
        ai.chat("Hello", model="haiku")
        cost = ai.get_cost()
        assert isinstance(cost, dict)
        assert "input_tokens" in cost
        assert "output_tokens" in cost
        assert "total_cost_usd" in cost


if __name__ == "__main__":
    print("="*60)
    print("AI-OS v2 DSL Test Suite")
    print("="*60)

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
