# Claude Code Integration: Technical Deep Dive

**Date:** 2026-01-17
**Status:** Design Phase
**Purpose:** Define exactly how AI-OS v2 interfaces with Claude Code

---

## Overview

Claude Code is Anthropic's official CLI for Claude. It provides:
- Native tool use (Read, Edit, Write, Bash, Grep, Glob, etc.)
- Sub-agent spawning via Task tool
- Context management
- Streaming output
- Permission management

This document specifies how AI-OS v2 uses Claude Code as its execution substrate.

---

## Claude Code CLI Interface

### Basic Invocation

```bash
# Interactive mode (default)
claude

# Non-interactive with prompt
claude -p "your prompt here"

# From stdin
echo "your prompt" | claude -p

# From file
claude -p < prompt.txt

# With flags
claude -p "prompt" --model opus
claude -p "prompt" --dangerously-skip-permissions
claude -p "prompt" --output-format json
```

### Key Flags

| Flag | Purpose | AI-OS Usage |
|------|---------|-------------|
| `-p` | Print mode (non-interactive) | Always use |
| `--model <name>` | Select model (sonnet, opus, haiku) | Optional, for cost control |
| `--dangerously-skip-permissions` | Skip approval prompts | Use for automated execution |
| `--output-format json` | Structured output | Use for parsing results |
| `--max-turns <n>` | Limit agent turns | Use to bound execution |

### Output Format

When using `--output-format json`, Claude Code returns:

```json
{
  "result": "The assistant's final response text",
  "cost": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "total_cost_usd": 0.0123
  },
  "duration_ms": 4567,
  "turns": 3
}
```

Without JSON format, output is plain text (streamed to stdout).

---

## Integration Patterns

### Pattern 1: Simple Prompt-Response

**Use case:** Ask Claude a question, get an answer.

```python
import subprocess
import json

def chat(prompt: str, model: str = "sonnet") -> str:
    """Send a prompt to Claude Code and return the response."""
    result = subprocess.run(
        [
            "claude", "-p",
            "--model", model,
            "--dangerously-skip-permissions",
            "--output-format", "json"
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {result.stderr}")

    output = json.loads(result.stdout)
    return output["result"]
```

**Streaming variant:**

```python
import subprocess
import sys

def chat_streaming(prompt: str, model: str = "sonnet") -> str:
    """Send a prompt and stream the response."""
    process = subprocess.Popen(
        [
            "claude", "-p",
            "--model", model,
            "--dangerously-skip-permissions"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Send prompt
    process.stdin.write(prompt)
    process.stdin.close()

    # Stream output
    full_response = []
    for line in iter(process.stdout.readline, ''):
        sys.stdout.write(line)
        sys.stdout.flush()
        full_response.append(line)

    process.wait()
    return ''.join(full_response)
```

---

### Pattern 2: File Operations

**Use case:** Have Claude read, edit, or create files.

```python
def edit_file(instruction: str, file_path: str) -> bool:
    """Have Claude edit a specific file."""
    prompt = f"""
    Edit the file {file_path} to accomplish this:
    {instruction}

    Use the Edit tool to make surgical changes.
    Do not create new files unless absolutely necessary.
    """

    result = subprocess.run(
        [
            "claude", "-p",
            "--dangerously-skip-permissions",
            "--output-format", "json"
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )

    return result.returncode == 0


def create_file(content: str, file_path: str) -> bool:
    """Have Claude create a file with specific content."""
    prompt = f"""
    Create the file {file_path} with this exact content:

    ```
    {content}
    ```

    Use the Write tool. Do not modify the content.
    """

    result = subprocess.run(
        [
            "claude", "-p",
            "--dangerously-skip-permissions"
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )

    return result.returncode == 0
```

---

### Pattern 3: Parallel Execution (Spawn/Join)

**Use case:** Run multiple Claude Code processes simultaneously.

