import MetaTrader5 as mt5
import time
import random
from logger_config import logger

# Store last tick data for comparison
last_ticks = {}

# Define major Forex symbols
FOREX_MAJORS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
FOREX_MAJORS = ['EURUSD',]

def get_forex_symbols(limit=5, only_major_forex=False):
    """
    Retrieves Forex symbols from MT5 and returns a limited selection.
    """
    symbols = mt5.symbols_get()
    forex_symbols = [s.name for s in symbols if "USD" in s.name or "EUR" in s.name or "GBP" in s.name]  # Basic Forex filter

    if only_major_forex:
        selected_symbols = [s for s in forex_symbols if s in FOREX_MAJORS]
        logger.info(f"Major Forex Mode: Listening to {len(selected_symbols)} major Forex pairs.")
    else:
        selected_symbols = random.sample(forex_symbols, min(limit, len(forex_symbols)))
        logger.info(f"Development Mode: Selected Forex Symbols: {selected_symbols}")

    if not selected_symbols:
        logger.error("No Forex symbols found.")
    return selected_symbols

def listen_to_ticks(sleep_time=0.1, forex_mode=False, only_major_forex=False):
    """
    Listens to market ticks for all symbols or selected Forex symbols.
    """
    global last_ticks

    if forex_mode:
        symbols = get_forex_symbols(5, only_major_forex=only_major_forex)  # Development mode: 5 random Forex symbols
    else:
        symbols = [s.name for s in mt5.symbols_get()]  # Production mode: all active symbols

    if not symbols:
        logger.error("No symbols available for listening.")
        return

    mode_text = "Major Forex Symbols" if only_major_forex else "Random 5 Forex Symbols" if forex_mode else "All Symbols"
    logger.info(f"Listening for ticks on {len(symbols)} ({mode_text})...")

    while True:
        tick_detected = False

        for symbol in symbols:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                last_bid, last_ask = last_ticks.get(symbol, (None, None))

                if last_bid != tick.bid or last_ask != tick.ask:
                    last_ticks[symbol] = (tick.bid, tick.ask)
                    logger.info(f"{symbol} | Bid: {tick.bid} | Ask: {tick.ask} | Spread: {tick.ask - tick.bid}")
                    tick_detected = True

            if not tick_detected:
                time.sleep(0.5)
            else:
                time.sleep(sleep_time)


if __name__ == "__main__":
    from connect import connect, disconnect 

    if connect():
        try:
            forex_mode = True
            only_major_forex = True
            listen_to_ticks(forex_mode=forex_mode, only_major_forex=True)
        except KeyboardInterrupt:
            logger.info("Tick listener stopped by user.")
        finally:
            disconnect()

# End of Listener



