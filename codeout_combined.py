

# === FILE: algoapp.py ===

# main.py
from src.connect import connect, disconnect
from src.account.account_info import get_account_info, check_account_limits
from src.positions.positions import get_positions
from src.history.history import get_trade_history
from src.symbols.symbols import get_symbols
from src.pending.orders import get_orders
from src.tick_listener import listen_to_ticks
from src.trader.trade import open_trade, close_trade, manage_trade
from src.portfolio.total_positions import get_total_positions
from src.limits.limits import load_trade_limits
from src.logger_config import logger


def on_tick(ticks):
    """
    Callback function to process tick events.
    """
    for tick in ticks:
        logger.info(f"|&|..|~~| -.-.- | Tick Event: {tick['symbol']} | Bid: {tick['bid']} | Ask: {tick['ask']} | Spread: {tick['spread']} | Time: {tick['time']}")

        # get_positions = get_total_positions(save=True, use_cache=False)
        # open_trade(tick['symbol'], get_positions=get_positions)
        # close_trade(tick['symbol'], get_positions=get_positions)

        get_total_positions(save=True, use_cache=False, report=True) # Note for self: this also check positinos as a dependency.
        open_trade(tick['symbol'])

        manage_trade(tick['symbol'])

        get_total_positions(save=True, use_cache=False) # Note for self: this also check positinos as a dependency.
        close_trade(tick['symbol'])


if __name__ == "__main__":
    if connect():  # Ensure MT5 is connected
        logger.info("OK - MT5 Connection Established in Main Script")

        # Retrieve and log account info
        load_trade_limits()
        check_account_limits()
        get_account_info()
        get_positions()
        get_orders()
        get_trade_history()
        get_symbols()

        # Process Positions
        get_total_positions(save=True, use_cache=False)

        # Listen to ticks for all symbols
        try:
            listen_to_ticks(forex_mode=True,
                            only_major_forex=True,
                            on_tick=on_tick)
        except KeyboardInterrupt:
            logger.info("Tick listener stopped by user.")
        finally:
            disconnect()
# End of Main Script


# === FILE: codeout.py ===

# ./codeout.py 
# Run this script to iterate over all python files in the project and compile a single file with all the code snippets. 
# The output file will be saved in the same directory as this script. 
# At the end you have a single file to provide to GPT and friends. 

import os
import re


# Settings
PROJECT_DIR = "."  # Change this if running from another folder
OUTPUT_FILE = "codeout_combined.py"
EXCLUDE_DIRS = {'__pycache__', '.git', 'venv', 'env', '.mypy_cache', 'build', 'dist', 'reports'}

def collect_python_files(base_dir):
    python_files = []
    for root, dirs, files in os.walk(base_dir):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                python_files.append(full_path)
    return sorted(python_files)

def extract_code(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"# Failed to read {file_path}: {e}\n"

def build_combined_file(file_list, output_path):
    with open(output_path, 'w', encoding='utf-8') as out:
        for path in file_list:
            rel_path = os.path.relpath(path, PROJECT_DIR)
            out.write(f"\n\n# === FILE: {rel_path} ===\n\n")
            code = extract_code(path)
            out.write(code)

if __name__ == "__main__":
    print(f"[Info] Collecting Python files in '{PROJECT_DIR}'...")
    all_py_files = collect_python_files(PROJECT_DIR)
    print(f"[Info] {len(all_py_files)} files found.")

    print(f"[Info] Writing combined file to '{OUTPUT_FILE}'...")
    build_combined_file(all_py_files, OUTPUT_FILE)
    print("[Success] Combined code output generated.")



# === FILE: src/__init__.py ===



# === FILE: src/account/__init__.py ===



# === FILE: src/account/account_info.py ===

# account_info.py
import MetaTrader5 as mt5
from src.logger_config import logger
import os
import json
from datetime import datetime
from src.config import HARD_MEMORY_DIR, ACCOUNT_INFO_FILE


def save_account_info(account_info):
    account_data = {
        "login": account_info.login,
        "balance": account_info.balance,
        "equity": account_info.equity,
        "margin": account_info.margin,
        "free_margin": account_info.margin_free,
        "leverage": account_info.leverage,
        "currency": account_info.currency,
        "trade_mode": account_info.trade_mode,
        "my_local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "my_local_timestamp": datetime.now().timestamp()
    }
    try:
        with open(ACCOUNT_INFO_FILE, "w", encoding='utf-8') as f:
            json.dump(account_data, f, indent=4)
        logger.info(f"OK! - Account info saved to {ACCOUNT_INFO_FILE}")
    except Exception as e:
        logger.error(f"Oh No! - Failed to save account info: {e}")

def get_account_info():
    """
    Retrieves and logs account information from MT5.
    """
    account_info = mt5.account_info()
    if account_info:
        logger.info("=== Account Info ===")
        logger.info(f" Login: {account_info.login}")
        logger.info(f" Balance: {account_info.balance} USD")
        logger.info(f" Equity: {account_info.equity} USD")
        logger.info(f" Margin: {account_info.margin} USD")
        logger.info(f" Free Margin: {account_info.margin_free} USD")
        logger.info(f" Leverage: {account_info.leverage}x")
        logger.info(f" Currency: {account_info.currency}")
        logger.info(f" Trade Mode: {account_info.trade_mode}")
        logger.info(f" Current Date Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        save_account_info(account_info)
    else:
        logger.error("Failed to retrieve account info.")
    return account_info


def check_account_limits():
    """Logs max allowed orders and positions from the broker."""
    """Logs max allowed orders and positions from the broker."""
    account_info = mt5.account_info()
    if account_info:
        logger.info(f"Trade Allowed: {account_info.trade_allowed}")
        logger.info(f"Trade Expert: {account_info.trade_expert}")
        
        # Check possible broker limits
        max_orders = getattr(account_info, "limit_orders", "Unknown")
        max_positions = getattr(account_info, "limit_positions", "Unknown")

        logger.info(f"Max Orders Allowed: {max_orders}")
        logger.info(f"Max Open Positions Allowed: {max_positions}")
    else:
        logger.error("Failed to retrieve account info from MT5.")


# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect
    if connect():
        get_account_info()
        disconnect()
# End of account_info.py


# === FILE: src/config.py ===

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
BROKER_SYMBOLS = os.path.join(HARD_MEMORY_DIR, 'symbols.json')
ACCOUNT_INFO_FILE = os.path.join(HARD_MEMORY_DIR, 'account_info.json')
TRADE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, 'trade_limits_config.json')
TRADE_DECISIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'trade_decisions.json')
POSITIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'positions.json')
TOTAL_POSITIONS_FILE = os.path.join(HARD_MEMORY_DIR, 'total_positions.json')
INDICATOR_RESULTS_FILE = os.path.join(HARD_MEMORY_DIR, 'indicator_results.json')
INDICATOR_CONFIG_FILE = os.path.join(HARD_MEMORY_DIR, 'indicator_config.json')
ORDERS_FILE = os.path.join(HARD_MEMORY_DIR, 'orders.json')
CLEARANCE_HEAT_FILE = os.path.join(HARD_MEMORY_DIR, 'clearance_heat.json')
CLEARANCE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, 'clearance_limit.json')
PAUSE_FILE = os.path.join(CONFIG_DIR, 'pause.json')

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
    return ['BTCUSD', 'ETHUSD', 'Crude-F', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'XAUUSD' ] # Default

SYMBOLS_ALLOWED = load_allowed_symbols()

# ==== Trade Settings ==== #
CLOSE_PROFIT_THRESHOLD = 1.0/100.0  # 1.0% profit
TRAILING_PROFIT_THRESHHOLD = 0.5/100.0  # 0.5% profit
DEFAULT_VOLATILITY = 0.03
DEFAULT_ATR_MULTIPLYER = 2.0


# === FILE: src/connect.py ===

import MetaTrader5 as mt5
from dotenv import load_dotenv
import os
from src.logger_config import logger

load_dotenv()

def connect():
    """
    Connects to the MetaTrader 5 terminal using credentials from .env file.
    Provides feedback on connection issues.
    """
    try:
        login_raw = os.getenv('MT5_PP_DEMO_LOGIN')
        server = os.getenv('MT5_PP_DEMO_SERVER', "").strip()
        password = os.getenv('MT5_PP_DEMO_PASSWORD', "").strip()

        # Validate login
        if not login_raw:
            logger.error("MT5_PP_DEMO_LOGIN is missing in the .env file.")
            return False
        
        try:
            login = int(login_raw.strip())
        except ValueError:
            logger.error(f"MT5_PP_DEMO_LOGIN '{login_raw}' is not a valid integer.")
            return False

        # Validate the remaining credentials
        if not server:
            logger.error("MT5_PP_DEMO_SERVER is missing or empty in the .env file.")
            return False
        if not password:
            logger.error("MT5_PP_DEMO_PASSWORD is missing or empty in the .env file.")
            return False

        # Initialize MT5 terminal
        if not mt5.initialize(login=login, server=server, password=password):
            error_code, error_msg = mt5.last_error()
            logger.error(f"Failed to initialize MT5: {error_code} - {error_msg}")
            handle_connection_error(error_code, server, login)
            return False

        # Successful initialization
        logger.info(f"Connected to MetaTrader 5 | Server: {server} | Login: {login}")

        account_info = mt5.account_info()
        if account_info:
            logger.info(f"Account Info: {account_info}")
        else:
            logger.warning("Connected, but failed to retrieve account info.")

        return True

    except Exception as e:
        logger.exception(f"Unexpected error during connection: {e}")
        return False


def disconnect():
    """
    Closes the MT5 connection safely.
    """
    mt5.shutdown()
    logger.info("Disconnected from MetaTrader 5")


def handle_connection_error(error_code, server, login):
    """
    Provides feedback on connection issues.
    """
    if error_code == -6:
        logger.error(f"Authorization failed. Check your credentials.")
        logger.error(f"Server: {server}, Login: {login}")
        logger.error("Possible causes: Invalid credentials, server down, or invalid server.")
    elif error_code == 5:
        logger.error("No connection to trade server. Check your internet connection.")
    elif error_code == 10014:
        logger.error("Terminal not connected or already closed.")
    else:
        logger.warning(f"Connection error: {error_code}")

# Run connection test
if __name__ == "__main__":
    if connect():
        print(mt5.terminal_info())  # Display connection info
        disconnect()



# === FILE: src/history/__init__.py ===



# === FILE: src/history/history.py ===

import MetaTrader5 as mt5
import os
import json
from datetime import datetime, timedelta
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR


def save_history(history):
    """
    Saves closed trades (history) to a JSON file.
    """
    history_data = []

    for deal in history:
        history_data.append({
            "ticket": deal.ticket,
            "position_id": deal.position_id,
            "order": deal.order,
            "symbol": deal.symbol,
            "type": get_order_type(deal.type),  # Convert type to human-readable
            "volume": deal.volume,
            "price": deal.price,
            "profit": deal.profit,
            "commission": deal.commission,
            "swap": deal.swap,
            "magic": deal.magic,
            "reaseon": deal.reason,
            "time_setup": datetime.fromtimestamp(deal.time).strftime("%Y-%m-%d %H:%M:%S"),
            "time_raw": deal.time,
            "comment": deal.comment
        })

    file_path = os.path.join(HARD_MEMORY_DIR, "history.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4)
        logger.info(f"Trade history saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save trade history: {e}")

def get_order_type(order_type):
    """
    Converts MT5 order type to human-readable string.
    """
    order_types = {
        0: "BUY",
        1: "SELL",
        2: "BUY_LIMIT",
        3: "SELL_LIMIT",
        4: "BUY_STOP",
        5: "SELL_STOP",
        6: "BUY_STOP_LIMIT",
        7: "SELL_STOP_LIMIT"
    }
    return order_types.get(order_type, "UNKNOWN")

def get_trade_history(days=30):
    """
    Retrieves and logs all closed trades within the last 'days' days from MT5.
    """
    date_from = datetime.now() - timedelta(days=days)
    date_to = datetime.now()

    history = mt5.history_deals_get(date_from, date_to)

    if history:
        logger.info(f"=== Trade History (Last {days} Days) ===")
        for deal in history:
            logger.info(f"Ticket: {deal.ticket}, {deal.symbol}, {get_order_type(deal.type)} {deal.volume} lots @ {deal.price} Profit: {deal.profit}")
        save_history(history)
    else:
        logger.info("No closed trades found.")
        save_history([])

    return history

# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        get_trade_history()
        disconnect()



# === FILE: src/indicators/__init__.py ===



# === FILE: src/indicators/adx_double_timeframe.py ===

# adx_double_timeframe.py - ADX indicator implementation
import MetaTrader5 as mt5
import json
import os
import time
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE


"""This indicator is an expansion on simple adx indicator, with the 
addition of a second timeframe for more accurate signals.
"""


def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    Treats it as an app state rather than appending.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")



def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    write_to_hard_memory(data)


def calculate_adx(symbol, period=14):
    """ 
    Calculate ADX - Average Directional Index
    Returns BUY if trend is strong, SELL if strong donw trend, otherwise None
    """

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, period)
    if rates is None:
        logger.error(f"Failed to retrieve rates for {symbol}")
        return None

    # Extract high low close
    high_prices = [bar['high'] for bar in rates]
    low_prices = [bar['low'] for bar in rates]
    close_prices = [bar['close'] for bar in rates]

    if len(high_prices) < period:
        logger.error(f"Not enough data for {symbol}")
        return None

    # Calculate directional movement
    plus_dm = [
        max(high_prices[i] - high_prices[i - 1], 0)
        if high_prices[i] - high_prices[i - 1] > low_prices[i - 1] - low_prices[i]
        else 0
        for i in range(1, len(high_prices))
    ]
    minus_dm = [
        max(low_prices[i - 1] - low_prices[i], 0)
        if low_prices[i - 1] - low_prices[i] > high_prices[i] - high_prices[i - 1]
        else 0
        for i in range(1, len(high_prices))
    ]

    plus_di = sum(plus_dm) / period
    minus_di = sum(minus_dm) / period

    adx = abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0

    logger.info(f"ADX for {symbol}: {adx:.2f} | +DI: {plus_di:.2f} | -DI: {minus_di:.2f}")

    if plus_di > minus_di and adx > 0.2:
        signal = "BUY"
    elif minus_di > plus_di and adx > 0.2:
        signal = "SELL"
    else:
        signal = "NONE"

    indicator_result(
            symbol,
            "ADX",
            signal,
            adx,
            {"period": period}, 
            {"plus_di": plus_di, "minus_di": minus_di}
        )
    return (signal, adx, plus_di, minus_di) if signal != "NONE" else None

