# src/tools/server_time.py
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5
from src.logger_config import logger
import pytz

BROKER_TIMEZONE = pytz.timezone("Europe/Athens")

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



def parse_time(value):
    """Convert string timestamps to UNIX timestamps if needed."""
    if not value:
        return 0
    if isinstance(value, str):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            logger.warning(f"Invalid timestamp format: {value}")
            return 0
    return float(value) if value else 0



def get_server_time_from_tick_tz(symbol):
    """Get the current server time."""
    tick_info = mt5.symbol_info_tick(symbol)
    if not tick_info:
        logger.warning(f"Failed to get tick data for {symbol}")
        return datetime.utcnow().timestamp()

    server_time = tick_info.time  # This is a raw timestamp

    # Convert MT5 server time (broker time) to its actual broker time zone
    broker_dt = datetime.fromtimestamp(server_time, tz=BROKER_TIMEZONE)

    # Convert broker time to True UTC
    true_utc_dt = broker_dt.astimezone(timezone.utc)
    true_utc_timestamp = true_utc_dt.timestamp()

    # Get system's current true UTC time
    system_utc_dt = datetime.now(timezone.utc)
    system_utc_timestamp = system_utc_dt.timestamp()

    # Logging with clear distinctions
    logger.info(f"MT5 Server Time (Broker's Timezone): {broker_dt} | True UTC Server Time: {true_utc_dt}")
    logger.info(f"System UTC Time: {system_utc_dt} | System UTC Timestamp: {system_utc_timestamp}")

    logger.debug(f"MT5 Server Timestamp: {server_time} | True UTC Timestamp: {true_utc_timestamp} | System UTC Timestamp: {system_utc_timestamp}")

    return true_utc_timestamp

