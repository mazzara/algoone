
# 🤖 AlgoOne

**AlgoOne** is a modular, event-driven trading system built primarily for use with MetaTrader 5 (MT5). It was designed to assist in executing portfolio-aware strategies on forex, CFDs, and other instruments, with a focus on transparency, control, and future scalability.

AlgoOne is structured, rule-based, testable, and logs every move.

AlgoOne is not just a bot—it’s a decision engine with state awareness, risk management, and a clear logic path.

---

## 🚀 Overview

AlgoOne operates as a tick-listener-based engine that:

- Connects to an MT5 terminal programmatically
- Collects live market data and tick events
- Opens, manages, and closes trades based on strategy logic
- Monitors portfolio exposure and applies defined trading limits

This is a **personal project**, originally developed for research, experimentation, and live testing. It is published publicly in case it helps others or inspires ideas.

---

## 📦 Project Structure

```
algoone/
│
├── src/
│   ├── connect/              # MT5 connection handlers
│   ├── account/              # Account information and limits
│   ├── positions/            # Live and historical positions
│   ├── symbols/              # Market symbols and tickers
│   ├── pending/              # Pending orders and open trades
│   ├── limits/               # Per-symbol trading rules & constraints
│   ├── trader/               # Trade execution logic (open/manage/close)
│   ├── history/              # Trade history retrieval
│   ├── journal/              # Trade journal for logging
│   ├── indicators/           # Strategy-specific indicators (e.g., ADX)
│   ├── logger_config.py      # Logging setup for observability
│   └── tick_listener.py      # Real-time tick event dispatcher
│
├── hard_memory/              # JSON-based persistent state (positions, limits, history)
├── config/                   # Strategy config files
├── main.py                   # Primary execution script
└── README.md                 # You are here
```

---

## ⚙️ Features

- ✅ Real-time tick listener via `listen_to_ticks()`
- ✅ Strategy logic encapsulated in `open_trade()`, `manage_trade()`, `close_trade()`
- ✅ Portfolio exposure control via `get_total_positions()`
- ✅ Risk and trade limits per symbol via JSON configs
- ✅ Built-in logger for audit trail and debugging
- ✅ Modular codebase, ready to extend with new indicators or strategies

---

## 🧠 Strategy Philosophy

This system focuses on:

- **Portfolio-level control** rather than individual SL/TP
- **Symbol-specific logic and limits** loaded from human-readable JSON
- **No full automation** — designed to augment decision-making or work alongside discretionary oversight

---

## 🧪 How to Run

1. Set up MetaTrader 5 on your machine.
2. Ensure Python can connect to MT5 (via `MetaTrader5` package).
3. Customize your trading limits in `hard_memory/trade_limits.json`.
4. Launch the main listener:

```bash
python main.py
```

5. Monitor logs and trade activity in real time.

---

## 📂 Trade Limits Example

Each symbol can be configured with trading parameters:

```json
{
  "EURUSD": {
    "max_long": 2,
    "max_short": 1,
    "lot_size": 0.1,
    "cooldown": 30,
    "MAX_ORDERS": 100,
    "sentiment": "RANGING"
  }
}
```

---

# AlgoOne: Structural Overview & Execution Flow Documentation

## ✨ Purpose
AlgoOne is a modular, auto-executing trading bot designed to run on tick data and execute trades based on a configurable strategy.
It integrates:
- Live market data (MT5)
- Modular indicator and strategy logic
- Configurable risk and trade management rules

The system is designed for:
- Real-time trading
- Plug-and-play indicator development
- Safe fallback behaviors for robustness

---

## 🔍 Core Concept
> **"AlgoOne listens to the market and acts."**

### Core Loop:
```
[MARKET TICK FROM MT5]
     ⇳
listen_to_ticks()
     ⇳
 on_tick(ticks)
     ⇳
 [open_trade, manage_trade, close_trade, abort_trade]
```

---

## ⚡ Execution Order
### Main entrypoint: `algoapp.py`

1. `connect()`
   - Connects to MT5 terminal

2. `load_trade_limits()`
   - Loads risk limits and symbol constraints from `trade_limits_config.json`

3. `check_account_limits()` / `get_account_info()`
   - Logs account balance and margin context

4. `get_positions()` / `get_orders()` / `get_trade_history()`
   - Retrieves historical and pending trade context

