# src/trader/sl_managers.py

import MetaTrader5 as mt5
import logging
from src.logger_config import logger
from src.trader.autotrade import get_autotrade_param
import os
from src.portfolio.total_positions import load_cached_positions
from src.positions.positions import get_positions, return_positions
from src.config import POSITIONS_FILE
import json
import time

# def load_cached_positions(ticket=None, retries=3, delay=0.2, depth=0):
#     """
#     Loads cached positions from 'hard_memory/positions.json'.
#     4 digit function signature: 6747
#     """
#     if depth > 3:
#         logger.error('[6747:00] :: Maximum retries reached. Returning empty list.')
#         return []
#
#     if not os.path.exists(POSITIONS_FILE):
#         logger.debug('[6747:10] :: No cashed positions found. File not found.')
#         get_positions()
#         time.sleep(delay)
#         logger.debug('[6747:20] :: Fallback: Positions just pulled from MT5.')
#         return load_cached_positions(retries=retries, delay=delay, depth=depth+1)
#
#     file_age = time.time() - os.path.getmtime(POSITIONS_FILE)
#
#     logger.debug(
#         f"[6747:30] :: "
#         f"Check cached-expire positions age: {file_age:.2f} seconds"
#     )
#
#     if file_age > 10:      # X seconds old
#         logger.debug('[6747:40] :: Cashed positions are outdated.')
#         get_positions()
#         time.sleep(delay)
#         return load_cached_positions(retries=retries, delay=delay, depth=depth+1)
#
#     for attempt in range(retries):
#         try:
#             with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
#                 positions = json.load(f)
#             if 'positions' in positions:
#                 pos_list = positions['positions']
#
#                 logger.info(
#                     f"[6747:60[ :: "
#                     f"Positions loaded from cache: {len(positions)}"
#                 )
#                 if ticket is not None:
#                     return next((p for p in pos_list if p['ticket'] == ticket), {})
#                 return pos_list
#             else:
#                 logger.warning(
#                     "[6747:70] :: "
#                     "Loaded JSON doen't have 'positions' key. Retrying..."
#                 )
#         except (json.JSONDecodeError, FileNotFoundError) as e:
#             logger.warning(
#                 f"[6747:80] :: Retry {attempt+1}/{retries}: "
#                 f"Failed to load cached positions: {e}"
#             )
#             time.sleep(delay)
#
#     logger.error('[6746:90] :: Multiple Failed to load cached positions.')
#     return []


def load_cached_pos_by_ticket(ticket):
    all_positions = load_cached_positions()
    for p in all_positions:
        if p['ticket'] == ticket:
            return p
    return {}


def simple_manage_sl(pos, tick, atr, config):
    """
    Break-even then trail using ATR.
    Returns the recommended stop-loss price (or None).
    """
    symbol = pos["symbol"]
    pos_type = pos["type"]
    open_price = pos["price_open"]
    current_sl = pos.get("sl")
    price_now = tick.bid if pos_type == "BUY" else tick.ask

    multiplier = config.get("atr_multiplier", get_autotrade_param(symbol, "atr_multiplier", default=2.0))
    break_even_offset = config.get("break_even_offset", get_autotrade_param(symbol, "break_even_offset_decimal", default=0.1))

    trail_sl = None

    if pos_type == "BUY":
        break_even_trigger = open_price + atr
        if price_now > break_even_trigger:
            trail_sl = price_now - atr * multiplier
            trail_sl = max(trail_sl, open_price + atr * break_even_offset)
            if not current_sl or trail_sl > current_sl:
                return trail_sl

    else:  # SELL
        break_even_trigger = open_price - atr
        if price_now < break_even_trigger:
            trail_sl = price_now + atr * multiplier
            trail_sl = min(trail_sl, open_price - atr * break_even_offset)
            if not current_sl or trail_sl < current_sl:
                return trail_sl
    return None



