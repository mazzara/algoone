from connect import connect, disconnect
from account_info import get_account_info
from positions import get_positions
from history import get_trade_history
from symbols import get_symbols
from orders import get_orders
from tick_listener import listen_to_ticks
from logger_config import logger

if __name__ == "__main__":
    if connect():  # Ensure MT5 is connected
        logger.info("OK - MT5 Connection Established in Main Script")

        # Retrieve and log account info
        get_account_info()
        get_positions()
        get_orders()
        get_trade_history()
        get_symbols()

        # Listen to ticks for all symbols
        try:
            listen_to_ticks(forex_mode=True, only_major_forex=True)
        except KeyboardInterrupt:
            logger.info("Tick listener stopped by user.")
        finally:
            disconnect()

        # Keep the connection open for other operations
        input("Press Enter to disconnect...")
        disconnect()
    else:
        logger.error("Oh ho! Failed to connect to MT5. Exiting...")

