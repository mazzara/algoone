# tick_listener.py
import MetaTrader5 as mt5
import time
import random
from typing import List
from src.logger_config import logger
from src.config import SYMBOLS_ALLOWED


# Store last tick data for comparison
last_ticks = {}

def get_forex_symbols(limit=5, only_major_forex=False):
    """
    Retrieves Forex symbols from MT5 and returns a limited selection.
    """
    symbols = mt5.symbols_get()
    if not symbols:
        logger.error("Failed to retrieve symbols from MT5.")
        return []

    forex_symbols = [s.name for s in symbols if "USD" in s.name or "EUR" in s.name or "GBP" in s.name]  # Basic Forex filter

    if only_major_forex:
        selected_symbols = [s for s in forex_symbols if s in SYMBOLS_ALLOWED]
        logger.info(f"Major Forex Mode: Listening to {len(selected_symbols)} major Forex pairs.")
        if not selected_symbols:
            logger.warning("No major forex pairs found. Using All available symbols instead.")
            selected_symbols = forex_symbols
    else:
        selected_symbols = random.sample(forex_symbols, min(limit, len(forex_symbols)))
        logger.info(f"Development Mode: Selected Forex Symbols: {selected_symbols}")

    if not selected_symbols:
        logger.error("No Forex symbols found.")
    return selected_symbols


def listen_to_ticks(sleep_time=0.1,
                    forex_mode=False,
                    only_major_forex=False,
                    on_tick=None,
                    symbols=None):
    """
    Listens to market ticks for all symbols or selected Forex symbols.
    """
    global last_ticks

    if symbols is None:
        if forex_mode:
            symbols = get_forex_symbols(200, only_major_forex=only_major_forex)  # Development mode: 5 random Forex symbols
        else:
            symbols = [s.name for s in mt5.symbols_get()]  # Production mode: all active symbols

    if not symbols:
        logger.error("No symbols available for listening.")
        return

    mode_text = (
        "Major Forex Symbols" if only_major_forex else
        "Random 5 Forex Symbols" if forex_mode else
        "Custom Symbol List" if symbols else
        "All Symbols"
    )
    logger.info(f"Listening for ticks on {len(symbols)} ({mode_text})...")

    while True:
        tick_detected = False
        tick_data = []

        for symbol in symbols:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                last_bid, last_ask = last_ticks.get(symbol, (None, None))

                # Inspect tick data for debugging
                logger.debug(f"[DEBUG 11749:00] Symbol: {symbol} | Tick Data: {tick}")

                if last_bid != tick.bid or last_ask != tick.ask:
                    last_ticks[symbol] = (tick.bid, tick.ask)
                    logger.info(f"{symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {tick.ask - tick.bid}")
                    tick_detected = True
                    tick_info = {
                        "symbol": symbol,
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "spread": tick.ask - tick.bid,
                        "time": tick.time
                    }
                    tick_data.append(tick_info)

        if tick_detected and on_tick and on_tick:
            on_tick(tick_data)

        time.sleep(sleep_time if tick_detected else 0.5)

def sample_on_tick(ticks):
    """
    Example callback function to process tick events.
    """
    for tick in ticks:
        logger.info(f"Tick Event: {tick['symbol']} | Bid: {tick['bid']} | Ask: {tick['ask']} | Spread: {tick['spread']} | Time: {tick['time']}")



if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        try:
            forex_mode = False
            only_major_forex = False
            listen_to_ticks(forex_mode=forex_mode, only_major_forex=False)
        except KeyboardInterrupt:
            logger.info("Tick listener stopped by user.")
        finally:
            disconnect()

# End of tick_listener.py



