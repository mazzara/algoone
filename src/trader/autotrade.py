# src/trader/autotrade.py 

import os
import json
from utils.config_watcher import ConfigWatcher

# Load autotrade_config.json
AUTOTRADE_CONFIG_FILE = os.path.join("config", "autotrade_config_settings.json")

autotrade_config_watcher = ConfigWatcher(AUTOTRADE_CONFIG_FILE)

def get_autotrade_param(symbol, key, default=None):
    """
    Retrive autotrade settings for a symbol, falling back to default.

    4 digit function signature: 3315
    """

    autotrade_config_watcher.load_if_changed()
    data = autotrade_config_watcher.config

    if not data:
        return default

    config = autotrade_config_watcher.config
    if not config:
        return default

    symbol_overrides = config.get("symbol_overrides", {})
    if symbol in symbol_overrides and key in symbol_overrides[symbol]:
        return symbol_overrides[symbol][key]

    return config.get("defaults", {}).get(key, default)
