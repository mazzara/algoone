# src/trader/trade.py
import MetaTrader5 as mt5
import os
import random
import json
import time
from datetime import datetime, timezone, timedelta
import pytz
from src.logger_config import logger
from src.portfolio.total_positions import (
    get_total_positions, total_positions_cache
)
from src.limits.limits import (
    get_limit_clearance, get_cooldown_clearance, get_symbol_limits,
    get_trade_limits
)
from src.limits.cycle_limit import check_cycle_clearance
from src.tools.server_time import parse_time
from src.positions.positions import get_positions, load_positions
from src.indicators.adx_indicator import calculate_adx
from src.indicators.signal_indicator import (
    dispatch_signals, dispatch_position_manager_indicator, maybe_invert_signal
)
from src.journal.position_journal import (
    log_open_trade, log_close_trade, append_tracking
)
from src.trader.awareness import evaluate_profit_awareness
from src.trader.autotrade import get_autotrade_param
from src.config import (
        HARD_MEMORY_DIR,
        POSITIONS_FILE,
        BROKER_SYMBOLS,
        TRADE_LIMIT_FILE,
        TRADE_DECISIONS_FILE,
        # CLOSE_PROFIT_THRESHOLD,
        # TRAILING_PROFIT_THRESHHOLD,
        CLEARANCE_HEAT_FILE,
        CLEARANCE_LIMIT_FILE
        # DEFAULT_VOLATILITY,
        # DEFAULT_ATR_MULTIPLYER,
        # MIN_ART_PCT
)

# Cash trade limits to avoid reloading
# trade_limits_cache = None
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
        logger.error(
            f"[ERROR 1247] :: "
            f"Symbol configuration file not found: {symbols_file}")
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
    logger.info(f"[INFO 1744:20] :: Signal Votes: {vote_counts}")

    consensus_signal = max(vote_counts, key=vote_counts.get)

    if vote_counts[consensus_signal] >= 1:
        logger.info(f"[INFO 1744:30] :: Consensus Signal: {consensus_signal}")
        return consensus_signal
    return None


