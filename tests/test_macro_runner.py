"""
Tests for MacroRunner - verifies macro execution works correctly.
"""

import pytest
import tempfile
import os
from pathlib import Path
from io import StringIO
from unittest.mock import patch, MagicMock

from rich.console import Console

from ai_os.core.macro_runner import MacroRunner
import ai_os.core.macro_helpers as ah


class TestMacroRunner:
    """Test the MacroRunner class."""

    def setup_method(self):
        """Setup for each test."""
        self.console = Console(file=StringIO(), force_terminal=True)
        self.runner = MacroRunner(console=self.console)

    def test_runner_creation(self):
        """Test that we can create a MacroRunner."""
        assert self.runner is not None
        assert self.runner.console is self.console

    def test_parse_argline_simple(self):
        """Test parsing simple macro arguments."""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b"def main(ctx, **kwargs): pass")
            f.flush()

            try:
                path, kwargs = self.runner._parse_argline(f.name)
                # Use realpath to handle macOS /var -> /private/var symlinks
                assert os.path.realpath(path) == os.path.realpath(f.name)
                assert kwargs == {}
            finally:
                os.unlink(f.name)

    def test_parse_argline_with_args(self):
        """Test parsing macro with key=value arguments."""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b"def main(ctx, **kwargs): pass")
            f.flush()

            try:
                argline = f'{f.name} name=Test count=3 flag=true'
                path, kwargs = self.runner._parse_argline(argline)
                # Use realpath to handle macOS /var -> /private/var symlinks
                assert os.path.realpath(path) == os.path.realpath(f.name)
                assert kwargs['name'] == 'Test'
                assert kwargs['count'] == 3
                assert kwargs['flag'] is True
            finally:
                os.unlink(f.name)

    def test_parse_value_types(self):
        """Test that values are parsed to correct types."""
        assert self.runner._parse_value('true') is True
        assert self.runner._parse_value('false') is False
        assert self.runner._parse_value('42') == 42
        assert self.runner._parse_value('3.14') == 3.14
        assert self.runner._parse_value('hello') == 'hello'

    def test_run_simple_macro(self):
        """Test running a simple macro that just logs."""
        macro_code = '''
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    name = kwargs.get("name", "World")
    ah.log(f"Hello, {name}!")
'''
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(macro_code)
            f.flush()

            try:
                self.runner.run(f'{f.name} name=Test')
                # If we get here without exception, the macro ran
            finally:
                os.unlink(f.name)

    def test_macro_with_shell(self):
        """Test macro that runs shell commands."""
        macro_code = '''
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    result = ah.shell("echo 'hello'", capture=True)
    ah.log(f"Shell said: {result}")
'''
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(macro_code)
            f.flush()

            try:
                self.runner.run(f.name)
            finally:
                os.unlink(f.name)

    def test_macro_with_file_ops(self):
        """Test macro that reads/writes files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            macro_code = f'''
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    ah.write("test_output.txt", "Hello from macro")
    content = ah.read("test_output.txt")
    ah.log(f"Read: {{content}}")
    assert ah.exists("test_output.txt")
'''
            macro_path = os.path.join(tmpdir, "test_macro.py")
            with open(macro_path, 'w') as f:
                f.write(macro_code)

            # Run from tmpdir so file ops work
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runner = MacroRunner(console=self.console)
                runner.run(macro_path)

                # Verify file was created
                assert os.path.exists(os.path.join(tmpdir, "test_output.txt"))
            finally:
                os.chdir(original_cwd)

    def test_macro_context_vars(self):
        """Test that context variables are passed correctly."""
        macro_code = '''
import ai_os.core.macro_helpers as ah

def main(ctx, **kwargs):
    # kwargs should have our arguments
    assert "test_arg" in kwargs
    assert kwargs["test_arg"] == "test_value"

    # get_var should also work
    val = ah.get_var("test_arg")
    assert val == "test_value"

    ah.log("Context vars test passed!")
'''
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(macro_code)
            f.flush()

            try:
                self.runner.run(f'{f.name} test_arg=test_value')
            finally:
                os.unlink(f.name)

    def test_macro_error_handling(self):
        """Test that macro errors are handled gracefully."""
        macro_code = '''
def main(ctx, **kwargs):
    raise ValueError("Intentional test error")
'''
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(macro_code)
            f.flush()

            try:
                # Should not raise, but log the error
                self.runner.run(f.name)
            finally:
                os.unlink(f.name)

    def test_invalid_macro_path(self):
        """Test handling of invalid macro path."""
        with pytest.raises(ValueError):
            self.runner._parse_argline("/nonexistent/path/macro.py")

    def test_macro_missing_main(self):
        """Test handling of macro without main function."""
        macro_code = '''
# No main function
x = 42
'''
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            f.write(macro_code)
            f.flush()

            try:
                # Should handle gracefully (log error)
                self.runner.run(f.name)
            finally:
                os.unlink(f.name)


class TestMacroHelpers:
    """Test macro helper functions."""

    def test_helpers_require_runner(self):
        """Test that helpers raise error outside of macro context."""
        # Ensure no runner is set
        ah.set_runner(None)

        with pytest.raises(RuntimeError):
            ah.log("test")

        with pytest.raises(RuntimeError):
            ah.shell("echo test")

    def test_helpers_with_mock_runner(self):
        """Test helpers work with a mock runner."""
        mock_runner = MagicMock()
        mock_runner.log = MagicMock()
        mock_runner.shell = MagicMock(return_value=0)

        ah.set_runner(mock_runner)
        try:
            ah.log("test message")
            mock_runner.log.assert_called_once_with("test message")

            ah.shell("echo test")
            mock_runner.shell.assert_called_once()
        finally:
            ah.set_runner(None)


class TestCLIIntegration:
    """Test CLI headless execution using shared parse_input."""

    def test_parse_input_chat(self):
        """Test parsing chat commands."""
        from ai_os.core.commands import parse_input

        cmd, arg = parse_input("> hello world")
        assert cmd == '/chat'
        assert arg == 'hello world'

        cmd, arg = parse_input("/chat hello world")
        assert cmd == '/chat'
        assert arg == 'hello world'

    def test_parse_input_macro(self):
        """Test parsing macro commands."""
        from ai_os.core.commands import parse_input

        cmd, arg = parse_input("@ examples/test.py arg=val")
        assert cmd == '/macro'
        assert arg == 'examples/test.py arg=val'

        cmd, arg = parse_input("/macro examples/test.py")
        assert cmd == '/macro'
        assert arg == 'examples/test.py'

    def test_parse_input_default(self):
        """Test that commands without prefix default to chat."""
        from ai_os.core.commands import parse_input

        cmd, arg = parse_input("just some text")
        assert cmd == '/chat'
        assert arg == 'just some text'
