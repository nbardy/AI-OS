import pytest
import sys
import os

# Adjust sys.path to allow imports from parent directories
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Assuming a function `factorial` will be implemented in src/math_operations.py
try:
    from src.math_operations import factorial
except ImportError:
    # This block allows the test file to be generated even if src/math_operations.py
    # or the factorial function doesn't exist yet.
    # Pytest will fail if factorial is not found when tests are run.
    pass

def test_factorial_zero():
    """Test factorial for 0."""
    try:
        assert factorial(0) == 1
    except NameError:
        pytest.fail("Could not import 'factorial' from 'src/math_operations.py'.")

def test_factorial_one():
    """Test factorial for 1."""
    try:
        assert factorial(1) == 1
    except NameError:
        pytest.fail("Could not import 'factorial'.")

def test_factorial_positive_small():
    """Test factorial for a small positive integer (e.g., 5)."""
    try:
        assert factorial(5) == 120
    except NameError:
        pytest.fail("Could not import 'factorial'.")

def test_factorial_positive_large():
    """Test factorial for a larger positive integer (e.g., 20)."""
    # 20! = 2,432,902,008,176,640,000
    expected_20_factorial = 2432902008176640000
    try:
        assert factorial(20) == expected_20_factorial
    except NameError:
        pytest.fail("Could not import 'factorial'.")

def test_factorial_negative_number():
    """Test factorial for a negative number should raise ValueError."""
    try:
        with pytest.raises(ValueError):
            factorial(-1)
    except NameError:
        pytest.fail("Could not import 'factorial'.")

def test_factorial_non_integer():
    """Test factorial for a non-integer should raise TypeError."""
    try:
        with pytest.raises(TypeError):
            factorial(3.5)
    except NameError:
        pytest.fail("Could not import 'factorial'.")