####  Deprecated open_trade function --- new version bellow improved signature
# def open_trade(symbol, lot_size=0.01):
#     """
#     Open a trade based on the symbol and lot size.
#     This function checks the current market conditions, trade limits, and cooldown periods before executing a trade.
#     It also aggregates signals from multiple indicators to determine the consensus signal for trading.
#
#     Supported kwargs:
#         - lot_size
#         - stop_loss
#         - take_profit
#         - signals
#
#     4 digit signature for this function: 1700
#     """
#
#     # global trade_limits_cache
#     global total_positions_cache
#
#     logger.debug(
#         f"[DEBUG 1700:10] :: "
#         f"\n[1700:10] function open_trade({symbol}, {lot_size}) "
#         f"\n[1700:10] total_positions_cache: {total_positions_cache}"
#     )
#
#     tick = mt5.symbol_info_tick(symbol)
#     if not tick:
#         logger.error(f"[ERROR 1700:12] :: Failed to get tick data for {symbol}")
#         return False
#
#     spread = tick.ask - tick.bid
#     logger.info(
#         f"[INFO 1700:15] TICK: {symbol} | "
#         f"Bid: {tick.bid} | Ask: {tick.ask} | "
#         f"Spread: {spread} | Time: {tick.time}"
#     )
#
#     # Call ATR - it is a core component of opening a trade logic.
#     atr_calculation = dispatch_position_manager_indicator(symbol, 'ATR')
#     # Properly extract ATR like in manage_trade. Latter YOU SHOULD (must) refactor this.
#     atr_result = atr_calculation.get("ATR")
#     if not atr_result:
#         logger.error(f"[ERROR 1700:49] :: Failed to extract ATR result for {symbol}")
#         return False
#
#     atr = atr_result.get("value", 0)
#
#     atr_pct = atr / tick.bid if tick and tick.bid else 0
#
#     # MIN_ART_PCT = 0.05/100.0
#
#     min_art_pct = MIN_ART_PCT
#
#     if atr_pct < min_art_pct:
#         logger.error(
#             f"[TRADE-LOGIC 1700:50:1] :: "
#             f"atr_pct is low for {symbol}: {atr_pct:.6f} | "
#             f"Expected > {min_art_pct:.6f} | "
#         )
#         return False
#     else:
#         logger.info(
#             f"[TRADE-LOGIC 1700:50:2] :: "
#             f"atr_pct for {symbol}: {atr_pct:.6f} | "
#             f"Expected > {min_art_pct:.6f} | "
#             f"Qualified ATR "
#         )
#
#     logger.debug(
#         f"[DEBUG 1700:51] :: "
#         f"ATR for {symbol}: {atr} | Spread: {spread} | Tick: {tick.bid} | "
#         f"Time: {tick.time} | ATR Multiplier: {DEFAULT_ATR_MULTIPLYER} | "
#         f"Volatility: {DEFAULT_VOLATILITY} | Lot Size: {lot_size} | "
#         f"Slippage: 20 | Magic Number: {random.randint(100000, 999999)} | "
#         f"Comment: 'Python Auto Trading Bot' | "
#         f"Type Filling: mt5.ORDER_FILLING_IOC"
#     )
#
#     if spread <= atr:
#         allow_buy, allow_sell = get_open_trade_clearance(symbol)
#         logger.debug(
#             f"[DEBUG 1700:60] :: "
#             f"Trade Clearance for {symbol}: {allow_buy}, {allow_sell}"
#         )
#
#         signals = dispatch_signals(symbol)
#         logger.debug(
#             f"[DEBUG 1700:61] :: "
#             f"Signals for {symbol}: {signals}"
#         )
#
#         # Just a deeper loging to check signals simply
#         for indicator_name, signal_data in signals.items():
#             indicator = signal_data.get("indicator", "Unknown")
#             sig = signal_data.get("signal", "NONE")
#             logger.debug(
#                 f"[DEBUG 1700:b61] :: "
#                 f"Signal {symbol}  {indicator_name} ({indicator}) {sig}"
#             )
#
#         position_manager = dispatch_position_manager_indicator(symbol, 'ATR')
#         logger.debug(
#             f"[DEBUG 1700:62] :: "
#             f"Position Manager for {symbol}: {position_manager}"
#         )
#
#         trailing_stop = None
#         if position_manager:
#             trailing_stop = position_manager.get('value', {})
#
#         logger.debug(
#             f"[DEBUG 1700:70] :: "
#             f"Trade Clearance for {symbol}: {allow_buy}, {allow_sell}"
#         )
#
#         logger.info(
#             f"[INFO 1700:71] :: "
#             f"Trade Limits {symbol}: {allow_buy}, {allow_sell}"
#         )
#
#         # Agregate the Signals to get a consensus
#         consensus_signal = aggregate_signals(signals)
#         logger.info(
#             f"[INFO 1700:72] :: "
#             f"Consensus Signal (open_trade): {symbol} {consensus_signal}"
#         )
#         if consensus_signal == 'NONE':
#             return False
#
#         trade_executed = None
#
#         # if trade_signal == "BUY" and allow_buy:
#         if consensus_signal == "BUY" and allow_buy:
#             sl = tick.bid - (tick.ask * DEFAULT_VOLATILITY)
#             tp = tick.bid + (tick.ask * DEFAULT_VOLATILITY * 2.0)
#             result = open_buy(symbol, lot_size, stop_loss=sl, take_profit=tp, signals=signals)
#             logger.debug(
#                 f"[DEBUG 1700:73] :: "
#                 f"System called open_buy({symbol}, {lot_size}) "
#                 f"with sl: {sl}, tp: {tp}"
#                 )
#             if result:
#                 trade_executed = "BUY"
#                 logger.debug(
#                     f"[DEBUG 1700:74] :: "
#                     f"Trade executed: {trade_executed} for {symbol} "
#                     f"with result: {result}"
#                 )
#
#         # elif trade_signal == "SELL" and allow_sell:
#         elif consensus_signal == "SELL" and allow_sell:
#             sl = tick.bid + (tick.ask * DEFAULT_VOLATILITY)
#             tp = tick.bid - (tick.ask * DEFAULT_VOLATILITY * 2.0)
#             result = open_sell(symbol, lot_size, stop_loss=sl, take_profit=tp, signals=signals)
#             logger.debug(
#                     f"[DEBUG 1700:75] :: "
#                     f"System called open_sell({symbol}, {lot_size}) "
#                     f"with sl: {sl}, tp: {tp}"
#                 )
#             if result:
#                 trade_executed = "SELL"
#                 logger.debug(
#                     f"[DEBUG 1700:76] :: "
#                     f"Trade executed: {trade_executed} for {symbol} "
#                     f"with result: {result}"
#                 )
#
#         if trade_executed:
#             trade_data = {
#                 "symbol": symbol,
#                 "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "spread": spread,
#                 "trade_executed": trade_executed,
#                 "result": result,
#                 "signals": signals,
#                 "trade_clearance": {
#                     "allow_buy": allow_buy,
#                     "allow_sell": allow_sell
#                 },
#                 "consensus_signal": consensus_signal
#             }
#             save_trade_decision(trade_data)
#             logger.info(f"[INFO 1700] :: Trade executed for {symbol}")
#             total_positions_cache = get_total_positions(save=True, use_cache=False)
#
#             logger.info(f"[INFO 1700] :: Total Positions Cached after trade: {total_positions_cache}")
#
#             time.sleep(9)  # Sleep for some seconds to assure data
#
#         else:
#             logger.error(f"[ERROR 1700] :: Trade limits reached for {symbol}")
#
#     else:
#         logger.error(f"[ERROR 1700] :: Spread too low, no trade executed for {symbol}")
#

