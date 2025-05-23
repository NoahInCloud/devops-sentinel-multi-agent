"""Logging configuration for DevOps Sentinel multi-agent system."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        if hasattr(record, 'agent_id'):
            record.msg = f"[{record.agent_id}] {record.msg}"
            
        if sys.platform == "win32":
            # Windows doesn't support ANSI colors in standard console
            return super().format(record)
        else:
            # Unix-like systems support ANSI colors
            log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
            return super().format(record)

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    enable_structured_logging: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """Setup logging configuration for the application."""
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create log directory if specified
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"devops_sentinel_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    if enable_structured_logging:
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": "%(lineno)d"}',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        # Use plain formatter for file output
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.INFO)
    
    logging.info(f"Logging configured - Level: {log_level}, File: {log_file or 'None'}")

def get_logger(name: str, agent_id: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with optional agent ID context."""
    logger = logging.getLogger(name)
    
    if agent_id:
        # Add agent ID to logger context
        class AgentAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                return f"[{self.extra['agent_id']}] {msg}", kwargs
        
        return AgentAdapter(logger, {'agent_id': agent_id})
    
    return logger

def log_function_call(func):
    """Decorator to log function calls with arguments and return values."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised exception: {e}")
            raise
    return wrapper

def log_async_function_call(func):
    """Decorator to log async function calls with arguments and return values."""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async {func.__name__} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Async {func.__name__} raised exception: {e}")
            raise
    return wrapper