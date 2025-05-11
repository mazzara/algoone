# src/indicators/scalp_adx.py

import MetaTrader5 as mt5
import json
from datetime import datetime
from src.logger_config import logger
from src.config import INDICATOR_RESULTS_FILE
from src.tools.server_time import get_server_time_from_tick
from src.indicators.adx_indicator import calculate_adx  # reusing ADX calc.


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



def calculate_sma(prices, period):
    """
    Calculate the simple moving average of the given prices.
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calculate_sma_slope(prices, sma_period=9, lookback_bars=3):
    """
    Calculate the slope of an SMA over a specified lookback period.

    Args:
        prices (list): List of closing prices.
        sma_period (int): Period for the SMA calculation.
        lookback_bars (int): Number of bars to look back for slope calculation.

    Returns:
        dict or None
    """
    if len(prices) < sma_period + lookback_bars:
        return None

    sma_now = sum(prices[-sma_period:]) / sma_period
    sma_past = sum(prices[-(sma_period + lookback_bars):-lookback_bars]) / sma_period

    if sma_past == 0:
        return None

    slope = sma_now - sma_past
    slope_pct = slope / sma_past * 100

    return {
        "slope": slope,
        "slope_pct": slope_pct,
        "sma_now": sma_now,
        "sma_past": sma_past
    }


def classify_slope(slope_data, min_slope_pct=0.02):
    """
    Classify the slope trend as UP, DOWN or FLAT.

    Args:
        slope_data (dict): Output from calculate_sma_slope().
        min_slope_pct (float): Minimum slope % to consider as a trend.

    Returns:
        str: One of ['UP', 'DOWN', 'FLAT'] or 'UNDEFINED' if data is invalid.
    """
    if not slope_data or 'slope_pct' not in slope_data:
        return 'UNDEFINED'

    slope_pct = slope_data['slope_pct']

    if slope_pct > min_slope_pct:
        return 'UP'
    elif slope_pct < -min_slope_pct:
        return 'DOWN'
    else:
        return 'FLAT'


def calculate_scalp_adx(symbol, period=14, threshold=20,
                        sma_short_period=9, sma_long_period=21, **kwargs):
    """
    Calculate a ScalpADX indicator:

    - Uses the ADX calculation (with DI+ and DI- computed in calculate_adx)
    - Computes two SMAs from closing prices:
        one short (default 9 bars) and
        one long (default 21 bars)
        - The short SMA is used to determine the slope.
    - Decides a signal:
        • If ADX is below the threshold: "NO SIGNAL"
        • If ADX is above threshold:
            - "LONG" if DI+ > DI- and short SMA > long SMA
            - "SHORT" if DI- > DI+ and short SMA < long SMA
            - Otherwise, "HOLD"

    - Evaluates slope using short SMA vs past short SMA (3-bar lookback by default)
    - Skips ADX check if slope is classified as FLAT

    The result is passed to indicator_result.
    It is than can be stored/ingested by other modules.

    4 digit signature: 3700
    """

    # Get latest price if tick not passed
    tick = kwargs.get("tick")
    if not tick:
        tick = mt5.symbol_info_tick(symbol)
        logger.debug(
            f"[ScalpADX 3700:10] :: Warning - revise calling function. "
            f"Tick not passed, fetched from MT5: {symbol} | {tick}"
        )

    if not tick:
        logger.error(
            f"[ScalpADX 3700:11] :: Escaped function. "
            f"Tick unavailable for {symbol}"
        )
        return None

    price = tick.bid
    logger.debug(f"[ScalpADX 3700:12] Current price for {symbol}: {price}")

    # Request enough bars for both ADX and SMA computations.
    # We use 200 bars for ADX (as in your existing function)
    # ensure at least sma_long_period bars.
    required_bars = max(200, sma_long_period)
    logger.debug(
        f"[ScalpADX 3700:15] Required bars for {symbol}: {required_bars}"
    )

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, required_bars)
    logger.debug(
        f"[ScalpADX 3700:16] Rates fetched for {symbol}: {len(rates)} bars"
    )

    if rates is None or len(rates) < sma_long_period:
        logger.error(
            f"[ScalpADX 3700:20] :: Escaped function. "
            f"Not enough data to calculate SMAs for {symbol}"
            f" (required: {sma_long_period}, available: {len(rates)})"
        )
        return None

    # Calculate SMAs using closing prices
    closing_prices = [bar['close'] for bar in rates]
    short_sma = calculate_sma(closing_prices, sma_short_period)
    long_sma = calculate_sma(closing_prices, sma_long_period)

    if short_sma is None or long_sma is None:
        logger.error(f"Failed to compute SMAs for {symbol}")
        return None

    logger.debug(
        f"[ScalpADX 3700:30] :: "
        f"SMAs for {symbol}: Short: {short_sma:.2f} | Long: {long_sma:.2f}"
    )

    # Evaluate Slope
    slope_data = calculate_sma_slope(closing_prices, sma_short_period, lookback_bars=3)
    slope = classify_slope(slope_data, min_slope_pct=0.01)
    slope_pct = slope_data["slope_pct"] if slope_data else None

    logger.debug(
                f"[ScalpADX 3700:42] :: Slope classification for {symbol}: {slope}"
    )

    # If slope is FLAT, we can skip the ADX calculation
    # if slope == "FLAT":
    #     logger.debug(
    #         f"[ScalpADX 3700:42] :: Escaped function. "
    #         f"Slope filter: market too flat for {symbol} | Slope: {slope}"
    #     )
    #     return {
    #         "indicator": "ScalpADX",
    #         "signal": "HOLD",
    #         "values": {
    #             "adx": None,  # Not yet calculated
    #             "plus_di": None,
    #             "minus_di": None,
    #             "sma_short": short_sma,
    #             "sma_long": long_sma,
    #             "slope_pct": slope_data["slope_pct"]
    #         }
    #     }

    # Calculate ADX (which also computes DI+ and DI-) using existing function
    adx_data = calculate_adx(symbol, period=period)
    if adx_data is None:
        logger.error(f"[ScalpADX 3700:43] :: ADX calculation failed for {symbol}")
        return None

    adx_value = adx_data["values"]["adx"]
    plus_di = adx_data["values"]["plus_di"]
    minus_di = adx_data["values"]["minus_di"]

    # Decide on the trading signal
    # if adx_value <= threshold:
    #     signal = "NO SIGNAL"
    # else:
        # if plus_di > minus_di and short_sma > long_sma:
        #     signal = "BUY"
        # elif minus_di > plus_di and short_sma < long_sma:
        #     signal = "SELL"
        # else:
        #     signal = "HOLD"

    logger.debug(
            f"[ScalpADX 3700:45] :: check signal parameters: " 
            f"ADX for {symbol}: {adx_value:.2f} | "
            f"+DI: {plus_di:.2f} | -DI: {minus_di:.2f} | "
            f"SMA Fast: {short_sma:.2f} | SMA Slow: {long_sma:.2f} | "
            f"Slope %: {slope_pct:.2f}"
        )

    # Testing with tick filtering
    if adx_value <= threshold:
        signal = "NO SIGNAL"
        logger.debug(
            f"[ScalpADX 3700:48:1] :: "
            f"ADX below threshold for {symbol} | ADX: {adx_value:.2f} | Signal: {signal}"
        )
    else:
        # NO SLOPE VERIFICATION
        # note: here, long_sma and short_sma has nothing to do with LONG or SHORT position. 
        # It was a naming decision, maybe better if were fast_sma and slow_sma. But well, changing names at this point requires too much code review, so I'll procrastinate this issue. Maybe never review - kkkk.
        if plus_di > minus_di and short_sma > long_sma and price < short_sma:
            signal = "BUY"
            logger.debug(
                    f"[ScalpADX 3700:48:2] :: "
                    f"BUY signal for {symbol} | ADX: {adx_value:.2f} | Signal: {signal}"
            )
        elif minus_di > plus_di and short_sma < long_sma and price > short_sma:
            signal = "SELL"
            logger.debug(
                    f"[ScalpADX 3700:48:3] :: "
                    f"SELL signal for {symbol} | ADX: {adx_value:.2f} | Signal: {signal}"
            )
        else:
            signal = "HOLD"
            logger.debug(
                    f"[ScalpADX 3700:48:4] :: "
                    f"HOLD signal for {symbol} | ADX: {adx_value:.2f} | Signal: {signal}"
            )


        #
        # SLOPE VERIFICATION
        # if plus_di > minus_di and short_sma > long_sma and price < short_sma and slope_pct > min_slope_pct:
        #     signal = "BUY"
        # elif minus_di > plus_di and short_sma < long_sma and price > short_sma and slope_pct < -min_slope_pct:
        #     signal = "SELL"
        # else:
        #     signal = "HOLD"

    # Log and persist the indicator result via the shared function.
    indicator_result(
        symbol,
        "ScalpADX",
        signal,
        adx_value,
        {"plus_di": plus_di, 
         "minus_di": minus_di, 
         "sma_short": short_sma, 
         "sma_long": long_sma,
         **slope_data
         },
        {"period": period, 
         "threshold": threshold,
         "sma_short_period": sma_short_period, 
         "sma_long_period": sma_long_period}
    )

    logger.debug(
        f"[ScalpADX 3700:50] :: Signal for {symbol}: {signal} | "
        f"ADX: {adx_value:.2f} | +DI: {plus_di:.2f} | -DI: {minus_di:.2f} | "
        f"SMA Short: {short_sma:.2f} | SMA Long: {long_sma:.2f} | "
        f"Slope %: {slope_pct:.2f}"
    )

    # Return a result dictionary for further processing if needed.
    return {
        "indicator": "ScalpADX",
        "signal": signal,
        "values": {
            "adx": adx_value,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "sma_short": short_sma,
            "sma_long": long_sma,
            **slope_data
        }
    }
