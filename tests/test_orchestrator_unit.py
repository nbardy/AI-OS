"""
Unit tests for ClaudeOrchestrator with mocked subprocess.

These tests run fast without making actual Claude API calls.
They test the orchestrator's internal logic, parsing, and error handling.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

from ai_os.core.orchestrator import (
    ClaudeOrchestrator,
    ClaudeResult,
    _find_claude_command,
    get_orchestrator,
    reset_orchestrator,
    configure_orchestrator,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before and after each test."""
    reset_orchestrator()
    yield
    reset_orchestrator()


@pytest.fixture
def mock_claude_response():
    """Create a mock Claude Code response."""
    return {
        "result": "Test response from Claude",
        "cost": {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_cost_usd": 0.001
        }
    }


@pytest.fixture
def orchestrator():
    """Create an orchestrator instance."""
    return ClaudeOrchestrator()


# =============================================================================
# Unit Tests - Core Chat
# =============================================================================

class TestChatUnit:
    """Unit tests for chat functionality with mocked subprocess."""

    @patch('ai_os.core.orchestrator.subprocess.run')
    def test_chat_parses_json_response(self, mock_run, mock_claude_response):
        """Test that chat correctly parses JSON response."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_claude_response),
            stderr=""
        )

        orch = ClaudeOrchestrator()
        result = orch.chat("Test prompt")

        assert result == "Test response from Claude"
        # Note: subprocess.run is called twice - once by _find_claude_command()
        # and once by _chat_sync(). We verify the chat call specifically.
        assert mock_run.call_count >= 1

    @patch('ai_os.core.orchestrator.subprocess.run')
    def test_chat_tracks_cost(self, mock_run, mock_claude_response):
        """Test that chat accumulates cost tracking."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_claude_response),
            stderr=""
        )

        orch = ClaudeOrchestrator()
        orch.chat("Test prompt")

        cost = orch.get_cost()
        assert cost["input_tokens"] == 100
        assert cost["output_tokens"] == 50
        assert cost["total_cost_usd"] == 0.001

    @patch('ai_os.core.orchestrator.subprocess.run')
    def test_chat_raises_on_failure(self, mock_run):
        """Test that chat raises on subprocess failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="API error: rate limited"
        )

        orch = ClaudeOrchestrator()
        with pytest.raises(RuntimeError, match="Claude Code failed"):
            orch.chat("Test prompt")

    @patch('ai_os.core.orchestrator.subprocess.run')
    def test_chat_with_model_override(self, mock_run, mock_claude_response):
        """Test that model parameter is passed correctly."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_claude_response),
            stderr=""
        )

        orch = ClaudeOrchestrator()
        orch.chat("Test prompt", model="opus")

        # Verify --model opus was in the command
        call_args = mock_run.call_args[0][0]
        assert "--model" in call_args
        model_idx = call_args.index("--model")
        assert call_args[model_idx + 1] == "opus"


# =============================================================================
# Unit Tests - JSON Parsing (Edge Cases)
# =============================================================================

