## 📈AlgoOne: Tick Flow and Trade Decision Chain

⏱ Tick Fetch
Ticks are retrieved directly from MT5 using:
```python
tick = mt5.symbol_info_tick(symbol)
```

The resulting tick is a dictionary structured like:

```json
{
  "symbol": "EURUSD",
  "bid": 1.09456,
  "ask": 1.09460,
  "spread": 0.00004,
  "last": 1.09458,
  "volume": 123456,
  "flags": 0,
  "volume_real": 123456.78,
  "time": 1747001234,
  "time_msc": 1747001234567
}
```

# 🔁 Tick Dispatch: on_tick(ticks)
Once received, new ticks are passed into on_tick(ticks: List[Dict]).
This function acts as the runtime router and triggers:

- open_trade(symbol)
- manage_trade(symbol)
- close_trade(symbol)
- abort_trade(symbol)


# 🚀 Trade Entry Logic: open_trade(symbol)
✅ Flow Summary
Re-fetch tick for symbol
Dispatch ATR indicator:

```python
atr_result = dispatch_position_manager_indicator(symbol, 'ATR')
```

Run basic spread check (skip trade if spread too wide)
Fetch signal via:
```python
signals = dispatch_signals(symbol)
```

Signals return a dict like:
```json
{
  "indicator": "ScalpADX",
  "signal": "SELL",
  "values": {
    "adx": 22.5,
    "plus_di": 18.4,
    "minus_di": 25.1,
    "sma_short": 104.3,
    "sma_long": 105.0
  }
}
```

Signal aggregation via aggregate_signals(signals) which supports:
- Multiple indicators
- Vote-based logic
- Signal types like 'BUY', 'SELL', 'HOLD', 'CLOSE'

Check entry permission:
```python
allow_buy, allow_sell = get_open_trade_clearance(symbol)
```

`get_open_trade_clearance()` internally checks:
- Symbol-specific position limits (`get_limit_clearance()`)
- Cooldown timers (get_cooldown_clearance())

If all checks pass, AlgoOne constructs and sends a trade request:
- Uses default SL/TP from config
- Executes via MT5 API

# 🔁 Trade Management: manage_trade(symbol)
🎯 Purpose
Manages open positions per symbol and dynamically adjusts SL if profitable.

🔄 Workflow
Fetch current tick:
```python
tick = mt5.symbol_info_tick(symbol)
```

Dispatch ATR again for SL logic:
```python
atr_result = dispatch_position_manager_indicator(symbol, "ATR")
```

Loop through open positions for the symbol

Evaluate if trailing logic is triggered:
```python
recommended_sl = sl_trailing_staircase(symbol, pos, tick, atr)
```

If recommended_sl is:
- More protective than current SL (closer to break-even or better)
- Only active if profit exceeds threshold
    → Then SL is updated


# 📉 Trailing SL Logic: sl_trailing_staircase()
Only applies when:
```python
position.profit_pct >= trailing_profit_threshold
```

Default threshold:
```python
"trailing_profit_threshold_decimal": 0.005  // i.e. +0.5%
```

SL is calculated as:
```python
trail_sl = price_now - atr * multiplier
trail_sl = max(trail_sl, open_price + atr * break_even_offset)
```

Defaults:
```python
"break_even_offset_decimal": 0.123  // 12.3% of ATR from open price
```


# 🧠 Design Notes
SL never regresses: once moved forward, it’s never pulled back.
- Indicator-agnostic: trade and SL logic are abstracted and modular.
- Decision pipeline: Signals, then aggregation, then risk checks.
- Throttled by design: via cooldown logic and spread filters.





<pre>```mermaid

flowchart TD

    A[on_tick] --> B[open_trade]
    B --> B1[load trade_limits_cache]
    B --> B2[load total_positions_cache]
    B --> C[get_open_trade_clearance]
    C --> C1[get_limit_clearance]
    C1 --> C2[load trade_limits file]
    C2 --> C3[returns: BUY, SELL, or None]
    C --> D[get_cooldown_clearance]
    D --> D1[returns: allow_buy, allow_sell]
    B --> E[calculate_adx]
    E --> F[SIGNAL]
    F --> G{Open Decision}
    G --> G1[open_sell]
    G --> G2[open_buy]
    B --> H[save_trade_decision]
    H --> I[get_total_positions_update]

    A --> J[get_total_positions]
    J --> J1[load total_positions_cache]

    A --> K[close_trade]
    K --> K1[load close_profit_threshold]
    K --> K2[get_positions]
    K --> K3[calculate_adx]
    K3 --> K4[SIGNAL]
    K4 --> L{Close Decision}
    L --> L1[close request]
    L --> L2[do nothing]

    A --> Z[Loop]


```</pre>
