# src/trader/autotrade.py 

from algoapp import autotrade_config_watcher 

def get_autotrade_param(symbol, key, default=None):
    """
    Retrive autotrade settings for a symbol, falling back to default.

    4 digit function signature: 3315
    """

    config = autotrade_config_watcher.config
    if not config:
        return default

    symbol_overrides = config.get("symbol_overrides", {})
    if symbol in symbol_overrides and key in symbol_overrides[symbol]:
        return symbol_overrides[symbol][key]

    return config.get("defaults", {}).get(key, default)
