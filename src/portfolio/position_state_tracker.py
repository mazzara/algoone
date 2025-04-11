# src/portfolio/position_state_tracker.py


from copy import deepcopy


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


def update_position_profit_chain(position, profit_step=0.01, max_chain_length=10):
    """
    Updates the profit_chain and peak_profit fields of a position.
    Modifies the position dict in-place.
    """

    profit = position.get("profit", 0.0)
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

    # Limit the lengh of the chain
    # if len(position["profit_chain"]) > max_chain_length:
    #     position["profit_chain"] = position["profit_chain"][-max_chain_length:]

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


def process_position_state(position):
    """
    Updates a single position with profit_chain tracking and close_signal logic.
    Returns updated position.
    """
    updated = update_position_profit_chain(position)
    if check_trailing_retrace(updated):
        updated["CLOSE_SIGNAL"] = True
    else:
        updated["CLOSE_SIGNAL"] = False
    return updated


def process_all_positions(positions):
    """
    Applies profit tracking and signal logic to a list of positions.
    Returns updated list.
    """
    # return [process_position_state(deepcopy(pos)) for pos in positions]
    return [process_position_state(pos) for pos in positions]
# End of position_state_tracker.py
