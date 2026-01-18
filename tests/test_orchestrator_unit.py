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
# Unit Tests - JSON Parsing
# =============================================================================

class TestJsonParsing:
    """Test JSON response parsing."""

    def test_parse_json_direct(self):
        """Test direct JSON parsing."""
        orch = ClaudeOrchestrator()
        result = orch._parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_markdown(self):
        """Test JSON parsing with markdown wrapping."""
        orch = ClaudeOrchestrator()
        response = """Here's the JSON:
```json
{"status": "success"}
```
"""
        result = orch._parse_json(response)
        assert result == {"status": "success"}

    def test_parse_json_array(self):
        """Test parsing JSON array."""
        orch = ClaudeOrchestrator()
        result = orch._parse_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_parse_json_invalid(self):
        """Test that invalid JSON raises ValueError."""
        orch = ClaudeOrchestrator()
        with pytest.raises(ValueError, match="No valid JSON"):
            orch._parse_json("This is not JSON at all")


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
# Unit Tests - Prompt Building
# =============================================================================

class TestPromptBuilding:
    """Test prompt construction logic."""

    def test_build_prompt_simple(self):
        """Test simple prompt building."""
        orch = ClaudeOrchestrator()
        result = orch._build_prompt("Hello")
        assert result == "Hello"

    def test_build_prompt_with_system_instruction(self):
        """Test prompt with system instruction."""
        orch = ClaudeOrchestrator()
        result = orch._build_prompt("Hello", system_instruction="Be helpful")
        assert "INSTRUCTION: Be helpful" in result
        assert "Hello" in result

    def test_build_prompt_with_context_files(self):
        """Test prompt with file context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "context.txt"
            test_file.write_text("File content here")

            orch = ClaudeOrchestrator(working_dir=tmpdir)
            result = orch._build_prompt("Hello", context_files=["context.txt"])

            assert "CONTEXT FILES:" in result
            assert "context.txt" in result
            assert "File content here" in result
            assert "Hello" in result


# =============================================================================
# Unit Tests - Cost Tracking
# =============================================================================

class TestCostTracking:
    """Test cost tracking accumulation."""

    def test_cost_starts_at_zero(self):
        """Test that cost starts at zero."""
        orch = ClaudeOrchestrator()
        cost = orch.get_cost()
        assert cost["input_tokens"] == 0
        assert cost["output_tokens"] == 0
        assert cost["total_cost_usd"] == 0.0

    def test_cost_accumulates(self):
        """Test that cost accumulates correctly."""
        orch = ClaudeOrchestrator()

        # First call
        orch._track_cost({
            "input_tokens": 100,
            "output_tokens": 50,
            "total_cost_usd": 0.001
        })

        # Second call
        orch._track_cost({
            "input_tokens": 200,
            "output_tokens": 100,
            "total_cost_usd": 0.002
        })

        cost = orch.get_cost()
        assert cost["input_tokens"] == 300
        assert cost["output_tokens"] == 150
        assert cost["total_cost_usd"] == 0.003


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
