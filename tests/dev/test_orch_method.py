import subprocess
import json
import shutil

def _find_claude_command():
    if shutil.which("claude"):
        return ["claude"]
    if shutil.which("npx"):
        return ["npx", "--yes", "@anthropic-ai/claude-code"]
    raise RuntimeError("Claude Code CLI not found")

cmd_base = _find_claude_command()
print(f"Found claude command: {cmd_base}")

cmd = cmd_base + ["-p", "--model", "haiku", "--dangerously-skip-permissions", "--output-format", "json"]
prompt = "Say 'orchestrator test'"

print(f"Running: {' '.join(cmd)}")
result = subprocess.run(
    cmd,
    input=prompt,
    capture_output=True,
    text=True,
    timeout=30
)

print(f"Return code: {result.returncode}")
if result.returncode == 0:
    output = json.loads(result.stdout)
    print(f"Result: {output.get('result', '')}")
    print("✓ SUCCESS")
else:
    print(f"✗ FAILED: {result.stderr}")
