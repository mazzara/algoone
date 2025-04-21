# src/limits/cycle_limit.py

import time
import json
import os
from datetime import datetime
from src.config import TOTAL_POSITIONS_FILE
from src.trader.autotrade import get_autotrade_param
from src.logger_config import logger

def load_total_positions():
    if os.path.exists(TOTAL_POSITIONS_FILE):
        with open(TOTAL_POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_total_positions(data):
    try:
        with open(TOTAL_POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.debug("[CYCLE LIMIT] :: Saved total positions.")
    except Exception as e:
        logger.error(f"[CYCLE LIMIT] :: Failed to save total positions: {e}")

def register_cycle(symbol):
    """
    Register the start of a new liquidation cycle if symbol is fully flat.
    """
    positions = load_total_positions()
    symbol_data = positions.get(symbol, {})

    net = symbol_data.get('NET', {})
    if net.get('SIZE_SUM', 0) == 0 and net.get('POSITION_COUNT', 0) == 0:
        now = int(time.time())
        now_human = datetime.utcfromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[CYCLE LIMIT 7707:50] :: Symbol {symbol} fully liquidated. Registering cycle at {now_human} UTC")

        if 'CYCLE' not in symbol_data:
            symbol_data['CYCLE'] = {}
        symbol_data['CYCLE']['LAST_CYCLE_TIME'] = now
        positions[symbol] = symbol_data
        save_total_positions(positions)
    else:
        logger.debug(f"[CYCLE LIMIT 7707:60] :: Symbol {symbol} is not flat. No cycle registered.")

def check_cycle_clearance(symbol):
    """
    Check if the symbol is allowed to re-engage after liquidation cooldown.
    """
    positions = load_total_positions()
    symbol_data = positions.get(symbol, {})

    cycle_data = symbol_data.get('CYCLE', {})
    last_cycle_time = cycle_data.get('LAST_CYCLE_TIME', 0)
    now = int(time.time())

    liquidation_cooldown = get_autotrade_param(symbol, 'liquidation_cycle_seconds', default=900)

    if last_cycle_time == 0:
        logger.info(f"[CYCLE LIMIT 7707:70] :: No cycle recorded for {symbol}. Clearance granted.")
        return True  # No cycle registered → allow

    elapsed = now - last_cycle_time
    logger.info(f"[CYCLE LIMIT 7707:80] :: {symbol} elapsed since liquidation: {elapsed}s / required: {liquidation_cooldown}s")

    if elapsed >= liquidation_cooldown:
        logger.info(f"[CYCLE LIMIT 7707:85] :: {symbol} cleared liquidation cooldown.")
        return True
    else:
        logger.info(f"[CYCLE LIMIT 7707:87] :: {symbol} still in liquidation cooldown. BLOCKING.")
        return False