```python
import subprocess
import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, Future

@dataclass
class Agent:
    """Represents a spawned Claude Code process."""
    process: subprocess.Popen
    prompt: str
    output_file: Optional[str]
    future: Future


class AgentOrchestrator:
    """Manages parallel Claude Code processes."""

    def __init__(self, max_workers: int = 5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.agents: List[Agent] = []

    def spawn(
        self,
        prompt: str,
        output_file: Optional[str] = None,
        model: str = "sonnet"
    ) -> Agent:
        """
        Spawn a new Claude Code process.

        Args:
            prompt: The task for Claude to perform
            output_file: Optional file path for Claude to write results to
            model: Model to use (sonnet, opus, haiku)

        Returns:
            Agent handle for joining later
        """
        # If output_file specified, include instruction
        full_prompt = prompt
        if output_file:
            full_prompt += f"\n\nWrite your final output to: {output_file}"

        def run_claude():
            result = subprocess.run(
                [
                    "claude", "-p",
                    "--model", model,
                    "--dangerously-skip-permissions",
                    "--output-format", "json"
                ],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            return result

        future = self.executor.submit(run_claude)

        agent = Agent(
            process=None,  # Process runs in thread
            prompt=prompt,
            output_file=output_file,
            future=future
        )
        self.agents.append(agent)
        return agent

    def join(self, agents: List[Agent], timeout: float = None) -> List[dict]:
        """
        Wait for all agents to complete.

        Args:
            agents: List of Agent handles from spawn()
            timeout: Optional timeout in seconds

        Returns:
            List of result dicts with 'success', 'result', 'error' keys
        """
        results = []
        for agent in agents:
            try:
                completed = agent.future.result(timeout=timeout)
                if completed.returncode == 0:
                    try:
                        output = json.loads(completed.stdout)
                        results.append({
                            'success': True,
                            'result': output.get('result', ''),
                            'cost': output.get('cost'),
                            'output_file': agent.output_file
                        })
                    except json.JSONDecodeError:
                        results.append({
                            'success': True,
                            'result': completed.stdout,
                            'output_file': agent.output_file
                        })
                else:
                    results.append({
                        'success': False,
                        'error': completed.stderr,
                        'output_file': agent.output_file
                    })
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'output_file': agent.output_file
                })

        return results

    def shutdown(self):
        """Clean up executor."""
        self.executor.shutdown(wait=True)
```

**Usage example:**

```python
orchestrator = AgentOrchestrator(max_workers=5)

# Spawn 5 parallel agents
agents = []
for i in range(5):
    agent = orchestrator.spawn(
        f"Write a creative shader using technique #{i+1}",
        output_file=f"shaders/candidate_{i}.glsl"
    )
    agents.append(agent)

# Wait for all to complete
results = orchestrator.join(agents)

# Process results
for i, result in enumerate(results):
    if result['success']:
        print(f"Agent {i} succeeded")
        # Read the output file
        with open(result['output_file']) as f:
            shader_code = f.read()
    else:
        print(f"Agent {i} failed: {result['error']}")

orchestrator.shutdown()
```

---

### Pattern 4: Vision/Image Analysis

**Use case:** Have Claude analyze an image.

```python
import base64
import subprocess
import json

def analyze_image(image_path: str, prompt: str, model: str = "sonnet") -> str:
    """
    Have Claude analyze an image.

    Note: This requires the image to be readable by Claude Code.
    Claude Code can read image files directly with the Read tool.
    """
    full_prompt = f"""
    Read and analyze the image at: {image_path}

    {prompt}

    Use the Read tool to view the image, then provide your analysis.
    """

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", model,
            "--dangerously-skip-permissions",
            "--output-format", "json"
        ],
        input=full_prompt,
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"Image analysis failed: {result.stderr}")

    output = json.loads(result.stdout)
    return output["result"]


def score_image(image_path: str, criteria: str) -> dict:
    """
    Score an image on given criteria.
    Returns dict with 'score' (1-10) and 'reason'.
    """
    prompt = f"""
    Analyze the image at {image_path} and score it from 1-10 on these criteria:
    {criteria}

    Be critical. Most images are mediocre (5-6).
    Reserve 9-10 for truly exceptional work.

    Output your response as JSON:
    {{"score": <number>, "reason": "<brief explanation>"}}

    Output ONLY the JSON, no other text.
    """

    result = subprocess.run(
        [
            "claude", "-p",
            "--model", model,
            "--dangerously-skip-permissions"
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )

    # Parse JSON from response
    response = result.stdout.strip()

    # Find JSON in response (may have other text)
    import re
    json_match = re.search(r'\{[^}]+\}', response)
    if json_match:
        return json.loads(json_match.group())
    else:
        raise ValueError(f"Could not parse JSON from: {response}")
```