# End of adx_indicator.py



# === FILE: src/indicators/adx_indicator.py ===

# adx_indicator.py - ADX indicator implementation
import MetaTrader5 as mt5
import json
import os
import time
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def get_signal(symbol, **kwargs):
    """
    Get the signal for the ADX indicator.
    """
    return calculate_adx(symbol, **kwargs)


def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    Treats it as an app state rather than appending.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")



def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")

        }
    }
    # write_to_hard_memory(data)



def calculate_adx(symbol, period=14):
    """
    Calculate ADX (Average Directional Index) using Welles Wilder's method,
    with debug logs of intermediate calculations.
    """

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 200)
    if rates is None or len(rates) < period + 1:
        logger.error(f"Not enough data for {symbol}")
        return None

    logger.debug(f"--- {symbol} RATES (LAST FEW) ---")
    for i in range(max(0, len(rates)-5), len(rates)):
        bar_time = datetime.utcfromtimestamp(rates[i]['time']).strftime('%Y-%m-%d %H:%M:%S')
        logger.debug(
            f"i={i}, time={bar_time}, O={rates[i]['open']}, "
            f"H={rates[i]['high']}, L={rates[i]['low']}, C={rates[i]['close']}"
        )

    def wilder_smooth(values, w_period, first_is_sum=True):
        """
        Wilder smoothing for arrays (TR, +DM, -DM, or DX).
        first_is_sum=True => initial seed = sum(...)
        first_is_sum=False => initial seed = average(...)
        """
        length = len(values)
        sm = [0.0] * length
        if length < w_period:
            return sm

        block_sum = sum(values[0:w_period])
        if first_is_sum:
            # used by TR, +DM, -DM
            sm[w_period - 1] = block_sum
        else:
            # used by DX => ADX
            sm[w_period - 1] = block_sum / w_period

        for i in range(w_period, length):
            sm[i] = sm[i-1] - (sm[i-1] / w_period) + (values[i] / w_period)
            # sm[i] = ( (w_period - 1) / w_period ) * sm[i-1] + (1.0 / w_period) * values[i]
        return sm

    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    # Build TR, +DM, -DM for each bar (except the very first)
    for i in range(1, len(rates)):
        curr = rates[i]
        prev = rates[i - 1]

        high_low   = curr['high'] - curr['low']
        high_close = abs(curr['high'] - prev['close'])
        low_close  = abs(curr['low'] - prev['close'])
        tr = max(high_low, high_close, low_close)
        tr_list.append(tr)

        up_move   = curr['high'] - prev['high']
        down_move = prev['low'] - curr['low']

        if up_move > down_move and up_move > 0:
            plus_dm_list.append(up_move)
        else:
            plus_dm_list.append(0.0)

        if down_move > up_move and down_move > 0:
            minus_dm_list.append(down_move)
        else:
            minus_dm_list.append(0.0)

    # Debug: Show the last few raw TR, +DM, -DM
    logger.debug(f"--- RAW TR/+DM/-DM (LAST FEW) ---")
    for i in range(max(0, len(tr_list)-5), len(tr_list)):
        logger.debug(
            f"i={i}, TR={tr_list[i]:.5f}, +DM={plus_dm_list[i]:.5f}, -DM={minus_dm_list[i]:.5f}"
        )

    # Wilder-smooth TR, +DM, -DM
    tr_smoothed      = wilder_smooth(tr_list,      period, first_is_sum=True)
    plus_dm_smoothed = wilder_smooth(plus_dm_list, period, first_is_sum=True)
    minus_dm_smoothed= wilder_smooth(minus_dm_list,period, first_is_sum=True)

    length = len(tr_smoothed)
    if length < period:
        logger.error(f"Not enough data AFTER smoothing for {symbol}")
        return None

    # Debug: Show the last few smoothed TR/+DM/-DM
    logger.debug(f"--- SMOOTHED TR/+DM/-DM (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(
            f"i={i}, TR_s={tr_smoothed[i]:.5f}, +DM_s={plus_dm_smoothed[i]:.5f}, "
            f"-DM_s={minus_dm_smoothed[i]:.5f}"
        )

    # Compute +DI, -DI each bar
    plus_di_list  = [0.0] * length
    minus_di_list = [0.0] * length

    for i in range(length):
        tr_val = tr_smoothed[i]
        if tr_val != 0.0:
            plus_di_list[i]  = 100.0 * (plus_dm_smoothed[i] / tr_val)
            minus_di_list[i] = 100.0 * (minus_dm_smoothed[i] / tr_val)

    # Debug: Show last few +DI / -DI
    logger.debug(f"--- +DI/-DI (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(
            f"i={i}, +DI={plus_di_list[i]:.5f}, -DI={minus_di_list[i]:.5f}"
        )

    # Compute DX each bar
    dx_list = [0.0] * length
    for i in range(length):
        pd = plus_di_list[i]
        md = minus_di_list[i]
        denom = pd + md
        if denom != 0.0:
            dx_list[i] = 100.0 * abs(pd - md) / denom
        else:
            dx_list[i] = 0.0

    # Debug: Show last few raw DX
    logger.debug(f"--- DX (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(f"i={i}, DX={dx_list[i]:.5f}")

    # Wilder-smooth DX -> ADX (avg seed)
    adx_smoothed = wilder_smooth(dx_list, period, first_is_sum=False)

    # Debug: Show last few ADX
    logger.debug(f"--- ADX SMOOTHED (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(f"i={i}, ADX={adx_smoothed[i]:.5f}")

    # Take the last bar's ADX, +DI, -DI
    adx_current     = adx_smoothed[-1]
    plus_di_current = plus_di_list[-1]
    minus_di_current= minus_di_list[-1]

    logger.info(
        f"Indicator {symbol}: "
        f"ADX: {adx_current:.2f} | +DI: {plus_di_current:.2f} | -DI: {minus_di_current:.2f}"
    )

    # Decide signal
    if plus_di_current > minus_di_current and adx_current >= 10:
        signal = "BUY"
    elif minus_di_current > plus_di_current and adx_current >= 10:
        signal = "SELL"
    elif adx_current < 10:
        signal = "CLOSE"
    else:
        signal = "NONE"

    logger.info(
        f"Signal adx_indicator: {signal} | "
        f"ADX: {adx_current:.2f} | +DI: {plus_di_current:.2f} | -DI: {minus_di_current:.2f}"
    )

    indicator_result(
        symbol,
        "ADX",
        signal,
        adx_current,
        {"period": period},
        {"plus_di": plus_di_current, "minus_di": minus_di_current}
    )

    # return (signal, adx_current, plus_di_current, minus_di_current) if signal != "NONE" else None
    
    return {
            "indicator": "ADX",
            "signal": signal,
            "values": {
                "adx": adx_current,
                "plus_di": plus_di_current,
                "minus_di": minus_di_current
            }
    }



# End of adx_indicator.py


# === FILE: src/indicators/adx_tick_indicator.py ===

# adx_ticker_indicator.py
import json
import time
from datetime import datetime

from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE

# We reuse the same "indicator_result" pattern
# that writes results to a JSON file
def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")

def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory, same as in adx_indicator.py
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    write_to_hard_memory(data)


# ------------------------------------------------------------------------
# A small "ticker-based bar" buffer:
# Each entry is a dict with:
#   {
#     "time":  <datetime of bar close>,
#     "open":  <float>,
#     "high":  <float>,
#     "low":   <float>,
#     "close": <float>
#   }
# ------------------------------------------------------------------------
tick_bars = []  # in practice, might store 500 or 1000 to handle warmup + ongoing


def wilder_smooth(values, w_period, first_is_sum=True):
    """
    Wilder smoothing for arrays (TR, +DM, -DM, or DX).
    first_is_sum=True => initial seed = sum(...)
    first_is_sum=False => initial seed = average(...)
    
    Then from i=w_period onward:
      sm[i] = sm[i-1] - (sm[i-1]/w_period) + (values[i]/w_period)
    """
    length = len(values)
    sm = [0.0] * length
    if length < w_period:
        return sm

    block_sum = sum(values[0:w_period])
    if first_is_sum:
        sm[w_period - 1] = block_sum
    else:
        # for DX => ADX
        sm[w_period - 1] = block_sum / w_period

    for i in range(w_period, length):
        sm[i] = sm[i-1] - (sm[i-1] / w_period) + (values[i] / w_period)

    return sm


def update_adx_with_tick(symbol, tick_price, period=14, warmup=2):
    """
    1) Called on every new tick.
    2) Builds a 'micro-bar' from the previous tick's close to this tick's price.
    3) If we have at least period+warmup bars, compute ADX via Wilder's method
       and call 'indicator_result' with the final values.

    :param symbol: e.g. "BTCUSD"
    :param tick_price: The new tick's price (float)
    :param period: ADX period (default 14)
    :param warmup: extra bars beyond 'period' to ensure we have a stable ADX
    """
    # 1) Create a new "bar" from the last close to this new tick price
    now_dt = datetime.now()
    if len(tick_bars) == 0:
        # This is our first bar => we have no previous close, so just store
        bar = {
            "time": now_dt,
            "open": tick_price,
            "high": tick_price,
            "low":  tick_price,
            "close": tick_price
        }
        tick_bars.append(bar)
        logger.debug("Initialized first tick-bar")
        return None

    # We already have at least one bar => we 'close' the previous bar
    prev_bar = tick_bars[-1]
    new_bar = {
        "time": now_dt,
        "open": prev_bar["close"],
        "high": max(prev_bar["close"], tick_price),
        "low":  min(prev_bar["close"], tick_price),
        "close": tick_price
    }
    tick_bars.append(new_bar)

    # If we want to limit max bars stored (say 2000 bars), we can do:
    # if len(tick_bars) > 2000:
    #     tick_bars.pop(0)

    # 2) Check if we have enough bars to do an ADX calculation
    if len(tick_bars) < period + warmup:
        logger.debug("Not enough tick-bars to compute ADX yet.")
        return None

    # 3) Build TR, +DM, -DM for all bars
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    # We'll skip the first bar because it doesn't have a 'previous' bar
    for i in range(1, len(tick_bars)):
        curr_bar = tick_bars[i]
        prev_bar = tick_bars[i - 1]

        high_low = curr_bar["high"] - curr_bar["low"]
        high_close = abs(curr_bar["high"] - prev_bar["close"])
        low_close = abs(curr_bar["low"] - prev_bar["close"])
        tr = max(high_low, high_close, low_close)
        tr_list.append(tr)

        up_move = curr_bar["high"] - prev_bar["high"]
        down_move = prev_bar["low"] - curr_bar["low"]

        if up_move > down_move and up_move > 0:
            plus_dm_list.append(up_move)
        else:
            plus_dm_list.append(0.0)

        if down_move > up_move and down_move > 0:
            minus_dm_list.append(down_move)
        else:
            minus_dm_list.append(0.0)

    # 4) Wilder-smooth TR, +DM, -DM
    tr_s = wilder_smooth(tr_list,      period, first_is_sum=True)
    plus_s = wilder_smooth(plus_dm_list, period, first_is_sum=True)
    minus_s = wilder_smooth(minus_dm_list,period, first_is_sum=True)

    length = len(tr_s)
    if length < period:
        logger.debug("Wilder smoothing not enough data.")
        return None

    # 5) Compute +DI, -DI each bar
    plus_di_list  = [0.0]*length
    minus_di_list = [0.0]*length
    for i in range(length):
        if tr_s[i] != 0.0:
            plus_di_list[i]  = 100.0 * (plus_s[i] / tr_s[i])
            minus_di_list[i] = 100.0 * (minus_s[i] / tr_s[i])

    # 6) DX each bar
    dx_list = [0.0]*length
    for i in range(length):
        pd = plus_di_list[i]
        md = minus_di_list[i]
        denom = pd + md
        if denom != 0.0:
            dx_list[i] = 100.0 * abs(pd - md) / denom

    # 7) Wilder-smooth DX => ADX
    adx_s = wilder_smooth(dx_list, period, first_is_sum=False)

    # 8) The "current" ADX is the last in the series
    adx_current     = adx_s[-1]
    plus_di_current = plus_di_list[-1]
    minus_di_current= minus_di_list[-1]

    logger.info(
        f"(TICK-ADX) {symbol}: "
        f"ADX={adx_current:.2f}, +DI={plus_di_current:.2f}, -DI={minus_di_current:.2f}"
    )

    # 9) Determine the signal (example thresholds)
    if plus_di_current > minus_di_current and adx_current >= 30:
        signal = "BUY"
    elif minus_di_current > plus_di_current and adx_current >= 30:
        signal = "SELL"
    elif adx_current < 30:
        signal = "CLOSE"
    else:
        signal = "NONE"

    logger.info(
        f"(TICK-ADX) Signal: {signal} | "
        f"ADX={adx_current:.2f}, +DI={plus_di_current:.2f}, -DI={minus_di_current:.2f}"
    )

    # 10) Save to indicator_result (same as your candle-based approach)
    indicator_result(
        symbol,
        "ADX_TICK",
        signal,
        adx_current,
        {"period": period, "warmup": warmup},
        {"plus_di": plus_di_current, "minus_di": minus_di_current}
    )

    # Return the same style tuple if you want
    return (signal, adx_current, plus_di_current, minus_di_current) if signal != "NONE" else None



# === FILE: src/indicators/atr_indicator.py ===

# src/indicators/atr_indicator.py

import MetaTrader5 as mt5
import json
import os
import random
from datetime import datetime
from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def get_signal(symbol, **kwargs):
    """
    Get the signal for the ATR indicator.
    """
    return calculate_atr(symbol, **kwargs)


def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    Treats it as an app state rather than appending.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")


def indicator_result(symbol, indicator, signal, value, calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    # Optionally, write the data to disk:
    # write_to_hard_memory(data)


def calculate_atr(symbol, period=14, low_threshold=None, high_threshold=None):
    """
    Calculate the Average True Range (ATR) indicator.
    
    The ATR is a volatility indicator that measures the range of price movement.
    It is calculated as the average of the True Range (TR) over a specified period.
    TR is defined as the maximum of:
        - (High - Low)
        - abs(High - Previous Close)
        - abs(Low - Previous Close)
    
    Parameters:
        symbol (str): The trading symbol.
        period (int): The number of bars over which to average TR (default is 14).
        low_threshold (float, optional): If provided and ATR is below this value, signal "LOW VOL".
        high_threshold (float, optional): If provided and ATR is above this value, signal "HIGH VOL".
    
    Returns:
        dict: A dictionary containing the indicator name, generated signal, and ATR value.
    """
    required_bars = period + 1  # one additional bar is needed to calculate the first TR
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, required_bars)
    if rates is None or len(rates) < required_bars:
        logger.error(f"Not enough data to calculate ATR for {symbol}")
        return None

    true_ranges = []
    # Compute the True Range for each bar (starting from index 1)
    for i in range(1, len(rates)):
        current = rates[i]
        previous = rates[i-1]
        high_low = current['high'] - current['low']
        high_prev_close = abs(current['high'] - previous['close'])
        low_prev_close = abs(current['low'] - previous['close'])
        tr = max(high_low, high_prev_close, low_prev_close)
        true_ranges.append(tr)
        logger.debug(f"Bar {i}: High={current['high']}, Low={current['low']}, Prev Close={previous['close']}, TR={tr}")

    # Calculate ATR as the simple average of the last `period` true range values
    atr_value = sum(true_ranges[-period:]) / period

    # Determine a trading signal based on optional thresholds
    if low_threshold is not None and atr_value < low_threshold:
        signal = "LOW VOL"
    elif high_threshold is not None and atr_value > high_threshold:
        signal = "HIGH VOL"
    else:
        signal = "NO SIGNAL"

    # Log the result and persist the indicator result using the shared function.
    indicator_result(
        symbol,
        "ATR",
        signal,
        atr_value,
        {"true_ranges": true_ranges},
        {"period": period, "low_threshold": low_threshold, "high_threshold": high_threshold}
    )

    logger.info(f"[INFO] :: ATR for {symbol}: {atr_value:.2f} | Signal: {signal}")

    # Return a result dictionary for further processing if needed.
    return {
        "indicator": "ATR",
        "signal": signal,
        "value": atr_value,
        "values": {
            "atr": atr_value,
            "true_ranges": true_ranges
        }
    }

# End of atr_indicator.py


# === FILE: src/indicators/rsi_indicator.py ===

# src/indicators/rsi_indicator.@property
import MetaTrader5 as mt5
import json
import os
import time 
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def get_signal(symbol, **kwargs):
    """
    Get the signal for the RSI indicator.
    """
    return calculate_rsi(symbol, **kwargs)


def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")

        }
    }


