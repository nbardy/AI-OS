"""
Command history management for AI-OS CLI.
Provides persistent command history storage and retrieval.
"""

import json
import os
from pathlib import Path
from typing import List
from prompt_toolkit.history import History


class CommandHistoryManager:
    """Manages persistent command history for AI-OS."""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.config_dir = Path.home() / ".aios"
        self.history_file = self.config_dir / "command_history.json"
        self._commands: List[str] = []
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing history
        self.load_history()
    
    def load_history(self) -> None:
        """Load command history from JSON file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._commands = data.get('commands', [])
                    # Ensure we don't exceed max_history
                    if len(self._commands) > self.max_history:
                        self._commands = self._commands[-self.max_history:]
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Warning] Could not load command history: {e}")
            self._commands = []
    
    def save_history(self) -> None:
        """Save command history to JSON file."""
        try:
            data = {
                'commands': self._commands,
                'max_history': self.max_history
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"[Warning] Could not save command history: {e}")
    
    def add_command(self, command: str) -> None:
        """Add a command to history."""
        if not command or not command.strip():
            return
        
        command = command.strip()
        
        # Remove duplicate if it exists (move to end)
        if command in self._commands:
            self._commands.remove(command)
        
        # Add to end
        self._commands.append(command)
        
        # Maintain max_history limit
        if len(self._commands) > self.max_history:
            self._commands = self._commands[-self.max_history:]
        
        # Save immediately for persistence
        self.save_history()
    
    def get_commands(self) -> List[str]:
        """Get all commands in history."""
        return self._commands.copy()
    
    def clear_history(self) -> None:
        """Clear all command history."""
        self._commands = []
        self.save_history()


class PersistentHistory(History):
    """prompt_toolkit History implementation that uses our CommandHistoryManager."""
    
    def __init__(self, history_manager: CommandHistoryManager):
        super().__init__()
        self.history_manager = history_manager
        # Pre-populate history on startup in reverse order (newest first)
        for cmd in reversed(self.history_manager.get_commands()):
            self._loaded_strings.append(cmd)
    
    def load_history_strings(self) -> List[str]:
        """Load history strings for prompt_toolkit."""
        # Return in reverse order (newest first) for prompt_toolkit
        return list(reversed(self.history_manager.get_commands()))
    
    def store_string(self, string: str) -> None:
        """Store a command string in history."""
        self.history_manager.add_command(string)