---

### Pattern 5: Structured Output (JSON Parsing)

**Use case:** Get structured data from Claude.

```python
import subprocess
import json
import re
from typing import Any, TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def chat_json(prompt: str, response_model: Type[T] = None) -> Any:
    """
    Get structured JSON output from Claude.

    Args:
        prompt: The prompt (should ask for JSON output)
        response_model: Optional Pydantic model to validate against

    Returns:
        Parsed JSON (as dict) or validated Pydantic model
    """
    full_prompt = f"""
    {prompt}

    IMPORTANT: Output your response as valid JSON only.
    Do not include any text before or after the JSON.
    """

    result = subprocess.run(
        [
            "claude", "-p",
            "--dangerously-skip-permissions"
        ],
        input=full_prompt,
        capture_output=True,
        text=True,
        timeout=300
    )

    response = result.stdout.strip()

    # Try to extract JSON from response
    # Handle both clean JSON and JSON embedded in text
    try:
        # First, try direct parse
        data = json.loads(response)
    except json.JSONDecodeError:
        # Try to find JSON object or array
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            raise ValueError(f"No valid JSON in response: {response[:200]}")

    # Validate with Pydantic if model provided
    if response_model:
        return response_model.model_validate(data)

    return data


# Example usage with Pydantic
from pydantic import BaseModel
from typing import List

class ShaderApproach(BaseModel):
    name: str
    technique: str
    description: str

class ShaderPlan(BaseModel):
    approaches: List[ShaderApproach]

plan = chat_json(
    "Plan 5 different mathematical approaches for generative shaders",
    response_model=ShaderPlan
)

for approach in plan.approaches:
    print(f"- {approach.name}: {approach.technique}")
```

---

### Pattern 6: Working Directory Management

**Use case:** Run Claude Code in a specific directory.

```python
import subprocess
import os

def chat_in_directory(prompt: str, working_dir: str) -> str:
    """
    Run Claude Code in a specific working directory.

    This is useful when:
    - The macro operates on files in a specific project
    - Relative paths in the prompt should resolve correctly
    - You want isolation between macro runs
    """
    result = subprocess.run(
        [
            "claude", "-p",
            "--dangerously-skip-permissions",
            "--output-format", "json"
        ],
        input=prompt,
        capture_output=True,
        text=True,
        cwd=working_dir,  # Key: set working directory
        timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed in {working_dir}: {result.stderr}")

    output = json.loads(result.stdout)
    return output["result"]
```

---

### Pattern 7: Context Injection

**Use case:** Provide Claude with relevant context before the task.

Since Claude Code processes are stateless, we need to inject context into each prompt.

```python
def chat_with_context(
    prompt: str,
    context_files: List[str] = None,
    prior_results: List[str] = None,
    system_context: str = None
) -> str:
    """
    Send a prompt with injected context.

    Args:
        prompt: The main task prompt
        context_files: File paths to read and include
        prior_results: Previous operation results to include
        system_context: Additional system-level context
    """
    parts = []

    # Add system context
    if system_context:
        parts.append(f"CONTEXT:\n{system_context}\n")

    # Add file contents
    if context_files:
        parts.append("RELEVANT FILES:")
        for file_path in context_files:
            if os.path.exists(file_path):
                with open(file_path) as f:
                    content = f.read()
                parts.append(f"\n--- {file_path} ---\n{content}")
        parts.append("")

    # Add prior results
    if prior_results:
        parts.append("PRIOR RESULTS:")
        for i, result in enumerate(prior_results, 1):
            parts.append(f"\n{i}. {result}")
        parts.append("")

    # Add main prompt
    parts.append(f"TASK:\n{prompt}")

    full_prompt = "\n".join(parts)

    return chat(full_prompt)
```

---

### Pattern 8: Error Handling and Retry

**Use case:** Robust execution with automatic retry.

