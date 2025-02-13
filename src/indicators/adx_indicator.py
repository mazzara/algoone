# adx_indicator.py - ADX indicator implementation
import MetaTrader5 as mt5
import json
import os
import time
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE


def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
    Treats it as an app state rather than appending.
    """
    try:
        with open(INDICATOR_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Indicator result updated in {INDICATOR_RESULTS_FILE}: {data}")
    except Exception as e:
        logger.error(f"Failed to write indicator result to {INDICATOR_RESULTS_FILE}: {e}")



def indicator_result(symbol, indicator, signal, value,
                     calculations, parameters):
    """
    Write indicator result to hard memory.
    """
    data = {
        "indicator_result": {
            "symbol": symbol,
            "indicator": indicator,
            "signal": signal,
            "value": value,
            "parameters": parameters,
            "calculations": calculations,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    write_to_hard_memory(data)



def calculate_adx(symbol, period=14):
    """
    Calculate ADX (Average Directional Index) using Welles Wilder's method,
    with debug logs of intermediate calculations.
    """

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 200)
    if rates is None or len(rates) < period + 1:
        logger.error(f"Not enough data for {symbol}")
        return None

    #
    # -- Debug Print: Last few bars (time, O, H, L, C)
    #
    logger.debug(f"--- {symbol} RATES (LAST FEW) ---")
    for i in range(max(0, len(rates)-5), len(rates)):
        bar_time = datetime.utcfromtimestamp(rates[i]['time']).strftime('%Y-%m-%d %H:%M:%S')
        logger.debug(
            f"i={i}, time={bar_time}, O={rates[i]['open']}, "
            f"H={rates[i]['high']}, L={rates[i]['low']}, C={rates[i]['close']}"
        )

    def wilder_smooth(values, w_period, first_is_sum=True):
        """
        Wilder smoothing for arrays (TR, +DM, -DM, or DX).
        first_is_sum=True => initial seed = sum(...)
        first_is_sum=False => initial seed = average(...)
        """
        length = len(values)
        sm = [0.0] * length
        if length < w_period:
            return sm

        block_sum = sum(values[0:w_period])
        if first_is_sum:
            # used by TR, +DM, -DM
            sm[w_period - 1] = block_sum
        else:
            # used by DX => ADX
            sm[w_period - 1] = block_sum / w_period

        for i in range(w_period, length):
            sm[i] = sm[i-1] - (sm[i-1] / w_period) + (values[i] / w_period)
            # sm[i] = ( (w_period - 1) / w_period ) * sm[i-1] + (1.0 / w_period) * values[i]
        return sm

    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    # Build TR, +DM, -DM for each bar (except the very first)
    for i in range(1, len(rates)):
        curr = rates[i]
        prev = rates[i - 1]

        high_low   = curr['high'] - curr['low']
        high_close = abs(curr['high'] - prev['close'])
        low_close  = abs(curr['low'] - prev['close'])
        tr = max(high_low, high_close, low_close)
        tr_list.append(tr)

        up_move   = curr['high'] - prev['high']
        down_move = prev['low'] - curr['low']

        if up_move > down_move and up_move > 0:
            plus_dm_list.append(up_move)
        else:
            plus_dm_list.append(0.0)

        if down_move > up_move and down_move > 0:
            minus_dm_list.append(down_move)
        else:
            minus_dm_list.append(0.0)

    # Debug: Show the last few raw TR, +DM, -DM
    logger.debug(f"--- RAW TR/+DM/-DM (LAST FEW) ---")
    for i in range(max(0, len(tr_list)-5), len(tr_list)):
        logger.debug(
            f"i={i}, TR={tr_list[i]:.5f}, +DM={plus_dm_list[i]:.5f}, -DM={minus_dm_list[i]:.5f}"
        )

    # Wilder-smooth TR, +DM, -DM
    tr_smoothed      = wilder_smooth(tr_list,      period, first_is_sum=True)
    plus_dm_smoothed = wilder_smooth(plus_dm_list, period, first_is_sum=True)
    minus_dm_smoothed= wilder_smooth(minus_dm_list,period, first_is_sum=True)

    length = len(tr_smoothed)
    if length < period:
        logger.error(f"Not enough data AFTER smoothing for {symbol}")
        return None

    # Debug: Show the last few smoothed TR/+DM/-DM
    logger.debug(f"--- SMOOTHED TR/+DM/-DM (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(
            f"i={i}, TR_s={tr_smoothed[i]:.5f}, +DM_s={plus_dm_smoothed[i]:.5f}, "
            f"-DM_s={minus_dm_smoothed[i]:.5f}"
        )

    # Compute +DI, -DI each bar
    plus_di_list  = [0.0] * length
    minus_di_list = [0.0] * length

    for i in range(length):
        tr_val = tr_smoothed[i]
        if tr_val != 0.0:
            plus_di_list[i]  = 100.0 * (plus_dm_smoothed[i] / tr_val)
            minus_di_list[i] = 100.0 * (minus_dm_smoothed[i] / tr_val)

    # Debug: Show last few +DI / -DI
    logger.debug(f"--- +DI/-DI (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(
            f"i={i}, +DI={plus_di_list[i]:.5f}, -DI={minus_di_list[i]:.5f}"
        )

    # Compute DX each bar
    dx_list = [0.0] * length
    for i in range(length):
        pd = plus_di_list[i]
        md = minus_di_list[i]
        denom = pd + md
        if denom != 0.0:
            dx_list[i] = 100.0 * abs(pd - md) / denom
        else:
            dx_list[i] = 0.0

    # Debug: Show last few raw DX
    logger.debug(f"--- DX (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(f"i={i}, DX={dx_list[i]:.5f}")

    # Wilder-smooth DX -> ADX (avg seed)
    adx_smoothed = wilder_smooth(dx_list, period, first_is_sum=False)

    # Debug: Show last few ADX
    logger.debug(f"--- ADX SMOOTHED (LAST FEW) ---")
    for i in range(max(0, length-5), length):
        logger.debug(f"i={i}, ADX={adx_smoothed[i]:.5f}")

    # Take the last bar's ADX, +DI, -DI
    adx_current     = adx_smoothed[-1]
    plus_di_current = plus_di_list[-1]
    minus_di_current= minus_di_list[-1]

    logger.info(
        f"Indicator {symbol}: "
        f"ADX: {adx_current:.2f} | +DI: {plus_di_current:.2f} | -DI: {minus_di_current:.2f}"
    )

    # Decide signal
    if plus_di_current > minus_di_current and adx_current >= 30:
        signal = "BUY"
    elif minus_di_current > plus_di_current and adx_current >= 30:
        signal = "SELL"
    elif adx_current < 30:
        signal = "CLOSE"
    else:
        signal = "NONE"

    logger.info(
        f"Signal adx_indicator: {signal} | "
        f"ADX: {adx_current:.2f} | +DI: {plus_di_current:.2f} | -DI: {minus_di_current:.2f}"
    )

    indicator_result(
        symbol,
        "ADX",
        signal,
        adx_current,
        {"period": period},
        {"plus_di": plus_di_current, "minus_di": minus_di_current}
    )

    return (signal, adx_current, plus_di_current, minus_di_current) if signal != "NONE" else None






# -- Previous calculation implementation -- #
# def wilder_smooth(values, period, first_is_sum=True):
#     """
#     Applies Wilder's smoothing (like an EMA with alpha=1/period).
#     If first_is_sum=True, the first 'smoothed' value at index period-1 
#     is the sum of the first 'period' raw items (for TR, +DM, -DM).
#     If first_is_sum=False, the first smoothed value is the average 
#     of the first 'period' items (for DX->ADX).
#     """
#     length = len(values)
#     smoothed = [0.0] * length
#     if length < period:
#         return smoothed  # not enough data
#
#     block_sum = sum(values[0:period])
#     if first_is_sum:
#         # used by TR, +DM, -DM
#         smoothed[period-1] = block_sum
#     else:
#         # used by DX => ADX
#         smoothed[period-1] = block_sum / period
#
#     for i in range(period, length):
#         smoothed[i] = smoothed[i-1] - (smoothed[i-1] / period) + values[i]
#
#     return smoothed
#
# def calculate_adx(symbol, period=14):
#     """
#     ADX calculation matching Wilder's approach & typical MT4/5 iADX, 
#     but returning a near real-time (intrabar) read.
#     """
#     # 1) Fetch enough bars
#     rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
#     if rates is None or len(rates) < period + 1:
#         logger.error(f"Not enough data for {symbol}")
#         return None
#
#     # 2) Compute per-bar TR, +DM, -DM
#     tr_list = []
#     plus_dm_list = []
#     minus_dm_list = []
#
#     for i in range(1, len(rates)):
#         curr = rates[i]
#         prev = rates[i-1]
#
#         high_low   = curr['high'] - curr['low']
#         high_close = abs(curr['high'] - prev['close'])
#         low_close  = abs(curr['low'] - prev['close'])
#
#         tr = max(high_low, high_close, low_close)
#         tr_list.append(tr)
#
#         up_move   = curr['high'] - prev['high']
#         down_move = prev['low'] - curr['low']
#
#         if up_move > down_move and up_move > 0:
#             plus_dm_list.append(up_move)
#         else:
#             plus_dm_list.append(0.0)
#
#         if down_move > up_move and down_move > 0:
#             minus_dm_list.append(down_move)
#         else:
#             minus_dm_list.append(0.0)
#
#     # 3) Wilder-smooth TR, +DM, -DM (first_is_sum=True)
#     tr_smoothed      = wilder_smooth(tr_list,      period, True)
#     plus_dm_smoothed = wilder_smooth(plus_dm_list, period, True)
#     minus_dm_smoothed= wilder_smooth(minus_dm_list,period, True)
#
#     length = len(tr_smoothed)
#     if length < period:
#         logger.error(f"Not enough data AFTER smoothing for {symbol}")
#         return None
#
#     # 4) Compute +DI, -DI for each bar
#     plus_di_list  = [0.0]*length
#     minus_di_list = [0.0]*length
#
#     for i in range(length):
#         tr_val = tr_smoothed[i]
#         if tr_val != 0:
#             plus_di_list[i]  = 100.0 * (plus_dm_smoothed[i]  / tr_val)
#             minus_di_list[i] = 100.0 * (minus_dm_smoothed[i] / tr_val)
#
#     # 5) Compute DX for each bar
#     dx_list = [0.0]*length
#     for i in range(length):
#         pd = plus_di_list[i]
#         md = minus_di_list[i]
#         denom = pd + md
#         if denom != 0:
#             dx_list[i] = 100.0 * abs(pd - md) / denom
#         else:
#             dx_list[i] = 0.0
#
#     # 6) Wilder-smooth the DX to get ADX (first_is_sum=False => average seed)
#     adx_smoothed = wilder_smooth(dx_list, period, first_is_sum=False)
#
#     # Final "current" values (last bar)
#     adx_current     = adx_smoothed[-1]
#     plus_di_current = plus_di_list[-1]
#     minus_di_current= minus_di_list[-1]
#
#     logger.info(
#         f"Indicator {symbol}: "
#         f"ADX: {adx_current:.2f} | "
#         f"+DI: {plus_di_current:.2f} | "
#         f"-DI: {minus_di_current:.2f}"
#     )
#
#     # 7) Determine your signal
#     if plus_di_current > minus_di_current and adx_current >= 50:
#         signal = "BUY"
#     elif minus_di_current > plus_di_current and adx_current >= 50:
#         signal = "SELL"
#     elif adx_current < 50:
#         signal = "CLOSE"
#     else:
#         signal = "NONE"
#
#     # Log via your existing system
#     indicator_result(
#         symbol,
#         "ADX",
#         signal,
#         adx_current,
#         {"period": period},
#         {"plus_di": plus_di_current, "minus_di": minus_di_current}
#     )
#
#     return (signal, adx_current, plus_di_current, minus_di_current) if signal != "NONE" else None
#
#
# -- Previous calculation implementation -- #
# def calculate_adx(symbol, period=14):
#     """ 
#     Calculate ADX - Average Directional Index using a conventional approach.
#     
#     The calculation steps are:
#       1. Fetch period+1 bars to allow computation of previous-close based values.
#       2. Compute True Range (TR) for each bar:
#              TR = max(high - low, abs(high - previous close), abs(low - previous close))
#       3. Compute directional movements:
#              +DM = (current high - previous high) if it's larger than (previous low - current low) and > 0, else 0.
#              -DM = (previous low - current low) if it's larger than (current high - previous high) and > 0, else 0.
#       4. Compute the Average True Range (ATR) as the average of TR over the period.
#       5. Compute the +DI and -DI:
#              +DI = 100 * (sum(+DM) / ATR)
#              -DI = 100 * (sum(-DM) / ATR)
#       6. Compute the directional index (DX):
#              DX = 100 * abs(+DI - -DI) / (+DI + -DI)
#       
#     For simplicity in this single-period snapshot, we use DX as the ADX.
#     
#     Signal rules:
#       - If +DI > -DI and ADX >= 50: signal "BUY"
#       - If -DI > +DI and ADX >= 50: signal "SELL"
#       - If ADX < 50: signal "CLOSE"
#     
#     The execution routines will only open positions on BUY/SELL signals,
#     and will act on CLOSE signals only if positions are profitable.    
#     """
#
#     if not symbol:
#         logger.error("calculate_adx called with invalid symbol: None")
#         return None
#
#     rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, period)
#     if rates is None:
#         logger.error(f"Failed to retrieve rates for {symbol}")
#         return None
#
#     # Extract high low close
#     high_prices = [bar['high'] for bar in rates]
#     low_prices = [bar['low'] for bar in rates]
#     close_prices = [bar['close'] for bar in rates]
#
#     if len(high_prices) < period:
#         logger.error(f"Not enough data for {symbol}")
#         return None
#
#     # Calculate directional movement
#     plus_dm = [
#         max(high_prices[i] - high_prices[i - 1], 0)
#         if high_prices[i] - high_prices[i - 1] > low_prices[i - 1] - low_prices[i]
#         else 0
#         for i in range(1, len(high_prices))
#     ]
#     minus_dm = [
#         max(low_prices[i - 1] - low_prices[i], 0)
#         if low_prices[i - 1] - low_prices[i] > high_prices[i] - high_prices[i - 1]
#         else 0
#         for i in range(1, len(high_prices))
#     ]
#
#     # plus_di = sum(plus_dm) / period
#     # minus_di = sum(minus_dm) / period
#
#     plus_di = (sum(plus_dm) / period) / sum(high_prices) * 100
#     minus_di = (sum(minus_dm) / period) / sum(low_prices) * 100
#
#     epsilon = 1e-10
#     adx = abs(plus_di - minus_di) / (plus_di + minus_di + epsilon)
#
#     # adx = abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0
#
#     logger.info(f"ADX for {symbol}: {adx:.2f} | +DI: {plus_di:.2f} | -DI: {minus_di:.2f}")
#
#     # ADX signal rule - a more complex rule to evaluate close profits.
#     # adx > 0.4 and plus_di > minus_di = BUY | adx > 0.2 and minus_di > plus_di = SELL
#     # adx > 0.2 and <= 0.4 to evaluate close profits | adx < 0.2 = NONE
#
#     if plus_di > minus_di and adx >= 0.5:
#         signal = "BUY"
#     elif minus_di > plus_di and adx >= 0.5:
#         signal = "SELL"
#     elif adx < 0.5:
#         signal = "CLOSE"
#     else:
#         signal = "NONE"
#     
#     # SIMPLEST SIGNAL RULE
#     # if plus_di > minus_di and adx > 0.2:
#     #     signal = "BUY"
#     # elif minus_di > plus_di and adx > 0.2:
#     #     signal = "SELL"
#     # else:
#     #     signal = "NONE"
#
#     indicator_result(
#             symbol,
#             "ADX",
#             signal,
#             adx,
#             {"period": period}, 
#             {"plus_di": plus_di, "minus_di": minus_di}
#     )
#         
#     return (signal, adx, plus_di, minus_di) if signal != "NONE" else None

# End of adx_indicator.py
