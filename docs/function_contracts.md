# 📘 AlgoOne Function Contracts

This document captures key function-level contracts and expectations for core runtime behavior in AlgoOne. It provides a concise reference for:

- Purpose
- Dependencies
- Outputs
- Fallbacks
- Runtime reload behavior

---

## 🔁 `on_tick(ticks)`

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `on_tick(ticks)`                                           |
| **Defined in**      | `main.py` or `algoapp.py`                                  |
| **Reads from**      | `override_watcher`, `limits_watcher`, `indicator_config_watcher` |
| **Writes to**       | Calls: `open_trade()`, `manage_trade()`, `close_trade()`, `abort_trade()` |
| **Triggers**        | Trade decision chain                                       |
| **Reloadable**      | Yes (uses `ConfigWatcher` to hot-reload config state)      |
| **Fallbacks**       | Skips execution if `pause_open` is True                   |
| **Returns**         | None                                                       |

---

## 🟩 `open_trade(symbol, **kwargs)`

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `open_trade()`                                             |
| **Defined in**      | `src/trader/trade.py`                                      |
| **Reads from**      | `tick = fetch_tick(symbol)`, ATR thresholds, trade limits  |
| **Writes to**       | Opens new position via MT5 API                             |
| **Triggers**        | Logs open in journal, appends position                     |
| **Reloadable**      | Yes (indirectly, via trade limits)                         |
| **Fallbacks**       | Fails gracefully if tick or ATR unavailable                |
| **Returns**         | Dict containing trade execution status and metadata        |

---

## 🟨 `manage_trade(symbol)`

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `manage_trade()`                                           |
| **Defined in**      | `src/trader/trade.py`                                      |
| **Reads from**      | Live positions, trailing stop logic, current tick          |
| **Writes to**       | Updates trailing stop, closes position on threshold        |
| **Triggers**        | SL modification, TP decisions                              |
| **Reloadable**      | Yes (indirectly via config or tick context)                |
| **Fallbacks**       | No action if position invalid or data missing              |
| **Returns**         | None                                                       |

---

## 🟥 `close_trade(symbol)`

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `close_trade()`                                            |
| **Defined in**      | `src/trader/trade.py`                                      |
| **Reads from**      | Open positions, symbol PnL context                         |
| **Writes to**       | Sends close order to MT5                                   |
| **Triggers**        | Trade journal close log                                    |
| **Reloadable**      | No (state-dependent)                                       |
| **Fallbacks**       | Fails silently if trade already closed                     |
| **Returns**         | None                                                       |

---

## 🧾 `get_positions()`

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `get_positions()`                                          |
| **Defined in**      | `src/positions/positions.py`                               |
| **Reads from**      | MT5 open positions API                                     |
| **Writes to**       | `hard_memory/positions.json`                               |
| **Triggers**        | Snapshot of current live positions                         |
| **Reloadable**      | Yes (can be refreshed manually)                            |
| **Fallbacks**       | Returns empty list if MT5 is disconnected or fails        |
| **Returns**         | List of open MT5 positions                                 |

---

## 📊 `get_total_positions()`

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `get_total_positions()`                                    |
| **Defined in**      | `src/portfolio/total_positions.py`                         |
| **Reads from**      | `positions.json` or live MT5 data                          |
| **Writes to**       | `total_positions.json`                                     |
| **Triggers**        | Exposure summary by symbol, long/short balance             |
| **Reloadable**      | Yes (always recalculated on demand)                        |
| **Fallbacks**       | Skips if no positions available                            |
| **Returns**         | Aggregated dictionary per symbol (long/short size, avg price, etc.) |

---