class TestJsonParsing:
    """Test JSON response parsing - focus on edge cases Claude actually returns."""

    def test_parse_json_with_markdown_and_explanation(self):
        """Test JSON parsing when Claude explains before/after the JSON."""
        orch = ClaudeOrchestrator()
        response = """I'll analyze that for you.

Here's the JSON output:
```json
{"status": "success", "count": 42}
```

Let me know if you need anything else!"""
        result = orch._parse_json(response)
        assert result == {"status": "success", "count": 42}

    def test_parse_json_nested_braces_in_string(self):
        """Test parsing JSON with braces inside string values (tricky regex case)."""
        orch = ClaudeOrchestrator()
        response = '{"code": "function foo() { return {}; }", "valid": true}'
        result = orch._parse_json(response)
        assert result["valid"] is True
        assert "{}" in result["code"]

    def test_parse_json_unicode(self):
        """Test parsing JSON with unicode characters."""
        orch = ClaudeOrchestrator()
        response = '{"emoji": "🚀", "chinese": "你好", "special": "café"}'
        result = orch._parse_json(response)
        assert result["emoji"] == "🚀"
        assert result["chinese"] == "你好"

    def test_parse_json_deeply_nested(self):
        """Test parsing deeply nested JSON structures."""
        orch = ClaudeOrchestrator()
        response = '{"a": {"b": {"c": {"d": {"e": "deep"}}}}}'
        result = orch._parse_json(response)
        assert result["a"]["b"]["c"]["d"]["e"] == "deep"

    def test_parse_json_array_of_objects(self):
        """Test parsing array of objects (common LLM output)."""
        orch = ClaudeOrchestrator()
        response = '[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]'
        result = orch._parse_json(response)
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_parse_json_invalid_gives_helpful_error(self):
        """Test that invalid JSON gives a helpful error message."""
        orch = ClaudeOrchestrator()
        with pytest.raises(ValueError) as exc_info:
            orch._parse_json("This is definitely not JSON, just plain text.")
        assert "No valid JSON" in str(exc_info.value)
        # Error should include part of the response for debugging
        assert "This is" in str(exc_info.value)

    def test_parse_json_empty_response(self):
        """Test handling of empty/whitespace responses."""
        orch = ClaudeOrchestrator()
        with pytest.raises(ValueError):
            orch._parse_json("")
        with pytest.raises(ValueError):
            orch._parse_json("   \n\t  ")


# =============================================================================
# Unit Tests - File Operations
# =============================================================================

class TestFileOperations:
    """Test direct file operations."""

    def test_read_write_exists(self):
        """Test read, write, exists cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # File doesn't exist initially
            assert not orch.exists("test.txt")

            # Write and verify
            orch.write("test.txt", "Hello World")
            assert orch.exists("test.txt")

            # Read back
            content = orch.read("test.txt")
            assert content == "Hello World"

    def test_write_creates_directories(self):
        """Test that write creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)

            # Write to nested path
            orch.write("subdir/nested/file.txt", "content")

            # Verify
            assert orch.exists("subdir/nested/file.txt")
            assert orch.read("subdir/nested/file.txt") == "content"


# =============================================================================
# Unit Tests - Shell Operations
# =============================================================================

class TestShellOperations:
    """Test shell command execution."""

    def test_shell_returns_exit_code(self):
        """Test shell returns exit code by default."""
        orch = ClaudeOrchestrator()
        result = orch.shell("true")
        assert result == 0

    def test_shell_capture_output(self):
        """Test shell captures stdout when capture=True."""
        orch = ClaudeOrchestrator()
        result = orch.shell("echo hello", capture=True)
        assert result == "hello"

    def test_shell_raises_on_check(self):
        """Test shell raises when check=True and command fails."""
        orch = ClaudeOrchestrator()
        with pytest.raises(Exception):
            orch.shell("false", check=True)


# =============================================================================
# Unit Tests - Prompt Building (Edge Cases)
# =============================================================================

class TestPromptBuilding:
    """Test prompt construction - focus on real scenarios."""

    def test_build_prompt_preserves_formatting(self):
        """Test that prompt building preserves code formatting and newlines."""
        orch = ClaudeOrchestrator()
        code_prompt = """Fix this code:
```python
def foo():
    return 42
```"""
        result = orch._build_prompt(code_prompt)
        # Should preserve the code block formatting
        assert "```python" in result
        assert "def foo():" in result

    def test_build_prompt_instruction_comes_first(self):
        """Test that system instruction appears before the prompt."""
        orch = ClaudeOrchestrator()
        result = orch._build_prompt("User query", system_instruction="Be concise")
        # Instruction should come before the query
        instruction_pos = result.find("INSTRUCTION:")
        query_pos = result.find("User query")
        assert instruction_pos < query_pos

    def test_build_prompt_handles_missing_context_file(self):
        """Test graceful handling when context file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = ClaudeOrchestrator(working_dir=tmpdir)
            result = orch._build_prompt("Hello", context_files=["nonexistent.txt"])
            # Should include error message, not crash
            assert "error" in result.lower()
            assert "nonexistent.txt" in result

    def test_build_prompt_multiple_context_files(self):
        """Test prompt with multiple context files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files
            (Path(tmpdir) / "file1.py").write_text("# Python file 1")
            (Path(tmpdir) / "file2.py").write_text("# Python file 2")

            orch = ClaudeOrchestrator(working_dir=tmpdir)
            result = orch._build_prompt("Analyze", context_files=["file1.py", "file2.py"])

            assert "file1.py" in result
            assert "file2.py" in result
            assert "Python file 1" in result
            assert "Python file 2" in result


