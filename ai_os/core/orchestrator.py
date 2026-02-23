"""
Claude Code Orchestrator - manages subprocess communication with Claude Code CLI.

This is the new backend for AI-OS v2. Instead of calling OpenRouter directly,
we invoke `claude -p` as a subprocess and let Claude Code handle tool use.
"""

import subprocess
import json
import os
import re
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from threading import Lock
from typing import Any, Dict, List, Optional, Generator, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ClaudeResult:
    """Result from a Claude Code call."""
    success: bool
    result: str = ""
    error: str = ""
    cost: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpawnedAgent:
    """Represents a spawned parallel Claude operation."""
    id: str
    prompt: str
    future: Future = None
    output_file: Optional[str] = None
    model: str = "sonnet"


def _find_cli_command(cli_name: str) -> List[str]:
    """
    Find a CLI command (claude, codex, etc).

    Tries in order:
    1. Use 'where' on Unix systems to find the real path (handles aliases)
    2. Direct binary (if installed globally)
    3. npx fallback for npm-based CLIs

    Returns the command as a list for subprocess.
    """
    import shutil
    import platform

    # Try using 'where' command on Unix systems to get the real path
    if platform.system() != "Windows":
        try:
            result = subprocess.run(
                ["zsh", "-c", f"where {cli_name} 2>/dev/null | grep -v alias | head -1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                if os.path.exists(path):
                    return [path]
        except Exception:
            pass

    # Try direct binary with which
    path = shutil.which(cli_name)
    if path and os.path.exists(path):
        return [path]

    # For npm-based CLIs, try npx
    if shutil.which("npx"):
        pkg_map = {
            "claude": "@anthropic-ai/claude-code",
            "codex": "@anthropic-ai/codex",
        }
        if cli_name in pkg_map:
            return ["npx", "--yes", pkg_map[cli_name]]

    raise RuntimeError(
        f"{cli_name} CLI not found. Install with: npm install -g @anthropic-ai/{cli_name}"
    )


def _find_claude_command() -> List[str]:
    """Find the Claude Code CLI command."""
    return _find_cli_command("claude")


def call_harness(
    harness: str,
    model: str,
    prompt: str,
    working_dir: str = None,
    skip_permissions: bool = True,
    timeout: int = 600
) -> Dict[str, Any]:
    """
    Call either Claude Code or Codex harness.

    Args:
        harness: 'claude' or 'codex'
        model: Model name (sonnet, opus, haiku, etc.)
        prompt: Input prompt
        working_dir: Working directory
        skip_permissions: Skip permission prompts
        timeout: Timeout in seconds

    Returns:
        Dict with 'result', 'cost', 'error' keys
    """
    if harness not in ["claude", "codex"]:
        return {"error": f"Unknown harness: {harness}", "result": "", "cost": {}}

    working_dir = working_dir or os.getcwd()

    try:
        cli_cmd = _find_cli_command(harness)

        # Build command based on harness
        if harness == "claude":
            cmd = cli_cmd + ["-p", "--model", model, "--output-format", "json"]
            if skip_permissions:
                cmd.append("--dangerously-skip-permissions")
        else:  # codex
            cmd = cli_cmd + ["exec", "--model", model]
            # Codex doesn't have --output-format json, will parse text output

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=timeout
        )

        if result.returncode != 0:
            return {
                "error": f"{harness} failed: {result.stderr}",
                "result": "",
                "cost": {}
            }

        # Parse output based on harness
        if harness == "claude":
            try:
                output = json.loads(result.stdout)
                return {
                    "result": output.get("result", ""),
                    "cost": output.get("cost", {}),
                    "error": None
                }
            except json.JSONDecodeError as e:
                return {
                    "error": f"Failed to parse JSON: {e}",
                    "result": result.stdout,
                    "cost": {}
                }
        else:  # codex - returns text, not JSON
            return {
                "result": result.stdout,
                "cost": {},  # Codex doesn't return cost info
                "error": None
            }

    except subprocess.TimeoutExpired:
        return {
            "error": f"{harness} timed out after {timeout}s",
            "result": "",
            "cost": {}
        }
    except Exception as e:
        return {
            "error": str(e),
            "result": "",
            "cost": {}
        }


class ClaudeOrchestrator:
    """
    Manages Claude Code subprocess invocations.

    This is the bridge between AI-OS Python code and the Claude Code CLI.
    All LLM operations go through here.
    """

    def __init__(
        self,
        working_dir: str = None,
        default_model: str = "sonnet",
        default_harness: str = "claude",
        timeout: int = 600,
        skip_permissions: bool = True
    ):
        if working_dir:
            self.working_dir = working_dir
        else:
            try:
                self.working_dir = os.getcwd()
            except (FileNotFoundError, OSError):
                # Fallback to home directory if cwd doesn't exist
                self.working_dir = str(Path.home())
        self.default_model = default_model
        self.default_harness = default_harness  # 'claude' or 'codex'
        self.timeout = timeout
        self.skip_permissions = skip_permissions
        self.total_cost = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost_usd": 0.0
        }
        # Lazy CLI command cache (populated on first use per harness)
        self._cli_cache: Dict[str, List[str]] = {}

    def _get_cli_cmd(self, harness: str) -> List[str]:
        """Get CLI command for a harness, caching the result."""
        if harness not in self._cli_cache:
            self._cli_cache[harness] = _find_cli_command(harness)
        return self._cli_cache[harness]

    # =========================================================================
    # Core Chat Functions
    # =========================================================================

    def chat(
        self,
        prompt: str,
        model: str = None,
        harness: str = None,
        reasoning_effort: str = None,
        context_files: List[str] = None,
        async_: bool = False,
        system_instruction: str = None
    ) -> Union[str, "asyncio.coroutine"]:
        """
        Send a prompt to Claude Code or Codex.

        Args:
            prompt: The prompt to send
            model: Model override (sonnet, opus, haiku for claude; o4-mini etc for codex)
            harness: 'claude' or 'codex' (defaults to self.default_harness)
            reasoning_effort: For codex only: 'low', 'medium', 'high'
            context_files: Files to include as context
            async_: If True, returns a coroutine for asyncio.gather()
            system_instruction: Optional system-level instruction prefix

        Returns:
            Response string if async_=False, coroutine if async_=True
        """
        if async_:
            return self._chat_async(prompt, model, harness, reasoning_effort, context_files, system_instruction)
        else:
            return self._chat_sync(prompt, model, harness, reasoning_effort, context_files, system_instruction)

    def _chat_sync(
        self,
        prompt: str,
        model: str = None,
        harness: str = None,
        reasoning_effort: str = None,
        context_files: List[str] = None,
        system_instruction: str = None
    ) -> str:
        """
        Synchronous chat - blocks until response.

        Supports both claude and codex harnesses. Builds the appropriate CLI
        command and parses output format (JSON for claude, text for codex).
        """
        full_prompt = self._build_prompt(prompt, context_files, system_instruction)
        model = model or self.default_model
        harness = harness or self.default_harness

        cli_cmd = self._get_cli_cmd(harness)

        if harness == "codex":
            cmd = cli_cmd + ["exec", "--model", model]
            if reasoning_effort:
                cmd.extend(["--reasoning-effort", reasoning_effort])
        else:  # claude
            cmd = cli_cmd + ["-p", "--model", model]
            if self.skip_permissions:
                cmd.append("--dangerously-skip-permissions")
            cmd.extend(["--output-format", "json"])

        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            cwd=self.working_dir,
            timeout=self.timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"{harness} failed: {result.stderr}")

        if harness == "codex":
            return result.stdout
        else:
            output = json.loads(result.stdout)
            self._track_cost(output.get("cost", {}))
            return output.get("result", "")

    async def _chat_async(
        self,
        prompt: str,
        model: str = None,
        harness: str = None,
        reasoning_effort: str = None,
        context_files: List[str] = None,
        system_instruction: str = None
    ) -> str:
        """Async chat - returns awaitable for asyncio.gather()."""
        full_prompt = self._build_prompt(prompt, context_files, system_instruction)
        model = model or self.default_model
        harness = harness or self.default_harness

        cli_cmd = self._get_cli_cmd(harness)

        if harness == "codex":
            cmd = cli_cmd + ["exec", "--model", model]
            if reasoning_effort:
                cmd.extend(["--reasoning-effort", reasoning_effort])
        else:  # claude
            cmd = cli_cmd + ["-p", "--model", model]
            if self.skip_permissions:
                cmd.append("--dangerously-skip-permissions")
            cmd.extend(["--output-format", "json"])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(full_prompt.encode()),
            timeout=self.timeout
        )

        if proc.returncode != 0:
            raise RuntimeError(f"{harness} failed: {stderr.decode()}")

        if harness == "codex":
            return stdout.decode()
        else:
            output = json.loads(stdout.decode())
            self._track_cost(output.get("cost", {}))
            return output.get("result", "")

    def chat_streaming(
        self,
        prompt: str,
        model: str = None,
        context_files: List[str] = None,
        system_instruction: str = None
    ) -> Generator[str, None, None]:
        """
        Streaming chat - yields chunks as they arrive.

        Note: Does not use --output-format json to enable streaming.
        Cost tracking not available in streaming mode.
        """
        full_prompt = self._build_prompt(prompt, context_files, system_instruction)
        model = model or self.default_model

        cmd = self._get_cli_cmd("claude") + ["-p", "--model", model]
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.working_dir
        )

        process.stdin.write(full_prompt)
        process.stdin.close()

        for line in iter(process.stdout.readline, ''):
            yield line

        process.wait()
        if process.returncode != 0:
            stderr = process.stderr.read()
            raise RuntimeError(f"Claude Code failed: {stderr}")

    # =========================================================================
    # JSON Response Handling
    # =========================================================================

    def chat_json(
        self,
        prompt: str,
        model: str = None,
        async_: bool = False,
        **kwargs
    ) -> Any:
        """
        Get structured JSON response from Claude.

        Args:
            prompt: Should request JSON output
            model: Model override
            async_: If True, returns coroutine

        Returns:
            Parsed JSON (dict or list)
        """
        json_prompt = f"{prompt}\n\nOutput valid JSON only. No other text."

        if async_:
            return self._chat_json_async(json_prompt, model, **kwargs)

        response = self.chat(json_prompt, model=model, **kwargs)
        return self._parse_json(response)

    async def _chat_json_async(self, prompt: str, model: str = None, **kwargs) -> Any:
        """Async JSON chat."""
        response = await self._chat_async(prompt, model, **kwargs)
        return self._parse_json(response)

    def _parse_json(self, response: str) -> Any:
        """Extract JSON from response text.

        IMPORTANT: Handles cases where Claude includes markdown formatting
        around JSON (e.g., ```json ... ```). Tries direct parse first,
        then falls back to regex extraction.

        This is critical for chat_json() to work reliably across different
        Claude responses that may include explanatory text.
        """
        response = response.strip()

        # Try direct parse first (fastest path)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Fallback: Find JSON object or array in response with regex
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"No valid JSON in response: {response[:200]}")

    # =========================================================================
    # Specialized Operations
    # =========================================================================

    def edit(
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
            return False

    def vision(
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
        full_prompt = f"Read and analyze the image at: {image}\n\n{prompt}"
        return self.chat(full_prompt, model=model, async_=async_)

    # =========================================================================
    # File Operations (Direct - not through Claude)
    # =========================================================================

    def read(self, path: str) -> str:
        """Read file contents directly."""
        full_path = Path(self.working_dir) / path
        return full_path.read_text()

    def write(self, path: str, content: str) -> None:
        """Write file contents directly."""
        full_path = Path(self.working_dir) / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    def exists(self, path: str) -> bool:
        """Check if file exists."""
        full_path = Path(self.working_dir) / path
        return full_path.exists()

    # =========================================================================
    # Shell Operations
    # =========================================================================

    def shell(
        self,
        command: str,
        capture: bool = False,
        check: bool = False
    ) -> Union[int, str]:
        """
        Execute a shell command.

        Args:
            command: Shell command to run
            capture: If True, return stdout instead of exit code
            check: If True, raise on non-zero exit

        Returns:
            Exit code (int) or stdout (str) if capture=True
        """
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            errors='replace',  # Handle binary output gracefully
            cwd=self.working_dir
        )

        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, command, result.stdout, result.stderr
            )

        if capture:
            return result.stdout.strip()

        return result.returncode

    # =========================================================================
    # Parallel Execution (spawn/join/gather)
    # =========================================================================

    def spawn(
        self,
        prompt: str,
        output_file: str = None,
        model: str = None,
        **kwargs
    ) -> SpawnedAgent:
        """
        Spawn an async Claude process.

        Args:
            prompt: The prompt to send
            output_file: Optional file to write result to
            model: Model override
            **kwargs: Additional arguments passed to chat

        Returns:
            SpawnedAgent that can be passed to join()
        """
        if not hasattr(self, '_executor'):
            self._executor = ThreadPoolExecutor(max_workers=10)
            self._cost_lock = Lock()

        agent_id = uuid.uuid4().hex[:8]
        agent_model = model or self.default_model

        def run_chat():
            try:
                result = self._chat_sync(prompt, model=agent_model, **kwargs)
                if output_file:
                    self.write(output_file, result)
                return ClaudeResult(success=True, result=result)
            except Exception as e:
                return ClaudeResult(success=False, error=str(e))

        future = self._executor.submit(run_chat)

        return SpawnedAgent(
            id=agent_id,
            prompt=prompt,
            future=future,
            output_file=output_file,
            model=agent_model
        )

    def join(
        self,
        agents: List[SpawnedAgent],
        timeout: float = None
    ) -> List[ClaudeResult]:
        """
        Wait for spawned agents to complete.

        Uses as_completed() for better performance - results are collected
        as they finish rather than waiting in order.

        Args:
            agents: List of SpawnedAgent from spawn()
            timeout: Optional timeout in seconds

        Returns:
            List of ClaudeResult in the same order as agents (preserves input order)
        """
        timeout = timeout or self.timeout

        # Map futures to their index for order preservation
        future_to_idx = {agent.future: i for i, agent in enumerate(agents)}
        results = [None] * len(agents)

        # Use as_completed() to get results as they finish (faster than sequential)
        try:
            for future in as_completed(future_to_idx.keys(), timeout=timeout):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result(timeout=0)  # Already complete
                except Exception as e:
                    results[idx] = ClaudeResult(success=False, error=str(e))
        except TimeoutError:
            # Fill remaining slots with timeout errors
            for i, result in enumerate(results):
                if result is None:
                    results[i] = ClaudeResult(success=False, error="Timeout waiting for result")

        return results

    def gather(
        self,
        *prompts: str,
        model: str = None,
        **kwargs
    ) -> List[str]:
        """
        Run multiple prompts in parallel and return results.

        This is a convenience wrapper around spawn/join.

        Args:
            *prompts: Variable number of prompts to run
            model: Model override (applies to all)
            **kwargs: Additional arguments passed to each chat

        Returns:
            List of response strings in the same order as prompts
        """
        agents = [
            self.spawn(prompt, model=model, **kwargs)
            for prompt in prompts
        ]

        results = self.join(agents)

        # Extract just the result strings (or empty string on failure)
        return [r.result if r.success else "" for r in results]

    async def gather_async(
        self,
        *prompts: str,
        model: str = None,
        **kwargs
    ) -> List[str]:
        """
        Run multiple prompts in parallel using true asyncio.

        This is faster than gather() for many concurrent requests because
        it uses asyncio.gather() directly instead of ThreadPoolExecutor.

        Args:
            *prompts: Variable number of prompts to run
            model: Model override (applies to all)
            **kwargs: Additional arguments passed to each chat

        Returns:
            List of response strings in the same order as prompts

        Example:
            results = await orch.gather_async(
                "prompt 1",
                "prompt 2",
                "prompt 3",
                model="haiku"
            )
        """
        coros = [
            self._chat_async(prompt, model=model, **kwargs)
            for prompt in prompts
        ]
        return await asyncio.gather(*coros, return_exceptions=True)

    def shutdown(self) -> None:
        """Shutdown the thread pool executor."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
            del self._executor

    # =========================================================================
    # Cost Tracking
    # =========================================================================

    def get_cost(self) -> Dict[str, Any]:
        """Get accumulated cost for this session."""
        return self.total_cost.copy()

    def _track_cost(self, cost: Dict[str, Any]) -> None:
        """Accumulate cost tracking."""
        self.total_cost["input_tokens"] += cost.get("input_tokens", 0)
        self.total_cost["output_tokens"] += cost.get("output_tokens", 0)
        self.total_cost["total_cost_usd"] += cost.get("total_cost_usd", 0.0)

    # =========================================================================
    # Prompt Building
    # =========================================================================

    def _build_prompt(
        self,
        prompt: str,
        context_files: List[str] = None,
        system_instruction: str = None
    ) -> str:
        """Build full prompt with optional context and system instruction."""
        parts = []

        if system_instruction:
            parts.append(f"INSTRUCTION: {system_instruction}\n")

        if context_files:
            parts.append("CONTEXT FILES:")
            for file_path in context_files:
                try:
                    content = self.read(file_path)
                    parts.append(f"\n--- {file_path} ---\n{content}")
                except Exception as e:
                    parts.append(f"\n--- {file_path} (error: {e}) ---")
            parts.append("")

        parts.append(prompt)
        return "\n".join(parts)


# Global orchestrator instance (lazily initialized)
_orchestrator: Optional[ClaudeOrchestrator] = None


def get_orchestrator() -> ClaudeOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ClaudeOrchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the global orchestrator (for testing)."""
    global _orchestrator
    _orchestrator = None


def configure_orchestrator(
    working_dir: str = None,
    default_model: str = "sonnet",
    default_harness: str = "claude",
    timeout: int = 600,
    skip_permissions: bool = True
) -> ClaudeOrchestrator:
    """Configure and return a new global orchestrator."""
    global _orchestrator
    _orchestrator = ClaudeOrchestrator(
        working_dir=working_dir,
        default_model=default_model,
        default_harness=default_harness,
        timeout=timeout,
        skip_permissions=skip_permissions
    )
    return _orchestrator
