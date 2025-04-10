# src/indicators/atr_indicator.py

import MetaTrader5 as mt5
import json
import os
import random
from datetime import datetime
from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def get_signal(symbol, **kwargs):
    """
    Get the signal for the ATR indicator.
    """
    return calculate_atr(symbol, **kwargs)


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


def indicator_result(symbol, indicator, signal, value, calculations, parameters):
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
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    # Optionally, write the data to disk:
    # write_to_hard_memory(data)


def calculate_atr(symbol, period=14, low_threshold=None, high_threshold=None):
    """
    Calculate the Average True Range (ATR) indicator.
    
    The ATR is a volatility indicator that measures the range of price movement.
    It is calculated as the average of the True Range (TR) over a specified period.
    TR is defined as the maximum of:
        - (High - Low)
        - abs(High - Previous Close)
        - abs(Low - Previous Close)
    
    Parameters:
        symbol (str): The trading symbol.
        period (int): The number of bars over which to average TR (default is 14).
        low_threshold (float, optional): If provided and ATR is below this value, signal "LOW VOL".
        high_threshold (float, optional): If provided and ATR is above this value, signal "HIGH VOL".
    
    Returns:
        dict: A dictionary containing the indicator name, generated signal, and ATR value.
    """
    required_bars = period + 1  # one additional bar is needed to calculate the first TR
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, required_bars)
    if rates is None or len(rates) < required_bars:
        logger.error(f"Not enough data to calculate ATR for {symbol}")
        return None

    true_ranges = []
    # Compute the True Range for each bar (starting from index 1)
    for i in range(1, len(rates)):
        current = rates[i]
        previous = rates[i-1]
        high_low = current['high'] - current['low']
        high_prev_close = abs(current['high'] - previous['close'])
        low_prev_close = abs(current['low'] - previous['close'])
        tr = max(high_low, high_prev_close, low_prev_close)
        true_ranges.append(tr)
        logger.debug(f"Bar {i}: High={current['high']}, Low={current['low']}, Prev Close={previous['close']}, TR={tr}")

    # Calculate ATR as the simple average of the last `period` true range values
    atr_value = sum(true_ranges[-period:]) / period

    # Determine a trading signal based on optional thresholds
    if low_threshold is not None and atr_value < low_threshold:
        signal = "LOW VOL"
    elif high_threshold is not None and atr_value > high_threshold:
        signal = "HIGH VOL"
    else:
        signal = "NO SIGNAL"

    # Log the result and persist the indicator result using the shared function.
    indicator_result(
        symbol,
        "ATR",
        signal,
        atr_value,
        {"true_ranges": true_ranges},
        {"period": period, "low_threshold": low_threshold, "high_threshold": high_threshold}
    )

    logger.info(f"[INFO] :: ATR for {symbol}: {atr_value:.2f} | Signal: {signal}")

    # Return a result dictionary for further processing if needed.
    return {
        "indicator": "ATR",
        "signal": signal,
        "value": atr_value,
        "values": {
            "atr": atr_value,
            "true_ranges": true_ranges
        }
    }

# End of atr_indicator.py