def fetch_tick(symbol: str):
    """
    Fetch the latest tick data for a symbol.
    """
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(f"[ERROR 1701:80] :: Failed to get tick data for {symbol}")
        return None
    return tick


def basic_atr_check(symbol: str, tick) -> bool:
    """
    Basic ATR verification for the symbol.
    """
    atr_result = None
    atr_result = dispatch_position_manager_indicator(symbol, 'ATR')
    if not atr_result:
        logger.error(f"[ERROR 1702:90] :: Failed to extract ATR result for {symbol}")
        return False
    atr_result = atr_result.get("ATR")
    atr = atr_result.get("value", 0)
    atr_pct = atr / tick.bid if tick and tick.bid else 0
    # min_art_pct = MIN_ART_PCT
    min_art_pct = get_autotrade_param(symbol, 'min_atr_pct', default=0.0005)
    if atr_pct < min_art_pct:
        logger.error(
            f"[TRADE-LOGIC 1702:90:1] :: "
            f"atr_pct is low for {symbol}: {atr_pct:.6f} | "
            f"Expected > {min_art_pct:.6f} | "
        )
        return False
    else:
        logger.info(
            f"[TRADE-LOGIC 1702:90:2] :: "
            f"atr_pct for {symbol}: {atr_pct:.6f} | "
            f"Expected > {min_art_pct:.6f} | "
            f"Qualified ATR "
        )
        return True


def basic_spread_check(symbol: str, tick, atr) -> bool:
    """
    Check if the spread is within acceptable limits for the symbol.
    """
    spread = tick.ask - tick.bid
    logger.info(
        f"[INFO 1703:100] TICK: {symbol} | "
        f"Bid: {tick.bid} | Ask: {tick.ask} | "
        f"Spread: {spread} | Time: {tick.time}"
    )
    if spread <= atr:
        return True
    else:
        logger.error(
            f"[ERROR 1703:200] :: "
            f"Spread too wide, no trade executed for {symbol}"
        )
        return False


