# Multi-File Patch Example

The AI-OS patch system supports creating/modifying multiple files in a single operation.

## Example Patch Request:

```
/patch Create a simple calculator module with tests
```

## Example LLM Response (following the XML format):

```xml
<code filename="src/calculator.py" language="python">
def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
</code>
<code filename="tests/test_calculator.py" language="python">
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.calculator import add, subtract, multiply, divide

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5

def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6

def test_divide():
    assert divide(10, 2) == 5
    assert divide(7, 2) == 3.5
    
    with pytest.raises(ValueError):
        divide(5, 0)
</code>
<code filename="README.md" language="markdown">
# Calculator Module

A simple calculator with basic arithmetic operations.

## Usage

```python
from src.calculator import add, subtract, multiply, divide

result = add(2, 3)  # 5
result = multiply(4, 5)  # 20
```

## Testing

Run tests with: `pytest tests/test_calculator.py`
</code>

--- summaries ---
src/calculator.py: Implement basic calculator functions (add, subtract, multiply, divide) with error handling.
tests/test_calculator.py: Add comprehensive tests for all calculator functions including edge cases.
README.md: Add documentation for the calculator module with usage examples.
```

## Result:

This single patch would:
1. Create the calculator module in `src/calculator.py`
2. Create tests in `tests/test_calculator.py`
3. Create documentation in `README.md`

All three files would be created, staged, and committed in a single git commit.