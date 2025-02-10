# logger_config.py
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOGGER_NAME

MAX_LOG_SIZE = 5 * 1024 * 1024 # 5MB
BACKUP_COUNT = 5 # Keep 5 log files

# Create Log Rotations Settings
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding='utf-8'
)

# Set log format
log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        file_handler,  # Save logs to file
        logging.StreamHandler()  # Also print logs to console
    ]
)

# Get the root logger
logger = logging.getLogger(LOGGER_NAME)
# End of logger_config.py