# NEW version of open_trade with better signature and data flow
def open_trade(symbol: str, **kwargs) -> dict:
    """
    Open a trade based on the symbol and kwargs.

    Supported kwargs:
        - lot_size
        - stop_loss
        - take_profit
        - signals
    """

    # global trade_limits_cache
    global total_positions_cache

    tick = fetch_tick(symbol)
    if not tick:
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "Tick fetch failed."
        }

    if not basic_atr_check(symbol, tick):
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "ATR check failed."
        }


    # Extract known parameters with defaults
    lot_size = kwargs.get('lot_size', 0.01)
    stop_loss = kwargs.get('stop_loss', None)
    take_profit = kwargs.get('take_profit', None)
    trailing_stop = kwargs.get('trailing_stop', None)
    slippage = kwargs.get('slippage', 20)
    signals = kwargs.get('signals', None)


    atr_result = dispatch_position_manager_indicator(symbol, 'ATR')
    atr_value = atr_result.get('ATR', {}).get('value', 0) if atr_result else 0

    if not basic_spread_check(symbol, tick, atr_value):
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "Spread check failed."
        }

    # A simple signals verification
    # if not signals:
    #     signals = dispatch_signals(symbol)
    #     logger.debug(f"[DEBUG 1700] :: Signals dispatched for {symbol}: {signals}")

    default_volatility = get_autotrade_param(symbol, 'default_volatility_decimal', default=0.03)

    # Enrich kwargs
    kwargs['spread'] = tick.ask - tick.bid
    kwargs['atr_value'] = atr_value
    kwargs['atr_pct'] = (atr_value / tick.bid) if tick and tick.bid else 0
    # kwargs['volatility'] = kwargs.get('volatility', DEFAULT_VOLATILITY)
    kwargs['volatility'] = kwargs.get('volatility', default_volatility)
    kwargs['tick_snapshot'] = {
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": tick.ask - tick.bid
        }

    if not signals:
        logger.info(
                f"[TRADE INFO 1700:15] :: "
                f"No signals prvided for {symbol}. Dispatching signals... "
        )
        signals = dispatch_signals(symbol)
        logger.debug(
                f"[DEBUG 1700:17] :: "
                f"Signals dispatched for {symbol}: {signals}"
        )

    # A robutst data signals verificationis
    # Now validate signals data structure
    if not isinstance(signals, dict) or not all(isinstance(v, dict) and 'signal' in v for v in signals.values()):
        logger.error(
            f"[ERROR 1700:20] :: "
            f"Invalid or incomplete signals received for {symbol}"
        )
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "Invalid signals."
        }

    consensus_signal = aggregate_signals(signals)
    logger.info(
        f"[INFO 1700:30] :: "
        f"Consensus signal for {symbol}: {consensus_signal}"
    )
    consensus_signal = maybe_invert_signal(symbol, consensus_signal)
    logger.info(
        f"[INFO 1700:31] :: "
        f"Consensus signal (after inversion check) for {symbol}: {consensus_signal}"
    )


    if not check_cycle_clearance(symbol):
        logger.warning(f"[CYCLE LIMIT] :: {symbol} blocked by liquidation cooldown. Skipping trade attempt.")
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "Blocked by liquidation cooldown."
        }

    allow_buy, allow_sell = get_open_trade_clearance(symbol)
    logger.debug(
        f"[DEBUG 1700:40] :: "
        f"Trade clearance for {symbol}: BUY={allow_buy}, SELL={allow_sell}"
    )


    # Calculate stop loss and take profit if not provided
    if stop_loss is None or take_profit is None:
        default_volatility = get_autotrade_param(
            symbol, 'default_volatility_decimal', default=0.03
        )

    if consensus_signal == "BUY":
        stop_loss = tick.bid - (tick.bid * default_volatility)
        take_profit = tick.bid + (tick.bid * default_volatility * 2.0)

    elif consensus_signal == "SELL":
        stop_loss = tick.bid + (tick.bid * default_volatility)
        take_profit = tick.bid - (tick.bid * default_volatility * 2.0)

    logger.info(f"[INFO 1700:25] :: Calculated SL/TP for {symbol} - SL: {stop_loss} | TP: {take_profit}")

    if consensus_signal == "BUY" and allow_buy:
        logger.info(f"[INFO 1700:50] :: Preparing BUY trade for {symbol}")
        result = open_buy(
            symbol,
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,
            slippage=slippage,
            signals=signals,
            **kwargs
        )
        executed_side = "BUY"
    elif consensus_signal == "SELL" and allow_sell:
        logger.info(f"[INFO 1700:60] :: Preparing SELL trade for {symbol}")
        result = open_sell(
            symbol,
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,
            slippage=slippage,
            signals=signals,
            **kwargs
        )
        executed_side = "SELL"
    else:
        logger.warning(
            f"[WARN 1700:70] :: "
            f"No valid trade executed for {symbol} due to signal or clearance."
        )
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "No trade executed (signal or clearance)."
        }

    if result:
        logger.info(
            f"[INFO 1700:80] :: "
            f"Trade executed successfully: {executed_side} {symbol}"
        )

        # total_positions_cache = get_total_positions(save=True, use_cache=False)  # Refresh cache after trade


        if result.get("success"):
            logger.info(
                f"[INFO 1700:90] :: "
                f"Trade executed successfully: {executed_side} {symbol}"
            )

            # === Refresh global total_positions_cache ===
            new_positions = get_total_positions(save=True, use_cache=False)
            total_positions_cache.clear()
            total_positions_cache.update(new_positions)
            logger.info(
                f"[INFO 1700:100] :: "
                f"Total Positions Cache refreshed after trade."
            )

        # === Check if liquidation cycle should be registered ===
        for symb, symb_data in total_positions_cache.items():
            net_data = symb_data.get('NET', {})
            if net_data.get('SIZE_SUM', 0) == 0 and net_data.get('POSITION_COUNT', 0) == 0:
                register_cycle(symb)

        trade_record = {
            "symbol": symbol,
            "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "executed_side": executed_side,
            "spread": tick.ask - tick.bid,
            "signals": signals,
            "consensus_signal": consensus_signal,
            "atr_value": atr_value,
        }
        save_trade_decision(trade_record)

        return {
            "success": True,
            "executed_side": executed_side,
            "order": result.get('order', None),
            "mt5_result": result.get('mt5_result', None),
            "message": "Trade executed."
        }
    else:
        logger.error(f"[ERROR 1700:110] :: Trade execution failed for {symbol}")
        return {
            "success": False,
            "executed_side": None,
            "order": None,
            "mt5_result": None,
            "message": "Trade execution failed."
        }


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
        order_type=None,
        signals=None,
        **kwargs):
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
        "deviation": slippage,
        "magic": magic if magic is not None else random.randint(100000, 599999),
        "comment": "Python Auto Trading Bot",
        "type_filling": type_filling if type_filling is not None else mt5.ORDER_FILLING_IOC
    }
    # Only add stop loss and take profit if they are provided.
    if stop_loss is not None:
        order["sl"] = stop_loss
    if take_profit is not None:
        order["tp"] = take_profit

    return execute_trade(order, signals, **kwargs)


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
        order_type=None,
        signals=None,
        **kwargs):
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
        "deviation": slippage,
        "magic": magic if magic is not None else random.randint(600000, 999999),
        "comment": "Python Auto Trading Bot",
        "type_filling": type_filling if type_filling is not None else mt5.ORDER_FILLING_IOC
    }
    # Only add stop loss and take profit if they are provided.
    if stop_loss is not None:
        order["sl"] = stop_loss
    if take_profit is not None:
        order["tp"] = take_profit

    return execute_trade(order, signals, **kwargs)



