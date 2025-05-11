## 📈 AlgoOne: Tick Execution Flow

```mermaid

flowchart TD

    A[on_tick(ticks)] --> B[open_trade(symbol)]
    B --> B1[Global: trade_limits_cache]
    B --> B2[Global: total_positions_cache]
    B --> C[get_open_trade_clearance(symbol)]
    C --> C1[get_limit_clearance(symbol)]
    C1 --> C2[Load File "TRADE_LIMIT_FILE"]
    C2 --> C3[BUY, SELL, None]
    C --> D[get_cooldown_clearance(symbol)]
    D --> D1[Boolean: Allow Buy, Allow Sell]
    B --> E[calculate_adx(symbol)]
    E --> F[SIGNAL]
    F --> G{Open Decision}
    G --> G1[open_sell(symbol, lot_size)]
    G --> G2[open_buy(symbol, lot_size)]
    B --> H[save_trade_decision(trade_data)]
    H --> I[get_total_positions (*an update*)]

    A --> J[get_total_positions()]
    J --> J1[Global: total_positions_cache]

    A --> K[close_trade()]
    K --> K1[Load File "CLOSE_PROFIT_THRESHOLD"]
    K --> K2[get_positions()]
    K --> K3[calculate_adx(symbol)]
    K3 --> K4[SIGNAL]
    K4 --> L{Open Decision}
    L --> L1[close request]
    L --> L2[do nothing]

    A --> Z[Loop...]

```
