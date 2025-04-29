# src/trader/volatility_ladder.py

import os
import json
import time
from src.logger_config import logger

RISK_PROFILES = os.path.join("config", "risk_profiles.json")

def load_risk_profile(symbol):
    try:
        with open(RISK_PROFILES, "r", encoding="utf-8") as f:
            if not f:
                logger.error(f"[RISK_PROFILE 8001] Failed to load risk profiles: {RISK_PROFILES}")
                return None
            
            profile = json.load(f)
            if not profile:
                logger.error(f"[RISK_PROFILE 8001] Failed to load risk profiles: {RISK_PROFILES}")
                return None
            
            return profile.get(symbol) or profile.get('defaults')

    except Exception as e:
        logger.error(f"[RISK_PROFILE 8001] Failed to load risk profiles: {e}")
        return None


def calculate_trail(open_price, trail_pct, pos_type):
    if pos_type == "BUY":
        return open_price + (trail_pct / 100.0 * open_price)
    else:
        return open_price - (trail_pct / 100.0 * open_price)


def trailing_staircase(symbol, pos, tick):
    """
    Decides traililng stop or take profit based on volatility stair levels

    Returns:
        - recommendes_sl (float) or None
        - take_profit (bool) 

    4 digit function signature: 8743
    """

    profile = load_risk_profile(symbol)
    logger.debug(f"[RISK_PROFILE 8743:00] Loaded risk profile for {symbol}: {profile}")
    if not profile:
        logger.error(f"[RISK_PROFILE 8743:05] No risk profile found for {symbol}.")
        return None, False

    pos_type = pos.get('type')
    open_price = pos.get('price_open')
    current_price = tick.bid if pos_type == 'BUY' else tick.ask

    logger.debug(f"[RISK_PROFILE 8743:10] Current price for {symbol}: {current_price:.5f}")

    try:
        one_m_pct = profile['1m']['mean_atr_pct'] / 100.0
        five_m_pct = profile['5m']['mean_atr_pct'] / 100.0
        fifteen_m_pct = profile['15m']['mean_atr_pct'] / 100.0
        one_h_pct = profile['1h']['mean_atr_pct'] / 100.0
        one_d_pct = profile['1d']['mean_atr_pct'] / 100.0

        logger.debug(
            f"[RISK_PROFILE 8743:15] ATR percentages for {symbol}: "
                f"1m: {one_m_pct:.4f}, 5m: {five_m_pct:.4f}, "
                f"15m: {fifteen_m_pct:.4f}, 1h: {one_h_pct:.4f}, "
                f"1d: {one_d_pct:.4f}"
        )

    except KeyError:
        logger.error(f"[RISK_PROFILE 8743:20] Missing ATR percentage in profile for {symbol}.")
        return None, False

    move_pct = (current_price - open_price) / open_price if pos_type == 'BUY' else (open_price - current_price) / open_price

    move_pct *= 100.0

    logger.debug(f"[RISK_PROFILE 8743:25] Move percentage for {symbol}: {move_pct:.4f}%")

    # Determine which ladder stage we are in
    recommended_sl = None
    take_profit = False

    # Original Logic
    # if move_pct >= one_d_pct:
    #     take_profit = True
    # elif move_pct >= one_h_pct:
    #     # Use 15M trailing
    #     recommended_sl = open_price + (fifteen_m_pct / 100.0 * open_price) if pos_type == "BUY" else open_price - (fifteen_m_pct / 100.0 * open_price)
    # elif move_pct >= fifteen_m_pct:
    #     # Use 5M trailing
    #     recommended_sl = open_price + (five_m_pct / 100.0 * open_price) if pos_type == "BUY" else open_price - (five_m_pct / 100.0 * open_price)
    # elif move_pct >= five_m_pct:
    #     # Use 1M trailing
    #     recommended_sl = open_price + (one_m_pct / 100.0 * open_price) if pos_type == "BUY" else open_price - (one_m_pct / 100.0 * open_price)
    #
    # if recommended_sl:
    #     logger.info(f"[V-LADDER] :: {symbol} Recommending SL adjustment to {recommended_sl:.5f}")
    #
    # if take_profit:
    #     logger.info(f"[V-LADDER] :: {symbol} Target 1D move reached. Recommending full close.")

    # A more elegant logic
    ladder = [
        (one_d_pct, None, "TAKE_PROFIT"),
        (one_h_pct, fifteen_m_pct, "TRAIL_15M"),
        (fifteen_m_pct, five_m_pct, "TRAIL_5M"),
        (five_m_pct, one_m_pct, "TRAIL_1M"),
    ]

    for threshold, trail_to, action in ladder:
        if move_pct >= threshold:
            if action == "TAKE_PROFIT":
                take_profit = True
                logger.info(f"[V-LADDER 8743:30] :: {symbol} Target 1D move reached. Recommending full close.")
            else:
                # recommended_sl = open_price + (trail_to / 100.0 * open_price) if pos_type == "BUY" else open_price - (trail_to / 100.0 * open_price)
                recommended_sl = calculate_trail(open_price, trail_to, pos_type)
                logger.info(f"[V-LADDER 8743:35] :: {symbol} Recommending SL adjustment to {recommended_sl:.5f}")
            break

    return recommended_sl, take_profit
