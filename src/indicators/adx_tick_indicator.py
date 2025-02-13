# adx_ticker_indicator.py
import json
import time
from datetime import datetime

from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE

# We reuse the same "indicator_result" pattern
# that writes results to a JSON file
def write_to_hard_memory(data):
    """
    Overwrites the indicator result file with the latest data.
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
    Write indicator result to hard memory, same as in adx_indicator.py
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


# ------------------------------------------------------------------------
# A small "ticker-based bar" buffer:
# Each entry is a dict with:
#   {
#     "time":  <datetime of bar close>,
#     "open":  <float>,
#     "high":  <float>,
#     "low":   <float>,
#     "close": <float>
#   }
# ------------------------------------------------------------------------
tick_bars = []  # in practice, might store 500 or 1000 to handle warmup + ongoing


def wilder_smooth(values, w_period, first_is_sum=True):
    """
    Wilder smoothing for arrays (TR, +DM, -DM, or DX).
    first_is_sum=True => initial seed = sum(...)
    first_is_sum=False => initial seed = average(...)
    
    Then from i=w_period onward:
      sm[i] = sm[i-1] - (sm[i-1]/w_period) + (values[i]/w_period)
    """
    length = len(values)
    sm = [0.0] * length
    if length < w_period:
        return sm

    block_sum = sum(values[0:w_period])
    if first_is_sum:
        sm[w_period - 1] = block_sum
    else:
        # for DX => ADX
        sm[w_period - 1] = block_sum / w_period

    for i in range(w_period, length):
        sm[i] = sm[i-1] - (sm[i-1] / w_period) + (values[i] / w_period)

    return sm


def update_adx_with_tick(symbol, tick_price, period=14, warmup=2):
    """
    1) Called on every new tick.
    2) Builds a 'micro-bar' from the previous tick's close to this tick's price.
    3) If we have at least period+warmup bars, compute ADX via Wilder's method
       and call 'indicator_result' with the final values.

    :param symbol: e.g. "BTCUSD"
    :param tick_price: The new tick's price (float)
    :param period: ADX period (default 14)
    :param warmup: extra bars beyond 'period' to ensure we have a stable ADX
    """
    # 1) Create a new "bar" from the last close to this new tick price
    now_dt = datetime.now()
    if len(tick_bars) == 0:
        # This is our first bar => we have no previous close, so just store
        bar = {
            "time": now_dt,
            "open": tick_price,
            "high": tick_price,
            "low":  tick_price,
            "close": tick_price
        }
        tick_bars.append(bar)
        logger.debug("Initialized first tick-bar")
        return None

    # We already have at least one bar => we 'close' the previous bar
    prev_bar = tick_bars[-1]
    new_bar = {
        "time": now_dt,
        "open": prev_bar["close"],
        "high": max(prev_bar["close"], tick_price),
        "low":  min(prev_bar["close"], tick_price),
        "close": tick_price
    }
    tick_bars.append(new_bar)

    # If we want to limit max bars stored (say 2000 bars), we can do:
    # if len(tick_bars) > 2000:
    #     tick_bars.pop(0)

    # 2) Check if we have enough bars to do an ADX calculation
    if len(tick_bars) < period + warmup:
        logger.debug("Not enough tick-bars to compute ADX yet.")
        return None

    # 3) Build TR, +DM, -DM for all bars
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    # We'll skip the first bar because it doesn't have a 'previous' bar
    for i in range(1, len(tick_bars)):
        curr_bar = tick_bars[i]
        prev_bar = tick_bars[i - 1]

        high_low = curr_bar["high"] - curr_bar["low"]
        high_close = abs(curr_bar["high"] - prev_bar["close"])
        low_close = abs(curr_bar["low"] - prev_bar["close"])
        tr = max(high_low, high_close, low_close)
        tr_list.append(tr)

        up_move = curr_bar["high"] - prev_bar["high"]
        down_move = prev_bar["low"] - curr_bar["low"]

        if up_move > down_move and up_move > 0:
            plus_dm_list.append(up_move)
        else:
            plus_dm_list.append(0.0)

        if down_move > up_move and down_move > 0:
            minus_dm_list.append(down_move)
        else:
            minus_dm_list.append(0.0)

    # 4) Wilder-smooth TR, +DM, -DM
    tr_s = wilder_smooth(tr_list,      period, first_is_sum=True)
    plus_s = wilder_smooth(plus_dm_list, period, first_is_sum=True)
    minus_s = wilder_smooth(minus_dm_list,period, first_is_sum=True)

    length = len(tr_s)
    if length < period:
        logger.debug("Wilder smoothing not enough data.")
        return None

    # 5) Compute +DI, -DI each bar
    plus_di_list  = [0.0]*length
    minus_di_list = [0.0]*length
    for i in range(length):
        if tr_s[i] != 0.0:
            plus_di_list[i]  = 100.0 * (plus_s[i] / tr_s[i])
            minus_di_list[i] = 100.0 * (minus_s[i] / tr_s[i])

    # 6) DX each bar
    dx_list = [0.0]*length
    for i in range(length):
        pd = plus_di_list[i]
        md = minus_di_list[i]
        denom = pd + md
        if denom != 0.0:
            dx_list[i] = 100.0 * abs(pd - md) / denom

    # 7) Wilder-smooth DX => ADX
    adx_s = wilder_smooth(dx_list, period, first_is_sum=False)

    # 8) The "current" ADX is the last in the series
    adx_current     = adx_s[-1]
    plus_di_current = plus_di_list[-1]
    minus_di_current= minus_di_list[-1]

    logger.info(
        f"(TICK-ADX) {symbol}: "
        f"ADX={adx_current:.2f}, +DI={plus_di_current:.2f}, -DI={minus_di_current:.2f}"
    )

    # 9) Determine the signal (example thresholds)
    if plus_di_current > minus_di_current and adx_current >= 30:
        signal = "BUY"
    elif minus_di_current > plus_di_current and adx_current >= 30:
        signal = "SELL"
    elif adx_current < 30:
        signal = "CLOSE"
    else:
        signal = "NONE"

    logger.info(
        f"(TICK-ADX) Signal: {signal} | "
        f"ADX={adx_current:.2f}, +DI={plus_di_current:.2f}, -DI={minus_di_current:.2f}"
    )

    # 10) Save to indicator_result (same as your candle-based approach)
    indicator_result(
        symbol,
        "ADX_TICK",
        signal,
        adx_current,
        {"period": period, "warmup": warmup},
        {"plus_di": plus_di_current, "minus_di": minus_di_current}
    )

    # Return the same style tuple if you want
    return (signal, adx_current, plus_di_current, minus_di_current) if signal != "NONE" else None