def close_trade(symbol=None):
    """
    Close a trade based on profit threshold.
    4 digit signature for this function: 1038
    """
    # close_profit_threshold = CLOSE_PROFIT_THRESHOLD
    close_profit_threshold = get_autotrade_param(
        symbol, 'close_profit_threshold_decimal', default=0.05)

    logger.info(
        f"[INFO 1038] :: "
        f"Closing trades with profit threshold: {close_profit_threshold}"
    )
    if not symbol:
        logger.error(
            "[ERROR 1038] :: close_trade() called without a valid symbol."
        )
        return False

    symbol_config = get_symbol_config(symbol)
    if symbol_config:
        symbol_contract_size = symbol_config.get('contract_size', 1)
        logger.info(
            f"[INFO 1038] :: "
            f"Symbol {symbol} contract size: {symbol_contract_size}"
        )

    signals = dispatch_signals(symbol)
    consensus_signal = aggregate_signals(signals)
    logger.info(
        f"[INFO 1038] :: Consensus Signal (close_trade): {consensus_signal}"
    )

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
        logger.warning(
            f"[WARNING 1038] :: "
            f"File positions not found. I am unable to close trades."
        )
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        positions_data = json.load(f)
        logger.info(
            f"[INFO 1038] :: close_trade() - "
            f"Positions loaded from cache 'positions_data': {len(positions_data)}"
        )

    positions = positions_data['positions']
    logger.info(f"[INFO 1038] :: Positions loaded from cache: {len(positions)}")

    if not positions:
        logger.warning(
            f"[WARNING 1038] :: "
            f"No open positions found on {file_path}."
        )
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

        logger.info(
            f"[INFO 1038] :: "
            f"Position PnL: {position_pnl} | Invested Amount: {invested_amount} "
            f"| Profit: {profit} | Symbol: {symbol} | Volume: {volume} | "
            f"Type: {pos_type} | Ticket: {ticket} | Price Open: {price_open} "
            f"| Min Profit: {min_profit} | "
            f"Close Profit Threshold: {close_profit_threshold} | "
            f"Contract Size: {symbol_contract_size} | "
            f"Trailing Stop: {trailing_stop}")

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
            logger.info(
                f"[INFO 1038] :: "
                f"Close request sent as mt5.position_close: {close_request}"
            )
            logger.error(f"[INFO 1038] :: MT5 last error: {mt5.last_error()}")

            if close_result is None:
                logger.error(
                    f"[ERROR 1038] :: "
                    f"Failed to close position on {symbol}. "
                    f"`mt5.order_send()` returned None."
                )
                continue

            logger.info(f"[INFO 1038] :: Close order response: {close_result}")

            if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(
                    f"[INFO 1038] :: Successfully closed position on {symbol}"
                )
                log_close_trade(ticket, close_reason="TP Triggered", final_profit=profit)
            else:
                logger.error(
                    f"[ERROR 1038] :: "
                    f"Failed to close position on {symbol}. "
                    f"Error Code: {close_result.retcode}, "
                    f"Message: {close_result.comment}"
                )

            if close_result and close_result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"[INFO 1038] :: Close order result: {close_result}")
                logger.info(f"[INFO 1038] :: Closed position on {symbol}")
    return True