def calculate_rsi(symbol, period=14, overbought=70, oversold=30):
    """Calculate RSI (Relative Strength Index) using Welles Wilder's method."""
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, period + 1)
    if rates is None or len(rates) < period + 1:
        logger.error(f"Failed to get rates for {symbol}")
        return None
    
    closes = [rate['close'] for rate in rates]

    deltas = [closes[i+1] - closes[i] for i in range(len(closes) - 1)]

    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    avg_gain = sum(gains) / period 
    avg_loss = sum(losses) / period 

    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    if rsi < oversold:
        signal = "BUY"
    elif rsi > overbought:
        signal = "SELL"
    else:
        signal = "CLOSE"

    logger.info(f"Indicator {symbol}: RSI: {rsi:.2f}")
    logger.info(f"Signal rsi_indicator: {signal} | RSI: {rsi:.2f}")

    if signal == 'NONE':
        return None

    return {
            "indicator": "RSI",
            "signal": signal,
            "value": {
                "rsi": rsi
            },
    }


# end of rsi_indicator.py


# === FILE: src/indicators/scalp_adx.py ===

# src/indicators/scalp_adx.py

import MetaTrader5 as mt5
import json
import os
from datetime import datetime
from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick
from src.indicators.adx_indicator import calculate_adx  # reusing your ADX calculation


def get_signal(symbol, **kwargs):
    """
    Get the signal for the ADX indicator.
    """
    return calculate_adx(symbol, **kwargs)


def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    Treats it as an app state rather than appending.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")


def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")

        }
    }
    # write_to_hard_memory(data)