```python
import time
from typing import Callable, Any

def retry_chat(
    prompt: str,
    max_retries: int = 3,
    backoff_seconds: float = 2.0,
    validator: Callable[[str], bool] = None
) -> str:
    """
    Execute a Claude Code call with retry logic.

    Args:
        prompt: The prompt to send
        max_retries: Maximum number of attempts
        backoff_seconds: Base delay between retries (exponential)
        validator: Optional function to validate the response

    Returns:
        The successful response

    Raises:
        RuntimeError: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [
                    "claude", "-p",
                    "--dangerously-skip-permissions",
                    "--output-format", "json"
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise RuntimeError(f"Exit code {result.returncode}: {result.stderr}")

            output = json.loads(result.stdout)
            response = output["result"]

            # Validate if validator provided
            if validator and not validator(response):
                raise ValueError("Response failed validation")

            return response

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = backoff_seconds * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

    raise RuntimeError(f"All {max_retries} attempts failed. Last error: {last_error}")


# Example with JSON validation
def is_valid_json(response: str) -> bool:
    try:
        json.loads(response)
        return True
    except:
        return False

result = retry_chat(
    "Output a JSON object with fields 'name' and 'value'",
    validator=is_valid_json
)
```

---

## Claude Code Behavior Notes

### Tool Usage

Claude Code has access to these tools internally:
- **Read** — Read files (including images)
- **Edit** — Surgical string replacement in files
- **Write** — Create new files
- **Bash** — Execute shell commands
- **Grep** — Search file contents
- **Glob** — Find files by pattern
- **Task** — Spawn sub-agents
- **WebFetch** — Fetch URLs
- **WebSearch** — Search the web

When we send a prompt, Claude Code decides which tools to use. We don't need to specify them.

### Permission Model

By default, Claude Code asks for permission before:
- Writing files
- Running shell commands
- Making web requests

Using `--dangerously-skip-permissions` bypasses all prompts. Use this for automated macro execution.

**Security note:** Only use skip-permissions for macros you trust. The macro author is responsible for safety.

### Context Window

Claude Code manages its own context:
- Reads relevant files automatically
- Truncates context intelligently
- Doesn't need us to manage message history

This means each Claude Code call is relatively stateless from our perspective. We inject context via the prompt, not via a persistent session.

### Cost Tracking

With `--output-format json`, cost information is returned:
```json
{
  "cost": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "total_cost_usd": 0.0123
  }
}
```

We can aggregate this across a macro run for cost reporting.

---

## Integration Architecture

### Orchestrator Class

The central component that manages Claude Code interactions:

