# main.py
from src.connect import connect, disconnect
from src.account.account_info import get_account_info, check_account_limits
from src.positions.positions import get_positions
from src.history.history import get_trade_history
from src.symbols.symbols import get_symbols
from src.pending.orders import get_orders
from src.tick_listener import listen_to_ticks
from src.trader.trade import (open_trade,
                              close_trade,
                              abort_trade,
                              manage_trade,
                              simple_manage_trade)
from src.portfolio.total_positions import get_total_positions
from src.limits.limits import load_trade_limits
from src.logger_config import logger
from utils.config_watcher import ConfigWatcher
from random import randint
from typing import List, Dict, Any

override_watcher = ConfigWatcher("config/trade_override.json")
limits_watcher = ConfigWatcher("config/trade_limits_config.json")
indicator_config_watcher = ConfigWatcher("config/indicator_config.json")


def on_tick(ticks: List[Dict[str, Any]]) -> None:
    """
    Callback function to process tick events.
    """
    override_watcher.load_if_changed()
    limits_watcher.load_if_changed()
    indicator_config_watcher.load_if_changed()

    # Unpack the tick data for debugging
    logger.debug(
        f"[ON TICK 7715:00:00] :: "
        f"Tick dictionary: {ticks} "
    )

    for tick in ticks:
        tickid = randint(1000, 9999)
        tick['tickid'] = tickid
        logger.info(
            f"|~~|.AlgoOne.|~~~| -.-.- | tickid:{tickid} | Tick Event: {tick['symbol']} | "
            f"Bid: {tick['bid']} | Ask: {tick['ask']} | "
            f"Spread: {tick['spread']} | Time: {tick['time']}"
        )

        if not override_watcher.get("pause_open", False):
            # logger.debug(
            #         f"[ON TICK 7715:50] :: "
            #         f"Override watcher: {override_watcher.get('pause_open', False)}"
            # )
            # Note for self: this check positions as a dependency.
            # it's not a waste to call it here, but mandatory status check.
            get_total_positions(save=True, use_cache=False, report=True)
            open_trade(tick['symbol'])

        manage_trade(tick['symbol'])

        # Note for self: this check positions as a dependency
        # it's not a waste to call it here, but mandatory status check.
        get_total_positions(save=True, use_cache=False)
        abort_trade(tick['symbol'])
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

        limits_watcher.load_if_changed()
        symbols = limits_watcher.keys()
        if not symbols:
            logger.warning(
                "[WARNING 7715:00] :: "
                "No symbols found in limits watcher. Using default symbols."
            )
            from src.config import DEFAULT_SYMBOLS
            symbols = DEFAULT_SYMBOLS

        # Listen to ticks for all symbols, relax and let it roll.
        try:
            listen_to_ticks(forex_mode=False,
                            only_major_forex=False,
                            on_tick=on_tick, symbols=symbols,)
        except KeyboardInterrupt:
            logger.info("[MAIN EXCEPTION] :: Tick listener stopped by user.")
        finally:
            disconnect()
# End of Main Script