def calculate_sma(prices, period):
    """Calculate the simple moving average of the given prices."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_scalp_adx(symbol, period=14, threshold=20,
                        sma_short_period=9, sma_long_period=21):
    """
    Calculate a ScalpADX indicator:
    
    - Uses the ADX calculation (with DI+ and DI- computed in calculate_adx)
    - Computes two SMAs from closing prices: one short (default 9 bars) and one long (default 21 bars)
    - Decides a signal:
        • If ADX is below the threshold: "NO SIGNAL"
        • If ADX is above threshold:
            - "LONG" if DI+ > DI- and short SMA > long SMA
            - "SHORT" if DI- > DI+ and short SMA < long SMA
            - Otherwise, "HOLD"
    
    The result is passed to indicator_result so that it can be stored/ingested by other modules.
    """
    # Request enough bars for both ADX and SMA computations.
    # We use 200 bars for ADX (as in your existing function) and ensure at least sma_long_period bars.
    required_bars = max(200, sma_long_period)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, required_bars)
    if rates is None or len(rates) < sma_long_period:
        logger.error(f"Not enough data to calculate SMAs for {symbol}")
        return None

    # Calculate SMAs using closing prices
    closing_prices = [bar['close'] for bar in rates]
    short_sma = calculate_sma(closing_prices, sma_short_period)
    long_sma = calculate_sma(closing_prices, sma_long_period)
    if short_sma is None or long_sma is None:
        logger.error(f"Failed to compute SMAs for {symbol}")
        return None

    # Calculate ADX (which also computes DI+ and DI-) using your existing function
    adx_data = calculate_adx(symbol, period=period)
    if adx_data is None:
        logger.error(f"ADX calculation failed for {symbol}")
        return None

    adx_value = adx_data["values"]["adx"]
    plus_di = adx_data["values"]["plus_di"]
    minus_di = adx_data["values"]["minus_di"]

    # Decide on the trading signal
    if adx_value <= threshold:
        signal = "NO SIGNAL"
    else:
        if plus_di > minus_di and short_sma > long_sma:
            signal = "BUY"
        elif minus_di > plus_di and short_sma < long_sma:
            signal = "SELL"
        else:
            signal = "HOLD"

    # Log and persist the indicator result via the shared function.
    indicator_result(
        symbol,
        "ScalpADX",
        signal,
        adx_value,
        {"plus_di": plus_di, "minus_di": minus_di, "sma_short": short_sma, "sma_long": long_sma},
        {"period": period, "threshold": threshold,
         "sma_short_period": sma_short_period, "sma_long_period": sma_long_period}
    )

    # Return a result dictionary for further processing if needed.
    return {
        "indicator": "ScalpADX",
        "signal": signal,
        "values": {
            "adx": adx_value,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "sma_short": short_sma,
            "sma_long": long_sma
        }
    }


# === FILE: src/indicators/signal_indicator.py ===

# src/indicators/signal_indicator.py 
import MetaTrader5 as mt5
import json
import importlib
import os
import time
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_CONFIG_FILE, INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def load_config():
    """Load indicator config file or create and save a default configuration."""
    if os.path.exists(INDICATOR_CONFIG_FILE):
        with open(INDICATOR_CONFIG_FILE, 'r') as file:
            return json.load(file)
    else:
        default_config = {
            "symbols": {
                "BTCUSD": {
                    "indicators": ["ADX", "RSI"]
                },
                "EURUSD": {
                    "indicators": ["ADX"]
                }
            },
            "position_manager_indicator": {
                "ATR": {
                    "period": 14
                }
            },
            "indicators": [
                {
                    "name": "ATR",
                    "module": "src.indicators.atr_indicator",
                    "function": "calculate_atr",
                    "parameters": {
                        "period": 14
                    }
                },
                {
                    "name": "ADX",
                    "module": "src.indicators.adx_indicator",
                    "function": "calculate_adx",
                    "parameters": {
                        "period": 14
                    }
                },
                {
                    "name": "ScalpADX",
                    "module": "src.indicators.scalp_adx",
                    "function": "calculate_scalp_adx",
                    "parameters": {
                        "period": 14,
                        "threshold": 20,
                        "sma_short_period": 9,
                        "sma_long_period": 21
                    }
                },
                {
                    "name": "RSI",
                    "module": "src.indicators.rsi_indicator",
                    "function": "calculate_rsi",
                    "parameters": {
                        "period": 14,
                        "overbought": 55,
                        "oversold": 50
                    }
                }
            ]
        }
        # Save the default config to the file
        with open(INDICATOR_CONFIG_FILE, 'w') as file:
            json.dump(default_config, file, indent=4)
        return default_config

def get_indicator_signal(indicator_config, symbol):
    """
    Dinamically load indicator module and calls its signal function.
    4 digit function signature: 1918
    """
    module_name = indicator_config.get('module')
    function_name = indicator_config.get('function')
    params = indicator_config.get('parameters', {})

    try:
        mod = importlib.import_module(module_name)
        func = getattr(mod, function_name)
        result = func(symbol, **params)
        logger.info(f"{indicator_config.get('name')} signal: {result}")
        return result
    except Exception as e:
        logger.error(f"[ERROR 1918] :: Error calling {module_name}.{function_name} for {symbol}: {e}")
        return None


def dispatch_position_manager_indicator(symbol, indicator_name):
    """
    Loads config, selects the indicator configured for position management, and runs it.
    
    The configuration should have a key "position_manager_indicator" that is an object
    mapping the indicator name (e.g., "ATR") to its parameters. This function finds
    the corresponding global indicator definition, merges its parameters with the
    position manager-specific overrides, and calls the indicator function.
    """
    config = load_config()

    # Retrieve position manager configuration.
    # Expected format: {"position_manager_indicator": { "ATR": { "period": 14 } } }
    pm_config = config.get("position_manager_indicator", {})
    if not pm_config:
        logger.error("No position manager indicator is configured in the config file.")
        return {}

    # For modularity, allow for a single position management indicator, regardless of its name.
    # (If you later support multiple, you could iterate over all keys.)
    indicator_name, pm_settings = list(pm_config.items())[0]

    # Find the matching indicator in the global indicators list.
    global_indicators = config.get("indicators", [])
    indicator_definition = next(
        (item for item in global_indicators if item.get("name") == indicator_name),
        None
    )
    if indicator_definition is None:
        logger.error(f"Position manager indicator '{indicator_name}' not found in global indicators.")
        return {}

    # Merge global parameters with position manager specific settings.
    merged_parameters = indicator_definition.get("parameters", {}).copy()
    merged_parameters.update(pm_settings)

    # Create a copy of the indicator definition with the merged parameters.
    pm_indicator_definition = indicator_definition.copy()
    pm_indicator_definition["parameters"] = merged_parameters

    # Call the indicator function using the merged parameters.
    result = get_indicator_signal(pm_indicator_definition, symbol)
    signals = {}
    if result is not None:
        signals[indicator_name] = result

    logger.debug(f"[DEBUG] :: Position manager indicator signal for {symbol}: {signals}")
    return signals


def dispatch_signals(symbol):
    """
    Loads config, calls each indicator and saves results.
    4 digit function signature: 1715
    """
    config = load_config()
    global_indicators = config.get('indicators', [])
    
    symbol_config = config.get('symbols', {}).get(symbol, {})
    allowed_indicator = symbol_config.get('indicators', [])

    signals = {}

    # If allowed indicators are specified, only run those indicators.
    if allowed_indicator:
        for indicator in global_indicators:
            if indicator.get('name') in allowed_indicator:
                result = get_indicator_signal(indicator, symbol)
                if result is not None:
                    signals[indicator.get('name', 'unknown')] = result
    else:
        # If no symbol-specific indicators are configured, run all global indicators.
        for indicator in global_indicators:
            result = get_indicator_signal(indicator, symbol)
            if result is not None:
                signals[indicator.get('name', 'unknown')] = result

    logger.debug(f"[DEBUG 1715] :: Dispatching called signals for {symbol} and indicators: {global_indicators}")
    logger.debug(f"[DEBUG 1715] :: Signals: {signals}")
    return signals


def write_indicator_results(data):
    logger.info(f"Writing indicator results to: {INDICATOR_RESULTS_FILE}")
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator results updated: {data}")
        logger.info(f"Writing indicator results to: {os.path.abspath(INDICATOR_RESULTS_FILE)}")

    except Exception as e:
        logger.error(f"Failed to save indicator results: {e}")


def send_signals(symbol, signals):
    """Transmits the signals to the trader."""
    logger.info(f"Sending signals for {symbol}: {signals}")
    write_indicator_results(signals)


def main(symbol):
    signals = dispatch_signals(symbol)
    send_signals(symbol, signals)

if __name__ == '__main__':
    symbol = 'BTCUSD'
    main(symbol)


# End of signal_indicator.py



# === FILE: src/limits/__init__.py ===



# === FILE: src/limits/limits.py ===

# limits.py
import json
import os
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, TRADE_LIMIT_FILE


def generate_default_trade_limits():
    """
    Generates a default trade limits configuration file if it does not exist.
    """
    default_limits = {
        "BTCUSD": {
            "MAX_LONG_SIZE": 0.05,
            "MAX_SHORT_SIZE": 0.05,
            "COOLDOWN_SECONDS": 300,
            "MAX_CAPITAL_ALLOCATION": 5000,
            "DEFAULT_LOT_SIZE": 0.01,
            "MAX_ORDERS": 100
        },
        "EURUSD": {
            "MAX_LONG_SIZE": 1.0,
            "MAX_SHORT_SIZE": 1.0,
            "COOLDOWN_SECONDS": 120,
            "MAX_CAPITAL_ALLOCATION": 10000,
            "DEFAULT_LOT_SIZE": 0.01,
            "MAX_ORDERS": 100
        }
    }

    with open(TRADE_LIMIT_FILE, "w", encoding="utf-8") as f:
        json.dump(default_limits, f, indent=4)
    logger.info(f"Default trade limits file created at {TRADE_LIMIT_FILE}")


def load_trade_limits():
    """
    Loads trade limits configuration from JSON, creating a default file if missing.
    """
    if not os.path.exists(TRADE_LIMIT_FILE):
        logger.warning(f"Trade limits file {TRADE_LIMIT_FILE} not found. Generating default.")
        generate_default_trade_limits()
    
    try:
        with open(TRADE_LIMIT_FILE, "r", encoding="utf-8") as f:
            limits = json.load(f)
        return limits
    except Exception as e:
        logger.error(f"Failed to load trade limits: {e}")
        return {}

if __name__ == "__main__":
    trade_limits = load_trade_limits()
    print(json.dumps(trade_limits, indent=4))

# End of limits.py


# === FILE: src/logger_config.py ===

# logger_config.py
import logging
from logging.handlers import RotatingFileHandler
from src.config import LOG_FILE, LOGGER_NAME

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
    level=logging.DEBUG,  # Set default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
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


# === FILE: src/pending/__init__.py ===



# === FILE: src/pending/orders.py ===

# orders.py
import MetaTrader5 as mt5
import os
import json
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, ORDERS_FILE

# Ensure the `hard_memory` directory exists
# HARD_MEMORY_DIR = "hard_memory"
# os.makedirs(HARD_MEMORY_DIR, exist_ok=True)

def save_orders(orders):
    """
    Saves pending orders to a JSON file.
    """
    orders_data = []

    for order in orders:
        orders_data.append({
            "ticket": order.ticket,
            "symbol": order.symbol,
            "type": order.type,  # 2 = BUY_LIMIT, 3 = SELL_LIMIT, 4 = BUY_STOP, 5 = SELL_STOP
            "type_str": get_order_type(order.type),  # Convert type to human-readable
            "volume_current": order.volume_current,
            "price_open": order.price_open,
            "sl": order.sl,
            "tp": order.tp,
            "price_current": order.price_current,
            "time_setup": datetime.fromtimestamp(order.time_setup).strftime("%Y-%m-%d %H:%M:%S"),
            "expiration": datetime.fromtimestamp(order.time_expiration).strftime("%Y-%m-%d %H:%M:%S") if order.time_expiration else "GTC",
            "comment": order.comment
        })

    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders_data, f, indent=4)
        logger.info(f"Ok - Pending orders saved to {ORDERS_FILE}")
    except Exception as e:
        logger.error(f"Oh No! - Failed to save pending orders: {e}")


def get_order_type(order_type):
    """
    Converts MT5 order type to human-readable string.
    """
    order_types = {
        0: "BUY",
        1: "SELL",
        2: "BUY_LIMIT",
        3: "SELL_LIMIT",
        4: "BUY_STOP",
        5: "SELL_STOP",
        6: "BUY_STOP_LIMIT",
        7: "SELL_STOP_LIMIT"
    }
    return order_types.get(order_type, "UNKNOWN")

def get_orders():
    """
    Retrieves and logs all pending orders from MT5.
    """
    orders = mt5.orders_get()

    if orders:
        logger.info("=== Pending Orders ===")
        for order in orders:
            logger.info(f"Ticket: {order.ticket} {order.symbol} {get_order_type(order.type)} {order.volume_current} lots @ {order.price_open}")
        save_orders(orders)
    else:
        logger.info("No pending orders found.")
        save_orders([])

    return orders

# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        get_orders()
        disconnect()

# End of orders.py


# === FILE: src/portfolio/__init__.py ===



# === FILE: src/portfolio/total_positions.py ===

# src/portfolio/total_positions.py
import MetaTrader5 as mt5
from src.logger_config import logger
import json
import os
import time
from datetime import datetime
from src.positions.positions import get_positions
from src.config import (HARD_MEMORY_DIR,
                        TOTAL_POSITIONS_FILE,
                        POSITIONS_FILE,
                        CLOSE_PROFIT_THRESHOLD,
                        TRAILING_PROFIT_THRESHHOLD)

### Functions Summary in this module - why this? to sign if a mudule gets too overcrowded with functions, indicating need to refactoring ### 
# load_cached_positions(retries=3, delay=0.2)
# get_total_positions(save=True, use_cache=True)
# save_total_positions(summary)


total_positions_cache = {}


def load_cached_positions(retries=3, delay=0.2):
    """
    Loads cached positions from 'hard_memory/positions.json'.
    """
    logger.info("Loading cashed positions................")

    if not os.path.exists(POSITIONS_FILE):
        logger.warning('No cashed positions found. File not found.')
        get_positions()
        time.sleep(delay)
        logger.info('Positions just pulled from MT5.')
        return load_cached_positions(retries=retries, delay=delay)

    file_age = time.time() - os.path.getmtime(POSITIONS_FILE)
    logger.info(f'Check cached-expire positions age: {file_age:.2f} seconds')

    if file_age > 10: # 10 seconds old
        logger.warning('Cashed positions are outdated.')
        get_positions()
        time.sleep(delay)
        logger.info('Positions just pulled from MT5.')
        return load_cached_positions(retries=retries, delay=delay)

    for attempt in range(retries):
        try:
            with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
                positions = json.load(f)
            if 'positions' in positions:
                logger.info(f"Positions loaded from cache: {len(positions)}")
                return positions['positions']
            else:
                logger.warning(f"Loaded JSON does not contain 'positions' key. Retrying...")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Retry {attempt+1}/{retries}: Failed to load cached positions: {e}")
            time.sleep(delay)

    logger.error('Failed to load cached positions after multiple attempts.')
    return []


def load_total_positions_accounting():
    if os.path.exists(TOTAL_POSITIONS_FILE):
        try:
            with open(TOTAL_POSITIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load total positions: {e}")
    return {}


def process_positions(positions):
    """
    Processes raw positions into detailed arrays for each symbol and side.
    """
    processed = {}
    for pos in positions:
        symbol = pos['symbol']
        side = "LONG" if pos['type'] == "BUY" else "SHORT"

        if symbol not in processed:
            processed[symbol] = {
                "LONG": {"TICKETS": [],
                         "SIZES": [],
                         "PRICES": [],
                         "CURRENT_PRICES": [],
                         "UNREALIZED_PROFITS": [],
                         "POSITION_TIMES": [],
                         "POSITION_TIMES_RAW": []},
                "SHORT": {"TICKETS": [],
                          "SIZES": [],
                          "PRICES": [],
                          "CURRENT_PRICES": [],
                          "UNREALIZED_PROFITS": [],
                          "POSITION_TIMES": [],
                          "POSITION_TIMES_RAW": []}
            }

        side_data = processed[symbol][side]
        side_data["TICKETS"].append(pos["ticket"])
        side_data["SIZES"].append(pos["volume"])
        side_data["PRICES"].append(pos["price_open"])
        side_data["CURRENT_PRICES"].append(pos["price_current"])
        side_data["UNREALIZED_PROFITS"].append(pos["profit"])
        side_data["POSITION_TIMES"].append(pos["time_open"])
        side_data["POSITION_TIMES_RAW"].append(pos["time_raw"])

    return processed


def aggregate_position_data(processed):
    """
    Aggregates detailed trade arrays into a final summary for each symbol/side.
    """
    summary = {}
    for symbol, sides in processed.items():
        summary[symbol] = {}
        for side, data in sides.items():
            position_count = len(data["TICKETS"])
            size_sum = sum(data["SIZES"])
            # Compute weighted average price
            total_weight = sum(data["SIZES"])
            if total_weight > 0:
                weighted_sum = sum(p * s for p, s in zip(data["PRICES"], data["SIZES"]))
                avg_price = weighted_sum / total_weight
            else:
                avg_price = 0

            unrealized_profit = sum(data["UNREALIZED_PROFITS"])

            # Compute the most recent trade's time (and its corresponding current price)
            if data["POSITION_TIMES_RAW"]:
                max_index = data["POSITION_TIMES_RAW"].index(max(data["POSITION_TIMES_RAW"]))
                last_position_time = data["POSITION_TIMES"][max_index]
                last_position_time_raw = data["POSITION_TIMES_RAW"][max_index]
                current_price = data["CURRENT_PRICES"][max_index]
            else:
                last_position_time = ""  # Using empty string to avoid None errors when formatting
                last_position_time_raw = 0
                current_price = None

            # last_position_time = max(data["POSITION_TIMES"]) if data["POSITION_TIMES"] else "" 
            # last_position_time_raw = max(data["POSITION_TIMES_RAW"]) if data["POSITION_TIMES_RAW"] else 0
            #
            summary[symbol][side] = {
                "SIZE_SUM": size_sum,
                "POSITION_COUNT": position_count,
                "AVG_PRICE": avg_price,
                "CURRENT_PRICE": current_price,
                "UNREALIZED_PROFIT": unrealized_profit,
                "LAST_POSITION_TIME": last_position_time,
                "LAST_POSITION_TIME_RAW": last_position_time_raw,
            }
            
        # Now compute the NET aggregation for the symbol.
        long_data = summary[symbol].get("LONG", {})
        short_data = summary[symbol].get("SHORT", {})

        # If a side is missing, assume zeros.
        long_size = long_data.get("SIZE_SUM", 0)
        short_size = short_data.get("SIZE_SUM", 0)
        # Net: LONG volumes are positive, SHORT volumes are negative.
        net_size = long_size - short_size
        net_count = long_data.get("POSITION_COUNT", 0) + short_data.get("POSITION_COUNT", 0)
        net_unrealized_profit = long_data.get("UNREALIZED_PROFIT", 0) + short_data.get("UNREALIZED_PROFIT", 0)

        # For AVG_PRICE, compute a weighted average using signed volumes.
        if net_size != 0:
            weighted_long = long_data.get("SIZE_SUM", 0) * long_data.get("AVG_PRICE", 0)
            weighted_short = short_data.get("SIZE_SUM", 0) * short_data.get("AVG_PRICE", 0)
            net_weighted = weighted_long - weighted_short
            net_avg_price = net_weighted / net_size
        else:
            net_avg_price = 0

        # Determine the most recent update from either side.
        if long_data.get("LAST_POSITION_TIME_RAW", 0) >= short_data.get("LAST_POSITION_TIME_RAW", 0):
            net_current_price = long_data.get("CURRENT_PRICE", None)
            net_last_time = long_data.get("LAST_POSITION_TIME", "")
            net_last_time_raw = long_data.get("LAST_POSITION_TIME_RAW", 0)
        else:
            net_current_price = short_data.get("CURRENT_PRICE", None)
            net_last_time = short_data.get("LAST_POSITION_TIME", "")
            net_last_time_raw = short_data.get("LAST_POSITION_TIME_RAW", 0)

        # If you are tracking best/worst trade records persistently,
        # you might merge them here as well—for example, taking the maximum profit and minimum loss.
        # For now, they are omitted.

        summary[symbol]["NET"] = {
            "SIZE_SUM": net_size,
            "POSITION_COUNT": net_count,
            "AVG_PRICE": net_avg_price,
            "CURRENT_PRICE": net_current_price,
            "UNREALIZED_PROFIT": net_unrealized_profit,
            "LAST_POSITION_TIME": net_last_time,
            "LAST_POSITION_TIME_RAW": net_last_time_raw,
        }

    return summary


def get_total_positions(save=True, use_cache=True, report=False):
    """
    Finalizes the processing: builds the detailed snapshot from positions,
    aggregates them, and then updates persistent records as needed.
    """
    # Get the raw positions from cache or MT5
    positions = load_cached_positions()
    if not positions:
        logger.warning("No positions found. Returning empty summary.")
        return {}

    # Process individual positions into detailed arrays
    processed = process_positions(positions)

    # Aggregate the processed data into final summary numbers
    snapshot_summary = aggregate_position_data(processed)

    # Load historical positions to merge and update data.class
    historical_summary = load_total_positions_accounting()

    # Merge snapshot with historical data.
    for symbol, sides in snapshot_summary.items():
        if symbol not in historical_summary:
            # New symbol: take the snapshot and initialize extreme records.
            historical_summary[symbol] = sides
            for side in ('LONG', 'SHORT', 'NET'):
                if side in historical_summary[symbol]:
                    # Initialize extremes with the current total side position.
                    historical_summary[symbol][side]["PROFIT_RECORD_TRACK"] = historical_summary[symbol][side]["UNREALIZED_PROFIT"]
                    historical_summary[symbol][side]["LOSS_RECORD_TRACK"] = historical_summary[symbol][side]["UNREALIZED_PROFIT"]
                    historical_summary[symbol][side]["GOAL_MET"] = False
                    historical_summary[symbol][side]["TRAILING_CROSSED"] = False
                    historical_summary[symbol][side]["CLOSE_SIGNAL"] = False
                    
        else:
            for side in ('LONG', 'SHORT', 'NET'):
                snap = sides.get(side, {})
                hist = historical_summary[symbol].get(side, {})

                # Initialize missing extreme fields with the current aggregated unrealized profit.
                if "PROFIT_RECORD_TRACK" not in hist:
                    hist["PROFIT_RECORD_TRACK"] = snap.get("UNREALIZED_PROFIT", 0)
                if "LOSS_RECORD_TRACK" not in hist:
                    hist["LOSS_RECORD_TRACK"] = snap.get("UNREALIZED_PROFIT", 0)

                if "PROFIT_GOAL" not in hist:
                    size = snap.get("SIZE_SUM", 0)
                    avg_price = snap.get("AVG_PRICE", 0)
                    investment = size * avg_price
                    target_profit = investment * CLOSE_PROFIT_THRESHOLD
                    hist["PROFIT_GOAL"] = target_profit

                if "TRAILING_PROFIT" not in hist:
                    size = snap.get("SIZE_SUM", 0)
                    avg_price = snap.get("AVG_PRICE", 0)
                    investment = size * avg_price
                    target_profit = investment * TRAILING_PROFIT_THRESHHOLD
                    hist["TRAILING_PROFIT"] = target_profit

                if not hist:
                    historical_summary[symbol][side] = snap
                else:
                    # Update persistent extreme records based on the aggregated (total) unrealized profit.
                    hist["PROFIT_RECORD_TRACK"] = max(
                        hist.get("PROFIT_RECORD_TRACK", snap.get("UNREALIZED_PROFIT", 0)),
                        snap.get("UNREALIZED_PROFIT", 0)
                    )
                    hist["LOSS_RECORD_TRACK"] = min(
                        hist.get("LOSS_RECORD_TRACK", snap.get("UNREALIZED_PROFIT", 0)),
                        snap.get("UNREALIZED_PROFIT", 0)
                    )
                    # Overwrite snapshot-dependent fields.
                    hist["SIZE_SUM"] = snap["SIZE_SUM"]
                    hist["POSITION_COUNT"] = snap["POSITION_COUNT"]
                    hist["AVG_PRICE"] = snap["AVG_PRICE"]
                    hist["CURRENT_PRICE"] = snap["CURRENT_PRICE"]
                    hist["UNREALIZED_PROFIT"] = snap["UNREALIZED_PROFIT"]
                    hist["LAST_POSITION_TIME"] = snap["LAST_POSITION_TIME"]
                    hist["LAST_POSITION_TIME_RAW"] = snap["LAST_POSITION_TIME_RAW"]

                    # Update profit goal and trailing profit
                    size = snap.get("SIZE_SUM", 0)
                    avg_price = snap.get("AVG_PRICE", 0)
                    investment = size * avg_price
                    target_profit = investment * CLOSE_PROFIT_THRESHOLD
                    hist["PROFIT_GOAL"] = target_profit

                    size = snap.get("SIZE_SUM", 0)
                    avg_price = snap.get("AVG_PRICE", 0)
                    investment = size * avg_price
                    target_profit = investment * TRAILING_PROFIT_THRESHHOLD
                    hist["TRAILING_PROFIT"] = target_profit

                    # Reset extreme records if no positions are open.
                    if snap.get("SIZE_SUM", 0) == 0:
                        hist["PROFIT_RECORD_TRACK"] = 0
                        hist["LOSS_RECORD_TRACK"] = 0
                        hist["PROFIT_GOAL"] = 0
                        hist["TRAILING_PROFIT"] = 0
                        hist["GOAL_MET"] = False
                        hist["TRAILING_CROSSED"] = False
                    else:
                        # Set flags if thresholds are reached.
                        if snap.get("UNREALIZED_PROFIT", 0) >= hist.get("PROFIT_GOAL", 0):
                            hist["GOAL_MET"] = True
                        else:
                            hist["GOAL_MET"] = False

                        if snap.get("UNREALIZED_PROFIT", 0) >= hist.get("TRAILING_PROFIT", 0):
                            hist["TRAILING_CROSSED"] = True
                        else:
                            hist["TRAILING_CROSSED"] = False

                        if hist.get("GOAL_MET", False) and hist.get("TRAILING_CROSSED", False):
                            hist["CLOSE_SIGNAL"] = True
                        else:
                            hist["CLOSE_SIGNAL"] = False

                    historical_summary[symbol][side] = hist

    if save:
        save_total_positions(historical_summary)

    # If report is True, print and log the summary.
    if report:
        logger.info("[INFO 1649] ====== POSITIONS - Total positions summary ======")
        for symbol, sides in snapshot_summary.items():
            logger.info(f"[INFO 1649] Symbol: {symbol}")
            for side, data in sides.items():
                logger.info(f"[INFO 1649]  {side}: {data}")

    return snapshot_summary



#
# def get_total_positions(save=True, use_cache=True):
#     """
#     Calculates the total volume and profit of all open positions.
#     """
#     global total_positions_cache
#
#     logger.debug(f"get_total_positions(save={save}, use_cache={use_cache})")
#
#     if use_cache and total_positions_cache:
#         logger.info("Using cached total positions now.")
#         logger.info(f"Total positions: {total_positions_cache}")
#         save_total_positions(total_positions_cache)
#         return total_positions_cache
#
#     if not mt5.initialize():
#         logger.error("MT5 is disconnected. Returning empty positions.")
#         return {}  # Avoids the NoneType error
#
#     logger.info("Calculating total positions...")
#     positions = load_cached_positions()
#
#     if positions is None or len(positions) == 0:
#         logger.warning('No positions found. Returning empty summary.')
#         return {}
#
#     # Load historical positions to merge and update data. 
#     historical_summary = load_total_positions_accounting()
#
#     current_snapshot = {}
#
#     for pos in positions:
#         symbol = pos['symbol']
#         position_type = "LONG" if pos['type'] == "BUY" else "SHORT"
#         volume = pos['volume']
#         price_open = pos['price_open']
#         price_current = pos['price_current']
#         profit = pos['profit']
#         time_open = pos['time_open']
#         time_raw = pos['time_raw']
#
#         logger.debug(f"Processing position: {symbol} | {position_type} | {volume} | {price_open} | {price_current} | {profit} | {time_open}")
#
#         if symbol not in current_snapshot:
#             current_snapshot[symbol] = {
#                 "LONG": {"SIZE_SUM": 0,
#                          "AVG_PRICE": 0,
#                          "POSITION_COUNT": 0,
#                          "CURRENT_PRICE": price_current,
#                          "UNREALIZED_PROFIT": 0,
#                          "LOSS_RECORD_TRACK": profit,
#                          "PROFIT_RECORD_TRACK": profit,
#                          "LAST_POSITION_TIME": time_open,
#                          "LAST_POSITION_TIME_RAW": time_raw},
#                 "SHORT": {"SIZE_SUM": 0,
#                           "AVG_PRICE": 0,
#                           "POSITION_COUNT": 0,
#                           "CURRENT_PRICE": price_current,
#                           "UNREALIZED_PROFIT": 0,
#                           "LOSS_RECORD_TRACK": profit,
#                           "PROFIT_RECORD_TRACK": profit,
#                           "LAST_POSITION_TIME": time_open,
#                           "LAST_POSITION_TIME_RAW": time_raw},
#             }
#
#         side_data = current_snapshot[symbol][position_type]
#         side_data["SIZE_SUM"] += volume
#         side_data["POSITION_COUNT"] += 1
#         side_data["UNREALIZED_PROFIT"] += profit
#         side_data["CURRENT_PRICE"] = price_current
#
#         # Update best profit and worst loss within snapshot
#         side_data["PROFIT_RECORD_TRACK"] = max(side_data["PROFIT_RECORD_TRACK"], profit)
#         side_data["LOSS_RECORD_TRACK"] = min(side_data["LOSS_RECORD_TRACK"], profit)
#
#         # Update last position time if this trade is newer
#         if time_raw > side_data["LAST_POSITION_TIME_RAW"]:
#             side_data["LAST_POSITION_TIME"] = time_open
#             side_data["LAST_POSITION_TIME_RAW"] = time_raw
#
#         # Update weighted average price (snapshot)
#         total_size = side_data["SIZE_SUM"]
#         if total_size > 0:
#             # Recalculate average price for the snapshot
#             # This assumes AVG_PRICE is recomputed each tick from scratch
#             # Here we simply average the price_open weighted by volume
#             previous_total = side_data.get("PREVIOUS_TOTAL", 0)
#             new_total = previous_total + (price_open * volume)
#             side_data["AVG_PRICE"] = new_total / total_size
#             side_data["PREVIOUS_TOTAL"] = new_total  # For continuous update within this tick
#
#
#         # if side_data["LAST_POSITION_TIME"] is None or time_open > side_data["LAST_POSITION_TIME"]:
#         #     side_data["LAST_POSITION_TIME"] = time_open
#         #
#         # if side_data["LAST_POSITION_TIME_RAW"] == 0 or time_raw > side_data["LAST_POSITION_TIME_RAW"]:
#         #     side_data["LAST_POSITION_TIME_RAW"] = time_raw
#         #
#         # # Update best profit
#         # if profit > side_data["PROFIT_RECORD_TRACK"]:
#         #     side_data["PROFIT_RECORD_TRACK"] = profit
#         #
#         # # Update worst loss
#         # if profit < side_data["LOSS_RECORD_TRACK"]:
#         #     side_data["LOSS_RECORD_TRACK"] = profit
#
#         # Update weighted average price
#         # total_size = side_data["SIZE_SUM"]
#         # if total_size > 0:
#         #     side_data["AVG_PRICE"] = ((side_data["AVG_PRICE"] * (total_size - volume)) + (price_open * volume)) / total_size
#         # # side_data["AVG_PRICE"] = ((side_data["AVG_PRICE"] * (total_size - volume)) + (price_open * volume)) / total_size
#
#
#
#     # Merge snapshot with historical data
#     for symbol, sides in current_snapshot.items():
#         if symbol not in historical_summary:
#             # If symbol is new, just take the snapshot
#             historical_summary[symbol] = sides
#         else:
#             for side in ("LONG", "SHORT"):
#                 snap = sides[side]
#                 hist = historical_summary[symbol].get(side, {
#                     "SIZE_SUM": 0,
#                     "AVG_PRICE": 0,
#                     "POSITION_COUNT": 0,
#                     "CURRENT_PRICE": snap["CURRENT_PRICE"],
#                     "UNREALIZED_PROFIT": 0,
#                     "LOSS_RECORD_TRACK": float('inf'),
#                     "PROFIT_RECORD_TRACK": -float('inf'),
#                     "LAST_POSITION_TIME": snap["LAST_POSITION_TIME"],
#                     "LAST_POSITION_TIME_RAW": 0,
#                 })
#                 # Update persistent fields only if a new record is observed
#                 hist["PROFIT_RECORD_TRACK"] = max(hist["PROFIT_RECORD_TRACK"], snap["PROFIT_RECORD_TRACK"])
#                 hist["LOSS_RECORD_TRACK"] = min(hist["LOSS_RECORD_TRACK"], snap["LOSS_RECORD_TRACK"])
#
#                 # Replace snapshot-dependent fields with current values
#                 hist["SIZE_SUM"] = snap["SIZE_SUM"]
#                 hist["POSITION_COUNT"] = snap["POSITION_COUNT"]
#                 hist["AVG_PRICE"] = snap["AVG_PRICE"]
#                 hist["CURRENT_PRICE"] = snap["CURRENT_PRICE"]
#                 hist["UNREALIZED_PROFIT"] = snap["UNREALIZED_PROFIT"]
#
#                 # Update last position time if newer
#                 if snap["LAST_POSITION_TIME_RAW"] > hist["LAST_POSITION_TIME_RAW"]:
#                     hist["LAST_POSITION_TIME"] = snap["LAST_POSITION_TIME"]
#                     hist["LAST_POSITION_TIME_RAW"] = snap["LAST_POSITION_TIME_RAW"]
#
#                 historical_summary[symbol][side] = hist
#
#     total_positions_cache = historical_summary
#
#
#     logger.info(f"Total positions calculated for {symbol}.")
#
#     logger.debug(f"Total positions: {historical_summary}")
#
#     if save:
#         save_total_positions(historical_summary)
#
#     return historical_summary