def sl_trailing_staircase(symbol, pos, tick, atr):
    """
    Unified trailing logic:
    - Initial SL checks with buffer
    - Minimum candle hold duration
    - Activation of trailing after profit threshold

    Returns:
        (recommended_sl, close_signal)

    function debyg signature: 0625:10:
    """
    # cached = get_cached_pos_by_ticket(pos["ticket"])
    # try:
    #     cached_all = load_cached_positions()
    #     cached = next((p for p in cached_all if p["ticket"] == pos["ticket"]), None)
    # except Exception as e:
    #     logger.warning(f"[SL Cache] :: Failed to load cached state for ticket {pos['ticket']}: {e}")
    #     cached = {}

    # cached = load_cached_positions(ticket=pos["ticket"])
    cached = load_cached_pos_by_ticket(pos["ticket"])

    logger.debug(
        f"[SL-Manage 0625:10:00] :: "
                f"CACHED POSITION LOADED FOR {pos['ticket']}: {cached}"
            )

    config = {
        "max_loss_decimal": get_autotrade_param(symbol, "max_loss_decimal", default=0.005),
        "initial_sl_buffer_atr": get_autotrade_param(symbol, "initial_sl_buffer_atr", default=1.5),
        "min_candles_hold": get_autotrade_param(symbol, "min_candles_hold", default=4),
        "min_ticks_to_hold": get_autotrade_param(symbol, "min_ticks_to_hold", default=9),
        "trailing_profit_threshold_decimal": get_autotrade_param(symbol, "trailing_profit_threshold_decimal", default=0.001),
        "atr_multiplier": get_autotrade_param(symbol, "atr_multiplier", default=2.0),
        "break_even_offset": get_autotrade_param(symbol, "break_even_offset_decimal", default=0.1)
    }

    price_now = tick.bid if pos["type"] == "BUY" else tick.ask
    open_price = pos["price_open"]
    pct_profit = (price_now - open_price) / open_price if pos["type"] == "BUY" else (open_price - price_now) / open_price
    peak_profit = cached.get("peak_profit", 0.0)
    profit_chain = cached.get("profit_chain", [])
    elapsed_candles = len(profit_chain)
    elapsed_ticks = len(profit_chain)

    logger.debug(
        f"[SL-Manage 0625:10:05] {pos['type']} {symbol} | "
            f"Current Price: {price_now} | "
            f"Open Price: {open_price} | "
            f"Peak Profit: {peak_profit} | "
            f"Elapsed Candles: {elapsed_candles} | "
            f"Elapsed Ticks: {elapsed_ticks} | "
            f"ATR: {atr} | "
            f"Profit Chain: {profit_chain} | "
            f"Config: {config}"
    )

    # -- Initial SL: Hard max loss cut
    if pct_profit < -config["max_loss_decimal"]:
        logger.info(f"[SL-Manage 0625:10:10] Hard stop triggered for {pos['symbol']} ticket {pos['ticket']}")
        return None, True

    # -- Initial SL: ATR-based buffer, after waiting period
    if elapsed_ticks < config["min_ticks_to_hold"]:
        logger.debug(f"[SL-Manage 0625:10:15] Waiting for {config['min_ticks_to_hold']} ticks before SL adjustment.")
        return None, False

    atr_buffer_cutoff = -atr * config["initial_sl_buffer_atr"] / open_price
    logger.debug(f"[SL-Manage 0625:10:20] ATR buffer cutoff: {atr_buffer_cutoff} | Current Profit: {pct_profit}")

    if pct_profit < atr_buffer_cutoff:
        logger.info(f"[SL-Manage 0625:10:25] ATR buffer stop triggered for {pos['symbol']} ticket {pos['ticket']}")
        return None, True

    # -- Trailing Activation
    if pct_profit > config["trailing_profit_threshold_decimal"]:
        logger.info(f"[SL-Manage 0625:10:30] Trailing activated for {pos['symbol']} ticket {pos['ticket']}")
        recommended_sl = simple_manage_sl(pos, tick, atr, config)
        return recommended_sl, False

    logger.debug(
        f"[SL-Manage 0625:10:40] No early exit triggeders for {pos['symbol']} ticket {pos['ticket']}"
       f" exiting function with HOLD state"
    )

    return None, False



def set_atr_sl(pos, tick, atr, config):
    """
    ATR-only trailing SL.
    """
    symbol = pos.symbol
    pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
    price_now = tick.bid if pos_type == "BUY" else tick.ask
    multiplier = config.get("atr_multiplier", get_autotrade_param(symbol, "atr_multiplier", default=2.0))

    if pos_type == "BUY":
        return price_now - atr * multiplier
    else:  # SELL
        return price_now + atr * multiplier


