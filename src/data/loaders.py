# src/data/loaders.py
from MetaTrader5 import positions_get
from src.logger_config import logger

def fetch_mt5_positions():
    positions = positions_get()
    if positions:
        logger.info(f"[INFO] Fetched {len(positions)} positions from MT5.")
    else:
        logger.info("[INFO] No open positions found.")
    return positions or []
