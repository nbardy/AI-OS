import subprocess
import json

cmd = ["/Users/nicholasbardy/.nvm/versions/node/v24.3.0/bin/claude", "-p", "--model", "haiku", "--dangerously-skip-permissions", "--output-format", "json"]
prompt = "Say 'test works'"

print(f"Running command: {' '.join(cmd)}")
print(f"With prompt: {prompt}")

result = subprocess.run(
    cmd,
    input=prompt,
    capture_output=True,
    text=True,
    timeout=30
)

print(f"Return code: {result.returncode}")
print(f"Stdout length: {len(result.stdout)}")
print(f"Stderr: {result.stderr}")

if result.returncode == 0:
    output = json.loads(result.stdout)
    print(f"Result: {output.get('result', '')}")
else:
    print("FAILED")