def close_position_by_ticket(ticket, symbol, pos_type, volume):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logger.error(
            f"[CloseByTicket 2606:03] :: "
            f"Failed to get tick data for {symbol}"
        )
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
        logger.info(
            f"[CloseByTicket 2606:07] :: "
            f"Successfully closed ticket {ticket} for {symbol}"
        )
        return True
    else:
        logger.error(
            f"[CloseByTicket 2606:08] :: "
            f"Failed to close ticket {ticket}. Error: {mt5.last_error()}"
        )
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
        logger.info(
            f"[INFO 0625] :: "
            f"No position manager signal for {symbol}; "
            f"no adjustments will be made."
        )
        return True

    # Extract the ATR result dictionary from pm_result.
    atr_result = pm_result.get("ATR")
    if not atr_result:
        logger.error(
            f"[ERROR 0625] :: "
            f"ATR result is missing from the position manager indicators."
        )
        return False

    # Retrieve the ATR value from the indicator result.
    atr_value = atr_result.get("value", {})
    if atr_value is None:
        logger.error(f"[ERROR 0625] :: ATR value is not available for {symbol}.")
        return False

    # multiplier = DEFAULT_ATR_MULTIPLYER
    multiplier = get_autotrade_param(symbol, 'default_atr_multiplier', default=1.5)

    # Get current open positions for the symbol.
    # (Assuming get_positions() returns a dict containing a list of positions under 'positions')
    get_positions()
    file_path = os.path.join(POSITIONS_FILE)
    logger.info(f"[INFO 0625] :: Loading positions from {file_path}")

    if not os.path.exists(file_path):
        logger.warning(
            f"[WARNING 0625] :: "
            f"File positions not found. Unable to manage trades."
        )
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
        current_sl = pos.get("sl", None)
        open_price = pos.get("price_open", None)
        volume = pos.get("volume", 0)
        recommended_sl = None

        append_tracking(
            ticket,
            price_open=pos["price_open"],
            price_current=pos["price_current"],
            pos_type=pos["type"]
        )

        # BREAK_EVEN_OFFSET = 0.103  # 10.3% of ATR value
        break_even_offset = get_autotrade_param(symbol, 'break_even_offset_decimal', default=0.103)

        # Evaluate Awareness
        take_profit = False
        take_profit = evaluate_profit_awareness(symbol, tick, atr_value,
                                                     open_price, pos_type)
        logger.debug(
            f"[DEBUG 0625:02] :: Evaluating profit awareness for {symbol} - "
            f"Take Profit: {take_profit} | ATR Value: {atr_value} | "
            f"Open Price: {open_price} | Position Type: {pos_type} | "
            f"Current SL: {current_sl} | Ticket: {ticket}"
        )

        if take_profit:
            logger.info(
                f"[INFO 0625:03] :: Closing Symbol {symbol} "
                f"position {ticket} due to profit awareness."
            )
            close_position_by_ticket(ticket, symbol, pos_type, volume)
            continue

        if pos_type == "BUY":
            has_moved_1_atr = tick.bid >= open_price + atr_value
            in_trailing_range = tick.bid < open_price + (atr_value * multiplier)

            if has_moved_1_atr and in_trailing_range:
                # Break-even logic
                # recommended_sl = open_price + (atr_value * BREAK_EVEN_OFFSET)
                recommended_sl = open_price + (atr_value * break_even_offset)
                logger.info(
                    f"[INFO 0625] :: BUY position {ticket}: "
                    f"Break-even zone. Recommending SL to {recommended_sl}"
                )
            else:
                # Trailing logic
                recommended_sl = tick.bid - multiplier * atr_value
                logger.info(
                    f"[INFO 0625] :: BUY position {ticket}: "
                    f"Trailing SL calculated at {recommended_sl}"
                )

            if current_sl is not None and recommended_sl <= current_sl:
                logger.info(
                    f"[INFO 0625] :: BUY position {ticket}: "
                    f"SL {recommended_sl} not better than current {current_sl}."
                    f" Skipping update."
                )
                continue

        elif pos_type == "SELL":
            has_moved_1_atr = tick.ask <= open_price - atr_value
            in_trailing_range = tick.ask > open_price - (atr_value * multiplier)

            if has_moved_1_atr and in_trailing_range:
                # Break-even logic
                # recommended_sl = open_price - (atr_value * BREAK_EVEN_OFFSET)
                recommended_sl = open_price - (atr_value * break_even_offset)
                logger.info(
                    f"[INFO 0625] :: SELL position {ticket}: Break-even zone."
                    f" Recommending SL to {recommended_sl}"
                )
            else:
                # Trailing logic
                recommended_sl = tick.ask + multiplier * atr_value
                logger.info(
                    f"[INFO 0625] :: SELL position {ticket}: "
                    f"Trailing SL calculated at {recommended_sl}"
                )

            if current_sl is not None and recommended_sl >= current_sl:
                logger.info(
                    f"[INFO 0625] :: SELL position {ticket}: SL {recommended_sl}"
                    f" not better than current {current_sl}. Skipping update."
                )
                continue

        else:
            logger.warning(
                f"[WARNING 0625] :: Position {ticket} "
                f"has unknown type: {pos_type}. Skipping."
            )
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
        logger.info(
            f"[INFO 0625] :: Sending modify request for "
            f"position {ticket}: {modify_request}"
        )
        modify_result = mt5.order_send(modify_request)
        logger.info(
            f"[INFO 0625] :: Modify result for "
            f"position {ticket}: {modify_result}"
        )

        if modify_result is not None and modify_result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(
                f"[INFO 0625] :: Successfully updated trailing stop for "
                f"position {ticket}."
            )
        else:
            logger.error(
                f"[0625] :: Failed to update trailing stop for "
                f"position {ticket}. MT5 Error: {mt5.last_error()}"
            )

    return True


