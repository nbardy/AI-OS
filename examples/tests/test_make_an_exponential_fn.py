import pytest

# Assuming a function `exponential_fn` will be implemented in src/math_functions.py
try:
    from src.math_functions import exponential_fn
except ImportError:
    # This block allows the test file to be generated even if src/math_functions.py
    # or the exponential_fn doesn't exist yet.
    # Pytest will fail if exponential_fn is not found when tests are run.
    pass

def test_positive_integers():
    """Test with positive base and positive integer exponent."""
    try:
        assert exponential_fn(2, 3) == 8 # 2^3
        assert exponential_fn(5, 2) == 25 # 5^2
    except NameError:
        pytest.fail("Could not import 'exponential_fn' from 'src/math_functions.py'.")

def test_zero_exponent():
    """Test with zero exponent."""
    try:
        assert exponential_fn(7, 0) == 1 # 7^0
        assert exponential_fn(0, 0) == 1 # Edge case 0^0, commonly defined as 1 in many contexts
        assert exponential_fn(-5, 0) == 1 # (-5)^0
    except NameError:
        pytest.fail("Could not import 'exponential_fn'.")

def test_one_as_base():
    """Test with base of 1."""
    try:
        assert exponential_fn(1, 100) == 1 # 1^100
    except NameError:
        pytest.fail("Could not import 'exponential_fn'.")

def test_zero_as_base():
    """Test with base of 0 and positive exponent."""
    try:
        assert exponential_fn(0, 5) == 0 # 0^5
    except NameError:
        pytest.fail("Could not import 'exponential_fn'.")

def test_negative_exponent():
    """Test with negative exponent (results in float)."""
    try:
        assert exponential_fn(2, -1) == 0.5 # 2^-1
        assert exponential_fn(2, -2) == 0.25 # 2^-2
        assert exponential_fn(4, -0.5) == 0.5 # 4^-0.5
    except NameError:
        pytest.fail("Could not import 'exponential_fn'.")

def test_float_exponent():
    """Test with float exponent."""
    try:
        assert exponential_fn(9, 0.5) == 3.0 # 9^0.5 (sqrt)
        assert exponential_fn(8, 1/3) == pytest.approx(2.0) # 8^(1/3) (cube root)
    except NameError:
        pytest.fail("Could not import 'exponential_fn'.")

def test_non_numeric_input():
    """Test with non-numeric base or exponent should raise TypeError."""
    try:
        with pytest.raises(TypeError):
            exponential_fn("a", 2)
        with pytest.raises(TypeError):
            exponential_fn(2, "b")
        with pytest.raises(TypeError):
            exponential_fn("a", "b")
    except NameError:
        pytest.fail("Could not import 'exponential_fn'.")