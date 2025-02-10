# account_info.py
import MetaTrader5 as mt5
from logger_config import logger
import os
import json
from datetime import datetime
from config import HARD_MEMORY_DIR, ACCOUNT_INFO_FILE


def save_account_info(account_info):
    account_data = {
        "login": account_info.login,
        "balance": account_info.balance,
        "equity": account_info.equity,
        "margin": account_info.margin,
        "free_margin": account_info.margin_free,
        "leverage": account_info.leverage,
        "currency": account_info.currency,
        "trade_mode": account_info.trade_mode,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(ACCOUNT_INFO_FILE, "w", encoding='utf-8') as f:
            json.dump(account_data, f, indent=4)
        logger.info(f"OK! - Account info saved to {ACCOUNT_INFO_FILE}")
    except Exception as e:
        logger.error(f"Oh No! - Failed to save account info: {e}")

def get_account_info():
    """
    Retrieves and logs account information from MT5.
    """
    account_info = mt5.account_info()
    if account_info:
        logger.info("=== Account Info ===")
        logger.info(f" Login: {account_info.login}")
        logger.info(f" Balance: {account_info.balance} USD")
        logger.info(f" Equity: {account_info.equity} USD")
        logger.info(f" Margin: {account_info.margin} USD")
        logger.info(f" Free Margin: {account_info.margin_free} USD")
        logger.info(f" Leverage: {account_info.leverage}x")
        logger.info(f" Currency: {account_info.currency}")
        logger.info(f" Trade Mode: {account_info.trade_mode}")
        logger.info(f" Current Date Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        save_account_info(account_info)
    else:
        logger.error("Failed to retrieve account info.")
    return account_info


def check_account_limits():
    """Logs max allowed orders and positions from the broker."""
    """Logs max allowed orders and positions from the broker."""
    account_info = mt5.account_info()
    if account_info:
        logger.info(f"Trade Allowed: {account_info.trade_allowed}")
        logger.info(f"Trade Expert: {account_info.trade_expert}")
        
        # Check possible broker limits
        max_orders = getattr(account_info, "limit_orders", "Unknown")
        max_positions = getattr(account_info, "limit_positions", "Unknown")

        logger.info(f"Max Orders Allowed: {max_orders}")
        logger.info(f"Max Open Positions Allowed: {max_positions}")
    else:
        logger.error("Failed to retrieve account info from MT5.")


# Run standalone
if __name__ == "__main__":
    from connect import connect, disconnect
    if connect():
        get_account_info()
        disconnect()
# End of account_info.py
