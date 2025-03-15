# src/indicators/rsi_indicator.@property
import MetaTrader5 as mt5
import json
import os
import time 
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def get_signal(symbol, **kwargs):
    """
    Get the signal for the RSI indicator.
    """
    return calculate_rsi(symbol, **kwargs)


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


def calculate_rsi(symbol, period=14, overbought=70, oversold=30):
    """Calculate RSI (Relative Strength Index) using Welles Wilder's method."""
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, period + 1)
    if rates is None or len(rates) < period + 1:
        logger.error(f"Failed to get rates for {symbol}")
        return None
    
    closes = [rate['close'] for rate in rates]

    deltas = [closes[i+1] - closes[i] for i in range(len(closes) - 1)]

    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    avg_gain = sum(gains) / period 
    avg_loss = sum(losses) / period 

    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    if rsi < oversold:
        signal = "BUY"
    elif rsi > overbought:
        signal = "SELL"
    else:
        signal = "CLOSE"

    logger.info(f"Indicator {symbol}: RSI: {rsi:.2f}")
    logger.info(f"Signal rsi_indicator: {signal} | RSI: {rsi:.2f}")

    if signal == 'NONE':
        return None

    return {
            "indicator": "RSI",
            "signal": signal,
            "value": {
                "rsi": rsi
            },
    }


# end of rsi_indicator.py
