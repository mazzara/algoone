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
    """Load indicator config file or create and save a default configuration."""
    if os.path.exists(INDICATOR_CONFIG_FILE):
        with open(INDICATOR_CONFIG_FILE, 'r') as file:
            return json.load(file)
    else:
        default_config = {
            "symbols": {
                "BTCUSD": {
                    "indicators": ["ADX", "RSI"]
                },
                "EURUSD": {
                    "indicators": ["ADX"]
                }
            },
            "position_manager_indicator": {
                "ATR": {
                    "period": 14
                }
            },
            "indicators": [
                {
                    "name": "ATR",
                    "module": "src.indicators.atr_indicator",
                    "function": "calculate_atr",
                    "parameters": {
                        "period": 14
                    }
                },
                {
                    "name": "ADX",
                    "module": "src.indicators.adx_indicator",
                    "function": "calculate_adx",
                    "parameters": {
                        "period": 14
                    }
                },
                {
                    "name": "ScalpADX",
                    "module": "src.indicators.scalp_adx",
                    "function": "calculate_scalp_adx",
                    "parameters": {
                        "period": 14,
                        "threshold": 20,
                        "sma_short_period": 9,
                        "sma_long_period": 21
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
        # Save the default config to the file
        with open(INDICATOR_CONFIG_FILE, 'w') as file:
            json.dump(default_config, file, indent=4)
        return default_config

def get_indicator_signal(indicator_config, symbol):
    """
    Dinamically load indicator module and calls its signal function.
    4 digit function signature: 1918
    """
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
        logger.error(f"[ERROR 1918] :: Error calling {module_name}.{function_name} for {symbol}: {e}")
        return None


def dispatch_position_manager_indicator(symbol, indicator_name):
    """
    Loads config, selects the indicator configured for position management, and runs it.
    
    The configuration should have a key "position_manager_indicator" that is an object
    mapping the indicator name (e.g., "ATR") to its parameters. This function finds
    the corresponding global indicator definition, merges its parameters with the
    position manager-specific overrides, and calls the indicator function.
    """
    config = load_config()

    # Retrieve position manager configuration.
    # Expected format: {"position_manager_indicator": { "ATR": { "period": 14 } } }
    pm_config = config.get("position_manager_indicator", {})
    if not pm_config:
        logger.error("No position manager indicator is configured in the config file.")
        return {}

    # For modularity, allow for a single position management indicator, regardless of its name.
    # (If you later support multiple, you could iterate over all keys.)
    indicator_name, pm_settings = list(pm_config.items())[0]

    # Find the matching indicator in the global indicators list.
    global_indicators = config.get("indicators", [])
    indicator_definition = next(
        (item for item in global_indicators if item.get("name") == indicator_name),
        None
    )
    if indicator_definition is None:
        logger.error(f"Position manager indicator '{indicator_name}' not found in global indicators.")
        return {}

    # Merge global parameters with position manager specific settings.
    merged_parameters = indicator_definition.get("parameters", {}).copy()
    merged_parameters.update(pm_settings)

    # Create a copy of the indicator definition with the merged parameters.
    pm_indicator_definition = indicator_definition.copy()
    pm_indicator_definition["parameters"] = merged_parameters

    # Call the indicator function using the merged parameters.
    result = get_indicator_signal(pm_indicator_definition, symbol)
    signals = {}
    if result is not None:
        signals[indicator_name] = result

    logger.debug(f"[DEBUG] :: Position manager indicator signal for {symbol}: {signals}")
    return signals


def dispatch_signals(symbol):
    """
    Loads config, calls each indicator and saves results.
    4 digit function signature: 1715
    """
    config = load_config()
    global_indicators = config.get('indicators', [])
    
    symbol_config = config.get('symbols', {}).get(symbol, {})
    allowed_indicator = symbol_config.get('indicators', [])

    signals = {}

    # If allowed indicators are specified, only run those indicators.
    if allowed_indicator:
        for indicator in global_indicators:
            if indicator.get('name') in allowed_indicator:
                result = get_indicator_signal(indicator, symbol)
                if result is not None:
                    signals[indicator.get('name', 'unknown')] = result
    else:
        # If no symbol-specific indicators are configured, run all global indicators.
        for indicator in global_indicators:
            result = get_indicator_signal(indicator, symbol)
            if result is not None:
                signals[indicator.get('name', 'unknown')] = result

    logger.debug(f"[DEBUG 1715] :: Dispatching called signals for {symbol} and indicators: {global_indicators}")
    logger.debug(f"[DEBUG 1715] :: Signals: {signals}")
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

