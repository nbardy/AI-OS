"""
Tests for ClaudeOrchestrator vision capabilities.

This replaces the old test_openrouter_images.py tests now that we use
Claude Code's native vision support via file paths.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from ai_os.core.orchestrator import ClaudeOrchestrator


def test_vision_basic():
    """Test basic vision API call structure."""
    import tempfile

    # Create a temporary image file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
        f.write("fake image data")
        temp_path = f.name

    try:
        orch = ClaudeOrchestrator()

        # Vision should construct a prompt that references the image file path
        with patch.object(orch, '_chat_sync', return_value="I see a red circle") as mock_chat:
            result = orch.vision("What shape is this?", temp_path)

            # Verify it called chat with the right prompt structure
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            prompt = call_args[0][0]  # First positional arg

            assert temp_path in prompt
            assert "What shape is this?" in prompt
            assert result == "I see a red circle"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_vision_with_model_override():
    """Test vision with custom model."""
    import tempfile

    # Create a temporary image file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
        f.write("fake image data")
        temp_path = f.name

    try:
        orch = ClaudeOrchestrator(default_model="sonnet")

        with patch.object(orch, '_chat_sync', return_value="Analysis complete") as mock_chat:
            result = orch.vision(
                "Analyze this chart",
                temp_path,
                model="opus"
            )

            # Verify model was passed through
            call_args = mock_chat.call_args
            assert call_args[1].get('model') == 'opus' or call_args[0][1] == 'opus'
            assert result == "Analysis complete"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_vision_async():
    """Test async vision call."""
    import asyncio
    import tempfile

    # Create a temporary image file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jpg', delete=False) as f:
        f.write("fake image data")
        temp_path = f.name

    try:
        orch = ClaudeOrchestrator()

        async def test_coroutine():
            # Mock the async chat method to return a coroutine
            async def mock_async_result(*args, **kwargs):
                return "Async result"

            with patch.object(orch, '_chat_async', side_effect=mock_async_result):
                result = await orch.vision(
                    "What's in this image?",
                    temp_path,
                    async_=True
                )
                return result

        # Run async test
        result = asyncio.run(test_coroutine())
        assert result == "Async result"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_vision_with_real_file():
    """Test vision with actual temp file (mocked Claude Code response)."""
    # Create a temporary image file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
        f.write("fake image data")
        temp_path = f.name

    try:
        orch = ClaudeOrchestrator()

        # Mock the subprocess call that talks to Claude Code
        with patch('subprocess.run') as mock_run:
            # Mock successful Claude Code response
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"result": "This is a test image", "cost": {}}',
                stderr=""
            )

            result = orch.vision("What is this?", temp_path)

            # Verify subprocess was called
            assert mock_run.called
            assert result == "This is a test image"

            # Verify the prompt included the file path
            call_args = mock_run.call_args
            input_text = call_args[1]['input']
            assert temp_path in input_text
    finally:
        # Clean up
        Path(temp_path).unlink(missing_ok=True)


def test_vision_file_not_found():
    """Test that vision handles non-existent files gracefully."""
    orch = ClaudeOrchestrator()

    # With the new file validation, it should raise FileNotFoundError before calling subprocess
    try:
        orch.vision("Analyze", "/nonexistent/image.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "Image not found" in str(e)
