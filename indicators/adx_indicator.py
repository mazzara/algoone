import MetaTrader5 as mt5
from logger_config import logger

def calculate_adx(symbol, period=14):
    """ 
    Calculate ADX - Average Directional Index
    Returns BUY if trend is strong, SELL if strong donw trend, otherwise None
    """

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, period)
    if rates is None:
        logger.error(f"Failed to retrieve rates for {symbol}")
        return None
    
    # Extract high low close
    high_prices = [bar['high'] for bar in rates]
    low_prices = [bar['low'] for bar in rates]
    close_prices = [bar['close'] for bar in rates]

    if len(high_prices) < period:
        logger.error(f"Not enough data for {symbol}")
        return None

    # Calculate directional movement
    plus_dm = [max(high_prices[i] - high_prices[i - 1], 0) if high_prices[i] - high_prices[i - 1] > low_prices[i - 1] - low_prices[i] else 0 for i in range(1, len(high_prices))]
    minus_dm = [max(low_prices[i - 1] - low_prices[i], 0) if low_prices[i - 1] - low_prices[i] > high_prices[i] - high_prices[i - 1] else 0 for i in range(1, len(high_prices))]
    
    plus_di = sum(plus_dm) / period
    minus_di = sum(minus_dm) / period
    
    adx = abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0
    
    logger.info(f"ADX for {symbol}: {adx:.2f} | +DI: {plus_di:.2f} | -DI: {minus_di:.2f}")

    if plus_di > minus_di and adx > 0.2:
        return "BUY"
    elif minus_di > plus_di and adx > 0.2:
        return "SELL"
    else:
        return None
