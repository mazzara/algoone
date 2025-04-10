# main.py
from src.connect import connect, disconnect
from src.account.account_info import get_account_info, check_account_limits
from src.positions.positions import get_positions
from src.history.history import get_trade_history
from src.symbols.symbols import get_symbols
from src.pending.orders import get_orders
from src.tick_listener import listen_to_ticks
from src.trader.trade import open_trade, close_trade, manage_trade
from src.portfolio.total_positions import get_total_positions
from src.limits.limits import load_trade_limits
from src.logger_config import logger


def on_tick(ticks):
    """
    Callback function to process tick events.
    """
    for tick in ticks:
        logger.info(f"|&|..|~~| -.-.- | Tick Event: {tick['symbol']} | Bid: {tick['bid']} | Ask: {tick['ask']} | Spread: {tick['spread']} | Time: {tick['time']}")

        # get_positions = get_total_positions(save=True, use_cache=False)
        # open_trade(tick['symbol'], get_positions=get_positions)
        # close_trade(tick['symbol'], get_positions=get_positions)

        get_total_positions(save=True, use_cache=False, report=True) # Note for self: this also check positinos as a dependency.
        open_trade(tick['symbol'])

        manage_trade(tick['symbol'])

        get_total_positions(save=True, use_cache=False) # Note for self: this also check positinos as a dependency.
        close_trade(tick['symbol'])


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
        get_total_positions(save=True, use_cache=False)

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
