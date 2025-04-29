# tests/test_sl_manager_manual.py

import sys
import os
import json

sys.path.append(os.path.abspath("."))

from src.trader.sl_managers import sl_trailing_staircase

# ==== Fake Minimal Structures ====

class FakeTick:
    def __init__(self, bid, ask):
        self.bid = bid
        self.ask = ask

# In-memory fake tracking
from src.trader import sl_managers
fake_profit_chains = []

def fake_load_cached_pos_by_ticket(ticket):
    return {
        "peak_profit": max(fake_profit_chains) if fake_profit_chains else 0.0,
        "profit_chain": fake_profit_chains.copy(),
    }

# Monkey patch sl_managers for test isolation
sl_managers.load_cached_pos_by_ticket = fake_load_cached_pos_by_ticket

# ==== Turbo Test Function ====

def run_turbo_test_case(pos_type, start_price, atr_value, tick_moves, description):
    """
    Turbo tests a sl_trailing_staircase scenario.
    """
    print(f"\n=== Turbo Test: {description} ===")

    # Set up fake position
    pos = {
        "ticket": 999999,
        "symbol": "TEST",
        "type": pos_type,
        "price_open": start_price,
        "sl": 0.0,
        "tp": 0.0,
    }

    # Reset memory
    fake_profit_chains.clear()

    price_now = start_price
    for idx, move in enumerate(tick_moves, 1):
        if pos_type == "BUY":
            price_now += move
        else:  # SELL
            price_now -= move

        tick = FakeTick(bid=price_now, ask=price_now + 1)

        # Update profit chain
        pct_profit = (price_now - pos["price_open"]) / pos["price_open"] if pos_type == "BUY" else (pos["price_open"] - price_now) / pos["price_open"]
        fake_profit_chains.append(pct_profit)

        print(f"\n--- Tick {idx} --- Price: {price_now:.2f} --- Profit %: {pct_profit:.5f}")

        recommended_sl, close_signal = sl_trailing_staircase(pos["symbol"], pos, tick, atr_value)
        print(f"Recommended SL: {recommended_sl}")
        print(f"Close Signal: {close_signal}")

# ==== Turbo Test Suite ====

if __name__ == "__main__":
    print("\n=== Turbo Test Suite Start ===")

    run_turbo_test_case(
        pos_type="BUY",
        start_price=10000,
        atr_value=50.0,
        tick_moves=[50, 50, 100, -20, 120, 100, 50, 50, 50, 20],
        description="BUY Uptrend then minor pullbacks"
    )

    run_turbo_test_case(
        pos_type="SELL",
        start_price=10000,
        atr_value=50.0,
        tick_moves=[-50, -50, -100, 20, -120, -100, -50, -50, -50, -20],
        description="SELL Downtrend then minor pullbacks"
    )

    run_turbo_test_case(
        pos_type="BUY",
        start_price=10000,
        atr_value=200.0,
        tick_moves=[50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
        description="BUY Slow climb vs Huge ATR"
    )

    run_turbo_test_case(
        pos_type="SELL",
        start_price=10000,
        atr_value=20.0,
        tick_moves=[-10, -15, -5, -20, -30, 5, -10, -5, 0, -15],
        description="SELL with choppy corrections"
    )

    print("\n=== Turbo Test Suite End ===")