# DEPRECATED  !!! ATENTION !!!  execute_trade version - below is an improved one.
# def execute_trade(order, signals):
#     result = mt5.order_send(order)
#     logger.info(f"Trade Order Sent: {order}")
#     logger.info(f"Full Order Response: {result}")
#
#     if result and result.retcode == mt5.TRADE_RETCODE_DONE:
#         logger.info(f"Trade opened: {result.order}")
#         ticket = result.order
#         # indicators = {"adx": 22.4, "sma_short": 102.3, "slope": "UP"}  # example - make it dynamic latter
#
#         if order["type"] == mt5.ORDER_TYPE_BUY:
#             order_type = "BUY"
#         elif order["type"] == mt5.ORDER_TYPE_SELL:
#             order_type = "SELL"
#         else:
#             order_type = "UNKNOWN"
#
#         log_open_trade(
#             ticket,
#             order["symbol"],
#             order_type,
#             order["volume"],
#             order["price"],
#             signals
#         )
#         return True
#     else:
#         logger.error(f"Trade failed: {result.retcode}")
#         return False


# NEW EXECUTE TRADE WITH UPGRADED SIGNATURE AND RETURNS
def execute_trade(order, signals, **kwargs):
    """
    Execute a trade by sending an order to MT5.

    Args:
        order (dict): Order dictionary formatted for mt5.order_send
        signals (dict): Signals at execution time
        kwargs: Future flexibility (e.g., risk context)

    Returns:
        dict:
            - success (bool)
            - order (dict of sent order)
            - mt5_result (full mt5 response object)
    """
    result = mt5.order_send(order)
    logger.info(f"Trade Order Sent: {order}")
    logger.info(f"Full Order Response: {result}")

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Trade opened: {result.order}")
        ticket = result.order

        if order["type"] == mt5.ORDER_TYPE_BUY:
            order_type = "BUY"
        elif order["type"] == mt5.ORDER_TYPE_SELL:
            order_type = "SELL"
        else:
            order_type = "UNKNOWN"

        log_open_trade(
            ticket,
            order["symbol"],
            order_type,
            order["volume"],
            order["price"],
            signals,
            rationale=None, 
            # rationale=None,  # optional
            # spread=kwargs.get('spread'),  # new
            # atr_value=kwargs.get('atr_value'),  # new
            # atr_pct=kwargs.get('atr_pct'),  # new
            # volatility=kwargs.get('volatility'),  # new
            # tick_snapshot=kwargs.get('tick_snapshot')  # new
            **kwargs
        )
        return {
            "success": True,
            "order": order,
            "mt5_result": result,
        }
    else:
        logger.error(f"Trade failed: {result.retcode if result else 'No Result'}")
        return {
            "success": False,
            "order": order,
            "mt5_result": result,
        }


if __name__ == "__main__":
    from connect import connect, disconnect

    if connect():
        open_trade("EURUSD")  # Test trade on EURUSD
        disconnect()


# End of trade.py
