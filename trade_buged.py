import MetaTrader5 as mt5
from logger_config import logger
import random
import json
from portfolio.total_positions import get_total_positions
from positions import get_positions
import os
from indicators.adx_indicator import calculate_adx

HARD_MEMORY_DIR = "hard_memory"
TRADE_LIMIT_FILE = os.path.join(HARD_MEMORY_DIR, "trade_limits.json")
TRADE_HISTORY_FILE = os.path.join(HARD_MEMORY_DIR, "trade_decisions.json")

CLOSE_PROFIT_THRESHOLD = 0.0002  # 0.5% profit threshold to close a trade

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


def save_trade_decision(trade_data):
    """ Saves trade decisions to history for later analysis."""
    os.makedirs(HARD_MEMORY_DIR, exist_ok=True)
    try:
        if os.path.exists(TRADE_HISTORY_FILE):
            with open(TRADE_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        history.append(trade_data)

        with open(TRADE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        logger.info("Trade decision saved to history.")
    except Exception as e:
        logger.error(f"Failed to save trade history: {e}")


def get_limit_clearance(symbol):
    """
    Check if a trade can be opened based on defined limits
    """
    trade_limits = load_trade_limits()
    if symbol not in trade_limits:
        logger.warning(f"No trade limits defined for {symbol}. "
                       f"Trading is not allowed.")
        return None, None

    limits = trade_limits[symbol]
    positions = get_total_positions()
    current_time = time.time()

    current_long_size = positions.get(symbol, {}).get("LONG", {}).get("SIZE_SUM", 0)
    current_short_size = positions.get(symbol, {}).get("SHORT", {}).get("SIZE_SUM", 0)
    total_positions = current_long_size + current_short_size
    last_long_position_time = positions.get(symbol, {}).get('LONG', {}).get('LAST_POSITION_TIME', 0)
    last_short_position_time = positions.get(symbol, {}.get('LONG', {}).get('LAST_POSITION_TIME', 0)

    # max_short_size = limits.get("MAX_SHORT_SIZE", float("inf"))

    max_long_size = limits.get("MAX_LONG_SIZE", float("inf"))

    max_long_size = limits.get('MAX_LONG_SIZE', float('inf'))
    max_orders = limits.get("MAX_ORDERS", 100)
    cooldown_seconds = limits.get('COOLDOWN_SECONDS', 120)

    logger.info(f"Limit Check for {symbol}:" 
                f"Max LONG {max_long_size}, Current LONG {current_long_size}, "
                f"Max SHORT {max_short_size},"
                f"Current SHORT {current_short_size}, Max Orders {max_orders}, "
                f"Total Open Positions {total_positions}, "
                f"Last LONG time {last_long_position_time}, "
                f"Last SHORT time {last_short_position_time}")

    if total_positions >= max_orders:
        logger.error(f"Max orders reached for {symbol}")
        return None, None

    long_size_available = current_long_size < max_long_size
    short_size_available = current_short_size < max_short_size
    long_cooled = (current_time - last_long_position_time) >= cooldown_seconds
    short_cooled = (current_time - last_short_position_time) >= cooldown_seconds

    allow_buy = long_size_available and long_cooled
    allow_sell = short_size_available and short_cooled

    logger.info(f"Limit Check for {symbol}: "
                f"Max LONG {max_long_size}, Current LONG {current_long_size}, "
                f"Max SHORT {max_short_size}, Current SHORT {current_short_size}, "
                f"Max Orders {max_orders}, Total Open Positions {total_positions}, "
                f"Last LONG time {last_long_position_time}, Last SHORT time {last_short_position_time}, "
                f"Long Available: {long_size_available}, Long Cooled: {long_cooled}, "
                f"Short Available: {short_size_available}, Short Cooled: {short_cooled}")

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
        adx_result = calculate_adx(symbol)

        if not adx_result:
            logger.error(f"ADX calculation failed or returned no signal for {symbol}")
            return False

        trade_signal, adx, plus_di, minus_di = adx_result

        if trade_signal == "BUY" and allow_buy:
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
    logger.info(f"Positions: {positions}")
    if not positions:
        logger.warning(f"No open positions found on {file_path}.")
        return

    for pos in positions:
        logger.info(f"Evaluate CLose Position: {pos}")
        symbol = pos['symbol']
        ticket = pos['ticket']
        pos_type = pos['type']
        volume = pos['volume']
        profit = pos['profit']
        price_open = pos['price_open']
        invested_amount = volume * price_open
        logger.info(f"POS | {symbol} | {pos_type} | {volume} | {price_open} | {invested_amount} | {profit} | {profit/invested_amount}")

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
