import MetaTrader5 as mt5
from logger_config import logger
import os
import json
from datetime import datetime
import time


# Ensure the `hard_memory` directory exists
HARD_MEMORY_DIR = "hard_memory"
os.makedirs(HARD_MEMORY_DIR, exist_ok=True)  # Cleaner directory check


def save_positions(positions):
    """
    Saves open positions to a JSON file.
    """
    positions_data = []

    data = {
        "timestamp": time.time(),
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
            "time_open": datetime.fromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M:%S"),
            "comment": pos.comment
        })

    data["positions"] = positions_data

    file_path = os.path.join(HARD_MEMORY_DIR, "positions.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"OK - Open positions saved to {file_path}")
    except Exception as e:
        logger.error(f"Oh No! - Failed to save positions: {e}")


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



