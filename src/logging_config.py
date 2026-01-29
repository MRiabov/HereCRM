import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """
    Configure logging for the application.

    If DEV_MODE is True (or ENVIRONMENT is 'local'), enables writing logs to a file
    with rotation (10MB limit).
    """
    # Basic configuration (this might already be set elsewhere, but good to ensure defaults)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Check for local development environment
    dev_mode = os.getenv("DEV_MODE", "False").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "").lower()

    if dev_mode or environment == "local":
        # Create a rotating file handler
        # Max size: 10MB = 10 * 1024 * 1024 bytes
        # Backup count: 1 (keep one old log file, or increase if needed)
        file_handler = RotatingFileHandler(
            "backend.log", maxBytes=10 * 1024 * 1024, backupCount=1
        )

        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # Add the handler to the root logger so it captures everything
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # Also ensure uvicorn logs are captured if they aren't propagating
        logging.getLogger("uvicorn").addHandler(file_handler)
        logging.getLogger("uvicorn.access").addHandler(file_handler)

        logging.info(
            "Local development logging enabled: writing to backend.log (max 10MB)"
        )
