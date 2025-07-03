import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List


class ConfigManager:
    """Manages AI-OS configuration stored in ~/.ai-os/config.json
    
    Provides persistent storage for:
    - Current model selection
    - Model cache data
    - API settings
    - User preferences
    
    Features:
    - Automatic config directory creation
    - Safe file operations with error handling
    - Model validation and caching
    - Extensible configuration schema
    """
    
    def __init__(self):
        self.config_dir = Path.home() / ".ai-os"
        self.config_file = self.config_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._ensure_schema()
    
    def _load_config(self) -> None:
        """Load configuration from disk with error handling"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                # Log error in production, for now create fresh config
                self._config = {}
        else:
            self._config = {}
    
    def _ensure_schema(self) -> None:
        """Ensure configuration has required schema structure"""
        defaults = {
            "version": "1.0",
            "current_model": None,
            "model_cache": {
                "data": [],
                "last_updated": 0,
                "ttl_hours": 24
            },
            "api_settings": {
                "timeout_seconds": 30,
                "retry_attempts": 3
            },
            "ui_preferences": {
                "auto_expand_folders": True,
                "show_model_details": True
            }
        }
        
        # Merge defaults with existing config
        for key, value in defaults.items():
            if key not in self._config:
                self._config[key] = value
            elif isinstance(value, dict) and isinstance(self._config[key], dict):
                # Merge nested dictionaries
                for nested_key, nested_value in value.items():
                    if nested_key not in self._config[key]:
                        self._config[key][nested_key] = nested_value
    
    def _save_config(self) -> bool:
        """Save configuration to disk
        
        Returns:
            bool: True if save was successful, False otherwise
        """
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.config_file)
            return True
        except (IOError, OSError):
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value and save to disk
        
        Args:
            key: Configuration key to set
            value: Value to set
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        self._config[key] = value
        return self._save_config()
    
    def get_nested(self, path: str, default: Any = None) -> Any:
        """Get a nested configuration value using dot notation
        
        Args:
            path: Dot-separated path (e.g., 'api_settings.timeout_seconds')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        keys = path.split('.')
        current = self._config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set_nested(self, path: str, value: Any) -> bool:
        """Set a nested configuration value using dot notation
        
        Args:
            path: Dot-separated path (e.g., 'api_settings.timeout_seconds')
            value: Value to set
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        keys = path.split('.')
        current = self._config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # Set the final key
        current[keys[-1]] = value
        return self._save_config()
    
    def get_current_model(self) -> Optional[str]:
        """Get the currently selected model ID
        
        Returns:
            Optional[str]: Current model ID or None if not set
        """
        return self.get("current_model")
    
    def set_current_model(self, model_id: str) -> bool:
        """Set the currently selected model
        
        Args:
            model_id: The model ID to set as current
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        if not model_id or not isinstance(model_id, str):
            return False
        return self.set("current_model", model_id)
    
    def validate_model_id(self, model_id: str) -> bool:
        """Validate that a model ID exists in cached models
        
        Args:
            model_id: Model ID to validate
            
        Returns:
            bool: True if model exists in cache, False otherwise
        """
        cached_models = self.get_cached_models()
        return any(model.get("id") == model_id for model in cached_models)
    
    def get_cached_models(self) -> List[Dict[str, Any]]:
        """Get cached model data
        
        Returns:
            List of model dictionaries from cache
        """
        return self.get_nested("model_cache.data", [])
    
    def set_cached_models(self, models: List[Dict[str, Any]]) -> bool:
        """Cache model data with timestamp
        
        Args:
            models: List of model dictionaries to cache
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        cache_data = {
            "data": models,
            "last_updated": int(time.time()),
            "ttl_hours": self.get_nested("model_cache.ttl_hours", 24)
        }
        return self.set("model_cache", cache_data)
    
    def is_model_cache_valid(self) -> bool:
        """Check if model cache is still valid
        
        Returns:
            bool: True if cache is valid, False if expired or empty
        """
        last_updated = self.get_nested("model_cache.last_updated", 0)
        ttl_hours = self.get_nested("model_cache.ttl_hours", 24)
        cached_models = self.get_cached_models()
        
        if not cached_models or last_updated == 0:
            return False
            
        age_hours = (time.time() - last_updated) / 3600
        return age_hours < ttl_hours
    
    def get_api_timeout(self) -> int:
        """Get API timeout setting
        
        Returns:
            int: Timeout in seconds
        """
        return self.get_nested("api_settings.timeout_seconds", 30)
    
    def get_retry_attempts(self) -> int:
        """Get API retry attempts setting
        
        Returns:
            int: Number of retry attempts
        """
        return self.get_nested("api_settings.retry_attempts", 3)
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration as dictionary
        
        Returns:
            Dict containing current configuration
        """
        return self._config.copy()
    
    def import_config(self, config_data: Dict[str, Any]) -> bool:
        """Import configuration from dictionary
        
        Args:
            config_data: Configuration dictionary to import
            
        Returns:
            bool: True if import and save was successful, False otherwise
        """
        if not isinstance(config_data, dict):
            return False
            
        self._config = config_data
        self._ensure_schema()  # Ensure imported config has proper schema
        return self._save_config()


# Global config manager instance
config_manager = ConfigManager()