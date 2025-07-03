#!/usr/bin/env python3
"""
Centralized logging configuration for AI-OS
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
import time


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured logs in JSON format"""
    
    def format(self, record):
        log_entry = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from LoggerAdapter or custom fields
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is None:
            self.logger.log(self.level, f"Completed {self.operation} in {duration:.3f}s")
        else:
            self.logger.error(f"Failed {self.operation} after {duration:.3f}s: {exc_val}")


class MonitoringLogger:
    """Enhanced logger with monitoring capabilities"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._counters = {}
        self._timers = {}
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a named counter"""
        self._counters[counter_name] = self._counters.get(counter_name, 0) + value
        self.logger.debug(f"Counter {counter_name}: {self._counters[counter_name]}")
    
    def timer(self, operation: str, level: int = logging.INFO):
        """Create a performance timer"""
        return PerformanceTimer(self.logger, operation, level)
    
    def log_performance_metrics(self):
        """Log current performance metrics"""
        metrics = {
            "counters": self._counters.copy(),
            "timers": self._timers.copy()
        }
        self.logger.info("Performance metrics", extra={"extra_fields": {"metrics": metrics}})
    
    def reset_metrics(self):
        """Reset all metrics"""
        self._counters.clear()
        self._timers.clear()
    
    # Delegate to underlying logger
    def __getattr__(self, name):
        return getattr(self.logger, name)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    structured: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        structured: Whether to use structured JSON logging
        console_output: Whether to output to console
    
    Returns:
        Configured root logger
    """
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str, monitoring: bool = False) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        monitoring: Whether to return a MonitoringLogger
    
    Returns:
        Logger instance
    """
    if monitoring:
        return MonitoringLogger(name)
    else:
        return logging.getLogger(name)


# Default logging setup for the application
def setup_default_logging():
    """Setup default logging for AI-OS"""
    log_dir = Path.home() / ".ai-os" / "logs"
    log_file = log_dir / "ai-os.log"
    
    setup_logging(
        log_level="INFO",
        log_file=log_file,
        structured=False,
        console_output=True
    )


# Initialize default logging when module is imported
setup_default_logging()