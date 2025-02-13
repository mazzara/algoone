# src/ticker/custom_candle_aggregator.py
import time
from datetime import datetime


"""
In a Real Tick Listener
In your actual environment:

Initialize a global (or class-level) aggregator:
aggregator = CustomCandleAggregator(mode="time", interval=30)

On each tick event or callback:
def on_tick(tick):
    candle = aggregator.on_new_tick(tick)
    if candle:
        # We have a finished candle, do something: 
        # e.g., store it, calculate indicators, etc.
        print("New Candle Bar formed:", candle)
That’s it. The aggregator automatically handles candle formation.
Create a 30‐tick candle aggregator by CustomCandleAggregator(mode="tick", interval=30).
Create a 30‐second candle aggregator by CustomCandleAggregator(mode="time", interval=30).
"""


class CustomCandleAggregator:
    """
    Maintains a single "in-progress" candle from a live tick stream,
    and closes it once a specified threshold is reached.

    Mode can be:
      - "time":  close candle after 'interval' seconds
      - "tick":  close candle after 'interval' ticks

    Usage:
      1) Create aggregator = CustomCandleAggregator(mode="time", interval=30)
      2) For each new tick, aggregator.on_new_tick(tick_dict)
      3) If it returns a 'finished_candle', you can process/store it.
    """

    def __init__(self, mode="time", interval=30):
        """
        :param mode: "time" or "tick"
        :param interval: number of seconds (mode="time") or ticks (mode="tick")
        """
        if mode not in ("time", "tick"):
            raise ValueError("mode must be 'time' or 'tick'")

        self.mode = mode
        self.interval = interval

        # Holds the "current" candle in progress
        self.candle_open_time = None
        self.open_price = None
        self.high_price = None
        self.low_price  = None
        self.close_price= None
        self.tick_count = 0

        # For time-based mode, track candle_end_time
        self.candle_end_ts = None

    def on_new_tick(self, tick):
        """
        Process a new tick. If a candle finishes by hitting
        the threshold, return that candle. Otherwise, return None.

        :param tick: dict with at least:
                     {
                       "time": <float/int or datetime>,
                       "price": <float>
                     }
        :return: A candle dict if we closed a candle this tick, else None.
        """
        # Convert tick time to float timestamp if needed
        ts = self._to_ts(tick["time"])
        price = tick["price"]

        # If no candle in progress, start one
        if self.open_price is None:
            self._start_candle(ts, price)
            return None

        # Update in-progress candle's high/low/close
        if price > self.high_price:
            self.high_price = price
        if price < self.low_price:
            self.low_price = price
        self.close_price = price
        self.tick_count += 1

        # Check if we need to close the candle
        if self.mode == "tick":
            if self.tick_count >= self.interval:
                return self._close_and_start_new(ts, price)
            else:
                return None
        else:
            # self.mode == "time"
            if ts >= self.candle_end_ts:
                return self._close_and_start_new(ts, price)
            else:
                return None

    def _start_candle(self, ts, price):
        """Initialize a fresh candle from this tick."""
        self.candle_open_time = ts
        self.open_price  = price
        self.high_price  = price
        self.low_price   = price
        self.close_price = price
        self.tick_count  = 1

        if self.mode == "time":
            self.candle_end_ts = ts + self.interval

    def _close_and_start_new(self, ts, price):
        """
        Close the current candle, build a candle dict,
        then start a new candle from this tick.
        """
        finished_candle = {
            "open_time":  self.candle_open_time,
            "open":       self.open_price,
            "high":       self.high_price,
            "low":        self.low_price,
            "close":      self.close_price,
            "close_time": ts,
            "tick_count": self.tick_count
        }
        # Start a new candle with this tick
        self._start_candle(ts, price)
        return finished_candle

    def _to_ts(self, t):
        """
        Convert t to float timestamp if it's a datetime, else assume
        it's already a float/int second-based timestamp.
        """
        if isinstance(t, datetime):
            return t.timestamp()
        elif isinstance(t, (float, int)):
            return float(t)
        else:
            raise ValueError(f"Unsupported tick time type: {type(t)}")


# --------------------------
# Example usage demonstration
# --------------------------
if __name__ == "__main__":
    # Create aggregator for a 30-second candle
    aggregator = CustomCandleAggregator(mode="time", interval=30)

    # Simulate receiving ticks
    # (In practice you'd get these from a live feed)
    simulated_ticks = [
        {"time": 1676671800, "price": 100.0},  # e.g. Wed Feb 17, ...
        {"time": 1676671815, "price": 101.2},
        {"time": 1676671818, "price": 99.8},
        {"time": 1676671831, "price": 100.5},  # surpasses 30s from 1800 => candle closes
        {"time": 1676671832, "price": 100.7},
        {"time": 1676671845, "price": 101.0},
        {"time": 1676671860, "price": 102.5},  # next candle might close, etc.
    ]

    for tick in simulated_ticks:
        candle = aggregator.on_new_tick(tick)
        if candle:
            # We just closed a candle
            print("Closed Candle:", candle)
    
    # After the final tick, you may have a partially-formed candle
    # that you can decide to close or keep open. E.g.:
    # last_candle = aggregator.force_close()
    # if last_candle:
    #    print("Final Partial Candle:", last_candle)