5. `get_symbols()`
   - Writes full symbol list to file (dev helper)
   - Symbols act like a financial Rosetta Stone

6. `get_total_positions()`
   - Aggregates portfolio exposure by symbol

7. `listen_to_ticks(symbols=symbols)`
   - Begins the infinite loop of live tick consumption
   - Periodically (every 1s) calls `mt5.symbol_info_tick()` for each symbol
   - Compares with last seen tick (bid/ask) to detect new data

8. `on_tick(ticks)`
   - Central orchestration spine
   - Triggers downstream modules:
     - `open_trade()` if not paused
     - `manage_trade()`
     - `abort_trade()`
     - `close_trade()`

---

## 🔹 Symbol Configuration and Selection
- Main driver of trading scope is `trade_limits_config.json`
- Symbols = top-level keys of the JSON
- Dynamic loading via `ConfigWatcher`

Fallback hierarchy:
1. **Trade limits file** (primary)
2. **symbols_allowed.json** (if used)
3. **DEFAULT_SYMBOLS** from `config.py`

---

## 🛳 Tick Listener Notes
- Tick stream is time-agnostic and random
- AlgoOne stores last tick per symbol to avoid processing duplicates
- Tick granularity is per second, but tick frequency is market-driven

---

### 🔐 load_trade_limits()

Loads per-symbol risk rules and constraints.

- Origin: `src/limits/limits.py`
- Reads: `config/trade_limits_config.json`
- Reloads dynamically via `ConfigWatcher`
- Important File location can be  customized at config.py, but it recommended to leave as is.
- `ConfigWatcher` is a class for lazy loading of JSON files. It watches for changes and reloads the config when necessary.

| 🔹 Component        | 🔍 Description                                              |
|--------------------|------------------------------------------------------------|
| **Function**        | `load_trade_limits()`                                      |
| **Reads from**      | `TRADE_LIMIT_FILE` (defined in `config.py`)               |
| **Writes to**       | None                                                       |
| **Triggers**        | Calls `generate_default_trade_limits()` if file is missing |
| **Reloadable**      | Yes (via `ConfigWatcher`)                                  |
| **Fallbacks**       | Uses generated default if file is not found or malformed   |
| **Returns**         | Dictionary of symbol-wise trading limits                   |


📌 **CONFIG EXPECTS:**
File expects symbol name as top-level key, and dictionary with expected keys, which will fallback to system defaults in case they are not found in file.

IMPORTANT: This file also defines which symbols are allowed to be traded. 
Class `ConfigWatcher` will load and return symbols by calling method .keys() to return 
list of symbols and feed listener.

```json
{
  "BTCUSD": {
    "MAX_LONG_SIZE": 0.02,
    "MAX_SHORT_SIZE": 0.02,
    "COOLDOWN_SECONDS": 300,
    "MAX_CAPITAL_ALLOCATION": 5000,
    "DEFAULT_LOT_SIZE": 0.02,
    "MAX_ORDERS": 100
  }
}
```

---

## ⚖️ Philosophy
> *Favor clarity, deterministic behavior, and modularity.*

- No trade happens without a configured limit
- Each module does one thing well
- Fallbacks exist for dev convenience, not production ambiguity
- Logging is sacred (every important decision has a trace)

---

## 📓 To Do / Next Refinements
- Refactor `on_tick()` into smaller subfunctions (e.g., `handle_open`, `handle_manage`)
- Add optional runtime reload of symbol list
- Remove legacy fallback logic if limits are enforced strictly
- Document module responsibilities (e.g., `trader`, `portfolio`, `limits`, `tick_listener`)

---

## 📄 Files of Interest
- `main.py` / `algoapp.py`: orchestrator
- `tick_listener.py`: market feed consumer
- `trade_limits_config.json`: rulebook
- `config.py`: paths and global constants
- `trade.py`: trade opening and lifecycle logic
- `ConfigWatcher`: live JSON config reloader

---

*Written to assist future maintainers, refactors, and your future self.*

---

## ⚠️ Disclaimer

This software is for **educational and experimental purposes only**. It is **not financial advice**, and comes with **no guarantee** of profitability or accuracy. Use at your own risk. Always test thoroughly before any live deployment.

---

## 👤 Author

Created by a trader and developer experimenting with systematized trading logic, real-time analysis, and execution control.

---

## 🌍 License

MIT License — see `LICENSE` file for details.




---
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
