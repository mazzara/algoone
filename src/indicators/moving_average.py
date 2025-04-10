# ./src/indicators/moving_average.py
import MetaTrader5 as mt5
# import pandas as pd
import logging

logger = logging.getLogger("AlgoOne")


def get_sma(symbol, period=3, timeframe=mt5.TIMEFRAME_M1):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period)
    if rates is None or len(rates) < period:
        return None
    closes = [rate['close'] for rate in rates]
    return sum(closes) / len(closes)


# THIS PROPOSED VERSION USES PANDAS
# def get_sma(symbol, period=3, timeframe=mt5.TIMEFRAME_M1):
#     """
#     Calculate simple moving average (SMA) for a symbol over the given period and timeframe.
#
#     Args:
#         symbol (str): Trading symbol
#         period (int): Number of periods for SMA
#         timeframe (int): MT5 timeframe (e.g., mt5.TIMEFRAME_M1)
#
#     Returns:
#         float or None: SMA value or None if unavailable
#
#     4 digit function signature: 1406
#     """
#     try:
#         rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period)
#         if rates is None or len(rates) < period:
#             logger.warning(f"[SMA 1406] Not enough data to calculate SMA({period}) for {symbol}")
#             return None
#
#         df = pd.DataFrame(rates)
#         sma = df['close'].mean()
#         return sma
#
#     except Exception as e:
#         logger.error(f"[SMA 1406] Error calculating SMA({period}) for {symbol}: {e}")
#         return None
