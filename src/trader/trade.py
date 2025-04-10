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
from src.trader.awareness import evaluate_profit_awareness
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
    atr_calculation = dispatch_position_manager_indicator(symbol, 'ATR')
    # Properly extract ATR like in manage_trade. Latter YOU SHOULD (must) refactor this.
    atr_result = atr_calculation.get("ATR")
    if not atr_result:
        logger.error(f"[ERROR 1700:50] :: Failed to extract ATR result for {symbol}")
        return False

    atr = atr_result.get("value", 0)

    logger.debug(f"[DEBUG 1700:51] :: ATR for {symbol}: {atr} | Spread: {spread} | Tick: {tick.bid} | Time: {tick.time} | ATR Multiplier: {DEFAULT_ATR_MULTIPLYER} | Volatility: {DEFAULT_VOLATILITY} | Lot Size: {lot_size} | Slippage: 20 | Magic Number: {random.randint(100000, 999999)} | Comment: 'Python Auto Trading Bot' | Type Filling: mt5.ORDER_FILLING_IOC")

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


def close_position_by_ticket(ticket, symbol, pos_type, volume):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"[CloseByTicket 2606:03] :: Failed to get tick data for {symbol}")
        return False

    price = tick.bid if pos_type == 'SELL' else tick.ask

    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if pos_type == "SELL" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": 20,
        "magic": random.randint(100000, 999999),
        "comment": "Close by Awareness",
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(close_request)
    logger.info(f"[CloseByTicket 2606:04] :: Sent close request: {close_request}")
    logger.info(f"[CloseByTicket 2606:05] :: MT5 response: {result}")

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"[CloseByTicket 2606:07] :: Successfully closed ticket {ticket} for {symbol}")
        return True
    else:
        logger.error(f"[CloseByTicket 2606:08] :: Failed to close ticket {ticket}. Error: {mt5.last_error()}")
        return False


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
        volume = pos.get("volume", 0)
        recommended_sl = None

        BREAK_EVEN_OFFSET = 0.103  # 10.3% of ATR value

        # Evaluate Awareness
        take_profit = False
        take_profit = evaluate_profit_awareness(symbol, tick, atr_value,
                                                     open_price, pos_type)
        logger.debug(f"[DEBUG 0625:02] :: Evaluating profit awareness for {symbol} - Take Profit: {take_profit} | ATR Value: {atr_value} | Open Price: {open_price} | Position Type: {pos_type} | Current SL: {current_sl} | Ticket: {ticket}")

        if take_profit:
            logger.info(f"[INFO 0625:03] :: Closing Symbol {symbol} position {ticket} due to profit awareness.")
            close_position_by_ticket(ticket, symbol, pos_type, volume)
            continue

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
