#config.py
import os
import json


# ==== Base Directories ==== #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HARD_MEMORY_DIR = os.path.join(BASE_DIR, 'hard_memory')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
APP_ROOT = os.path.dirname(BASE_DIR)
CONFIG_DIR = os.path.join(APP_ROOT, 'config')

# ==== Ensure directories exist ==== #
def ensure_directories_exist():
    """Ensure necessary directories exist before use."""
    os.makedirs(HARD_MEMORY_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

ensure_directories_exist()


# ==== File Paths ==== #
# Config files #
PAUSE_FILE = os.path.join(CONFIG_DIR, 'pause.json')
INDICATOR_CONFIG_FILE = os.path.join(CONFIG_DIR, 'indicator_config.json')
TRADE_LIMIT_FILE = os.path.join(CONFIG_DIR, 'trade_limits_config.json')
AUTOTRADE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'autotrade_config_settings.json')
# Trade files #
BROKER_SYMBOLS = os.path.join(HARD_MEMORY_DIR, 'symbols.json')
ACCOUNT_INFO_FILE = os.path.join(HARD_MEMORY_DIR, 'account_info.json')
TRADE_DECISIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'trade_decisions.json')
POSITIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'positions.json')
TOTAL_POSITIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'total_positions.json')
INDICATOR_RESULTS_FILE = os.path.join(HARD_MEMORY_DIR, 'indicator_results.json')
ORDERS_FILE = os.path.join(HARD_MEMORY_DIR, 'orders.json')
CLEARANCE_HEAT_FILE = os.path.join(HARD_MEMORY_DIR, 'clearance_heat.json')
CLEARANCE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, 'clearance_limit.json')

# ==== Logger Settings ==== #
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOGGER_NAME = 'AlgoOne'

# ==== Symbol Settings ==== #
SYMBOLS_CONFIG_FILE = os.path.join(HARD_MEMORY_DIR, 'symbols_allowed.json')
FOREX_MAJORS = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD']

def load_allowed_symbols():
    """
    Load SYMBOLS_ALLOWED from a file.

    Return a list of allowed symbols. If the file does not exist

    4 digit function signature: 2901
    """
    if os.path.exists(SYMBOLS_CONFIG_FILE):
        with open(SYMBOLS_CONFIG_FILE, 'r') as file:
            return json.load(file).get('SYMBOLS_ALLOWED', [])

    return ['BTCUSD', 'ETHUSD', 'Crude-F', 'SpotCrude', 'EURUSD', 'GBPUSD',
            'Brent-F', 'SpotBrent', 'NaturalGas', 'Gold', 'Silver',
            'Coffee', 'Sugar', 'Corn', 'Soybeans',
            'EUSTX50', 'DAX', 'FTSE', 'SP500',
            'USDJPY', 'USDCHF', 'XAUUSD' ] # Default

SYMBOLS_ALLOWED = load_allowed_symbols()

# ==== Trade Settings ==== #
CLOSE_PROFIT_THRESHOLD = 5.0/100.0  # 5.0% profit
CLOSE_PROFIT_DOLLAR_THRESHOLD = 0.25  # $0.25 profit
TRAILING_PROFIT_THRESHHOLD = 0.5/100.0  # 0.5% profit
DEFAULT_VOLATILITY = 0.03
DEFAULT_ATR_MULTIPLYER = 3.0
MIN_ART_PCT = 0.02/100.0