def save_total_positions(summary):
    """
    Saves the summarized positions to 'hard_memory/total_positions.json'.
    """
    logger.info("Saving total positions...")
    logger.info(f"Total positions: {summary}")

    try:
        with open(TOTAL_POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)
        logger.info(f"Total positions saved to {TOTAL_POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save total positions: {e}")


if __name__ == "__main__":
    logger.info("Starting total_positions.py...")
    summary = get_total_positions(save=True, use_cache=False)
    if summary:
        save_total_positions(summary)
        logger.info("total_positions.py completed.")
        print(json.dumps(summary, indent=4))
    else:
        logger.error("total_positions.py failed.")

# End of total_positions.py


# === FILE: src/positions/__init__.py ===



# === FILE: src/positions/positions.py ===

# src/positions/positions.py
import MetaTrader5 as mt5
from src.logger_config import logger
import os
import json
from datetime import datetime
import time
from src.config import HARD_MEMORY_DIR, POSITIONS_FILE
from src.tools.server_time import get_server_time_from_tick


# Ensure the `hard_memory` directory exists
# HARD_MEMORY_DIR = "hard_memory"
# os.makedirs(HARD_MEMORY_DIR, exist_ok=True)  # Cleaner directory check


def save_positions(positions):
    """
    Saves open positions to a JSON file.
    """
    positions_data = []

    data = {
        "my_timestamp": time.time(),
        "my_local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": []
    }

    for pos in positions:
        positions_data.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == 0 else "SELL",
            "volume": pos.volume,
            "price_open": pos.price_open,
            "sl": pos.sl,
            "tp": pos.tp,
            "price_current": pos.price_current,
            "profit": pos.profit,
            "swap": pos.swap,
            "magic": pos.magic,
            # "time_open": datetime.fromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
            "time_open": datetime.utcfromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
            "time_raw": pos.time,
            "comment": pos.comment
        })

    data["positions"] = positions_data

    try:
        with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"OK - Open positions saved to {POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"Oh No! - Failed to save positions: {e}")


def get_positions():
    """
    Retrieves and logs all open positions from MT5.
    """
    positions = mt5.positions_get()

    if positions:
        logger.info("=== Open Positions ===")
        # for pos in positions:
        #     # logger.info(f"Ticket: {pos.ticket} {pos.symbol} {('BUY' if pos.type == 0 else 'SELL')} {pos.volume} lots @ {pos.price_open}")
        #     pass
        save_positions(positions)
        logger.info(f"Total open positions saved: {len(positions)}")
    else:
        logger.info("No open positions found.")
        save_positions([])
    
    return positions


# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect
    if connect():
        get_positions()
        disconnect()


# End of positions.py


# === FILE: src/symbols/__init__.py ===



# === FILE: src/symbols/symbols.py ===

# symbols.py
import MetaTrader5 as mt5
import os
import json
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, SYMBOLS_ALLOWED

