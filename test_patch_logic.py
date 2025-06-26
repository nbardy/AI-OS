"""
Comprehensive tests for the patch application logic in ai_os/core/patch.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import subprocess

from ai_os.core.models import Patch
from ai_os.core.patch import apply_patch_with_approval


class TestApplyPatchWithApproval:
    """Test suite for apply_patch_with_approval function"""
    
    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing"""
        return Mock()
    
    @pytest.fixture
    def sample_patch(self):
        """Create a sample patch for testing"""
        patch = Patch(
            file_changes={
                "test_file1.py": "print('Hello, World!')\n",
                "subdir/test_file2.py": "def test():\n    pass\n"
            },
            summaries={
                "test_file1.py": "Add hello world script",
                "subdir/test_file2.py": "Add test function"
            }
        )
        return patch
    
    @pytest.fixture
    def mock_context_manager(self):
        """Mock the context manager to avoid side effects"""
        with patch('ai_os.core.patch.context_manager') as mock:
            yield mock
    
    def test_successful_patch_application(self, mock_console, sample_patch, mock_context_manager):
        """Test successful patch application with file writing, git add, and git commit"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch.Prompt.ask', return_value='y'), \
             patch('ai_os.core.patch._run_git') as mock_run_git:
            
            # Mock Path operations
            mock_path_instances = {}
            def create_mock_path(path_str):
                if path_str not in mock_path_instances:
                    mock_path = Mock()
                    mock_path.parent = Mock()
                    mock_path.parent.mkdir = Mock()
                    mock_path.write_text = Mock()
                    mock_path.__str__ = Mock(return_value=path_str)
                    mock_path_instances[path_str] = mock_path
                return mock_path_instances[path_str]
            
            mock_path_class.side_effect = create_mock_path
            
            # Mock git operations
            mock_run_git.side_effect = [
                # git add
                Mock(returncode=0, stdout='', stderr=''),
                # git commit
                Mock(returncode=0, stdout='', stderr=''),
                # git rev-parse HEAD
                Mock(returncode=0, stdout='abc123def456\n', stderr='')
            ]
            
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is True
            assert result['sha'] == 'abc123def456'
            assert result['patch_obj'] == sample_patch
            
            # Verify file operations
            for file_path in sample_patch.file_changes.keys():
                mock_path = mock_path_instances[file_path]
                mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_path.write_text.assert_called_once_with(
                    sample_patch.file_changes[file_path], 
                    encoding='utf-8'
                )
            
            # Verify git operations
            assert mock_run_git.call_count == 3
            # git add
            mock_run_git.assert_any_call(
                ['add', '--', 'subdir/test_file2.py', 'test_file1.py']
            )
            # git commit
            expected_commit_message = (
                "Apply AI-OS patch\n\n"
                "- subdir/test_file2.py: Add test function\n"
                "- test_file1.py: Add hello world script"
            )
            mock_run_git.assert_any_call(
                ['commit', '-m', expected_commit_message],
                check=False
            )
            # git rev-parse HEAD
            mock_run_git.assert_any_call(['rev-parse', 'HEAD'])
    
    def test_failed_patch_git_commit_fails(self, mock_console, sample_patch, mock_context_manager):
        """Test failed patch when git commit fails due to existing uncommitted changes"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch.Prompt.ask', return_value='y'), \
             patch('ai_os.core.patch._run_git') as mock_run_git:
            
            # Mock Path operations
            mock_path = Mock()
            mock_path.parent = Mock()
            mock_path.parent.mkdir = Mock()
            mock_path.write_text = Mock()
            mock_path.__str__ = Mock(return_value="test_file.py")
            mock_path_class.return_value = mock_path
            
            # Mock git operations
            mock_run_git.side_effect = [
                # git add - success
                Mock(returncode=0, stdout='', stderr=''),
                # git commit - fails with uncommitted changes
                Mock(
                    returncode=1, 
                    stdout='', 
                    stderr='error: Your local changes to the following files would be overwritten by merge:\n    existing_file.py\nPlease commit your changes or stash them before you merge.'
                )
            ]
            
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is False
            assert result['sha'] is None
            assert 'error' in result
            assert 'Your local changes' in result['error']
    
    def test_user_rejection_of_patch(self, mock_console, sample_patch, mock_context_manager):
        """Test user rejection of patch"""
        with patch('ai_os.core.patch.Prompt.ask', return_value='n'):
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is False
            assert result['sha'] is None
            assert result['patch_obj'] == sample_patch
            
            # Verify console output
            mock_console.print.assert_any_call("[red]Rejected by user.[/red]")
            
            # Verify context manager message
            mock_context_manager.add_message.assert_called_with(
                role="system", 
                content="Patch rejected by user."
            )
    
    def test_file_writing_errors(self, mock_console, sample_patch, mock_context_manager):
        """Test handling of file writing errors"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch.Prompt.ask', return_value='y'):
            
            # Mock Path to raise an exception on write_text
            mock_path = Mock()
            mock_path.parent = Mock()
            mock_path.parent.mkdir = Mock()
            mock_path.write_text.side_effect = PermissionError("Permission denied")
            mock_path_class.return_value = mock_path
            
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is False
            assert result['sha'] is None
            assert 'error' in result
            assert 'Permission denied' in result['error']
            
            # Verify console output
            assert any(
                'Error writing files:' in str(call) 
                for call in mock_console.print.call_args_list
            )
    
    def test_git_add_errors(self, mock_console, sample_patch, mock_context_manager):
        """Test handling of git add errors"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch.Prompt.ask', return_value='y'), \
             patch('ai_os.core.patch._run_git') as mock_run_git:
            
            # Mock Path operations
            mock_path = Mock()
            mock_path.parent = Mock()
            mock_path.parent.mkdir = Mock()
            mock_path.write_text = Mock()
            mock_path.__str__ = Mock(return_value="test_file.py")
            mock_path_class.return_value = mock_path
            
            # Mock git add to fail
            mock_run_git.side_effect = subprocess.CalledProcessError(
                1, 
                ['git', 'add', 'test_file.py'],
                stderr='fatal: pathspec \'test_file.py\' did not match any files'
            )
            
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is False
            assert result['sha'] is None
            assert 'error' in result
            assert 'pathspec' in result['error']
    
    def test_invalid_patch_handling(self, mock_console, mock_context_manager):
        """Test handling of invalid or empty patches"""
        # Test with None patch
        result = apply_patch_with_approval(None, mock_console)
        assert result is not None
        assert result['applied'] is False
        
        # Test with empty file_changes
        empty_patch = Patch(file_changes={}, summaries={})
        result = apply_patch_with_approval(empty_patch, mock_console)
        assert result is not None
        assert result['applied'] is False
        
        # Verify console output
        mock_console.print.assert_any_call("[yellow]Invalid or empty patch.[/yellow]")
    
    def test_user_approval_override(self, mock_console, sample_patch, mock_context_manager):
        """Test user_approval_override parameter"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch._run_git') as mock_run_git:
            
            # Mock Path operations
            mock_path = Mock()
            mock_path.parent = Mock()
            mock_path.parent.mkdir = Mock()
            mock_path.write_text = Mock()
            mock_path.__str__ = Mock(return_value="test_file.py")
            mock_path_class.return_value = mock_path
            
            # Mock git operations for success
            mock_run_git.side_effect = [
                Mock(returncode=0, stdout='', stderr=''),  # git add
                Mock(returncode=0, stdout='', stderr=''),  # git commit
                Mock(returncode=0, stdout='abc123\n', stderr='')  # git rev-parse
            ]
            
            # Execute with user_approval_override=False (no prompt)
            with patch('ai_os.core.patch.Prompt.ask') as mock_prompt:
                result = apply_patch_with_approval(
                    sample_patch, 
                    mock_console, 
                    user_approval_override=False
                )
                
                # Verify no prompt was shown
                mock_prompt.assert_not_called()
                
                # Verify patch was applied
                assert result['applied'] is True
    
    def test_nothing_to_commit_scenario(self, mock_console, sample_patch, mock_context_manager):
        """Test handling when there's nothing to commit"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch.Prompt.ask', return_value='y'), \
             patch('ai_os.core.patch._run_git') as mock_run_git:
            
            # Mock Path operations
            mock_path = Mock()
            mock_path.parent = Mock()
            mock_path.parent.mkdir = Mock()
            mock_path.write_text = Mock()
            mock_path.__str__ = Mock(return_value="test_file.py")
            mock_path_class.return_value = mock_path
            
            # Mock git operations
            mock_run_git.side_effect = [
                # git add - success
                Mock(returncode=0, stdout='', stderr=''),
                # git commit - nothing to commit
                Mock(
                    returncode=1, 
                    stdout='', 
                    stderr='On branch main\nnothing to commit, working tree clean'
                )
            ]
            
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result - should still be considered successful
            assert result is not None
            assert result['applied'] is True
            assert result['sha'] is None
            
            # Verify console output
            assert any(
                'No effective changes; nothing committed.' in str(call) 
                for call in mock_console.print.call_args_list
            )
    
    def test_eof_error_during_prompt(self, mock_console, sample_patch, mock_context_manager):
        """Test handling of EOFError during approval prompt"""
        with patch('ai_os.core.patch.Prompt.ask', side_effect=EOFError()):
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is False
            assert result['sha'] is None
            
            # Verify console output
            assert any(
                'Input stream closed during approval prompt' in str(call) 
                for call in mock_console.print.call_args_list
            )
    
    def test_generic_exception_during_prompt(self, mock_console, sample_patch, mock_context_manager):
        """Test handling of generic exceptions during approval prompt"""
        with patch('ai_os.core.patch.Prompt.ask', side_effect=Exception("Unexpected error")):
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result
            assert result is not None
            assert result['applied'] is False
            assert result['sha'] is None
            assert 'error' in result
            assert 'Unexpected error' in result['error']
    
    def test_git_rev_parse_failure(self, mock_console, sample_patch, mock_context_manager):
        """Test handling when git rev-parse fails after successful commit"""
        with patch('ai_os.core.patch.Path') as mock_path_class, \
             patch('ai_os.core.patch.Prompt.ask', return_value='y'), \
             patch('ai_os.core.patch._run_git') as mock_run_git:
            
            # Mock Path operations
            mock_path = Mock()
            mock_path.parent = Mock()
            mock_path.parent.mkdir = Mock()
            mock_path.write_text = Mock()
            mock_path.__str__ = Mock(return_value="test_file.py")
            mock_path_class.return_value = mock_path
            
            # Mock git operations
            mock_run_git.side_effect = [
                # git add - success
                Mock(returncode=0, stdout='', stderr=''),
                # git commit - success
                Mock(returncode=0, stdout='', stderr=''),
                # git rev-parse HEAD - fails
                subprocess.CalledProcessError(
                    128, 
                    ['git', 'rev-parse', 'HEAD'],
                    stderr='fatal: ambiguous argument \'HEAD\': unknown revision or path not in the working tree.'
                )
            ]
            
            # Execute
            result = apply_patch_with_approval(sample_patch, mock_console)
            
            # Verify result - should still be considered applied, but with no SHA
            assert result is not None
            assert result['applied'] is True
            assert result['sha'] is None