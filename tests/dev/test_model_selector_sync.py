#!/usr/bin/env python3
"""
Synchronous test script to run the model selector in isolation
"""

import sys
from pathlib import Path

# Add the ai_os package to the path
sys.path.insert(0, str(Path(__file__).parent))

from ai_os.ui.model_selector import run_model_selector
from ai_os.utils.config import config_manager

def main():
    """Run the model selector synchronously"""
    print("Current model:", config_manager.get_current_model() or "None")
    print("Starting model selector...")
    print("Controls:")
    print("  - Type to search models")
    print("  - Use arrow keys to navigate")
    print("  - Press Enter to select")
    print("  - Press Escape to cancel")
    print()
    
    result = run_model_selector()
    
    if result:
        print(f"Selected model: {result}")
        print(f"Saved to config: {config_manager.get_current_model()}")
    else:
        print("No model selected")

if __name__ == "__main__":
    main()