# Ensure the `hard_memory` directory exists
# HARD_MEMORY_DIR = "hard_memory"
# os.makedirs(HARD_MEMORY_DIR, exist_ok=True)

SYMBOLS_FILE = os.path.join(HARD_MEMORY_DIR, "symbols.json")

def save_symbols(symbols):
    """
    Saves detailed symbol information to a JSON file.
    """
    symbols_data = []

    for symbol in symbols:
        info = mt5.symbol_info(symbol.name)  # Retrieve additional details
        if info:
            symbols_data.append({
                "name": info.name,
                "description": info.description,
                "currency_base": info.currency_base,
                "currency_profit": info.currency_profit,
                "currency_margin": info.currency_margin,
                "digits": info.digits,
                "point": info.point,
                "spread": info.spread,
                "trade_mode": info.trade_mode,  # 0 = Disabled, 1 = Long & Short, 2 = Close Only
                "category": get_symbol_category(info),  # Determine category (Forex, Crypto, etc.)
                "contract_size": info.trade_contract_size,  # Contract size
                "volume_min": info.volume_min,  # Minimum trade volume
                "volume_max": info.volume_max,  # Maximum trade volume
                "volume_step": info.volume_step,  # Volume increment step
                "margin_initial": info.margin_initial,  # Required margin for a position
                "margin_maintenance": info.margin_maintenance,  # Maintenance margin
                "margin_hedged": info.margin_hedged  # Margin for hedged positions
            })
    file_path = os.path.join(HARD_MEMORY_DIR, "symbols.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(symbols_data, f, indent=4)
        logger.info(f"Saved {len(symbols_data)} symbols to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save symbols: {e}")

def get_symbol_category(symbol_info):
    """
    Determines the category of the symbol based on its attributes.
    """
    if "USD" in symbol_info.currency_base and "USD" in symbol_info.currency_profit:
        return "Forex"
    elif "BTC" in symbol_info.name or "ETH" in symbol_info.name:
        return "Crypto"
    elif "US30" in symbol_info.name or "NAS" in symbol_info.name or "SPX" in symbol_info.name:
        return "Indices"
    elif "OIL" in symbol_info.name or "GOLD" in symbol_info.name or "XAU" in symbol_info.name:
        return "Commodities"
    else:
        return "Stocks"

def get_symbols():
    """
    Retrieves all available symbols from MT5, categorizes them, and saves them.
    """
    symbols = mt5.symbols_get()

    if symbols:
        logger.info(f"Retrieved {len(symbols)} symbols from MetaTrader 5")
        save_symbols(symbols)
    else:
        logger.warning("No symbols retrieved from MetaTrader 5")
        save_symbols([])

    return symbols

# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        get_symbols()
        disconnect()

# End of symbols.py


# === FILE: src/tick_listener.py ===

# tick_listener.py
import MetaTrader5 as mt5
import time
import random
from src.logger_config import logger
from src.config import SYMBOLS_ALLOWED

# Store last tick data for comparison
last_ticks = {}

# Define major Forex symbols
# FOREX_MAJORS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
# FOREX_MAJORS = ['EURUSD', 'BTCUSD']
# FOREX_MAJORS = ['BTCUSD']

def get_forex_symbols(limit=5, only_major_forex=False):
    """
    Retrieves Forex symbols from MT5 and returns a limited selection.
    """
    symbols = mt5.symbols_get()
    if not symbols:
        logger.error("Failed to retrieve symbols from MT5.")
        return []

    forex_symbols = [s.name for s in symbols if "USD" in s.name or "EUR" in s.name or "GBP" in s.name]  # Basic Forex filter

    if only_major_forex:
        selected_symbols = [s for s in forex_symbols if s in SYMBOLS_ALLOWED]
        logger.info(f"Major Forex Mode: Listening to {len(selected_symbols)} major Forex pairs.")
        if not selected_symbols:
            logger.warning("No major forex pairs found. Using All available symbols instead.")
            selected_symbols = forex_symbols
    else:
        selected_symbols = random.sample(forex_symbols, min(limit, len(forex_symbols)))
        logger.info(f"Development Mode: Selected Forex Symbols: {selected_symbols}")

    if not selected_symbols:
        logger.error("No Forex symbols found.")
    return selected_symbols


def listen_to_ticks(sleep_time=0.1, forex_mode=False, only_major_forex=False, on_tick=None):
    """
    Listens to market ticks for all symbols or selected Forex symbols.
    """
    global last_ticks

    if forex_mode:
        symbols = get_forex_symbols(5, only_major_forex=only_major_forex)  # Development mode: 5 random Forex symbols
    else:
        symbols = [s.name for s in mt5.symbols_get()]  # Production mode: all active symbols

    if not symbols:
        logger.error("No symbols available for listening.")
        return

    mode_text = "Major Forex Symbols" if only_major_forex else "Random 5 Forex Symbols" if forex_mode else "All Symbols"
    logger.info(f"Listening for ticks on {len(symbols)} ({mode_text})...")

    while True:
        tick_detected = False
        tick_data = []

        for symbol in symbols:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                last_bid, last_ask = last_ticks.get(symbol, (None, None))

                if last_bid != tick.bid or last_ask != tick.ask:
                    last_ticks[symbol] = (tick.bid, tick.ask)
                    logger.info(f"{symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {tick.ask - tick.bid}")
                    tick_detected = True
                    tick_info = {
                        "symbol": symbol,
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "spread": tick.ask - tick.bid,
                        "time": tick.time
                    }
                    tick_data.append(tick_info)

        if tick_detected and on_tick and on_tick:
            on_tick(tick_data)

        time.sleep(sleep_time if tick_detected else 0.5)

def sample_on_tick(ticks):
    """
    Example callback function to process tick events.
    """
    for tick in ticks:
        logger.info(f"Tick Event: {tick['symbol']} | Bid: {tick['bid']} | Ask: {tick['ask']} | Spread: {tick['spread']} | Time: {tick['time']}")



if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        try:
            forex_mode = True
            only_major_forex = True
            listen_to_ticks(forex_mode=forex_mode, only_major_forex=True)
        except KeyboardInterrupt:
            logger.info("Tick listener stopped by user.")
        finally:
            disconnect()

# End of tick_listener.py





# === FILE: src/ticker/__init__.py ===



# === FILE: src/ticker/custom_candle_aggregator.py ===

# src/ticker/custom_candle_aggregator.py
import time
from datetime import datetime


"""
In a Real Tick Listener
In your actual environment:

Initialize a global (or class-level) aggregator:
aggregator = CustomCandleAggregator(mode="time", interval=30)

On each tick event or callback:
def on_tick(tick):
    candle = aggregator.on_new_tick(tick)
    if candle:
        # We have a finished candle, do something: 
        # e.g., store it, calculate indicators, etc.
        print("New Candle Bar formed:", candle)
That’s it. The aggregator automatically handles candle formation.
Create a 30‐tick candle aggregator by CustomCandleAggregator(mode="tick", interval=30).
Create a 30‐second candle aggregator by CustomCandleAggregator(mode="time", interval=30).
"""


class CustomCandleAggregator:
    """
    Maintains a single "in-progress" candle from a live tick stream,
    and closes it once a specified threshold is reached.

    Mode can be:
      - "time":  close candle after 'interval' seconds
      - "tick":  close candle after 'interval' ticks

    Usage:
      1) Create aggregator = CustomCandleAggregator(mode="time", interval=30)
      2) For each new tick, aggregator.on_new_tick(tick_dict)
      3) If it returns a 'finished_candle', you can process/store it.
    """

    def __init__(self, mode="time", interval=30):
        """
        :param mode: "time" or "tick"
        :param interval: number of seconds (mode="time") or ticks (mode="tick")
        """
        if mode not in ("time", "tick"):
            raise ValueError("mode must be 'time' or 'tick'")

        self.mode = mode
        self.interval = interval

        # Holds the "current" candle in progress
        self.candle_open_time = None
        self.open_price = None
        self.high_price = None
        self.low_price  = None
        self.close_price= None
        self.tick_count = 0

        # For time-based mode, track candle_end_time
        self.candle_end_ts = None

    def on_new_tick(self, tick):
        """
        Process a new tick. If a candle finishes by hitting
        the threshold, return that candle. Otherwise, return None.

        :param tick: dict with at least:
                     {
                       "time": <float/int or datetime>,
                       "price": <float>
                     }
        :return: A candle dict if we closed a candle this tick, else None.
        """
        # Convert tick time to float timestamp if needed
        ts = self._to_ts(tick["time"])
        price = tick["price"]

        # If no candle in progress, start one
        if self.open_price is None:
            self._start_candle(ts, price)
            return None

        # Update in-progress candle's high/low/close
        if price > self.high_price:
            self.high_price = price
        if price < self.low_price:
            self.low_price = price
        self.close_price = price
        self.tick_count += 1

        # Check if we need to close the candle
        if self.mode == "tick":
            if self.tick_count >= self.interval:
                return self._close_and_start_new(ts, price)
            else:
                return None
        else:
            # self.mode == "time"
            if ts >= self.candle_end_ts:
                return self._close_and_start_new(ts, price)
            else:
                return None

    def _start_candle(self, ts, price):
        """Initialize a fresh candle from this tick."""
        self.candle_open_time = ts
        self.open_price  = price
        self.high_price  = price
        self.low_price   = price
        self.close_price = price
        self.tick_count  = 1

        if self.mode == "time":
            self.candle_end_ts = ts + self.interval

    def _close_and_start_new(self, ts, price):
        """
        Close the current candle, build a candle dict,
        then start a new candle from this tick.
        """
        finished_candle = {
            "open_time":  self.candle_open_time,
            "open":       self.open_price,
            "high":       self.high_price,
            "low":        self.low_price,
            "close":      self.close_price,
            "close_time": ts,
            "tick_count": self.tick_count
        }
        # Start a new candle with this tick
        self._start_candle(ts, price)
        return finished_candle

    def _to_ts(self, t):
        """
        Convert t to float timestamp if it's a datetime, else assume
        it's already a float/int second-based timestamp.
        """
        if isinstance(t, datetime):
            return t.timestamp()
        elif isinstance(t, (float, int)):
            return float(t)
        else:
            raise ValueError(f"Unsupported tick time type: {type(t)}")


# --------------------------
# Example usage demonstration
# --------------------------
if __name__ == "__main__":
    # Create aggregator for a 30-second candle
    aggregator = CustomCandleAggregator(mode="time", interval=30)

    # Simulate receiving ticks
    # (In practice you'd get these from a live feed)
    simulated_ticks = [
        {"time": 1676671800, "price": 100.0},  # e.g. Wed Feb 17, ...
        {"time": 1676671815, "price": 101.2},
        {"time": 1676671818, "price": 99.8},
        {"time": 1676671831, "price": 100.5},  # surpasses 30s from 1800 => candle closes
        {"time": 1676671832, "price": 100.7},
        {"time": 1676671845, "price": 101.0},
        {"time": 1676671860, "price": 102.5},  # next candle might close, etc.
    ]

    for tick in simulated_ticks:
        candle = aggregator.on_new_tick(tick)
        if candle:
            # We just closed a candle
            print("Closed Candle:", candle)
    
    # After the final tick, you may have a partially-formed candle
    # that you can decide to close or keep open. E.g.:
    # last_candle = aggregator.force_close()
    # if last_candle:
    #    print("Final Partial Candle:", last_candle)



# === FILE: src/tools/__init__.py ===



# === FILE: src/tools/server_time.py ===

# src/tools/server_time.py
from datetime import datetime
import MetaTrader5 as mt5
from src.logger_config import logger


def get_server_time_from_tick(symbol):
    """Get the raw server time from the latest tick. Returns both timestamp and human-readable format."""

    tick_info = mt5.symbol_info_tick(symbol)

    if not tick_info:
        logger.warning(f"Failed to get tick data for {symbol}")
        return None, None  # Returning None to handle failure cases explicitly

    server_timestamp = tick_info.time  # Raw UNIX timestamp from MT5
    server_datetime = datetime.fromtimestamp(server_timestamp)  # Human-readable format

    logger.debug(f"Raw MT5 Tick Time (Server Timestamp): {server_timestamp} | Tick Time (Human-readable): {server_datetime}")

    return server_timestamp


# === FILE: src/tools/timeframe.py ===

import MetaTrader5 as mt5

# Define the mapping of timeframes with their minute values
TIMEFRAMES = [
    (mt5.TIMEFRAME_M1, 1),
    (mt5.TIMEFRAME_M2, 2),
    (mt5.TIMEFRAME_M3, 3),
    (mt5.TIMEFRAME_M4, 4),
    (mt5.TIMEFRAME_M5, 5),
    (mt5.TIMEFRAME_M6, 6),
    (mt5.TIMEFRAME_M10, 10),
    (mt5.TIMEFRAME_M12, 12),
    (mt5.TIMEFRAME_M15, 15),
    (mt5.TIMEFRAME_M20, 20),
    (mt5.TIMEFRAME_M30, 30),
    (mt5.TIMEFRAME_H1, 60),
    (mt5.TIMEFRAME_H2, 120),
    (mt5.TIMEFRAME_H3, 180),
    (mt5.TIMEFRAME_H4, 240),
    (mt5.TIMEFRAME_H6, 360),
    (mt5.TIMEFRAME_H8, 480),
    (mt5.TIMEFRAME_H12, 720),
    (mt5.TIMEFRAME_D1, 1440),
    (mt5.TIMEFRAME_W1, 10080),
    (mt5.TIMEFRAME_MN1, 43200)
]

# Convert to a dictionary for easy lookup
TIMEFRAME_MAP = {tf[1]: tf[0] for tf in TIMEFRAMES}
TIMEFRAME_VALUES = sorted(TIMEFRAME_MAP.keys())  # Sorted list of available timeframes


def get_timeframe(current_timeframe: int, step: int = 0):
    """
    Get the appropriate MT5 timeframe.
    
    Parameters:
        current_timeframe (int): The current timeframe in minutes.
        step (int): The number of levels to move up (positive) or down (negative).

    Returns:
        int: Corresponding MT5 timeframe ID, or None if out of range.
    """
    if current_timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Invalid timeframe: {current_timeframe} minutes")

    idx = TIMEFRAME_VALUES.index(current_timeframe)

    # Compute new index with boundary check
    new_idx = max(0, min(len(TIMEFRAME_VALUES) - 1, idx + step))

    return TIMEFRAME_MAP[TIMEFRAME_VALUES[new_idx]]


# Example usage

# get_timeframe(5, 2)   # Moves two levels up → Returns TIMEFRAME_M10
# get_timeframe(30, -1) # Moves one level down → Returns TIMEFRAME_M20
# get_timeframe(1, -2)  # Moves two levels down (stays at lowest) → Returns TIMEFRAME_M1
# get_timeframe(1440, 1) # Moves one level up from 1 day → Returns TIMEFRAME_W1 (1 week)




if __name__ == "__main__":
    timeframe = 5  # 5-minute timeframe
    print("Same:", get_timeframe(timeframe, 0))      # Same timeframe
    print("One level down:", get_timeframe(timeframe, -1))  # One level lower (4 min)
    print("One level up:", get_timeframe(timeframe, 1))     # One level higher (6 min)
    print("Two levels up:", get_timeframe(timeframe, 2))    # Two levels higher (10 min)
    print("Three levels down:", get_timeframe(timeframe, -3))  # Three levels lower (1 min)



# === FILE: src/trader/__init__.py ===



# === FILE: src/trader/trade.py ===

# src/trader/trade.py
import MetaTrader5 as mt5
import os
import random
import json
import time
from datetime import datetime, timezone, timedelta
import pytz
from src.logger_config import logger
from src.portfolio.total_positions import get_total_positions, total_positions_cache
from src.positions.positions import get_positions
from src.indicators.adx_indicator import calculate_adx
from src.indicators.signal_indicator import dispatch_signals, dispatch_position_manager_indicator
from src.config import (
        HARD_MEMORY_DIR,
        POSITIONS_FILE,
        BROKER_SYMBOLS, 
        TRADE_LIMIT_FILE,
        TRADE_DECISIONS_FILE,
        CLOSE_PROFIT_THRESHOLD,
        TRAILING_PROFIT_THRESHHOLD,
        CLEARANCE_HEAT_FILE,
        CLEARANCE_LIMIT_FILE,
        DEFAULT_VOLATILITY,
        DEFAULT_ATR_MULTIPLYER)

# Cash trade limits to avoid reloading
trade_limits_cache = None
# total_positions_cache = {}

# Global variable to hold cached symbol conficurations
_SYMBOLS_CONFIG_CACHE = None


### --- Functions Index in this file --- ###
# load_trade_limits()
# save_trade_decision(trade_data)
# parse_time(value)
# get_server_time_from_tick(symbol)
# load_limits(symbol)
# load_positions(symbol)
# get_cooldown_clearance(symbol)
# get_limit_clearance(symbol)
# get_open_trade_clearance(symbol)
# open_trade(symbol, lot_size=0.01)
# open_buy(symbol, lot_size=0.01)
# open_sell(symbol, lot_size=0.01)
# close_trade(symbol=None)
# manage_trade(symbol)
# execute_trade(order)


BROKER_TIMEZONE = pytz.timezone("Europe/Athens")


def get_symbols_config():
    global _SYMBOLS_CONFIG_CACHE
    if _SYMBOLS_CONFIG_CACHE is not None:
        return _SYMBOLS_CONFIG_CACHE
    
    symbols_file = BROKER_SYMBOLS
    if not os.path.exists(symbols_file):
        logger.error(f"[ERROR 1247] :: Symbol configuration file not found: {symbols_file}")
        return None
    try:
        with open(symbols_file, 'r', encoding='utf-8') as f:
            symbols_config = json.load(f)
            _SYMBOLS_CONFIG_CACHE = symbols_config
        return symbols_config
    except Exception as e:
        logger.error(f"[ERROR 1247] :: Failed to load symbols configuration: {e}")
        return None

def get_symbol_config(symbol):
    symbols_list = get_symbols_config()
    if symbols_list is None:
        return None
    for sym in symbols_list:
        if sym.get('name') == symbol:
            return sym
    logger.error(f"[ERROR 1252] :: Symbol {symbol} not found in configuration.")
    return None



def load_trade_limits():
    """
    Loads trade limits configuration from JSON, creating a default file if missing.
    """
    global trade_limits_cache
    if trade_limits_cache is not None:
        return trade_limits_cache

    if not os.path.exists(TRADE_LIMIT_FILE):
        logger.warning(f"Trade limits file {TRADE_LIMIT_FILE} not found. Generating default.")
        trade_limits_cache = {}
        return trade_limits_cache
    try:
        with open(TRADE_LIMIT_FILE, "r", encoding="utf-8") as f:
            trade_limits_cache = json.load(f)
            return trade_limits_cache
    except Exception as e:
        logger.error(f"Failed to load trade limits: {e}")
        trade_limits_cache = {}
        return trade_limits_cache


def save_trade_decision(trade_data):
    """ Saves trade decisions to history for later analysis."""
    try:
        # decisions = []
        if os.path.exists(TRADE_DECISIONS_FILE):
            with open(TRADE_DECISIONS_FILE, "r", encoding="utf-8") as f:
                decisions = json.load(f)
        else:
            decisions = []

        decisions.append(trade_data)

        with open(TRADE_DECISIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(decisions, f, indent=4)
        logger.info("Trade decision saved to file.")
    except Exception as e:
        logger.error(f"Failed to save trade decisions: {e}")


def parse_time(value):
    """Convert string timestamps to UNIX timestamps if needed."""
    if not value:
        return 0
    if isinstance(value, str):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            logger.warning(f"Invalid timestamp format: {value}")
            return 0
    return float(value) if value else 0


def get_server_time_from_tick(symbol):
    """Get the current server time."""
    tick_info = mt5.symbol_info_tick(symbol)
    if not tick_info:
        logger.warning(f"Failed to get tick data for {symbol}")
        return datetime.utcnow().timestamp()

    server_time = tick_info.time  # This is a raw timestamp

    # Convert MT5 server time (broker time) to its actual broker time zone
    broker_dt = datetime.fromtimestamp(server_time, tz=BROKER_TIMEZONE)

    # Convert broker time to True UTC
    true_utc_dt = broker_dt.astimezone(timezone.utc)
    true_utc_timestamp = true_utc_dt.timestamp()

    # Get system's current true UTC time
    system_utc_dt = datetime.now(timezone.utc)
    system_utc_timestamp = system_utc_dt.timestamp()

    # Logging with clear distinctions
    logger.info(f"MT5 Server Time (Broker's Timezone): {broker_dt} | True UTC Server Time: {true_utc_dt}")
    logger.info(f"System UTC Time: {system_utc_dt} | System UTC Timestamp: {system_utc_timestamp}")

    logger.debug(f"MT5 Server Timestamp: {server_time} | True UTC Timestamp: {true_utc_timestamp} | System UTC Timestamp: {system_utc_timestamp}")

    return true_utc_timestamp


def load_limits(symbol):
    trade_limits = load_trade_limits()
    if symbol not in trade_limits:
        logger.warning(f"No Limits. Symbol {symbol} not found in trade limits.")
        return None
    limits = trade_limits[symbol]
    logger.info(f"Trade limits found for {symbol}")

    return {
        "max_long_size": limits.get('MAX_LONG_SIZE', float('inf')),
        "max_short_size": limits.get('MAX_SHORT_SIZE', float('inf')),
        "max_orders": limits.get('MAX_ORDERS', 100),
        "cooldown_seconds": limits.get('COOLDOWN_SECONDS', 120)
    }

def load_positions(symbol):
    """Retrive open positions for a symbol."""
    positions = get_total_positions(save=True, use_cache=False)
    logger.info(f"Total positions: {positions}")

    position_data = positions.get(symbol, {})
    long_data = position_data.get('LONG', {})
    short_data = position_data.get('SHORT', {})

    return {
        "current_long_size": long_data.get('SIZE_SUM', 0) or 0,
        "current_short_size": short_data.get('SIZE_SUM', 0) or 0,
        "long_data": long_data,
        "short_data": short_data,
    }


def get_cooldown_clearance(symbol):
    """Cooldwn clearance - an arbitrary but necessary time limit between trades."""
    current_time = datetime.utcnow().timestamp()

    current_tick_time = get_server_time_from_tick(symbol)

    limits = load_limits(symbol)
    if not limits:
        return None, None

    cooldown_limit = limits.get('cooldown_seconds', 120)
    positions = load_positions(symbol)

    long_positions = positions.get('long_data', {})
    short_positions = positions.get('short_data', {})

    last_long_time = parse_time(long_positions.get('LAST_POSITION_TIME', 0))
    last_short_time = parse_time(short_positions.get('LAST_POSITION_TIME', 0))

    logger.info(f"Last Position Time: LONG: {last_long_time}, SHORT: {last_short_time}")

    # Calculate how long it has been since the last trade cached.
    long_time_diff = current_tick_time - last_long_time
    short_time_diff = current_tick_time - last_short_time

    logger.debug(f"Cooldown Calculation: Current Tick Time: {current_tick_time} | Last Long Time: {last_long_time} | Last Short Time: {last_short_time}")

    logger.info(f"Time since last position: LONG: {long_time_diff}, SHORT: {short_time_diff}")

    allow_buy = long_time_diff > cooldown_limit
    allow_sell = short_time_diff > cooldown_limit

    if not allow_buy:
        logger.info(f"Symbol {symbol} has not cleared cooldown for LONG positions.")
    if not allow_sell:
        logger.info(f"Symbol {symbol} has not cleared cooldown for SHORT positions.")

    logger.info(f"Symbol Cooldown Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")

    ## Dumping to file for debugging
    with open(CLEARANCE_HEAT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": symbol,
            "current_tick_time": current_tick_time,
            "last_long_time": last_long_time,
            "last_short_time": last_short_time,
            "long_time_diff": long_time_diff,
            "short_time_diff": short_time_diff,
            "cooldown_limit": cooldown_limit,
            "allow_buy": allow_buy,
            "allow_sell": allow_sell
        }, f, indent=4)

    return ('BUY' if allow_buy else None), ('SELL' if allow_sell else None)


def get_limit_clearance(symbol):
    """
    Returns the limit clearance defined in limits file.
    4 digit signature for this function: 1712
    """
    limits = load_limits(symbol)
    if limits is None:
        logger.warning(f"[WARNING 1712] :: No Limits. Symbol {symbol} not found in trade limits.")
        return None, None

    # limits = limits[symbol]
    logger.info(f"Current {symbol} limits: {limits}")
    max_long_size = limits.get('max_long_size', float('inf'))
    max_short_size = limits.get('max_short_size', float('inf'))
    max_orders = limits.get('max_orders', 100)

    positions = load_positions(symbol)

    current_long_size = positions.get('current_long_size', 0)
    current_short_size = positions.get('current_short_size', 0)
    total_positions = current_long_size + current_short_size

    logger.info(f"[INFO 1712] :: Current Position Sizes: LONG: {current_long_size}, SHORT: {current_short_size}")

    long_size_clarance = current_long_size < max_long_size
    short_size_clarance = current_short_size < max_short_size

    if long_size_clarance:
        logger.info(f"[INFO 1712] :: Symbol {symbol} has LONG size clearance.")
    if short_size_clarance:
        logger.info(f"[INFO 1712] :: Symbol {symbol} has SHORT size clearance.")

    allow_buy = long_size_clarance
    allow_sell = short_size_clarance

    logger.info(f"[INFO 1712] :: Symbol Limit Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")

    # Dumping to file for debugging
    with open(CLEARANCE_LIMIT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": symbol,
            "max_long_size": max_long_size,
            "max_short_size": max_short_size,
            "max_orders": max_orders,
            "current_long_size": current_long_size,
            "current_short_size": current_short_size,
            "total_positions": total_positions,
            "long_size_clarance": long_size_clarance,
            "short_size_clarance": short_size_clarance,
            "allow_buy": allow_buy,
            "allow_sell": allow_sell
        }, f, indent=4)

    return ('BUY' if allow_buy else None), ('SELL' if allow_sell else None)


