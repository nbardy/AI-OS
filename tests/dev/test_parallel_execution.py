#!/usr/bin/env python3
"""Test parallel execution with spawn/join/gather."""

from ai_os.core.orchestrator import ClaudeOrchestrator

def test_gather():
    """Test gather() for parallel execution."""
    print("Testing gather() - parallel execution...")
    orch = ClaudeOrchestrator()
    
    try:
        # Run 3 simple prompts in parallel
        results = orch.gather(
            "Say 'first'",
            "Say 'second'",
            "Say 'third'",
            model="haiku"  # Use haiku for speed
        )
        
        print(f"Got {len(results)} results")
        for i, result in enumerate(results):
            print(f"  Result {i+1}: {result[:50]}...")
        
        if len(results) == 3:
            print("✓ Gather test PASSED")
            return True
        else:
            print(f"✗ Gather test FAILED - expected 3 results, got {len(results)}")
            return False
    except Exception as e:
        print(f"✗ Gather test FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spawn_join():
    """Test spawn()/join() for parallel execution."""
    print("\nTesting spawn()/join()...")
    orch = ClaudeOrchestrator()
    
    try:
        # Spawn multiple agents
        agents = [
            orch.spawn(f"Count to {i+1}", model="haiku")
            for i in range(3)
        ]
        
        print(f"Spawned {len(agents)} agents")
        
        # Wait for all to complete
        results = orch.join(agents)
        
        successful = sum(1 for r in results if r.success)
        print(f"{successful}/{len(results)} agents completed successfully")
        
        if successful == len(results):
            print("✓ Spawn/join test PASSED")
            return True
        else:
            print(f"✗ Spawn/join test FAILED - some agents failed")
            return False
    except Exception as e:
        print(f"✗ Spawn/join test FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("Parallel Execution Tests")
    print("="*60)
    
    results = []
    results.append(test_gather())
    results.append(test_spawn_join())
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)
    
    exit(0 if all(results) else 1)
