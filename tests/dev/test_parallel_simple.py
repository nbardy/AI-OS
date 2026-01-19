#!/usr/bin/env python3
"""Simple test for parallel execution."""

import sys
sys.path.insert(0, '.')

from ai_os.core.orchestrator import ClaudeOrchestrator

def test():
    print("Testing gather()...")
    orch = ClaudeOrchestrator()
    
    results = orch.gather(
        "Say 'one'",
        "Say 'two'",
        model="haiku"
    )
    
    print(f"Got {len(results)} results:")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r[:100]}")
    
    return len(results) == 2

if __name__ == "__main__":
    success = test()
    print("\n" + ("✓ PASSED" if success else "✗ FAILED"))
    exit(0 if success else 1)
