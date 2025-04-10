# src/indicators/scalp_adx.py

import MetaTrader5 as mt5
import json
import os
from datetime import datetime
from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick
from src.indicators.adx_indicator import calculate_adx  # reusing your ADX calculation


def get_signal(symbol, **kwargs):
    """
    Get the signal for the ADX indicator.
    """
    return calculate_adx(symbol, **kwargs)


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
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")

        }
    }
    # write_to_hard_memory(data)



def calculate_sma(prices, period):
    """Calculate the simple moving average of the given prices."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_scalp_adx(symbol, period=14, threshold=20,
                        sma_short_period=9, sma_long_period=21):
    """
    Calculate a ScalpADX indicator:
    
    - Uses the ADX calculation (with DI+ and DI- computed in calculate_adx)
    - Computes two SMAs from closing prices: one short (default 9 bars) and one long (default 21 bars)
    - Decides a signal:
        • If ADX is below the threshold: "NO SIGNAL"
        • If ADX is above threshold:
            - "LONG" if DI+ > DI- and short SMA > long SMA
            - "SHORT" if DI- > DI+ and short SMA < long SMA
            - Otherwise, "HOLD"
    
    The result is passed to indicator_result so that it can be stored/ingested by other modules.
    """
    # Request enough bars for both ADX and SMA computations.
    # We use 200 bars for ADX (as in your existing function) and ensure at least sma_long_period bars.
    required_bars = max(200, sma_long_period)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, required_bars)
    if rates is None or len(rates) < sma_long_period:
        logger.error(f"Not enough data to calculate SMAs for {symbol}")
        return None

    # Calculate SMAs using closing prices
    closing_prices = [bar['close'] for bar in rates]
    short_sma = calculate_sma(closing_prices, sma_short_period)
    long_sma = calculate_sma(closing_prices, sma_long_period)
    if short_sma is None or long_sma is None:
        logger.error(f"Failed to compute SMAs for {symbol}")
        return None

    # Calculate ADX (which also computes DI+ and DI-) using your existing function
    adx_data = calculate_adx(symbol, period=period)
    if adx_data is None:
        logger.error(f"ADX calculation failed for {symbol}")
        return None

    adx_value = adx_data["values"]["adx"]
    plus_di = adx_data["values"]["plus_di"]
    minus_di = adx_data["values"]["minus_di"]

    # Decide on the trading signal
    if adx_value <= threshold:
        signal = "NO SIGNAL"
    else:
        if plus_di > minus_di and short_sma > long_sma:
            signal = "BUY"
        elif minus_di > plus_di and short_sma < long_sma:
            signal = "SELL"
        else:
            signal = "HOLD"

    # Log and persist the indicator result via the shared function.
    indicator_result(
        symbol,
        "ScalpADX",
        signal,
        adx_value,
        {"plus_di": plus_di, "minus_di": minus_di, "sma_short": short_sma, "sma_long": long_sma},
        {"period": period, "threshold": threshold,
         "sma_short_period": sma_short_period, "sma_long_period": sma_long_period}
    )

    # Return a result dictionary for further processing if needed.
    return {
        "indicator": "ScalpADX",
        "signal": signal,
        "values": {
            "adx": adx_value,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "sma_short": short_sma,
            "sma_long": long_sma
        }
    }
