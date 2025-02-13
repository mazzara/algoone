#config.py
import os
import json

# ==== Base Directories ==== #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HARD_MEMORY_DIR = os.path.join(BASE_DIR, 'hard_memory')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# ==== Ensure directories exist ==== #
def ensure_directories_exist():
    """Ensure necessary directories exist before use."""
    os.makedirs(HARD_MEMORY_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

ensure_directories_exist()


# ==== File Paths ==== #
ACCOUNT_INFO_FILE = os.path.join(HARD_MEMORY_DIR, 'account_info.json')
TRADE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, 'trade_limits.json')
TRADE_DECISIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'trade_decisions.json')
POSITIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'positions.json')
TOTAL_POSITIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'total_positions.json')
INDICATOR_RESULTS_FILE = os.path.join(HARD_MEMORY_DIR, 'indicator_results.json')
ORDERS_FILE = os.path.join(HARD_MEMORY_DIR, 'orders.json')

# ==== Logger Settings ==== #
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOGGER_NAME = 'AlgoOne'

# ==== Symbol Settings ==== #
SYMBOLS_CONFIG_FILE = os.path.join(HARD_MEMORY_DIR, 'symbols_allowed.json')
FOREX_MAJORS = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD']

def load_allowed_symbols():
    """Load SYMBOLS_ALLOWED from a file."""
    if os.path.exists(SYMBOLS_CONFIG_FILE):
        with open(SYMBOLS_CONFIG_FILE, 'r') as file:
            return json.load(file).get('SYMBOLS_ALLOWED', [])
    return ['BTCUSD'] # Default

SYMBOLS_ALLOWED = load_allowed_symbols()

# ==== Trade Settings ==== #
CLOSE_PROFIT_THRESHOLD = 0.0002
