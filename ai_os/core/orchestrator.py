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
from typing import Any, Dict, List, Optional, Generator, Union
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
import uuid


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


def _find_claude_command() -> List[str]:
    """
    Find the Claude Code CLI command.

    Tries in order:
    1. Direct 'claude' binary (if installed globally)
    2. npx @anthropic-ai/claude-code (npm install)

    Returns the command as a list for subprocess.
    """
    import shutil

    # Try direct claude binary first
    if shutil.which("claude"):
        return ["claude"]

    # Fall back to npx
    if shutil.which("npx"):
        return ["npx", "--yes", "@anthropic-ai/claude-code"]

    raise RuntimeError(
        "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
    )


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
        timeout: int = 600,
        skip_permissions: bool = True
    ):
        self.working_dir = working_dir or os.getcwd()
        self.default_model = default_model
        self.timeout = timeout
        self.skip_permissions = skip_permissions
        self.total_cost = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost_usd": 0.0
        }
        # Cache the claude command
        self._claude_cmd = _find_claude_command()

    # =========================================================================
    # Core Chat Functions
    # =========================================================================

    def chat(
        self,
        prompt: str,
        model: str = None,
        context_files: List[str] = None,
        async_: bool = False,
        system_instruction: str = None
    ) -> Union[str, "asyncio.coroutine"]:
        """
        Send a prompt to Claude Code.

        Args:
            prompt: The prompt to send
            model: Model override (sonnet, opus, haiku)
            context_files: Files to include as context
            async_: If True, returns a coroutine for asyncio.gather()
            system_instruction: Optional system-level instruction prefix

        Returns:
            Response string if async_=False, coroutine if async_=True
        """
        if async_:
            return self._chat_async(prompt, model, context_files, system_instruction)
        else:
            return self._chat_sync(prompt, model, context_files, system_instruction)

    def _chat_sync(
        self,
        prompt: str,
        model: str = None,
        context_files: List[str] = None,
        system_instruction: str = None
    ) -> str:
        """Synchronous chat - blocks until response."""
        full_prompt = self._build_prompt(prompt, context_files, system_instruction)
        model = model or self.default_model

        cmd = self._claude_cmd + ["-p", "--model", model]
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
            raise RuntimeError(f"Claude Code failed: {result.stderr}")

        output = json.loads(result.stdout)
        self._track_cost(output.get("cost", {}))
        return output.get("result", "")

    async def _chat_async(
        self,
        prompt: str,
        model: str = None,
        context_files: List[str] = None,
        system_instruction: str = None
    ) -> str:
        """Async chat - returns awaitable for asyncio.gather()."""
        full_prompt = self._build_prompt(prompt, context_files, system_instruction)
        model = model or self.default_model

        cmd = self._claude_cmd + ["-p", "--model", model]
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
            raise RuntimeError(f"Claude Code failed: {stderr.decode()}")

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

        cmd = self._claude_cmd + ["-p", "--model", model]
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
        """Extract JSON from response text."""
        response = response.strip()

        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object or array in response
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

        Claude Code can read image files directly with the Read tool.

        Args:
            prompt: Analysis prompt
            image: Path to image file
            model: Model override
            async_: If True, returns coroutine
        """
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

        Args:
            agents: List of SpawnedAgent from spawn()
            timeout: Optional timeout in seconds

        Returns:
            List of ClaudeResult in the same order as agents
        """
        timeout = timeout or self.timeout
        results = []

        for agent in agents:
            try:
                result = agent.future.result(timeout=timeout)
                results.append(result)
            except Exception as e:
                results.append(ClaudeResult(success=False, error=str(e)))

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
    timeout: int = 600,
    skip_permissions: bool = True
) -> ClaudeOrchestrator:
    """Configure and return a new global orchestrator."""
    global _orchestrator
    _orchestrator = ClaudeOrchestrator(
        working_dir=working_dir,
        default_model=default_model,
        timeout=timeout,
        skip_permissions=skip_permissions
    )
    return _orchestrator
