import json
import os
from logger_config import logger

HARD_MEMORY_DIR = "hard_memory"
TRADE_LIMITS_FILE = os.path.join(HARD_MEMORY_DIR, "trade_limits.json")

def generate_default_trade_limits():
    """
    Generates a default trade limits configuration file if it does not exist.
    """
    default_limits = {
        "BTCUSD": {
            "MAX_LONG_SIZE": 0.05,
            "MAX_SHORT_SIZE": 0.05,
            "COOLDOWN_SECONDS": 300,
            "MAX_CAPITAL_ALLOCATION": 5000,
            "DEFAULT_LOT_SIZE": 0.01
        },
        "EURUSD": {
            "MAX_LONG_SIZE": 1.0,
            "MAX_SHORT_SIZE": 1.0,
            "COOLDOWN_SECONDS": 120,
            "MAX_CAPITAL_ALLOCATION": 10000,
            "DEFAULT_LOT_SIZE": 0.01
        }
    }
    
    os.makedirs(HARD_MEMORY_DIR, exist_ok=True)
    with open(TRADE_LIMITS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_limits, f, indent=4)
    logger.info(f"Default trade limits file created at {TRADE_LIMITS_FILE}")

def load_trade_limits():
    """
    Loads trade limits configuration from JSON, creating a default file if missing.
    """
    if not os.path.exists(TRADE_LIMITS_FILE):
        logger.warning(f"Trade limits file {TRADE_LIMITS_FILE} not found. Generating default.")
        generate_default_trade_limits()
    
    try:
        with open(TRADE_LIMITS_FILE, "r", encoding="utf-8") as f:
            limits = json.load(f)
        return limits
    except Exception as e:
        logger.error(f"Failed to load trade limits: {e}")
        return {}

if __name__ == "__main__":
    trade_limits = load_trade_limits()
    print(json.dumps(trade_limits, indent=4))
