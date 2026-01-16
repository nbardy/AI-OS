#!/usr/bin/env python3
"""
Script to improve orchestrator.py with better vision validation and error handling.
This creates an improved version that can be reviewed before committing.
"""

import re
from pathlib import Path

# Read the current orchestrator
orch_path = Path("ai_os/core/orchestrator.py")
content = orch_path.read_text()

# Improvement 1: Add image path validation to vision()
old_vision = '''    def vision(
        self,
        prompt: str,
        image: str,
        model: str = None,
        async_: bool = False
    ) -> Union[str, "asyncio.coroutine"]:
        """
        Analyze an image with Claude.

        Claude Code can read image files directly with the Read tool.

        Args:
            prompt: Analysis prompt
            image: Path to image file
            model: Model override
            async_: If True, returns coroutine
        """
        full_prompt = f"Read and analyze the image at: {image}\\n\\n{prompt}"
        return self.chat(full_prompt, model=model, async_=async_)'''

new_vision = '''    def vision(
        self,
        prompt: str,
        image: str,
        model: str = None,
        async_: bool = False
    ) -> Union[str, "asyncio.coroutine"]:
        """
        Analyze an image with Claude.

        ARCHITECTURE NOTE:
        Claude Code can read image files directly with the Read tool.
        This method validates the image path exists before sending to Claude.

        IMPORTANT:
        - Image path must be relative to working_dir or absolute
        - Supported formats: PNG, JPG, JPEG, GIF, WEBP, BMP
        - File must exist and be readable
        - Claude Code's Read tool handles the actual image loading

        MAINTENANCE:
        - If Claude Code adds more image formats, update validation
        - Consider adding file size validation for very large images

        Args:
            prompt: Analysis prompt
            image: Path to image file
            model: Model override (recommend sonnet or opus for vision)
            async_: If True, returns coroutine

        Returns:
            Claude's analysis of the image

        Raises:
            FileNotFoundError: If image doesn't exist
            ValueError: If image format is unsupported
        """
        # Validate image path exists
        img_path = Path(self.working_dir) / image if not Path(image).is_absolute() else Path(image)

        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {image}")

        if not img_path.is_file():
            raise ValueError(f"Path is not a file: {image}")

        # Check for supported image formats
        supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
        if img_path.suffix.lower() not in supported_formats:
            raise ValueError(
                f"Unsupported image format: {img_path.suffix}. "
                f"Supported: {', '.join(supported_formats)}"
            )

        # Build prompt for Claude Code to read and analyze
        full_prompt = f"Read and analyze the image at: {image}\\n\\n{prompt}"
        return self.chat(full_prompt, model=model, async_=async_)'''

content = content.replace(old_vision, new_vision)

# Improvement 2: Better edit() implementation
old_edit_method = '''    def edit(
        self,
        instruction: str,
        file: str = None,
        async_: bool = False
    ) -> Union[bool, "asyncio.coroutine"]:
        """
        Have Claude edit files.

        Args:
            instruction: What changes to make
            file: Specific file to edit (optional)
            async_: If True, returns coroutine

        Returns:
            True if successful
        """
        prompt = instruction
        if file:
            prompt = f"Edit the file {file}: {instruction}"

        system = "You are editing files. Use the Edit tool for surgical changes. Summarize what you changed."

        if async_:
            return self._edit_async(prompt, system)

        try:
            self.chat(prompt, system_instruction=system)
            return True
        except Exception:
            return False

    async def _edit_async(self, prompt: str, system: str) -> bool:
        """Async edit."""
        try:
            await self._chat_async(prompt, system_instruction=system)
            return True
        except Exception:
            return False'''

new_edit_method = '''    def edit(
        self,
        instruction: str,
        file: str = None,
        async_: bool = False
    ) -> Union[bool, "asyncio.coroutine"]:
        """
        Have Claude edit files using Claude Code's native Edit tool.

        ARCHITECTURE NOTE:
        This delegates to Claude Code subprocess, which has native Edit/Write tools.
        The prompt engineering is critical - we need clear instructions to trigger tool use.

        IMPORTANT:
        - For existing files: Claude will use the Edit tool (surgical changes)
        - For new files: Claude will use the Write tool
        - Generic edits: Claude decides which files to modify
        - All edits go through human approval (unless skip_permissions=True)

        MAINTENANCE:
        - If Claude Code changes Edit tool behavior, update prompts here
        - The system_instruction helps guide Claude to use tools properly
        - File existence check helps guide Edit vs Write decision

        Args:
            instruction: What changes to make
            file: Specific file to edit (optional)
            async_: If True, returns coroutine

        Returns:
            True if successful, False if failed
        """
        # Build a prompt that clearly indicates file editing is needed
        if file:
            # Check if file exists to determine Edit vs Write guidance
            file_path = Path(self.working_dir) / file
            if file_path.exists():
                prompt = f"""Edit the file `{file}` as follows:

{instruction}

Read the file first, then use the Edit tool to make surgical changes. Only modify what's necessary."""
            else:
                prompt = f"""Create a new file `{file}` with the following requirements:

{instruction}

Use the Write tool to create this file."""
        else:
            # Generic edit - Claude needs to figure out which files
            prompt = f"""Make the following code changes:

{instruction}

Use the Edit or Write tools as appropriate. Read files first if needed."""

        system = "You are editing code. Use the Edit tool for precise changes to existing files, or Write tool for new files."

        if async_:
            return self._edit_async(prompt, system)

        try:
            self.chat(prompt, system_instruction=system)
            return True
        except Exception as e:
            # Log error for debugging (helps with troubleshooting failed edits)
            import sys
            print(f"Edit failed: {e}", file=sys.stderr)
            return False

    async def _edit_async(self, prompt: str, system: str) -> bool:
        """Async edit - same as sync but uses async chat."""
        try:
            await self._chat_async(prompt, system_instruction=system)
            return True
        except Exception as e:
            import sys
            print(f"Async edit failed: {e}", file=sys.stderr)
            return False'''

content = content.replace(old_edit_method, new_edit_method)

# Write improved version
improved_path = Path("ai_os/core/orchestrator_improved.py")
improved_path.write_text(content)

print(f"✓ Created improved orchestrator at: {improved_path}")
print(f"✓ Added image path validation to vision()")
print(f"✓ Improved edit() with better prompts and error handling")
print(f"✓ Added comprehensive documentation comments")
print()
print("To apply: mv ai_os/core/orchestrator_improved.py ai_os/core/orchestrator.py")
