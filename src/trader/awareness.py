# ./src/awareness.py
import logging
from src.indicators.moving_average import get_sma

logger = logging.getLogger("AlgoOne")


def evaluate_profit_awareness(symbol, tick, atr, open_price, position_type, threshold_atr=1.0):
    """
    Evaluates if it's a good moment to book profit based on expansion and momentum fade.
    
    Params:
        symbol (str): Trading symbol
        tick (obj): MT5 tick data object
        atr (float): ATR value for the symbol
        open_price (float): Position entry price
        position_type (str): 'BUY' or 'SELL'
        threshold_atr (float): Expansion factor threshold

    Returns:
        bool: True if profit should be booked, False otherwise

    4 digit function signature: 1354
    """
    try:
        current_price = tick.bid if position_type == 'BUY' else tick.ask
        expansion = abs(current_price - open_price)
        expansion_factor = expansion / atr if atr else 0

        # More flexible fade threshold
        fade_buffer = atr * 0.1  # Allow a bit of margin

        # Get short-term SMA to check momentum fade
        sma_period = 3
        sma_value = get_sma(symbol, sma_period)

        in_profit = current_price > open_price if position_type == 'BUY' else current_price < open_price

        logger.debug(f"[AWARENESS 1354:45] {symbol} | in_profit: {in_profit} - Current Price: {current_price}, Open Price: {open_price}, ATR: {atr}, Expansion Factor: {expansion_factor:.2f}, SMA: {sma_value}")
        
        if sma_value is None:
            logger.warning(f"[AWARENESS 1354:46] Could not retrieve SMA for {symbol}")
            return False

        # Fade detection
        if position_type == 'BUY':
            momentum_fade = current_price < sma_value - fade_buffer
        else:  # SELL
            momentum_fade = current_price > sma_value + fade_buffer

        # Awareness condition
        if in_profit and expansion_factor > threshold_atr and momentum_fade:
            logger.info(f"[AWARENESS 1354:47] {symbol} profit awareness triggered: expansion={expansion_factor:.2f} ATR, fade={momentum_fade}")
            return True

    except Exception as e:
        logger.error(f"[AWARENESS 1354:48] Error evaluating awareness for {symbol}: {e}")

    return False
