"""
Integration tests for AI-OS v2 (Claude Code native backend).

These tests verify that the orchestrator and macro helpers work correctly
with Claude Code as the execution substrate.
"""

import pytest
import tempfile
import os
import asyncio
from pathlib import Path

from ai_os.core.orchestrator import ClaudeOrchestrator, get_orchestrator, reset_orchestrator


class TestOrchestratorBasics:
    """Test basic orchestrator functionality."""

    def setup_method(self):
        """Reset orchestrator before each test."""
        reset_orchestrator()

    def test_orchestrator_creation(self):
        """Test that we can create an orchestrator instance."""
        orch = ClaudeOrchestrator()
        assert orch is not None
        assert orch.default_model == "sonnet"

    def test_get_orchestrator_singleton(self):
        """Test that get_orchestrator returns consistent instance."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2

    def test_file_read_write(self):
        """Test direct file operations without Claude."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # Write a file
            test_content = "Hello from AI-OS v2"
            orch.write("test.txt", test_content)

            # Read it back
            read_content = orch.read("test.txt")
            assert read_content == test_content

            # Check existence
            assert orch.exists("test.txt")
            assert not orch.exists("nonexistent.txt")

    def test_shell_execution(self):
        """Test shell command execution."""
        orch = ClaudeOrchestrator()

        # Test exit code
        exit_code = orch.shell("echo 'test'")
        assert exit_code == 0

        # Test capture
        output = orch.shell("echo 'hello world'", capture=True)
        assert "hello world" in output.lower()

        # Test non-zero exit
        exit_code = orch.shell("exit 42")
        assert exit_code == 42

    def test_cost_tracking(self):
        """Test that cost tracking structure exists."""
        orch = ClaudeOrchestrator()
        cost = orch.get_cost()

        assert isinstance(cost, dict)
        assert "input_tokens" in cost
        assert "output_tokens" in cost
        assert "total_cost_usd" in cost
        assert cost["input_tokens"] == 0
        assert cost["output_tokens"] == 0


class TestOrchestratorLLMOperations:
    """Test LLM operations that call Claude Code.

    These tests make real API calls and may be slow.
    Use pytest -m "not slow" to skip them.
    """

    @pytest.mark.slow
    def test_basic_chat(self):
        """Test basic synchronous chat."""
        orch = ClaudeOrchestrator()

        response = orch.chat("Say 'orchestrator test passed' and nothing else", model="haiku")

        assert isinstance(response, str)
        assert len(response) > 0
        # Should get some response - the exact content may vary
        assert len(response) > 5  # Should be a meaningful response

    @pytest.mark.slow
    def test_chat_json(self):
        """Test JSON response parsing."""
        orch = ClaudeOrchestrator()

        result = orch.chat_json(
            'Output this exact JSON and nothing else: {"status": "ok", "value": 42}',
            model="haiku"
        )

        assert isinstance(result, dict)
        assert "status" in result or "value" in result

    @pytest.mark.slow
    def test_chat_with_context_files(self):
        """Test chat with file context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # Create a context file
            orch.write("data.txt", "The secret number is 42")

            # Ask about it
            response = orch.chat(
                "What is the secret number in data.txt?",
                context_files=["data.txt"],
                model="haiku"
            )

            assert "42" in response

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_async_chat(self):
        """Test asynchronous chat with asyncio.gather."""
        orch = ClaudeOrchestrator()

        # Run 3 prompts in parallel
        results = await asyncio.gather(
            orch.chat("Say 'one'", model="haiku", async_=True),
            orch.chat("Say 'two'", model="haiku", async_=True),
            orch.chat("Say 'three'", model="haiku", async_=True),
        )

        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)
        assert all(len(r) > 0 for r in results)

    @pytest.mark.slow
    def test_streaming_chat(self):
        """Test streaming chat response."""
        orch = ClaudeOrchestrator()

        chunks = []
        for chunk in orch.chat_streaming("Say hello", model="haiku"):
            chunks.append(chunk)
            # Should be getting string chunks
            assert isinstance(chunk, str)

        # Should have received multiple chunks
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0


class TestMacroHelpersIntegration:
    """Test that macro_helpers properly integrates with orchestrator."""

    def test_macro_helpers_import(self):
        """Test that macro helpers can be imported."""
        import ai_os.core.macro_helpers as ah
        import ai_os as ai

        # Check that key functions exist
        assert callable(ah.log)
        assert callable(ah.chat)
        assert callable(ah.edit)
        assert callable(ah.read)
        assert callable(ah.write)
        assert callable(ah.shell)
        assert callable(ah.approve)

        # Check ai_os module exports
        assert callable(ai.chat)
        assert callable(ai.log)

    def test_file_operations_via_helpers(self):
        """Test file operations through macro helpers in isolation."""
        from ai_os.core.orchestrator import ClaudeOrchestrator
        from ai_os.core.macro_runner import MacroRunner
        from rich.console import Console
        import ai_os.core.macro_helpers as ah

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            console = Console()
            runner = MacroRunner(console)

            try:
                # Install runner
                ah.set_runner(runner)

                # Test write/read/exists via helpers
                ah.write("test.txt", "hello macro")
                assert ah.exists("test.txt")
                content = ah.read("test.txt")
                assert content == "hello macro"

            finally:
                ah.set_runner(None)


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_simple_macro_workflow(self):
        """Simulate a simple macro workflow."""
        from ai_os.core.macro_runner import MacroRunner
        from ai_os.core.orchestrator import reset_orchestrator
        from rich.console import Console
        import shutil

        reset_orchestrator()

        # Use a persistent temp dir that we control cleanup for
        tmpdir = tempfile.mkdtemp()
        original_cwd = tmpdir  # We'll start from tmpdir

        try:
            # First ensure we're in a valid directory
            os.chdir(tmpdir)

            # Create a simple test macro
            macro_path = Path(tmpdir) / "test_macro.py"
            macro_path.write_text("""
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    name = kwargs.get("name", "world")
    ah.log(f"Hello {name}")
    ah.write("output.txt", f"Macro ran with name={name}")
""")

            # Run it
            console = Console()
            runner = MacroRunner(console)
            runner.run(f"{macro_path} name=test")

            # Check output - should be in the macro's directory (tmpdir)
            output_file = Path(tmpdir) / "output.txt"
            assert output_file.exists(), f"Output file not found. Files in {tmpdir}: {list(Path(tmpdir).iterdir())}"
            content = output_file.read_text()
            assert "Macro ran with name=test" in content
        finally:
            # Go to a safe directory before cleanup
            os.chdir(Path.home())
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-m", "not slow"])
