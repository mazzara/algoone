# orders.py
import MetaTrader5 as mt5
import os
import json
from datetime import datetime
from logger_config import logger
from config import HARD_MEMORY_DIR, ORDERS_FILE

# Ensure the `hard_memory` directory exists
# HARD_MEMORY_DIR = "hard_memory"
# os.makedirs(HARD_MEMORY_DIR, exist_ok=True)

def save_orders(orders):
    """
    Saves pending orders to a JSON file.
    """
    orders_data = []

    for order in orders:
        orders_data.append({
            "ticket": order.ticket,
            "symbol": order.symbol,
            "type": order.type,  # 2 = BUY_LIMIT, 3 = SELL_LIMIT, 4 = BUY_STOP, 5 = SELL_STOP
            "type_str": get_order_type(order.type),  # Convert type to human-readable
            "volume_current": order.volume_current,
            "price_open": order.price_open,
            "sl": order.sl,
            "tp": order.tp,
            "price_current": order.price_current,
            "time_setup": datetime.fromtimestamp(order.time_setup).strftime("%Y-%m-%d %H:%M:%S"),
            "expiration": datetime.fromtimestamp(order.time_expiration).strftime("%Y-%m-%d %H:%M:%S") if order.time_expiration else "GTC",
            "comment": order.comment
        })

    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders_data, f, indent=4)
        logger.info(f"Ok - Pending orders saved to {ORDERS_FILE}")
    except Exception as e:
        logger.error(f"Oh No! - Failed to save pending orders: {e}")


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

def get_orders():
    """
    Retrieves and logs all pending orders from MT5.
    """
    orders = mt5.orders_get()

    if orders:
        logger.info("=== Pending Orders ===")
        for order in orders:
            logger.info(f"Ticket: {order.ticket} {order.symbol} {get_order_type(order.type)} {order.volume_current} lots @ {order.price_open}")
        save_orders(orders)
    else:
        logger.info("No pending orders found.")
        save_orders([])

    return orders

# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        get_orders()
        disconnect()

# End of orders.py
