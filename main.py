# main.py
from connect import connect, disconnect
from account_info import get_account_info, check_account_limits
from positions import get_positions
from history import get_trade_history
from symbols import get_symbols
from orders import get_orders
from tick_listener import listen_to_ticks
from trade import open_trade, close_trade
from portfolio.total_positions import get_total_positions
from limits import load_trade_limits
from logger_config import logger
from config import SYMBOLS_ALLOWED, LOGGER_NAME


def on_tick(ticks):
    """
    Example callback function to process tick events.
    """
    for tick in ticks:
        logger.info(f"Tick Event: {tick['symbol']} | Bid: {tick['bid']} | Ask: {tick['ask']} | Spread: {tick['spread']} | Time: {tick['time']}")
        open_trade(tick['symbol'])
        get_total_positions() # Note for self: this also check positinos as a dependency.
        logger.info(f"Closing trade... Calling close_trade()")
        close_trade()


if __name__ == "__main__":
    if connect():  # Ensure MT5 is connected
        logger.info("OK - MT5 Connection Established in Main Script")

        # Retrieve and log account info
        load_trade_limits()
        check_account_limits()
        get_account_info()
        get_positions()
        get_orders()
        get_trade_history()
        get_symbols()

        # Process Positions
        get_total_positions()

        # Listen to ticks for all symbols
        try:
            listen_to_ticks(forex_mode=True,
                            only_major_forex=True,
                            on_tick=on_tick)
        except KeyboardInterrupt:
            logger.info("Tick listener stopped by user.")
        finally:
            disconnect()
# End of Main Script