def set_volatility_sl(pos, config):
    """
    Set initial SL based on volatility cap.
    """
    symbol = pos.symbol
    pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
    open_price = pos.price_open
    cap = config.get("volatility_cap_decimal",
                     get_autotrade_param(symbol, "volatility_cap_decimal", default=0.03)
                     )

    if pos_type == "BUY":
        return open_price * (1 - cap)
    else:
        return open_price * (1 + cap)



def manage_atr_sl(pos, tick, atr, config):
    """
    ATR-based trailing SL manager.
    Only adjusts if new SL improves protection.
    """
    symbol = pos.symbol
    pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
    current_sl = pos.sl
    price_now = tick.bid if pos_type == "BUY" else tick.ask
    multiplier = config.get("atr_multiplier", get_autotrade_param(symbol, "atr_multiplier", default=2.0))

    if pos_type == "BUY":
        new_sl = price_now - atr * multiplier
        return new_sl if not current_sl or new_sl > current_sl else None
    else:
        new_sl = price_now + atr * multiplier
        return new_sl if not current_sl or new_sl < current_sl else None


def manage_volatility_sl(pos, tick, atr, config):
    """
    Experimental: trailing SL using volatility-aware zone logic.
    (Can be refined based on standard deviation bands, etc.)
    """
    symbol = pos.symbol
    pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
    current_sl = pos.sl
    price_now = tick.bid if pos_type == "BUY" else tick.ask
    cap = config.get("volatility_cap_decimal", get_autotrade_param(symbol, "volatility_cap_decimal", default=0.03))

    offset = price_now * cap
    new_sl = price_now - offset if pos_type == "BUY" else price_now + offset
    improved = new_sl > current_sl if pos_type == "BUY" else new_sl < current_sl

    logger.debug(f"[SL-Manage-Vol] {pos_type} {symbol} | New SL: {new_sl} | Improved: {improved}")
    return new_sl if improved else None





def manage_initial_sl(pos, tick, atr, config):
    """
    Applies an adaptive initial SL check based on:
    - A max_loss_pct hard cap (e.g., 0.5%)
    - An ATR-based buffer zone (e.g., 1.5 ATR)
    - A minimum candle wait time before acting (e.g., 4 candles)
    """
    symbol = pos.symbol
    price_now = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
    max_loss_pct = config.get("max_loss_pct", get_autotrade_param(symbol, "max_loss_pct", default=0.005))  # 0.5%
    atr_multiplier_buffer = config.get("initial_sl_buffer_atr", get_autotrade_param(symbol, "initial_sl_buffer_atr", default=1.5))
    min_candle_wait = config.get("initial_sl_wait_candles", get_autotrade_param(symbol, "initial_sl_wait_candles", default=4))

    open_price = pos.price_open
    pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
    elapsed_candles = pos.custom.get("elapsed_candles", 0)

    # Calculate current % loss
    pct_move = (price_now - open_price) / open_price if pos_type == "BUY" else (open_price - price_now) / open_price

    # Absolute hard stop
    if pct_move < -max_loss_pct:
        return "CLOSE_SIGNAL_HARD_STOP"

    # Buffer rule: Don't close too early if within ATR buffer
    if elapsed_candles < min_candle_wait:
        return "HOLD"

    if pct_move < -atr * atr_multiplier_buffer / open_price:
        return "CLOSE_SIGNAL_BUFFER_SL"

    return "HOLD"



def manage_trade_sl(pos, tick, atr, config):
    """
    Combines initial SL logic and trailing SL logic.
    """
    # Step 1: Initial SL phase
    if not pos.custom.get("trailing_active", False):
        decision = manage_initial_sl(pos, tick, atr, config)

        if decision.startswith("CLOSE_SIGNAL"):
            logger.info(f"[SL SIGNAL] :: {decision} for {pos.symbol} ticket {pos.ticket}")
            return decision

        # Check for trailing activation condition
        price_now = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        profit_pct = (price_now - pos.price_open) / pos.price_open if pos.type == mt5.ORDER_TYPE_BUY else (pos.price_open - price_now) / pos.price_open
        activate_trailing_pct = config.get("activate_trailing_pct", get_autotrade_param(pos.symbol, "activate_trailing_pct", default=0.001))

        if profit_pct > activate_trailing_pct:
            pos.custom["trailing_active"] = True
            logger.info(f"[TRAILING ACTIVATED] :: {pos.symbol} ticket {pos.ticket}")

    # Step 2: Trailing SL phase
    if pos.custom.get("trailing_active", False):
        simple_manage_sl(pos, tick, atr, config)

    return "HOLD"
