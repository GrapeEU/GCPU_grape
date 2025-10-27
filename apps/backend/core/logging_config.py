"""
Logging Configuration for Agent Execution

Configures colored, structured logging for backend debugging.
"""

import logging
import sys
from typing import Any


class ColoredFormatter(logging.Formatter):
    """Colored formatter for terminal output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Icons for different log types
    ICONS = {
        'scenario_detection': '🎯',
        'entity_extraction': '📝',
        'concept_search': '🔎',
        'neighbourhood_exploration': '🌐',
        'sparql_query': '⚡',
        'result_interpretation': '💬',
        'error': '❌',
        'success': '✅'
    }

    def format(self, record: logging.LogRecord) -> str:
        # Get color for log level
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET

        # Get icon if available
        icon = ''
        if hasattr(record, 'details') and isinstance(record.details, dict):
            step_type = record.details.get('step_type', '')
            icon = self.ICONS.get(step_type, '▪️')

        # Format: [LEVEL] icon message
        levelname = f"{color}{self.BOLD}[{record.levelname}]{reset}"
        message = f"{icon} {record.getMessage()}" if icon else record.getMessage()

        # Add timestamp
        timestamp = self.formatTime(record, '%H:%M:%S')

        return f"{timestamp} {levelname} {message}"


def setup_logging(level: str = "INFO"):
    """
    Setup logging configuration for the backend.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    ))

    root_logger.addHandler(console_handler)

    # Agent logger with special formatting
    agent_logger = logging.getLogger('agent')
    agent_logger.setLevel(level)
    agent_logger.propagate = True  # Also propagate to root

    # Suppress noisy third-party loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('langchain').setLevel(logging.WARNING)

    return root_logger
