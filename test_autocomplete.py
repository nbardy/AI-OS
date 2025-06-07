#!/usr/bin/env python3
"""
Test script for AI-OS autocomplete functionality.
Tests specific cases for @ completion.
"""

import sys
import os
from pathlib import Path

# Add the ai_os directory to the path so we can import
sys.path.insert(0, str(Path(__file__).parent))

from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent

from ai_os.cli import AIOSCompleter

def test_completion(text, cursor_pos=None):
    """Test completion for a given text input."""
    if cursor_pos is None:
        cursor_pos = len(text)
    
    print(f"\n=== Testing: '{text}' (cursor at {cursor_pos}) ===")
    
    # Create completer and document
    completer = AIOSCompleter()
    document = Document(text=text, cursor_position=cursor_pos)
    complete_event = CompleteEvent()
    
    # Get completions
    completions = list(completer.get_completions(document, complete_event))
    
    print(f"Input: '{text}'")
    print(f"Found {len(completions)} completions:")
    
    for i, completion in enumerate(completions[:10]):  # Show first 10
        print(f"  {i+1:2d}. '{completion.text}' (start_pos: {completion.start_position})")
    
    if len(completions) > 10:
        print(f"  ... and {len(completions) - 10} more")
    
    return completions

def main():
    """Test the specific cases mentioned by the user."""
    print("AI-OS Autocomplete Test")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        "@",              # Just @ - should complete files in current dir
        "@examples/",     # @examples/ - should complete files in examples dir
        "@ex",            # @ex - should complete to @examples/ 
        "@examples/h",    # @examples/h - should complete files starting with h
    ]
    
    for test_case in test_cases:
        try:
            test_completion(test_case)
        except Exception as e:
            print(f"ERROR testing '{test_case}': {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    main() 