def get_open_trade_clearance(symbol):
    """
    Returns clearance to open a trade.
    4 digit signature for this function: 1711
    """
    allow_limit_buy, allow_limit_sell = get_limit_clearance(symbol)
    allow_cooldown_buy, allow_cooldown_sell = get_cooldown_clearance(symbol)

    allow_buy = bool(allow_limit_buy and allow_cooldown_buy)
    allow_sell = bool(allow_limit_sell and allow_cooldown_sell)

    logger.info(f"[INFO 1711] :: Symbol Trade Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")
    return allow_buy, allow_sell


def aggregate_signals(signals):
    """
    Agregate indicator signals from multiple indicators.
    4 digit signature for this function: 1744
    """
    vote_counts = {
            'BUY': 0,
            'SELL': 0,
            'CLOSE': 0,
            'BUY_CLOSE': 0,
            'SELL_CLOSE': 0,
            'NONE': 0,
            'NO SIGNAL': 0,
            'LONG': 0,
            'SHORT': 0,
            'HOLD': 0
            }
    for name, result in signals.items():
        sig = result.get('signal', 'NONE')
        vote_counts[sig] += 1
    logger.info(f"[INFO 1744] :: Signal Votes: {vote_counts}")

    consensus_signal = max(vote_counts, key=vote_counts.get)

    if vote_counts[consensus_signal] >= 1:
        logger.info(f"[INFO 1744] :: Consensus Signal: {consensus_signal}")
        return consensus_signal
    return None



