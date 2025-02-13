import MetaTrader5 as mt5
import os
import random
import json
import time
from datetime import datetime, timezone
from src.logger_config import logger
from src.portfolio.total_positions import get_total_positions, total_positions_cache
from src.positions.positions import get_positions
from src.indicators.adx_indicator import calculate_adx
from src.config import (
        HARD_MEMORY_DIR,
        POSITIONS_FILE,
        TRADE_LIMIT_FILE,
        TRADE_DECISIONS_FILE,
        CLOSE_PROFIT_THRESHOLD)

# Cash trade limits to avoid reloading
trade_limits_cache = None
# total_positions_cache = {}

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

    server_time = tick_info.time
    # create a time-zone datetime in UTC
    utc_dt = datetime.fromtimestamp(server_time, tz=timezone.utc)
    utc_server_time = utc_dt.timestamp()
    logger.info(f"MT5 Server Time: {datetime.utcfromtimestamp(server_time)} | Local System Time: {datetime.utcnow()}")
    # Show clock in timestamp format
    logger.info(f"MT5 Server Time: {utc_server_time} | Local System Time: {datetime.utcnow().timestamp()}")
    return utc_server_time


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
    positions = get_total_positions()
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

    logger.info(f"Time since last position: LONG: {long_time_diff}, SHORT: {short_time_diff}")

    allow_buy = long_time_diff > cooldown_limit
    allow_sell = short_time_diff > cooldown_limit

    if not allow_buy:
        logger.info(f"Symbol {symbol} has not cleared cooldown for LONG positions.")
    if not allow_sell:
        logger.info(f"Symbol {symbol} has not cleared cooldown for SHORT positions.")

    logger.info(f"Symbol Cooldown Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")

    return ('BUY' if allow_buy else None), ('SELL' if allow_sell else None)


def get_limit_clearance(symbol):
    """
    Returns the limit clearance defined in limits file.
    """
    limits = load_limits(symbol)
    if limits is None:
        logger.warning(f"No Limits. Symbol {symbol} not found in trade limits.")
        return None, None

    # limits = limits[symbol]
    logger.info(f"Current {symbol} limits: {limits}")
    max_long_size = limits.get('max_long_size', float('inf'))
    max_short_size = limits.get('max_short_size', float('inf'))
    max_orders = limits.get('max_orders', 100)

    positions = load_positions(symbol)
    logger.info(f"Total positions: {positions}")

    current_long_size = positions.get('current_long_size', 0)
    current_short_size = positions.get('current_short_size', 0)
    total_positions = current_long_size + current_short_size

    logger.info(f"Current Position Sizes: LONG: {current_long_size}, SHORT: {current_short_size}")

    # position_data = positions.get(symbol, {})
    # long_data = position_data.get('LONG', {})
    # short_data = position_data.get('SHORT', {})

    # current_long_size = long_data.get('SIZE_SUM', 0) or 0
    # current_short_size = short_data.get('SIZE_SUM', 0) or 0
    # total_positions = current_long_size + current_short_size

    # logger.info(f"Current Position Sizes: LONG: {current_long_size}, SHORT: {current_short_size}")

    # logger.info(f"Symbol {symbol} has limits: {limits}")

    # if total_positions >= max_orders:
    #     logger.info(f"Symbol {symbol} has reached maximum orders.")
    #     return None, None

    long_size_clarance = current_long_size < max_long_size
    short_size_clarance = current_short_size < max_short_size

    if long_size_clarance:
        logger.info(f"Symbol {symbol} has LONG size clearance.")
    if short_size_clarance:
        logger.info(f"Symbol {symbol} has SHORT size clearance.")

    allow_buy = long_size_clarance
    allow_sell = short_size_clarance

    logger.info(f"Symbol Limit Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")
    return ('BUY' if allow_buy else None), ('SELL' if allow_sell else None)


def get_open_trade_clearance(symbol):
    """Returns clearance to open a trade."""
    allow_limit_buy, allow_limit_sell = get_limit_clearance(symbol)
    allow_cooldown_buy, allow_cooldown_sell = get_cooldown_clearance(symbol)

    allow_buy = bool(allow_limit_buy and allow_cooldown_buy)
    allow_sell = bool(allow_limit_sell and allow_cooldown_sell)

    logger.info(f"Symbol Trade Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")
    return allow_buy, allow_sell


def open_trade(symbol, lot_size=0.01):
    global trade_limits_cache
    global total_positions_cache

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Failed to get tick data for {symbol}")
        return False

    spread = tick.ask - tick.bid
    logger.info(f"TICK: {symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {spread}")

    if spread > 0.0:
        allow_buy, allow_sell = get_open_trade_clearance(symbol)
        adx_result = calculate_adx(symbol)

        if not adx_result:
            logger.error(f"ADX calculation failed or returned no signal for {symbol}")
            return False

        trade_signal, adx, plus_di, minus_di = adx_result

        logger.info(f"Indicator {symbol}: {trade_signal} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")
        logger.info(f"Trade Limits {symbol}: {allow_buy}, {allow_sell}")

        trade_executed = None

        if trade_signal == "BUY" and allow_buy:
            logger.info(f"Signal BUY for {symbol} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")
            result = open_buy(symbol, lot_size)
            if result:
                trade_executed = "BUY"

        elif trade_signal == "SELL" and allow_sell:
            logger.info(f"Signal SELL for {symbol} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")
            result = open_sell(symbol, lot_size)
            if result:
                trade_executed = "SELL"

        if trade_executed:
            trade_data = {
                "symbol": symbol,
                "spread": spread,
                "adx": adx,
                "plus_di": plus_di,
                "minus_di": minus_di,
                "trade_executed": trade_executed,
                "result": result
            }
            save_trade_decision(trade_data)
            logger.info(f"Trade executed for {symbol}")
            total_positions_cache = get_total_positions(save=True, use_cache=False)

            logger.info(f"Total Positions Cached after trade: {total_positions_cache}")

            time.sleep(3)  # Sleep for a second to avoid overloading the server

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
    file_path = os.path.join(POSITIONS_FILE)
    logger.info(f"Loading positions from {file_path}")

    if not symbol:
        logger.error("close_trade() called without a valid symbol.")
        return False

    adx_result = calculate_adx(symbol)
    if not adx_result:
        logger.error(f"ADX calculation failed in close_trade for {symbol}")
        return False

    trade_signal, adx, plus_di, minus_di = adx_result
    logger.info(f"Signal (close_trade): {trade_signal} - ADX: {adx} | +DI: {plus_di} | -DI: {minus_di}")

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
        position_pnl = profit / invested_amount

        min_profit = position_pnl > close_profit_threshold
        key_signal = trade_signal in ['BUY_CLOSE', 'SELL_CLOSE', 'CLOSE']

        if invested_amount > 0 and min_profit and key_signal:
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
