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
from src.indicators.signal_indicator import dispatch_signals
from src.config import (
        HARD_MEMORY_DIR,
        POSITIONS_FILE,
        TRADE_LIMIT_FILE,
        TRADE_DECISIONS_FILE,
        CLOSE_PROFIT_THRESHOLD,
        TRAILING_PROFIT_THRESHHOLD,
        CLEARANCE_HEAT_FILE,
        CLEARANCE_LIMIT_FILE)

# Cash trade limits to avoid reloading
trade_limits_cache = None
# total_positions_cache = {}


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
# execute_trade(order)


BROKER_TIMEZONE = pytz.timezone("Europe/Athens")

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

    current_long_size = positions.get('current_long_size', 0)
    current_short_size = positions.get('current_short_size', 0)
    total_positions = current_long_size + current_short_size

    logger.info(f"Current Position Sizes: LONG: {current_long_size}, SHORT: {current_short_size}")

    long_size_clarance = current_long_size < max_long_size
    short_size_clarance = current_short_size < max_short_size

    if long_size_clarance:
        logger.info(f"Symbol {symbol} has LONG size clearance.")
    if short_size_clarance:
        logger.info(f"Symbol {symbol} has SHORT size clearance.")

    allow_buy = long_size_clarance
    allow_sell = short_size_clarance

    logger.info(f"Symbol Limit Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")

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
    """Returns clearance to open a trade."""
    allow_limit_buy, allow_limit_sell = get_limit_clearance(symbol)
    allow_cooldown_buy, allow_cooldown_sell = get_cooldown_clearance(symbol)

    allow_buy = bool(allow_limit_buy and allow_cooldown_buy)
    allow_sell = bool(allow_limit_sell and allow_cooldown_sell)

    logger.info(f"Symbol Trade Clearance {symbol} ALLOW BUY: {allow_buy}, ALLOW SELL: {allow_sell}")
    return allow_buy, allow_sell


def aggregate_signals(signals):
    """Agregate indicator signals from multiple indicators."""
    vote_counts = {'BUY': 0, 'SELL': 0, 
                   'CLOSE': 0, 'BUY_CLOSE': 0, 
                   'SELL_CLOSE': 0, 'NOENE': 0}
    for name, result in signals.items():
        sig = result.get('signal', 'NONE')
        vote_counts[sig] += 1
    logger.info(f"Signal Votes: {vote_counts}")

    consensus_signal = max(vote_counts, key=vote_counts.get)

    if vote_counts[consensus_signal] > 1:
        logger.info(f"Consensus Signal: {consensus_signal}")
        return consensus_signal
    return None



def open_trade(symbol, lot_size=0.01):
    global trade_limits_cache
    global total_positions_cache

    logger.debug(f"--open_trade({symbol}, {lot_size}) globals: trade_limits_cache: {trade_limits_cache}, total_positions_cache: {total_positions_cache}")

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"Failed to get tick data for {symbol}")
        return False

    spread = tick.ask - tick.bid
    logger.info(f"TICK: {symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {spread} | Time: {tick.time}")

    if spread > 0.0:
        allow_buy, allow_sell = get_open_trade_clearance(symbol)

        signals = dispatch_signals(symbol)

        logger.debug(f"Trade Clearance for {symbol}: {allow_buy}, {allow_sell}")

        logger.info(f"Trade Limits {symbol}: {allow_buy}, {allow_sell}")

        # Agregate the SIgnals to get a consensus
        consensus_signal = aggregate_signals(signals)
        logger.info(f"Consensus Signal (open_trade): {consensus_signal}")
        if consensus_signal == 'NONE':
            return False

        trade_executed = None

        # if trade_signal == "BUY" and allow_buy:
        if consensus_signal == "BUY" and allow_buy:
            result = open_buy(symbol, lot_size)
            if result:
                trade_executed = "BUY"

        # elif trade_signal == "SELL" and allow_sell:
        elif consensus_signal == "SELL" and allow_sell:
            result = open_sell(symbol, lot_size)
            if result:
                trade_executed = "SELL"

        if trade_executed:
            trade_data = {
                "symbol": symbol,
                "spread": spread,
                "trade_executed": trade_executed,
                "result": result
            }
            save_trade_decision(trade_data)
            logger.info(f"Trade executed for {symbol}")
            total_positions_cache = get_total_positions(save=True, use_cache=False)

            logger.info(f"Total Positions Cached after trade: {total_positions_cache}")

            time.sleep(9)  # Sleep for some seconds to assure data

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

    if not symbol:
        logger.error("close_trade() called without a valid symbol.")
        return False

    signals = dispatch_signals(symbol)
    consensus_signal = aggregate_signals(signals)
    logger.info(f"Consensus Signal (close_trade): {consensus_signal}")

    if consensus_signal == 'NONE':
        logger.error(f"No consensus signal to close trade.")
        return False
    
    get_positions()
    file_path = os.path.join(POSITIONS_FILE)
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
        position_pnl = profit / invested_amount

        min_profit = position_pnl > close_profit_threshold
        valid_signals = ['BUY_CLOSE', 'SELL_CLOSE', 'CLOSE']
        closing_signal = consensus_signal in valid_signals

        if invested_amount > 0 and min_profit and closing_signal:
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
