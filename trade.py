import MetaTrader5 as mt5
from logger_config import logger
import random
import json
from portfolio.total_positions import get_total_positions
import os
from indicators.adx_indicator import calculate_adx

HARD_MEMORY_DIR = "hard_memory"
TRADE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, "trade_limits.json")


def load_trade_limits():
    """
    Loads trade limits configuration from JSON, creating a default file if missing.
    """
    if not os.path.exists(TRADE_LIMIT_FILE):
        logger.warning(f"Trade limits file {TRADE_LIMIT_FILE} not found. Generating default.")
        return {}
    try:
        with open(TRADE_LIMIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load trade limits: {e}")
        return {}


def get_limit_clearance(symbol):
    """
    Check if a trade can be opened based on defined limits
    """
    trade_limits = load_trade_limits()
    if symbol not in trade_limits:
        logger.warning(f"No trade limits defined for {symbol}")
        return "BUY", "SELL"  # as it is - if no limits no restrictions ??
    
    limits = trade_limits[symbol]
    positions = get_total_positions()
    current_long_size = positions.get(symbol, {}).get("LONG", {}).get("SIZE_SUM", 0)
    current_short_size = positions.get(symbol, {}).get("SHORT", {}).get("SIZE_SUM", 0)

    max_long_size = limits.get("MAX_LONG_SIZE", float("inf"))
    max_short_size = limits.get("MAX_SHORT_SIZE", float("inf"))

    allow_buy = current_long_size < max_long_size
    allow_sell = current_short_size < max_short_size

    return ("BUY" if allow_buy else None), ("SELL" if allow_sell else None)


def open_trade(symbol, lot_size=0.01):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Failed to get tick data for {symbol}")
        return False

    spread = tick.ask - tick.bid
    logger.info(f"{symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {spread}")

    if spread > 0.0:
        allow_buy, allow_sell = get_limit_clearance(symbol)
        trade_signal = calculate_adx(symbol)

        if trade_signal == "BUY" and allow_buy:
            open_buy(symbol, lot_size)
        elif trade_signal == "SELL" and allow_sell:
            open_sell(symbol, lot_size)
        else:
            logger.error(f"Trade limits reached for {symbol}")

        # # Randomly execute a buy or sell trade
        # if allow_buy and random.choice([True, False]):
        #     open_buy(symbol, lot_size)
        # elif allow_sell:
        #     open_sell(symbol, lot_size)
        # else:
        #     logger.error(f"Trade limits reached for {symbol}")
    else:
        logger.error(f"Spread too low, no trade executed for {symbol}")


def open_buy(symbol, lot_size=0.01):
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

    return execute_trade(order)


def open_sell(symbol, lot_size=0.01):
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

    return execute_trade(order)


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
