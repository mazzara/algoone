# adx_indicator.py - ADX indicator implementation
import MetaTrader5 as mt5
import json
import os
import time
from datetime import datetime
from src.logger_config import logger
from src.config import HARD_MEMORY_DIR, INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick


def get_signal(symbol, **kwargs):
    """
    Get the signal for the ADX indicator.
    """
    return calculate_adx(symbol, **kwargs)


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
            "my_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tick_timestamp": get_server_time_from_tick(symbol),
            "tick_time": datetime.utcfromtimestamp(get_server_time_from_tick(symbol)).strftime("%Y-%m-%d %H:%M:%S")

        }
    }
    # write_to_hard_memory(data)



def calculate_adx(symbol, period=14):
    """
    Calculate ADX (Average Directional Index) using Welles Wilder's method,
    with debug logs of intermediate calculations.
    """

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 200)
    if rates is None or len(rates) < period + 1:
        logger.error(f"Not enough data for {symbol}")
        return None

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
    if plus_di_current > minus_di_current and adx_current >= 10:
        signal = "BUY"
    elif minus_di_current > plus_di_current and adx_current >= 10:
        signal = "SELL"
    elif adx_current < 10:
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

    # return (signal, adx_current, plus_di_current, minus_di_current) if signal != "NONE" else None
    
    return {
            "indicator": "ADX",
            "signal": signal,
            "values": {
                "adx": adx_current,
                "plus_di": plus_di_current,
                "minus_di": minus_di_current
            }
    }



# End of adx_indicator.py