```python
# ai_os/core/orchestrator.py

import subprocess
import json
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AgentResult:
    success: bool
    result: str = ""
    error: str = ""
    cost: Dict[str, Any] = field(default_factory=dict)
    output_file: Optional[str] = None

@dataclass
class SpawnedAgent:
    future: Future
    prompt: str
    output_file: Optional[str]
    model: str

class ClaudeOrchestrator:
    """
    Manages Claude Code process invocations for AI-OS macros.

    This is the bridge between the Python DSL and Claude Code CLI.
    """

    def __init__(
        self,
        working_dir: str = None,
        default_model: str = "sonnet",
        max_parallel: int = 5,
        timeout: int = 600
    ):
        self.working_dir = working_dir or os.getcwd()
        self.default_model = default_model
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_parallel)
        self.spawned_agents: List[SpawnedAgent] = []
        self.total_cost = {"input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0.0}

    def chat(
        self,
        prompt: str,
        model: str = None,
        parse_json: bool = False,
        context_files: List[str] = None
    ) -> Any:
        """
        Synchronous chat completion.

        Args:
            prompt: The prompt to send
            model: Model override (default uses self.default_model)
            parse_json: If True, parse response as JSON
            context_files: Files to include in context

        Returns:
            Response string, or parsed JSON if parse_json=True
        """
        full_prompt = self._build_prompt(prompt, context_files)
        model = model or self.default_model

        result = subprocess.run(
            [
                "claude", "-p",
                "--model", model,
                "--dangerously-skip-permissions",
                "--output-format", "json"
            ],
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

        response = output.get("result", "")

        if parse_json:
            return self._parse_json(response)

        return response

    def spawn(
        self,
        prompt: str,
        output_file: str = None,
        model: str = None
    ) -> SpawnedAgent:
        """
        Spawn an async Claude Code process.

        Args:
            prompt: The task prompt
            output_file: Optional file for Claude to write output to
            model: Model override

        Returns:
            SpawnedAgent handle for joining
        """
        model = model or self.default_model

        full_prompt = prompt
        if output_file:
            full_prompt += f"\n\nWrite your final output to: {output_file}"

        def run_claude():
            return subprocess.run(
                [
                    "claude", "-p",
                    "--model", model,
                    "--dangerously-skip-permissions",
                    "--output-format", "json"
                ],
                input=full_prompt,
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=self.timeout
            )

        future = self.executor.submit(run_claude)

        agent = SpawnedAgent(
            future=future,
            prompt=prompt,
            output_file=output_file,
            model=model
        )
        self.spawned_agents.append(agent)
        return agent

    def join(
        self,
        agents: List[SpawnedAgent],
        timeout: float = None
    ) -> List[AgentResult]:
        """
        Wait for spawned agents to complete.

        Args:
            agents: List of SpawnedAgent handles
            timeout: Optional timeout per agent

        Returns:
            List of AgentResult objects
        """
        results = []

        for agent in agents:
            try:
                completed = agent.future.result(timeout=timeout)

                if completed.returncode == 0:
                    try:
                        output = json.loads(completed.stdout)
                        self._track_cost(output.get("cost", {}))
                        results.append(AgentResult(
                            success=True,
                            result=output.get("result", ""),
                            cost=output.get("cost", {}),
                            output_file=agent.output_file
                        ))
                    except json.JSONDecodeError:
                        results.append(AgentResult(
                            success=True,
                            result=completed.stdout,
                            output_file=agent.output_file
                        ))
                else:
                    results.append(AgentResult(
                        success=False,
                        error=completed.stderr,
                        output_file=agent.output_file
                    ))

            except Exception as e:
                results.append(AgentResult(
                    success=False,
                    error=str(e),
                    output_file=agent.output_file
                ))

        return results

    def edit(self, instruction: str, file_path: str = None) -> bool:
        """
        Have Claude edit files.

        Args:
            instruction: What to do
            file_path: Optional specific file to edit

        Returns:
            True if successful
        """
        prompt = instruction
        if file_path:
            prompt = f"Edit {file_path}: {instruction}"

        try:
            self.chat(prompt)
            return True
        except Exception as e:
            return False

    def read(self, file_path: str) -> str:
        """Read a file directly (not through Claude)."""
        path = Path(self.working_dir) / file_path
        return path.read_text()

    def write(self, file_path: str, content: str) -> bool:
        """Write a file directly (not through Claude)."""
        path = Path(self.working_dir) / file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return True

    def shell(self, command: str, capture: bool = False) -> Any:
        """Execute a shell command directly."""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=self.working_dir
        )

        if capture:
            return result.stdout.strip()
        return result.returncode

    def get_total_cost(self) -> Dict[str, Any]:
        """Get aggregated cost for this session."""
        return self.total_cost.copy()

    def shutdown(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)

    # --- Private helpers ---

    def _build_prompt(
        self,
        prompt: str,
        context_files: List[str] = None
    ) -> str:
        """Build full prompt with optional context."""
        if not context_files:
            return prompt

        parts = ["CONTEXT FILES:"]
        for file_path in context_files:
            try:
                content = self.read(file_path)
                parts.append(f"\n--- {file_path} ---\n{content}")
            except Exception as e:
                parts.append(f"\n--- {file_path} (error: {e}) ---")

        parts.append(f"\n\nTASK:\n{prompt}")
        return "\n".join(parts)

    def _parse_json(self, response: str) -> Any:
        """Extract JSON from response."""
        import re

        # Try direct parse
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
        if match:
            return json.loads(match.group(1))

        raise ValueError(f"No valid JSON in response: {response[:200]}")

    def _track_cost(self, cost: Dict[str, Any]):
        """Aggregate cost tracking."""
        self.total_cost["input_tokens"] += cost.get("input_tokens", 0)
        self.total_cost["output_tokens"] += cost.get("output_tokens", 0)
        self.total_cost["total_cost_usd"] += cost.get("total_cost_usd", 0.0)
```

