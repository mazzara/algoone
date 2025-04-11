# symbols.py
import MetaTrader5 as mt5
import os
import json
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, SYMBOLS_ALLOWED

# Ensure the `hard_memory` directory exists
# HARD_MEMORY_DIR = "hard_memory"
# os.makedirs(HARD_MEMORY_DIR, exist_ok=True)

SYMBOLS_FILE = os.path.join(HARD_MEMORY_DIR, "symbols.json")

def save_symbols(symbols):
    """
    Saves detailed symbol information to a JSON file.
    """
    symbols_data = []

    for symbol in symbols:
        info = mt5.symbol_info(symbol.name)  # Retrieve additional details
        if info:
            symbols_data.append({
                "name": info.name,
                "description": info.description,
                "currency_base": info.currency_base,
                "currency_profit": info.currency_profit,
                "currency_margin": info.currency_margin,
                "digits": info.digits,
                "point": info.point,
                "spread": info.spread,
                "trade_mode": info.trade_mode,  # 0 = Disabled, 1 = Long & Short, 2 = Close Only
                "category": get_symbol_category(info),  # Determine category (Forex, Crypto, etc.)
                "contract_size": info.trade_contract_size,  # Contract size
                "volume_min": info.volume_min,  # Minimum trade volume
                "volume_max": info.volume_max,  # Maximum trade volume
                "volume_step": info.volume_step,  # Volume increment step
                "margin_initial": info.margin_initial,  # Required margin for a position
                "margin_maintenance": info.margin_maintenance,  # Maintenance margin
                "margin_hedged": info.margin_hedged  # Margin for hedged positions
            })
    file_path = os.path.join(HARD_MEMORY_DIR, "symbols.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(symbols_data, f, indent=4)
        logger.info(f"Saved {len(symbols_data)} symbols to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save symbols: {e}")

def get_symbol_category(symbol_info):
    """
    Determines the category of the symbol based on its attributes.
    """
    if "USD" in symbol_info.currency_base and "USD" in symbol_info.currency_profit:
        return "Forex"
    elif "BTC" in symbol_info.name or "ETH" in symbol_info.name:
        return "Crypto"
    elif "US30" in symbol_info.name or "NAS" in symbol_info.name or "SPX" in symbol_info.name:
        return "Indices"
    elif "OIL" in symbol_info.name or "GOLD" in symbol_info.name or "XAU" in symbol_info.name:
        return "Commodities"
    else:
        return "Stocks"

def get_symbols():
    """
    Retrieves all available symbols from MT5, categorizes them, and saves them.
    
    4 digit function signature: 0855
    """
    symbols = mt5.symbols_get()

    if symbols:
        logger.info(
            f"[INFO 0855] :: "
            f"Retrieved {len(symbols)} symbols from MetaTrader 5"
        )
        save_symbols(symbols)
    else:
        logger.warning(
            "[WARNING 0855] :: "
            "No symbols retrieved from MetaTrader 5"
        )
        save_symbols([])

    return symbols

# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        get_symbols()
        disconnect()

# End of symbols.py
