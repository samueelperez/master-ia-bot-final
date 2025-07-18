"""
Logging configuration for the External Data Service.
"""
import logging
import sys
from typing import Dict, Any

from core.config import settings


def setup_logging() -> None:
    """
    Set up logging for the application.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set log levels for specific loggers
    loggers = {
        "uvicorn": logging.INFO,
        "uvicorn.access": logging.INFO,
        "uvicorn.error": logging.INFO,
        "fastapi": logging.INFO,
        "aiohttp": logging.WARNING,
        "httpx": logging.WARNING,
    }
    
    for logger_name, logger_level in loggers.items():
        logging.getLogger(logger_name).setLevel(logger_level)
    
    # Create a logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
