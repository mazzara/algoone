# src/limits/limits.py
import json
import os
from datetime import datetime
from src.logger_config import logger
from src.positions.positions import load_positions
from src.tools.server_time import get_server_time_from_tick, get_server_time_from_tick_tz, parse_time
from utils.config_watcher import ConfigWatcher
from src.config import HARD_MEMORY_DIR, TRADE_LIMIT_FILE, CLEARANCE_LIMIT_FILE, CLEARANCE_HEAT_FILE

_config_watcher = ConfigWatcher(TRADE_LIMIT_FILE)


def get_trade_limits():
    """
    Returns the most updated trade limits configuration.
    """
    _config_watcher.load_if_changed()
    return _config_watcher.config


def get_limit_clearance(symbol):
    """
    Checks whether trading is allowed for given symbol.
    """
    limits = get_trade_limits()
    symbol_limits = limits.get(symbol, limits.get("DEFAULT", {}))

    if symbol_limits.get("COOLDOWN", False):
        logger.debug(f"[LIMITS 8825] :: {symbol} is on cooldown.")
        return False
    
    return True


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


def get_symbol_limits(symbol):
    limits = get_trade_limits()
    return limits.get(symbol, limits.get("DEFAULT", {}))


def get_limit_clearance(symbol):
    """
    Returns the limit clearance defined in limits file.
    4 digit signature for this function: 1712
    """
    limits = get_symbol_limits(symbol)
    if limits is None or not isinstance(limits, dict) or not limits:
        logger.warning(f"[WARNING 1712] :: No Limits. Symbol {symbol} not found in trade limits.")
        return None, None

    # Safe fallback: 0 (no clearance) and log if key missing
    max_long_size = limits.get('MAX_LONG_SIZE')
    if max_long_size is None:
        logger.warning(f"[WARNING 1712] :: MAX_LONG_SIZE missing for {symbol}. Defaulting to 0.")
        max_long_size = 0

    max_short_size = limits.get('MAX_SHORT_SIZE')
    if max_short_size is None:
        logger.warning(f"[WARNING 1712] :: MAX_SHORT_SIZE missing for {symbol}. Defaulting to 0.")
        max_short_size = 0

    max_orders = limits.get('MAX_ORDERS', 100)

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


def get_cooldown_clearance(symbol):
    """Cooldwn clearance - an arbitrary but necessary time limit between trades."""
    current_time = datetime.utcnow().timestamp()

    current_tick_time = get_server_time_from_tick_tz(symbol)

    limits = get_symbol_limits(symbol)
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
