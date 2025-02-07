import MetaTrader5 as mt5
import os
import json
from datetime import datetime, timedelta
from logger_config import logger

# Ensure the `hard_memory` directory exists
HARD_MEMORY_DIR = "hard_memory"
os.makedirs(HARD_MEMORY_DIR, exist_ok=True)

def save_history(history):
    """
    Saves closed trades (history) to a JSON file.
    """
    history_data = []

    for deal in history:
        history_data.append({
            "ticket": deal.ticket,
            "order": deal.order,
            "symbol": deal.symbol,
            "type": get_order_type(deal.type),  # Convert type to human-readable
            "volume": deal.volume,
            "price": deal.price,
            "profit": deal.profit,
            "commission": deal.commission,
            "swap": deal.swap,
            "time_setup": datetime.fromtimestamp(deal.time).strftime("%Y-%m-%d %H:%M:%S"),
            "comment": deal.comment
        })

    file_path = os.path.join(HARD_MEMORY_DIR, "history.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4)
        logger.info(f"Trade history saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save trade history: {e}")

def get_order_type(order_type):
    """
    Converts MT5 order type to human-readable string.
    """
    order_types = {
        0: "BUY",
        1: "SELL",
        2: "BUY_LIMIT",
        3: "SELL_LIMIT",
        4: "BUY_STOP",
        5: "SELL_STOP",
        6: "BUY_STOP_LIMIT",
        7: "SELL_STOP_LIMIT"
    }
    return order_types.get(order_type, "UNKNOWN")

def get_trade_history(days=30):
    """
    Retrieves and logs all closed trades within the last 'days' days from MT5.
    """
    date_from = datetime.now() - timedelta(days=days)
    date_to = datetime.now()

    history = mt5.history_deals_get(date_from, date_to)

    if history:
        logger.info(f"=== Trade History (Last {days} Days) ===")
        for deal in history:
            logger.info(f"Ticket: {deal.ticket}, {deal.symbol}, {get_order_type(deal.type)} {deal.volume} lots @ {deal.price} Profit: {deal.profit}")
        save_history(history)
    else:
        logger.info("No closed trades found.")
        save_history([])

    return history

# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        get_trade_history()
        disconnect()

