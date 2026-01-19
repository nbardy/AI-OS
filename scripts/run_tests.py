#!/usr/bin/env python3
"""
Test runner script for AI-OS model selector tests
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Run AI-OS tests with various options")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--file", help="Run tests from specific file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies first")
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path("ai_os").exists():
        print("ERROR: Please run this script from the AI-OS root directory")
        sys.exit(1)
    
    success = True
    
    # Install dependencies if requested
    if args.install_deps:
        success &= run_command(
            [sys.executable, "-m", "pip", "install", "-e", ".[test]"],
            "Installing test dependencies"
        )
        if not success:
            sys.exit(1)
    
    # Build pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        pytest_cmd.append("-v")
    
    # Add coverage if requested
    if args.coverage:
        pytest_cmd.extend([
            "--cov=ai_os.ui.model_selector",
            "--cov=ai_os.utils.config",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Add marker filters
    if args.unit:
        pytest_cmd.extend(["-m", "unit"])
    elif args.integration:
        pytest_cmd.extend(["-m", "integration"])
    
    # Skip slow tests if requested
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])
    
    # Run specific file if requested
    if args.file:
        pytest_cmd.append(args.file)
    else:
        pytest_cmd.append("tests/")
    
    # Run tests
    success &= run_command(pytest_cmd, "Running tests")
    
    if not success:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        
        if args.coverage:
            print("\n📊 Coverage report generated in htmlcov/index.html")


if __name__ == "__main__":
    main()