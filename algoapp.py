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
        logger.info(
            f"|&|..|~~| -.-.- | Tick Event: {tick['symbol']} | "
            f"Bid: {tick['bid']} | Ask: {tick['ask']} | "
            f"Spread: {tick['spread']} | Time: {tick['time']}"
        )

        # Note for self: this check positions as a dependency.
        # it's not a waste to call it here, but mandatory status check.
        get_total_positions(save=True, use_cache=False, report=True)
        open_trade(tick['symbol'])

        manage_trade(tick['symbol'])

        # Note for self: this check positions as a dependency
        # it's not a waste to call it here, but mandatory status check.
        get_total_positions(save=True, use_cache=False)
        close_trade(tick['symbol'])


if __name__ == "__main__":
    # Ensure MT5 is connected
    if connect():
        logger.info("[MAIN INFO] :: MT5 Connection Established in Main Script")

        # Retrieve and log account info - check your trading environment, mate!
        load_trade_limits()
        check_account_limits()
        get_account_info()
        get_positions()
        get_orders()
        get_trade_history()
        get_symbols()

        # Process Positions - check your positions, mate!
        get_total_positions(save=True, use_cache=False)

        # Listen to ticks for all symbols, relax and let it roll.
        try:
            listen_to_ticks(forex_mode=False,
                            only_major_forex=False,
                            on_tick=on_tick)
        except KeyboardInterrupt:
            logger.info("[MAIN EXCEPTION] :: Tick listener stopped by user.")
        finally:
            disconnect()
# End of Main Script
