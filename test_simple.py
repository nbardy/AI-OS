#!/usr/bin/env python3
from ai_os.core.orchestrator import ClaudeOrchestrator
import sys

print("Creating orchestrator...")
orch = ClaudeOrchestrator()

print("Testing sync chat...")
try:
    response = orch.chat("Say 'test works'", model="haiku")
    print(f"Response: {response}")
    if response:
        print("✓ Test PASSED")
        sys.exit(0)
    else:
        print("✗ Test FAILED")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
