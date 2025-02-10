# adx_indicator.py - ADX indicator implementation
import MetaTrader5 as mt5
from logger_config import logger
import json
import os
import time
from datetime import datetime
from config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE

# Define hard memory directory and file paths
# HARD_MEMORY_DIR = "hard_memory"
# HARD_MEMORY_FILE = os.path.join(HARD_MEMORY_DIR, "indicator_result.json")
# INDICATOR_RESULT = 'indicator_result'

#
# def ensure_directory_exists():
#     """Ensure the hard memory directory exists before writing files."""
#     os.makedirs(HARD_MEMORY_DIR, exist_ok=True)
#



def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    Treats it as an app state rather than appending.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")



def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    write_to_hard_memory(data)


def calculate_adx(symbol, period=14):
    """ 
    Calculate ADX - Average Directional Index
    Returns BUY if trend is strong, SELL if strong donw trend, otherwise None
    """

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, period)
    if rates is None:
        logger.error(f"Failed to retrieve rates for {symbol}")
        return None

    # Extract high low close
    high_prices = [bar['high'] for bar in rates]
    low_prices = [bar['low'] for bar in rates]
    close_prices = [bar['close'] for bar in rates]

    if len(high_prices) < period:
        logger.error(f"Not enough data for {symbol}")
        return None

    # Calculate directional movement
    plus_dm = [
        max(high_prices[i] - high_prices[i - 1], 0)
        if high_prices[i] - high_prices[i - 1] > low_prices[i - 1] - low_prices[i]
        else 0
        for i in range(1, len(high_prices))
    ]
    minus_dm = [
        max(low_prices[i - 1] - low_prices[i], 0)
        if low_prices[i - 1] - low_prices[i] > high_prices[i] - high_prices[i - 1]
        else 0
        for i in range(1, len(high_prices))
    ]

    plus_di = sum(plus_dm) / period
    minus_di = sum(minus_dm) / period

    adx = abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0

    logger.info(f"ADX for {symbol}: {adx:.2f} | +DI: {plus_di:.2f} | -DI: {minus_di:.2f}")

    if plus_di > minus_di and adx > 0.2:
        signal = "BUY"
    elif minus_di > plus_di and adx > 0.2:
        signal = "SELL"
    else:
        signal = "NONE"

    indicator_result(
            symbol,
            "ADX",
            signal,
            adx,
            {"period": period}, 
            {"plus_di": plus_di, "minus_di": minus_di}
        )
    return (signal, adx, plus_di, minus_di) if signal != "NONE" else None

# End of adx_indicator.py