def open_trade(symbol, lot_size=0.01):
    # Generate function description and random 4 digit number
    """
    Open a trade based on the symbol and lot size.
    This function checks the current market conditions, trade limits, and cooldown periods before executing a trade.
    It also aggregates signals from multiple indicators to determine the consensus signal for trading.
    4 digit signature for this function: 1700
    """

    global trade_limits_cache
    global total_positions_cache

    logger.debug(f"[DEBUG 1700] :: function open_trade({symbol}, {lot_size}) globals: trade_limits_cache: {trade_limits_cache}, total_positions_cache: {total_positions_cache}")

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"[ERROR 1700] :: Failed to get tick data for {symbol}")
        return False

    spread = tick.ask - tick.bid
    logger.info(f"[INFO 1700] TICK: {symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {spread} | Time: {tick.time}")

    # Call ATR 
    # atr = calculate_adx(symbol, period=14)
    atr = dispatch_position_manager_indicator(symbol, 'ATR')
    atr = atr.get('value', {}).get('atr', 0)

    if spread <= atr:
        allow_buy, allow_sell = get_open_trade_clearance(symbol)

        signals = dispatch_signals(symbol)

        position_manager = dispatch_position_manager_indicator(symbol, 'ATR')
        trailing_stop = None
        if position_manager:
            trailing_stop = position_manager.get('value', {})

        logger.debug(f"[DEBUG 1700] :: Trade Clearance for {symbol}: {allow_buy}, {allow_sell}")

        logger.info(f"[INFO 1700] :: Trade Limits {symbol}: {allow_buy}, {allow_sell}")

        # Agregate the Signals to get a consensus
        consensus_signal = aggregate_signals(signals)
        logger.info(f"[INFO 1700] :: Consensus Signal (open_trade): {consensus_signal}")
        if consensus_signal == 'NONE':
            return False

        trade_executed = None

        # if trade_signal == "BUY" and allow_buy:
        if consensus_signal == "BUY" and allow_buy:
            sl = tick.bid - (tick.ask * DEFAULT_VOLATILITY)
            tp = tick.bid + (tick.ask * DEFAULT_VOLATILITY * 2.0)
            result = open_buy(symbol, lot_size, stop_loss=sl, take_profit=tp)
            if result:
                trade_executed = "BUY"

        # elif trade_signal == "SELL" and allow_sell:
        elif consensus_signal == "SELL" and allow_sell:
            sl = tick.bid + (tick.ask * DEFAULT_VOLATILITY)
            tp = tick.bid - (tick.ask * DEFAULT_VOLATILITY * 2.0)
            result = open_sell(symbol, lot_size, stop_loss=sl, take_profit=tp)
            if result:
                trade_executed = "SELL"

        if trade_executed:
            trade_data = {
                "symbol": symbol,
                "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "spread": spread,
                "trade_executed": trade_executed,
                "result": result,
                "signals": signals,
                "trade_clearance": {
                    "allow_buy": allow_buy,
                    "allow_sell": allow_sell
                },
                "consensus_signal": consensus_signal
            }
            save_trade_decision(trade_data)
            logger.info(f"[INFO 1700] :: Trade executed for {symbol}")
            total_positions_cache = get_total_positions(save=True, use_cache=False)

            logger.info(f"[INFO 1700] :: Total Positions Cached after trade: {total_positions_cache}")

            time.sleep(9)  # Sleep for some seconds to assure data

        else:
            logger.error(f"[ERROR 1700] :: Trade limits reached for {symbol}")

    else:
        logger.error(f"[ERROR 1700] :: Spread too low, no trade executed for {symbol}")


def open_buy(
        symbol,
        lot_size=0.01,
        stop_loss=None,
        take_profit=None,
        trailing_stop=None,
        slippage=20,
        magic=None,
        comment="Python Auto Trading Bot",
        type_filling=None,
        order_type=None):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Failed to get tick data for {symbol}")
        return False
    order = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": 20,
        "magic": random.randint(100000, 599999),
        "comment": "Python Auto Trading Bot",
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    # Only add stop loss and take profit if they are provided.
    if stop_loss is not None:
        order["sl"] = stop_loss
    if take_profit is not None:
        order["tp"] = take_profit

    return execute_trade(order)


def open_sell(
        symbol,
        lot_size=0.01,
        stop_loss=None,
        take_profit=None,
        trailing_stop=None,
        slippage=20,
        magic=None,
        comment="Python Auto Trading Bot",
        type_filling=None,
        order_type=None):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Failed to get tick data for {symbol}")
        return False
    order = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_SELL,
        "price": tick.bid,
        "deviation": 20,
        "magic": random.randint(600000, 999999),
        "comment": "Python Auto Trading Bot",
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    # Only add stop loss and take profit if they are provided.
    if stop_loss is not None:
        order["sl"] = stop_loss
    if take_profit is not None:
        order["tp"] = take_profit

    return execute_trade(order)



def close_trade(symbol=None):
    """
    Close a trade based on profit threshold.
    4 digit signature for this function: 1038
    """
    close_profit_threshold = CLOSE_PROFIT_THRESHOLD
    logger.info(f"[INFO 1038] :: Closing trades with profit threshold: {close_profit_threshold}")
    if not symbol:
        logger.error("[ERROR 1038] :: close_trade() called without a valid symbol.")
        return False

    symbol_config = get_symbol_config(symbol)
    if symbol_config:
        symbol_contract_size = symbol_config.get('contract_size', 1)
        logger.info(f"[INFO 1038] :: Symbol {symbol} contract size: {symbol_contract_size}")

    signals = dispatch_signals(symbol)
    consensus_signal = aggregate_signals(signals)
    logger.info(f"[INFO 1038] :: Consensus Signal (close_trade): {consensus_signal}")

    position_manager = dispatch_position_manager_indicator(symbol, 'ATR')
    trailing_stop = None
    if position_manager:
        trailing_stop = position_manager.get('value', {})

    # if consensus_signal in ['BUY', 'SELL']:
    #     logger.error(f"[ERROR 1038] :: No consensus signal to close trade.")
    #     return False

    get_positions()
    file_path = os.path.join(POSITIONS_FILE)
    logger.info(f"[INFO 1038] :: Loading positions from {file_path}")

    if not os.path.exists(file_path):
        logger.warning(f"[WARNING 1038] :: File positions not found. I am unable to close trades.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        positions_data = json.load(f)
        logger.info(f"[INFO 1038] :: close_trade() - Positions loaded from cache 'positions_data': {len(positions_data)}")

    positions = positions_data['positions']
    logger.info(f"[INFO 1038] :: Positions loaded from cache: {len(positions)}")

    if not positions:
        logger.warning(f"[WARNING 1038] :: No open positions found on {file_path}.")
        return

    for pos in positions:
        symbol = pos['symbol']
        symbol_config = get_symbol_config(symbol)
        ticket = pos['ticket']
        pos_type = pos['type']
        volume = pos['volume']
        profit = pos['profit']
        price_open = pos['price_open']
        symbol_contract_size = symbol_config.get('contract_size', 1)
        invested_amount = volume * price_open * symbol_contract_size
        position_pnl = profit / invested_amount

        min_profit = position_pnl > close_profit_threshold

        logger.info(f"[INFO 1038] :: Position PnL: {position_pnl} | Invested Amount: {invested_amount} | Profit: {profit} | Symbol: {symbol} | Volume: {volume} | Type: {pos_type} | Ticket: {ticket} | Price Open: {price_open} | Min Profit: {min_profit} | Close Profit Threshold: {close_profit_threshold} | Contract Size: {symbol_contract_size} | Trailing Stop: {trailing_stop}")

        if invested_amount > 0 and min_profit:
            logger.info(f"Closing trade on {symbol} - Profit reached: {profit}")
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if pos["type"] == "SELL" else mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid if pos["type"] == "SELL" else mt5.symbol_info_tick(symbol).ask,
                "deviation": 20,
                "magic": random.randint(100000, 999999),
                "comment": "Auto Close TP",
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            close_result = mt5.order_send(close_request)
            logger.info(f"[INFO 1038] :: Close request sent as mt5.position_close: {close_request}")
            logger.error(f"[INFO 1038] :: MT5 last error: {mt5.last_error()}")

            if close_result is None:
                logger.error(f"[ERROR 1038] :: Failed to close position on {symbol}. `mt5.order_send()` returned None.")
                continue

            logger.info(f"[INFO 1038] :: Close order response: {close_result}")

            if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"[INFO 1038] :: Successfully closed position on {symbol}")
            else:
                logger.error(f"[ERROR 1038] :: Failed to close position on {symbol}. Error Code: {close_result.retcode}, Message: {close_result.comment}")

            if close_result and close_result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"[INFO 1038] :: Close order result: {close_result}")
                logger.info(f"[INFO 1038] :: Closed position on {symbol}")
    return True


def manage_trade(symbol):
    """
    Manage open positions for a symbol by updating trailing stops based on 
    a volatility indicator (e.g. ATR). This function:
      - Retrieves current tick data and the position management indicator result.
      - Calculates a recommended trailing stop level using an ATR-based multiplier.
      - Iterates over open positions for the symbol and, if the recommended stop is more favorable,
        submits an order modification to adjust the position's stop loss.

    Returns True if management actions (or no action) complete successfully.
    4 digit signature for this function: 0625
    """
    logger.info(f"[INFO 0625] :: Managing trade for {symbol}")

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"[ERROR 0625] :: Failed to get tick data for {symbol}.")
        return False

    # Dispatch the position manager indicator (e.g., ATR must be set in the config file)
    pm_result = dispatch_position_manager_indicator(symbol, 'ATR')
    if not pm_result:
        logger.info(f"[INFO 0625] :: No position manager signal for {symbol}; no adjustments will be made.")
        return True

    # Extract the ATR result dictionary from pm_result.
    atr_result = pm_result.get("ATR")
    if not atr_result:
        logger.error(f"[ERROR 0625] :: ATR result is missing from the position manager indicators.")
        return False

    # Retrieve the ATR value from the indicator result.
    atr_value = atr_result.get("value", {})
    if atr_value is None:
        logger.error(f"[ERROR 0625] :: ATR value is not available for {symbol}.")
        return False

    multiplier = DEFAULT_ATR_MULTIPLYER

    # Get current open positions for the symbol.
    # (Assuming get_positions() returns a dict containing a list of positions under 'positions')
    get_positions()
    file_path = os.path.join(POSITIONS_FILE)
    logger.info(f"[INFO 0625] :: Loading positions from {file_path}")

    if not os.path.exists(file_path):
        logger.warning(f"[WARNING 0625] :: File positions not found. Unable to manage trades.")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        positions_data = json.load(f)
        logger.info(f"[INFO 0625] :: manage_trade() - Positions loaded from cache 'positions_data': {len(positions_data)}")
        
    positions = positions_data.get('positions', [])

    if not positions_data or "positions" not in positions_data:
        logger.info(f"[INFO 0625] :: No open positions found for {symbol}.")
        return True

    # Filter only positions matching the symbol.
    positions = [pos for pos in positions_data.get("positions", []) if pos.get("symbol") == symbol]
    if not positions:
        logger.info(f"[INFO 0625] :: No open positions for {symbol} to manage.")
        return True

    # Iterate over each open position and update stop loss if appropriate.
    for pos in positions:
        pos_type = pos.get("type")
        ticket = pos.get("ticket")
        current_sl = pos.get("sl", None)  # current stop loss; may be None if not set
        open_price = pos.get("price_open", None)
        recommended_sl = None

        BREAK_EVEN_OFFSET = 0.103  # 10.3% of ATR value

        if pos_type == "BUY":
            has_moved_1_atr = tick.bid >= open_price + atr_value
            in_trailing_range = tick.bid < open_price + (atr_value * multiplier)

            if has_moved_1_atr and in_trailing_range:
                # Break-even logic
                recommended_sl = open_price + (atr_value * BREAK_EVEN_OFFSET)
                logger.info(f"[INFO 0625] :: BUY position {ticket}: Break-even zone. Recommending SL to {recommended_sl}")
            else:
                # Trailing logic
                recommended_sl = tick.bid - multiplier * atr_value
                logger.info(f"[INFO 0625] :: BUY position {ticket}: Trailing SL calculated at {recommended_sl}")

            if current_sl is not None and recommended_sl <= current_sl:
                logger.info(f"[INFO 0625] :: BUY position {ticket}: SL {recommended_sl} not better than current {current_sl}. Skipping update.")
                continue

        elif pos_type == "SELL":
            has_moved_1_atr = tick.ask <= open_price - atr_value
            in_trailing_range = tick.ask > open_price - (atr_value * multiplier)

            if has_moved_1_atr and in_trailing_range:
                # Break-even logic
                recommended_sl = open_price - (atr_value * BREAK_EVEN_OFFSET)
                logger.info(f"[INFO 0625] :: SELL position {ticket}: Break-even zone. Recommending SL to {recommended_sl}")
            else:
                # Trailing logic
                recommended_sl = tick.ask + multiplier * atr_value
                logger.info(f"[INFO 0625] :: SELL position {ticket}: Trailing SL calculated at {recommended_sl}")

            if current_sl is not None and recommended_sl >= current_sl:
                logger.info(f"[INFO 0625] :: SELL position {ticket}: SL {recommended_sl} not better than current {current_sl}. Skipping update.")
                continue

        else:
            logger.warning(f"[WARNING 0625] :: Position {ticket} has unknown type: {pos_type}. Skipping.")
            continue


        # Build a modify request.
        modify_request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": recommended_sl,
            "tp": pos.get("tp", 0),  # keep current TP unchanged
            "deviation": 20,
            "magic": pos.get("magic", random.randint(100000, 999999)),
            "comment": "Trailing Stop Adjustment"
        }
        logger.info(f"[INFO 0625] :: Sending modify request for position {ticket}: {modify_request}")
        modify_result = mt5.order_send(modify_request)
        logger.info(f"[INFO 0625] :: Modify result for position {ticket}: {modify_result}")

        if modify_result is not None and modify_result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"[INFO 0625] :: Successfully updated trailing stop for position {ticket}.")
        else:
            logger.error(f"[0625] :: Failed to update trailing stop for position {ticket}. MT5 Error: {mt5.last_error()}")

    return True



def execute_trade(order):
    result = mt5.order_send(order)
    logger.info(f"Trade Order Sent: {order}")
    logger.info(f"Full Order Response: {result}")

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Trade opened: {result.order}")
        return True
    else:
        logger.error(f"Trade failed: {result.retcode}")
        return False



if __name__ == "__main__":
    from connect import connect, disconnect

    if connect():
        open_trade("EURUSD")  # Test trade on EURUSD
        disconnect()


# End of trade.py
