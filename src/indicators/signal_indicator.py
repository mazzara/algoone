# src/indicators/signal_indicator.py 
import MetaTrader5 as mt5
import json
import importlib
import os
import time
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_CONFIG_FILE, INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def load_config():
    """Load indicator config file or create default."""
    if os.path.exists(INDICATOR_CONFIG_FILE):
        with open(INDICATOR_CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {
    "symbols": {
        "BTCUSD": {
            "indicators": ["ADX", "RSI"]
        },
        "EURUSD": {
            "indicators": ["ADX"]
        }
    },
    "indicators": [
        {
            "name": "ADX",
            "module": "src.indicators.adx_indicator",
            "function": "calculate_adx",
            "parameters": {
                "period": 14
            }
        },
        {
            "name": "RSI",
            "module": "src.indicators.rsi_indicator",
            "function": "calculate_rsi",
            "parameters": {
                "period": 14,
                "overbought": 55,
                "oversold": 50
            }
        }
    ]
    }

def get_indicator_signal(indicator_config, symbol):
    """Dinamically load indicator module and calls its signal function."""
    module_name = indicator_config.get('module')
    function_name = indicator_config.get('function')
    params = indicator_config.get('parameters', {})

    try:
        mod = importlib.import_module(module_name)
        func = getattr(mod, function_name)
        result = func(symbol, **params)
        logger.info(f"{indicator_config.get('name')} signal: {result}")
        return result
    except Exception as e:
        logger.error(f"Error calling {module_name}.{function_name} for {symbol}: {e}")
        return None


def dispatch_signals(symbol):
    """Loads config, calls each indicator and saves results. """

    logger.info(f"Dispatching called signals for {symbol}")

    config = load_config()
    global_indicators = config.get('indicators', [])
    symbol_config = config.get('symbols', {}).get(symbol, {})
    enabled_indicators_names = symbol_config.get('indicators', [])
    signals = {}

    for indicator in global_indicators:
        result = get_indicator_signal(indicator, symbol)
        if result is not None:
            signals[indicator.get('name', 'unknown')] = result
    return signals


def write_indicator_results(data):
    logger.info(f"Writing indicator results to: {INDICATOR_RESULTS_FILE}")
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator results updated: {data}")
        logger.info(f"Writing indicator results to: {os.path.abspath(INDICATOR_RESULTS_FILE)}")

    except Exception as e:
        logger.error(f"Failed to save indicator results: {e}")


def send_signals(symbol, signals):
    """Transmits the signals to the trader."""
    logger.info(f"Sending signals for {symbol}: {signals}")
    write_indicator_results(signals)


def main(symbol):
    signals = dispatch_signals(symbol)
    send_signals(symbol, signals)

if __name__ == '__main__':
    symbol = 'BTCUSD'
    main(symbol)


# End of signal_indicator.py

