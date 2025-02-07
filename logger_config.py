import logging
import os

# Define log directory
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Define log file
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Ensure UTF-8 encoding for file logging
log_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Log to a file
        logging.StreamHandler()  # Also print logs to console
    ]
)

# Get the root logger
logger = logging.getLogger(__name__)

