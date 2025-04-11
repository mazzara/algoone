# src/positions/positions.py
import MetaTrader5 as mt5
from src.logger_config import logger
import os
import json
from datetime import datetime
import time
from src.config import HARD_MEMORY_DIR, POSITIONS_FILE
from src.tools.server_time import get_server_time_from_tick
from src.portfolio.position_state_tracker import process_all_positions


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
            # "time_open": datetime.fromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
            "time_open": datetime.utcfromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
            "time_raw": pos.time,
            "comment": pos.comment
        })

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
        # for pos in positions:
        #     # logger.info(f"Ticket: {pos.ticket} {pos.symbol} {('BUY' if pos.type == 0 else 'SELL')} {pos.volume} lots @ {pos.price_open}")
        #     pass

        save_positions(positions)
        logger.info(f"Total open positions saved: {len(positions)}")
    else:
        logger.info("No open positions found.")
        save_positions([])
    
    return positions


# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect
    if connect():
        get_positions()
        disconnect()


# End of positions.py
