# src/positions/positions.py
import MetaTrader5 as mt5
from src.logger_config import logger
import os
import json
from datetime import datetime
import time
from typing import List, Dict
from src.config import HARD_MEMORY_DIR, POSITIONS_FILE, BROKER_SYMBOLS
from src.tools.server_time import get_server_time_from_tick
from src.portfolio.position_state_tracker import process_all_positions


def get_symbols_config():
    # global _SYMBOLS_CONFIG_CACHE
    # if _SYMBOLS_CONFIG_CACHE is not None:
    #     return _SYMBOLS_CONFIG_CACHE

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


# Deprecated
def load_positions(symbol):
    """Retrive open positions for a symbol."""
    from src.portfolio.total_positions import get_total_positions
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


# def load_positions(symbol):
#     """Retrieve open positions for a symbol from cached total_positions.json"""
#     from src.portfolio.total_positions import load_cached_positions
#     positions = load_cached_positions()
#     logger.info(f"[INFO 1712] :: Loaded cached positions for limit check: {positions}")
#
#     position_data = positions.get(symbol, {})
#     long_data = position_data.get('LONG', {})
#     short_data = position_data.get('SHORT', {})
#
#     return {
#         "current_long_size": long_data.get('SIZE_SUM', 0) or 0,
#         "current_short_size": short_data.get('SIZE_SUM', 0) or 0,
#         "long_data": long_data,
#         "short_data": short_data,
#     }



def calculate_individual_risk(pos: dict, contract_size: float = 1.0) -> float:
    """
    Calculate the stop-loss risk for a single position.

    Args:
        pos (dict): A position dictionary with keys: 'type', 'price_open', 'sl', 'volume'

    Returns:
        float: Potential loss if SL is hit, 0.0 if invalid or trailing stop in profit
    """
    volume = pos.get("volume", 0)
    price_open = pos.get("price_open", 0)
    stop_loss = pos.get("sl", None)
    pos_type = pos.get("type")

    if stop_loss is None or stop_loss <= 0:
        return 0.0  # No SL or invalid

    if pos_type == "BUY":
        loss = (price_open - stop_loss) * volume * contract_size
    elif pos_type == "SELL":
        loss = (stop_loss - price_open) * volume * contract_size
    else:
        return 0.0

    return round(loss, 2) if loss > 0 else 0.0


def enrich_positions_with_risk(positions: list) -> list:
    """
    Adds a 'risk_at_sl' field to each position in the list.

    Args:
        positions (list): List of position dicts

    Returns:
        list: The same list with enriched 'risk_at_sl' per item
    """

    for pos in positions:
        symbol = pos.get("symbol")
        symbol_config = get_symbol_config(symbol)
        contract_size = symbol_config.get("contract_size", 1.0) if symbol_config else 1.0
        pos["risk_at_sl"] = calculate_individual_risk(pos, contract_size)
    return positions



def update_last_closed_timestamps(prev_positions: list, current_positions: list, total_summary: dict) -> dict:
    """
    Compares old and new positions to identify which ones were closed,
    and updates total_summary with LAST_CLOSED_TIME[_RAW] per symbol and side.
    """
    # Map current positions by ticket
    current_tickets = {p["ticket"] for p in current_positions}

    # Map previous positions by ticket
    prev_map = {p["ticket"]: p for p in prev_positions}
    
    # Detect closed positions (in prev but not in current)
    closed_tickets = [t for t in prev_map if t not in current_tickets]
    if not closed_tickets:
        return total_summary  # Nothing to do

    now = datetime.now()
    now_ts = now.timestamp()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    for ticket in closed_tickets:
        pos = prev_map[ticket]
        symbol = pos["symbol"]
        side = "LONG" if pos["type"] == "BUY" else "SHORT"

        if symbol in total_summary and side in total_summary[symbol]:
            total_summary[symbol][side]["LAST_CLOSED_TIME"] = now_str
            total_summary[symbol][side]["LAST_CLOSED_TIME_RAW"] = now_ts

    return total_summary



def save_positions(positions):
    """
    Saves open positions to a JSON file.

    4 digit function signature: 6737.
    """
    positions_data = []

    data = {
        "my_timestamp": time.time(),
        "my_local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": []
    }

    for pos in positions:
        if isinstance(pos, dict):
            positions_data.append(pos)
        else:
            positions_data.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": pos.volume,
                "price_open": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "price_current": pos.price_current,
                "profit": pos.profit,
                "swap": pos.swap,
                "magic": pos.magic,
                "time_open": datetime.utcfromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
                "time_raw": pos.time,
                "comment": pos.comment
            })
    positions_data = enrich_positions_with_risk(positions_data)

    # Resolving in-memory traking vs. stateless update issue.
    # Load previously saved state if available
    existing_data = {}
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception as e:
            logger.warning(f"[WARN 6737] :: Failed to load existing position memory: {e}")

    # Create a mapping by ticket for fast lookup
    previous_map = {p['ticket']: p for p in existing_data.get("positions", [])}

    logger.debug(
        f"[Save Position 6737:10] :: Previous positions: {previous_map}"
    )

    # Merge in previous memory
    for pos in positions_data:
        prev = previous_map.get(pos["ticket"])
        if prev:
            pos["profit_chain"] = prev.get("profit_chain", [])
            pos["peak_profit"] = prev.get("peak_profit", 0.0)
        logger.debug(
            f"[Save Position 6737:20] :: Merged position: {pos}"
        )

    data["positions"] = process_all_positions(positions_data)

    try:
        with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"OK - Open positions saved to {POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"[Save Positions 6737:40] :: "
                     f"Oh No! - Failed to save positions: {e}"
                     )


def get_positions():
    """
    Retrieves and logs all open positions from MT5.
    """
    positions = mt5.positions_get()

    if positions:
        logger.info("=== Open Positions ===")

        save_positions(positions)
        logger.info(f"Total open positions saved: {len(positions)}")
    else:
        logger.info("No open positions found.")
        save_positions([])
    
    return positions


def return_positions():
    """
    Retrieves and logs all open positions from MT5.
    """
    positions = mt5.positions_get()

    if positions:
        logger.info("=== Open Positions ===")

        # save_positions(positions)
        logger.info(f"Total open positions saved: {len(positions)}")
    else:
        logger.info("No open positions found.")
        # save_positions([])
    
    return [
    {
        "ticket": pos.ticket,
        "symbol": pos.symbol,
        "type": "BUY" if pos.type == 0 else "SELL",
        "volume": pos.volume,
        "price_open": pos.price_open,
        "sl": pos.sl,
        "tp": pos.tp,
        "price_current": pos.price_current,
        "profit": pos.profit,
        "swap": pos.swap,
        "magic": pos.magic,
        "time_open": datetime.utcfromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
        "time_raw": pos.time,
        "comment": pos.comment,
    }
    for pos in positions
]


# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect
    if connect():
        get_positions()
        disconnect()


# End of positions.py
