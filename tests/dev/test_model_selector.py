#!/usr/bin/env python3
"""
Test script to run the model selector in isolation
"""

import sys
import asyncio
from pathlib import Path

# Add the ai_os package to the path
sys.path.insert(0, str(Path(__file__).parent))

from ai_os.ui.model_selector import ModelSelector

async def main():
    """Run the model selector"""
    print("Starting model selector...")
    app = ModelSelector()
    result = await app.run_async()
    
    if result:
        print(f"Selected model: {result}")
    else:
        print("No model selected")

if __name__ == "__main__":
    asyncio.run(main())