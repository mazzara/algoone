
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

## ⚠️ Disclaimer

This software is for **educational and experimental purposes only**. It is **not financial advice**, and comes with **no guarantee** of profitability or accuracy. Use at your own risk. Always test thoroughly before any live deployment.

---

## 👤 Author

Created by a trader and developer experimenting with systematized trading logic, real-time analysis, and execution control.

---

## 🌍 License

MIT License — see `LICENSE` file for details.
