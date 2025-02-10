import MetaTrader5 as mt5
from logger_config import logger
import random
import json
from portfolio.total_positions import get_total_positions
from positions import get_positions
import os
from indicators.adx_indicator import calculate_adx
import time
from datetime import datetime
from config import (
        HARD_MEMORY_DIR,
        TRADE_LIMIT_FILE,
        TRADE_DECISIONS_FILE,
        CLOSE_PROFIT_THRESHOLD)

# HARD_MEMORY_DIR = "hard_memory"
# TRADE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, "trade_limits.json")
# TRADE_HISTORY_FILE = os.path.join(HARD_MEMORY_DIR, "trade_decisions.json")

# CLOSE_PROFIT_THRESHOLD = 0.0002  # 0.5% profit threshold to close a trade


# Cash trade limits to avoid reloading
trade_limits_cache = None

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
        decisions = []
        if os.path.exists(TRADE_DECISIONS_FILE):
            with open(TRADE_DECISIONS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            decisions = []

        decisions.append(trade_data)

        with open(TRADE_DECISIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        logger.info("Trade decision saved to file.")
    except Exception as e:
        logger.error(f"Failed to save trade decisions: {e}")


def parse_time(value):
    """Convert string timestamps to UNIX timestamps if needed."""
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            logger.warning(f"Invalid timestamp format: {value}")
            return 0  # Default to 0 if parsing fails
    return float(value) if value else 0  # Ensure it's a float

def get_limit_clearance(symbol):
    """
    Returns the limit clearance defined in limits file.
    """
    trade_limits = load_trade_limits()
    if symbol not in trade_limits:
        logger.warning(f"Symbol {symbol} not found in trade limits.")
        return None, None

    limits = trade_limits[symbol]
    positions = get_total_positions()
    logger.info(f"Trade limits found for {symbol}")
    logger.info(f"Limits: {limits}")

    current_time = datetime.utcnow().timestamp()

    tick_info = mt5.symbol_info_tick(symbol)
    server_time = tick_info.time if tick_info else current_time

    mt5_server_time = datetime.utcfromtimestamp(server_time)
    local_time = datetime.fromtimestamp(current_time)

    latest_tick = mt5.symbol_info_tick(symbol)
    if latest_tick:
        logger.info(f"Latest Tick {symbol}: {latest_tick}")
    else:
        logger.error(f"No data latest tick for {symbol}")

    logger.info(f"Local System Time: {local_time} | MT5 Server Time: {mt5_server_time}")

    position_data = positions.get(symbol, {})
    long_data = position_data.get('LONG', {})
    short_data = position_data.get('SHORT', {})

    current_long_size = long_data.get('SIZE_SUM', 0) or 0
    current_short_size = short_data.get('SIZE_SUM', 0) or 0
    total_positions = current_long_size + current_short_size

    last_long_time = parse_time(long_data.get('LAST_POSITION_TIME', 0))
    last_short_time = parse_time(short_data.get('LAST_POSITION_TIME', 0))

    long_time_diff = current_time - last_long_time
    short_time_diff = current_time - last_short_time

    logger.info(f"Current Position Sizes: LONG: {current_long_size}, SHORT: {current_short_size}")
    logger.info(f"Last Position Time (Parsed): LONG: {last_long_time}, SHORT: {last_short_time}")
    logger.info(f"Seconds since last position: LONG: {long_time_diff}, SHORT: {short_time_diff}")

    max_long_size = limits.get('MAX_LONG_SIZE', float('inf'))
    max_short_size = limits.get('MAX_SHORT_SIZE', float('inf'))
    max_orders = limits.get('MAX_ORDERS', 100)
    cooldown_seconds = limits.get('COOLDOWN_SECONDS', 120)

    logger.info(f"Symbol {symbol} has limits: {limits}")

    if total_positions >= max_orders:
        logger.info(f"Symbol {symbol} has reached maximum orders.")
        return None, None

    long_size_clarance = current_long_size < max_long_size
    short_size_clarance = current_short_size < max_short_size
    long_cooled = (current_time - last_long_time) > cooldown_seconds
    short_cooled = (current_time - last_short_time) > cooldown_seconds

    if long_size_clarance:
        logger.info(f"Symbol {symbol} has LONG size clearance.")
    if short_size_clarance:
        logger.info(f"Symbol {symbol} has SHORT size clearance.")
    if long_cooled:
        logger.info(f"Symbol {symbol} has LONG cooled.")
    if short_cooled:
        logger.info(f"Symbol {symbol} has SHORT cooled.")

    allow_buy = long_size_clarance and long_cooled
    allow_sell = short_size_clarance and short_cooled

    logger.info(f"Symbol {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")

    return ('BUY' if allow_buy else None), ('SELL' if allow_sell else None)


def open_trade(symbol, lot_size=0.01):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Failed to get tick data for {symbol}")
        return False

    spread = tick.ask - tick.bid
    logger.info(f"TICK: {symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {spread}")


    if spread > 0.0:
        allow_buy, allow_sell = get_limit_clearance(symbol)
        adx_result = calculate_adx(symbol)

        if not adx_result:
            logger.error(f"ADX calculation failed or returned no signal for {symbol}")
            return False

        trade_signal, adx, plus_di, minus_di = adx_result
        
        logger.info(f"Indicator {symbol}: {trade_signal} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")
        logger.info(f"Trade Limits {symbol}: {allow_buy}, {allow_sell}")

        if trade_signal == "BUY" and allow_buy:
            logger.info(f"Signal BUY for {symbol} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")
            result = open_buy(symbol, lot_size)
            if result:
                trade_data = {
                    "symbol": symbol,
                    "spread": spread,
                    "adx": adx,
                    "plus_di": plus_di,
                    "minus_di": minus_di,
                    "trade_executed": "BUY",
                    "result": result                }
                save_trade_decision(trade_data)
        elif trade_signal == "SELL" and allow_sell:
            logger.info(f"Signal SELL for {symbol} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")
            result = open_sell(symbol, lot_size)
            if result:
                trade_data = {
                    "symbol": symbol,
                    "spread": spread,
                    "adx": adx,
                    "plus_di": plus_di,
                    "minus_di": minus_di,
                    "trade_executed": "SELL",
                    "result": result                }
                save_trade_decision(trade_data)
        else:
            logger.error(f"Trade limits reached for {symbol}")

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



def close_trade(symbol=None):
    """
    Close a trade based on profit threshold.
    """
    close_profit_threshold = CLOSE_PROFIT_THRESHOLD
    logger.info(f"Closing trades with profit threshold: {close_profit_threshold}")
    get_positions()
    file_path = os.path.join(HARD_MEMORY_DIR, 'positions.json')
    logger.info(f"Loading positions from {file_path}")

    if not os.path.exists(file_path):
        logger.warning(f"File positions not found. I am unable to close trades.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        positions_data = json.load(f)
        logger.info(f"close_trade() - Positions loaded from cache 'positions_data': {len(positions_data)}")

    positions = positions_data['positions']
    logger.info(f"Positions loaded from cache: {len(positions)}")

    if not positions:
        logger.warning(f"No open positions found on {file_path}.")
        return

    for pos in positions:
        symbol = pos['symbol']
        ticket = pos['ticket']
        pos_type = pos['type']
        volume = pos['volume']
        profit = pos['profit']
        price_open = pos['price_open']
        invested_amount = volume * price_open

        if invested_amount > 0 and (profit / invested_amount) > close_profit_threshold:
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
            logger.info(f"Close request sent as mt5.position_close: {close_request}")
            logger.error(f"MT5 last error: {mt5.last_error()}")

            if close_result is None:
                logger.error(f"Failed to close position on {symbol}. `mt5.order_send()` returned None.")
                continue

            logger.info(f"Close order response: {close_result}")

            if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Successfully closed position on {symbol}")
            else:
                logger.error(f"Failed to close position on {symbol}. Error Code: {close_result.retcode}, Message: {close_result.comment}")

            if close_result and close_result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Close order result: {close_result}")
                logger.info(f"Closed position on {symbol}")






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
