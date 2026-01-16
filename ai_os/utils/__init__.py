"""
AI-OS Utils - Utility modules for the agentic macro framework.

Contains:
- context: Conversation context management
- config: Configuration management
- command_history: CLI history tracking
"""

from ai_os.utils.context import context_manager
from ai_os.utils.config import config_manager

__all__ = [
    "context_manager",
    "config_manager",
]
