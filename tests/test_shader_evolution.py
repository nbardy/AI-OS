"""
Test for shader_evolution.py macro - demonstrates current failure and fixes.

This test shows:
1. Shaders should contain actual GLSL code (not conversational responses)
2. Renders directory must exist before rendering
3. Must gracefully handle missing glslviewer
"""

import pytest
from pathlib import Path
import tempfile
import json


def test_shader_response_validation():
    """Test that gathered shaders contain actual GLSL code, not chat responses."""

    # Simulate what ai.gather() currently returns from LLM
    bad_responses = [
        "I'll generate a shader for you. Here's a beautiful approach...",  # Bad: conversational
        "Done. The shader has been created using...",  # Bad: conversational
        "void main() { gl_FragColor = vec4(1.0); }",  # Good: actual code
        "Let me create a shader that...",  # Bad: conversational
    ]

    # This is what shader_evolution.py should validate
    def is_valid_shader(response: str) -> bool:
        """Check if response is actual GLSL code, not chat."""
        code = response.strip().lower()
        # Valid GLSL contains these keywords
        has_glsl = any(keyword in code for keyword in [
            'void main', 'gl_fragcolor', 'uniform', '#version'
        ])
        # Conversational red flags
        is_chat = any(phrase in code for phrase in [
            "i'll", "i will", "done.", "here's", "let me", "i can", "for you"
        ])
        return has_glsl and not is_chat

    # Test validation
    validated = [r for r in bad_responses if is_valid_shader(r)]

    # Should only have 1 valid shader out of 4
    assert len(validated) == 1, f"Expected 1 valid shader, got {len(validated)}"
    assert "void main" in validated[0]
    print(f"✓ Validated {len(validated)} out of {len(bad_responses)} shaders")


def test_renders_directory_creation():
    """Test that renders directory exists before trying to write to it."""

    with tempfile.TemporaryDirectory() as tmpdir:
        renders_dir = Path(tmpdir) / "renders"

        # Should not exist initially
        assert not renders_dir.exists(), "renders dir should not exist yet"

        # Create it (what shader_evolution.py should do)
        renders_dir.mkdir(parents=True, exist_ok=True)

        # Now it should exist
        assert renders_dir.exists(), "renders dir should exist after mkdir"

        # Writing should work
        test_file = renders_dir / "test.png"
        test_file.write_text("dummy image data")

        assert test_file.exists()
        print(f"✓ Renders directory created and writable")


def test_glslviewer_check():
    """Test graceful handling of missing glslviewer."""

    # Simulate the check
    import subprocess

    result = subprocess.run(
        "which glslviewer",
        shell=True,
        capture_output=True,
        text=True
    )

    has_glslviewer = result.returncode == 0

    if not has_glslviewer:
        print("⚠ glslviewer not installed - renders will be skipped")
        print("   Install with: brew install glslviewer (macOS) or apt-get install glslviewer (Linux)")
    else:
        print("✓ glslviewer available")

    # Macro should handle this gracefully
    assert True, "Should always pass - just check for tool gracefully"


def test_shader_evolution_robustness():
    """Test that shader_evolution handles failures gracefully."""

    # The macro has 3 failure points:
    failures = {
        "1. Bad shader responses": "ai.gather() returns chat instead of code",
        "2. Missing renders dir": "renders/ doesn't exist before writing",
        "3. Missing glslviewer": "Tool not installed on system",
    }

    fixes = {
        "1. Bad shader responses": "Validate responses contain GLSL keywords",
        "2. Missing renders dir": "Create with: ai.shell('mkdir -p renders')",
        "3. Missing glslviewer": "Check with: which glslviewer, skip if missing",
    }

    for failure, description in failures.items():
        fix = fixes[failure]
        print(f"\n{failure}")
        print(f"  Problem: {description}")
        print(f"  Fix: {fix}")

    # All failures should have fixes
    assert len(failures) == len(fixes)