---

## Environment Setup

### Prerequisites

1. **Claude Code installed:**
   ```bash
   # Via npm
   npm install -g @anthropic-ai/claude-code

   # Or via Homebrew
   brew install claude-code
   ```

2. **API key configured:**
   ```bash
   # Claude Code uses ANTHROPIC_API_KEY
   export ANTHROPIC_API_KEY=sk-...
   ```

3. **Python 3.11+** (for AI-OS)

### Verification Script

```python
#!/usr/bin/env python3
"""Verify Claude Code integration is working."""

import subprocess
import json
import sys

def check_claude_code():
    print("Checking Claude Code installation...")

    # Check if claude command exists
    result = subprocess.run(
        ["which", "claude"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("ERROR: 'claude' command not found")
        print("Install with: npm install -g @anthropic-ai/claude-code")
        return False

    print(f"  Found: {result.stdout.strip()}")

    # Check version
    result = subprocess.run(
        ["claude", "--version"],
        capture_output=True,
        text=True
    )
    print(f"  Version: {result.stdout.strip()}")

    # Test simple prompt
    print("\nTesting prompt execution...")
    result = subprocess.run(
        [
            "claude", "-p",
            "--output-format", "json",
            "--dangerously-skip-permissions"
        ],
        input="Say 'Hello from Claude Code' and nothing else.",
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        print(f"ERROR: Test prompt failed: {result.stderr}")
        return False

    try:
        output = json.loads(result.stdout)
        print(f"  Response: {output.get('result', '')[:50]}")
        print(f"  Cost: ${output.get('cost', {}).get('total_cost_usd', 0):.4f}")
        print("\nClaude Code integration working!")
        return True
    except json.JSONDecodeError:
        print(f"ERROR: Could not parse JSON output")
        return False

if __name__ == "__main__":
    success = check_claude_code()
    sys.exit(0 if success else 1)
```

---

## Limitations and Workarounds

### Limitation 1: No Persistent Session

**Problem:** Each Claude Code call is independent. No conversation history persists.

**Workaround:** Inject relevant context into each prompt. Use file system for state.

### Limitation 2: No Real-time Streaming in Subprocess

**Problem:** When using `--output-format json`, we get all output at once.

**Workaround:** For streaming, don't use JSON format. Parse raw stdout line by line.

### Limitation 3: Context Window Per Call

**Problem:** Each call has its own context window. Long running tasks may lose context.

**Workaround:** Break into smaller tasks. Use files to persist intermediate results.

### Limitation 4: Cost Accumulation

**Problem:** Parallel agents can accumulate cost quickly.

**Workaround:** Track cost in orchestrator. Set budget limits. Use haiku for simple tasks.

### Limitation 5: No Direct Tool Control

**Problem:** We can't force Claude to use specific tools.

**Workaround:** Write prompts that clearly imply the needed tool (e.g., "Edit the file X" → Edit tool).

---

## Best Practices

### 1. Be Explicit in Prompts

Bad:
```
Fix the bug
```

Good:
```
In the file src/auth.py, fix the bug in the login() function
where passwords are not being hashed before comparison.
Use the Edit tool to make the change.
```

### 2. Use Files for Large Outputs

Bad:
```
Generate a 500-line shader and output it in your response.
```

Good:
```
Generate a shader and write it to shaders/output.glsl using the Write tool.
```

### 3. Validate Outputs

Always validate Claude's output before using it:
```python
result = orchestrator.chat(prompt, parse_json=True)
if not validate_shader_syntax(result):
    # Retry or handle error
```

### 4. Cost-Aware Model Selection

- **Haiku:** Simple tasks, validation, scoring
- **Sonnet:** Complex generation, code writing
- **Opus:** Critical decisions, complex reasoning

### 5. Timeout Management

Set appropriate timeouts:
```python
# Quick task
orchestrator = ClaudeOrchestrator(timeout=60)

# Complex generation
orchestrator = ClaudeOrchestrator(timeout=600)
```

---

## Next Steps

This document specifies how we interface with Claude Code. The next document (04_python_dsl_design.md) will define the Python DSL API that macros use, built on top of this integration layer.
