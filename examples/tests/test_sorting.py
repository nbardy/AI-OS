import pytest
# Assuming a function `sort_list` exists in src/sorting.py
try:
    from src.sorting import sort_list
except ImportError:
    # Provide a placeholder/mock if the actual file doesn't exist yet,
    # or expect the next patch step to create src/sorting.py
    # For the purpose of generating the test file, we assume it will exist.
    # A simple mock or placeholder might be needed in a real scenario
    # where the test could be run immediately before the implementation.
    # For this test *generation* step, we just assume the import will work later.
    pass


def test_sort_list_basic():
    """Tests sorting a basic list of integers."""
    unsorted = [3, 1, 4, 1, 5, 9, 2, 6]
    expected = [1, 1, 2, 3, 4, 5, 6, 9]
    # Using try/except for the test function call to give better error info if import failed
    try:
        assert sort_list(unsorted) == expected
    except NameError:
        pytest.fail("Could not import 'sort_list' from 'src.sorting'. Ensure the function and file exist.")


def test_sort_list_empty():
    """Tests sorting an empty list."""
    try:
        assert sort_list([]) == []
    except NameError:
        pytest.fail("Could not import 'sort_list'.")


def test_sort_list_already_sorted():
    """Tests sorting a list that is already sorted."""
    sorted_list = [1, 2, 3, 4, 5]
    try:
        assert sort_list(sorted_list) == sorted_list
    except NameError:
        pytest.fail("Could not import 'sort_list'.")

def test_sort_list_reverse_sorted():
    """Tests sorting a list sorted in reverse order."""
    reverse_list = [5, 4, 3, 2, 1]
    expected = [1, 2, 3, 4, 5]
    try:
        assert sort_list(reverse_list) == expected
    except NameError:
        pytest.fail("Could not import 'sort_list'.")

# To make this test runnable by pytest and adhere to the 0/non-zero exit code:
# 1. Save this content as tests/test_sorting.py
# 2. Install pytest: pip install pytest
# 3. Run from your terminal: pytest tests/test_sorting.py
# Pytest handles the exit codes automatically based on test outcomes.