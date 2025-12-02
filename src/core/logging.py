import logging
import sys
from typing import Optional

from config import settings

def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure the application logging.
    
    Args:
        log_level: Optional override for the log level. If not provided,
                  uses the level from settings.
    """
    level_name = log_level.upper() if log_level else settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("workflow_orchestrator.log"),
        ]
    )
    
    # Set third-party loggers to a higher level to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
