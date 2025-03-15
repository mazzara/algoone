# src/tools/server_time.py
from datetime import datetime
import MetaTrader5 as mt5
from src.logger_config import logger


def get_server_time_from_tick(symbol):
    """Get the raw server time from the latest tick. Returns both timestamp and human-readable format."""

    tick_info = mt5.symbol_info_tick(symbol)

    if not tick_info:
        logger.warning(f"Failed to get tick data for {symbol}")
        return None, None  # Returning None to handle failure cases explicitly

    server_timestamp = tick_info.time  # Raw UNIX timestamp from MT5
    server_datetime = datetime.fromtimestamp(server_timestamp)  # Human-readable format

    logger.debug(f"Raw MT5 Tick Time (Server Timestamp): {server_timestamp} | Tick Time (Human-readable): {server_datetime}")

    return server_timestamp