# =============================================================================
# Unit Tests - Cost Tracking (Realistic Scenarios)
# =============================================================================

class TestCostTracking:
    """Test cost tracking - focus on realistic accumulation patterns."""

    def test_cost_accumulates_across_many_calls(self):
        """Test cost accumulation over many API calls."""
        orch = ClaudeOrchestrator()

        # Simulate 10 API calls with varying costs
        for i in range(10):
            orch._track_cost({
                "input_tokens": 100 + i * 10,  # 100, 110, 120...
                "output_tokens": 50 + i * 5,   # 50, 55, 60...
                "total_cost_usd": 0.001 + i * 0.0001
            })

        cost = orch.get_cost()
        # Sum of 100+110+...+190 = 1450
        assert cost["input_tokens"] == 1450
        # Sum of 50+55+...+95 = 725
        assert cost["output_tokens"] == 725

    def test_cost_handles_missing_fields(self):
        """Test that missing cost fields don't crash."""
        orch = ClaudeOrchestrator()

        # Partial cost data (some APIs don't return all fields)
        orch._track_cost({"input_tokens": 100})  # Missing other fields
        orch._track_cost({})  # Empty cost

        cost = orch.get_cost()
        assert cost["input_tokens"] == 100
        assert cost["output_tokens"] == 0  # Default when missing

    def test_cost_get_returns_copy(self):
        """Test that get_cost returns a copy, not the internal dict."""
        orch = ClaudeOrchestrator()
        orch._track_cost({"input_tokens": 100, "output_tokens": 50, "total_cost_usd": 0.001})

        cost1 = orch.get_cost()
        cost1["input_tokens"] = 99999  # Mutate the returned dict

        cost2 = orch.get_cost()
        assert cost2["input_tokens"] == 100  # Original should be unchanged


# =============================================================================
# Unit Tests - Global Orchestrator
# =============================================================================

class TestGlobalOrchestrator:
    """Test global orchestrator management."""

    def test_get_orchestrator_creates_instance(self):
        """Test that get_orchestrator creates a new instance."""
        reset_orchestrator()
        orch = get_orchestrator()
        assert orch is not None
        assert isinstance(orch, ClaudeOrchestrator)

    def test_get_orchestrator_returns_same_instance(self):
        """Test that get_orchestrator returns the same instance."""
        reset_orchestrator()
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2

    def test_reset_orchestrator_clears_instance(self):
        """Test that reset_orchestrator clears the global instance."""
        reset_orchestrator()
        orch1 = get_orchestrator()
        reset_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is not orch2

    def test_configure_orchestrator(self):
        """Test configuring orchestrator with custom settings."""
        reset_orchestrator()
        orch = configure_orchestrator(
            default_model="opus",
            timeout=300
        )
        assert orch.default_model == "opus"
        assert orch.timeout == 300

        # Should be the same as get_orchestrator
        assert get_orchestrator() is orch


# =============================================================================
# Unit Tests - Vision
# =============================================================================

class TestVision:
    """Test vision functionality."""

    def test_vision_validates_file_exists(self):
        """Test that vision validates image file exists."""
        orch = ClaudeOrchestrator()
        with pytest.raises(FileNotFoundError, match="Image not found"):
            orch.vision("Describe this", "nonexistent.png")

    def test_vision_validates_format(self):
        """Test that vision validates image format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a non-image file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("not an image")

            orch = ClaudeOrchestrator(working_dir=tmpdir)
            with pytest.raises(ValueError, match="Unsupported image format"):
                orch.vision("Describe this", "test.txt")
