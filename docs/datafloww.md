📊 Data Flow & Trade Execution Logic
AlgoOne's trade logic is centered on real-time tick updates. It follows a clear execution pipeline, integrating indicator signals, risk filters, and rule-based trade clearance.

⏱️ 1. Tick Reception
Ticks are retrieved using:

```python
tick = mt5.symbol_info_tick(symbol)
```

Tick Data Structure Example:

```json
{
  "symbol": "EURUSD",
  "bid": 1.1012,
  "ask": 1.1014,
  "spread": 0.0002,
  "last": 1.1013,
  "volume": 123,
  "flags": 1,
  "volume_real": 123.45,
  "time": 1747000610,
  "time_msc": 1747000610999
}
```

These ticks are passed to:

```python
on_tick(ticks: List[Dict[str, Any]])
```

## 🔁 Tick Dispatch: on_tick(ticks)
Once received, new ticks are passed into on_tick(ticks: List[Dict]).
This function acts as the runtime router and triggers:
- open_trade(symbol)
- manage_trade(symbol)
- close_trade(symbol)
- abort_trade(symbol)


🔁 2. on_tick() Callback Flow
For each symbol's tick, the following procedures are triggered in order:

1. open_trade(symbol)
2. manage_trade(symbol)
3. close_trade(symbol)


## 🚀 Trade Entry Logic: `open_trade(symbol)`
✅ Flow Summary
Re-fetch tick for `symbol`

Dispatch ATR indicator:
```python
atr_result = dispatch_position_manager_indicator(symbol, 'ATR')
```


🧠 3. Inside open_trade(symbol)
Re-fetch Tick: Ensures up-to-date market data

Call ATR Indicator:

```python
atr_result = dispatch_position_manager_indicator(symbol, 'ATR')
```

Spread Filter:
```python
if not basic_spread_check(symbol, tick): return
```

Get Indicator Signals:

```python
signals = dispatch_signals(symbol)
```

Signal Structure:
```json
{
  "indicator": "ScalpADX",
  "signal": "BUY",
  "values": {
    "adx": 19.4,
    "plus_di": 24.1,
    "minus_di": 16.3,
    "sma_short": 1.1012,
    "sma_long": 1.1005,
    "slope": 0.0003
  }
}
```

Signal Aggregation:
```python
aggregate_signals(signals, min_votes=1)
```

Uses vote counts across indicators:

BUY / SELL / CLOSE / NONE / HOLD / etc.


🔐 4. Risk & Trade Clearance
Before executing a trade, AlgoOne checks multiple filters:

✅ Limit Clearance:
```python   
allow_limit_buy, allow_limit_sell = get_limit_clearance(symbol)
```

Compares current positions against per-symbol limits in trade_limits_config.json.

🔁 Cooldown Throttle:
```python
allow_cooldown_buy, allow_cooldown_sell = get_cooldown_clearance(symbol)
```

Prevents overtrading by enforcing time-based restrictions.

🧮 Combined:
```python
allow_buy, allow_sell = get_open_trade_clearance(symbol)
```

🎯 5. Final Checks and Execution
If signal + clearance pass:

Default SL and TP are applied

Trade is opened using:
```python
open_buy(symbol, lot_size)
# or
open_sell(symbol, lot_size)
```

This system is modular, allowing:
- Multiple indicator sources per symbol
- Votable signal aggregation
- Clear separation between logic, data, and execution layers


