# src/portfolio/position_state_tracker.py


from copy import deepcopy
from utils.config_watcher import ConfigWatcher

autotrade_config = ConfigWatcher("config/autotrade_config_settings.json")


def calculate_profit_pct(position):
    try:
        entry = position.get("price_open")
        current = position.get("price_current")
        if entry and current:
            if position.get("type") == "SELL":
                return (entry - current) / entry * 100
            else:
                return (current - entry) / entry * 100
    except Exception:
        return 0.0
    return 0.0


def calculate_individual_risk(pos: dict) -> float:
    """
    Calculate the stop-loss risk for a single position.

    Args:
        pos (dict): A position dictionary with keys: 'type', 'price_open', 'sl', 'volume'

    Returns:
        float: Potential loss if SL is hit, 0.0 if invalid or trailing stop in profit
    """
    volume = pos.get("volume", 0)
    price_open = pos.get("price_open", 0)
    stop_loss = pos.get("sl", None)
    pos_type = pos.get("type")

    if stop_loss is None or stop_loss <= 0:
        return 0.0  # No SL or invalid

    if pos_type == "BUY":
        loss = (price_open - stop_loss) * volume
    elif pos_type == "SELL":
        loss = (stop_loss - price_open) * volume
    else:
        return 0.0

    return round(loss, 2) if loss > 0 else 0.0


def enrich_positions_with_risk(positions: list) -> list:
    """
    Adds a 'risk_at_sl' field to each position in the list.

    Args:
        positions (list): List of position dicts

    Returns:
        list: The same list with enriched 'risk_at_sl' per item
    """
    for pos in positions:
        if "risk_at_sl" not in pos:
            pos["risk_at_sl"] = calculate_individual_risk(pos)
    return positions


def update_position_profit_chain(position, profit_step=0.01, max_chain_length=10):
    """
    Updates the profit_chain and peak_profit fields of a position.
    Modifies the position dict in-place.
    """
    profit_pct = calculate_profit_pct(position)

    # Initialize profit_chain if it doesn't exist
    if "profit_chain" not in position:
        position["profit_chain"] = []
    if "peak_profit" not in position:
        position["peak_profit"] = profit_pct

    # Update peak profit
    position["peak_profit"] = max(position.get("peak_profit", profit_pct), profit_pct)

    # Add current profit to chain (rounded to step)
    rounded_profit = round(profit_pct / profit_step) * profit_step
    # position["profit_chain"].append(rounded_profit)
    chain = position.get("profit_chain", [])

    # Append only if different from last entry
    if not chain or chain[-1] != rounded_profit:
        chain.append(rounded_profit)

    # Enforce max length
    if len(chain) > max_chain_length:
        chain = chain[-max_chain_length:]

    position["profit_chain"] = chain

    return position


def check_trailing_retrace(position, retrace_pct=0.382):
    """
    Checks if the current profit has retraced more than X% from peak.
    Returns True if a trailing exit condition is triggered.
    """
    peak = position.get("peak_profit", 0.0)
    # current = position.get("profit", 0.0)
    current = calculate_profit_pct(position)

    if peak <= 0:
        return False

    retraced = (peak - current) / peak >= retrace_pct
    return retraced


def check_failed_bounce(position, lookback=3):
    """
    If peak is negative and last 3 profits show lower lows, exit.
    """
    peak = position.get("peak_profit", 0.0)
    chain = position.get("profit_chain", [])

    if peak >= 0 or len(chain) < lookback:
        return False

    recent = chain[-lookback:]
    return all(x > y for x, y in zip(recent, recent[1:]))


def process_position_state(position):
    """
    Updates a single position with profit_chain tracking and close_signal logic.
    Returns updated position.
    """
    symbol = position.get("symbol")
    max_chain_length = autotrade_config.get_param(
        symbol, "min_ticks_to_hold", fallback=10)

    updated = update_position_profit_chain(
        position, max_chain_length=max_chain_length)

    if check_trailing_retrace(updated) or check_failed_bounce(updated):
        updated["CLOSE_SIGNAL"] = True
    else:
        updated["CLOSE_SIGNAL"] = False
    return updated


def process_all_positions(positions):
    """
    Applies profit tracking and signal logic to a list of positions.
    Returns updated list.
    """
    enrich_positions_with_risk(positions)
    # return [process_position_state(deepcopy(pos)) for pos in positions]
    return [process_position_state(pos) for pos in positions]
# End of position_state_tracker.py
