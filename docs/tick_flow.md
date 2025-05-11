## 📈 AlgoOne: Tick Execution Flow

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
    H --> I[get_total_positions (update)]

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
