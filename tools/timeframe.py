import MetaTrader5 as mt5

# Define the mapping of timeframes with their minute values
TIMEFRAMES = [
    (mt5.TIMEFRAME_M1, 1),
    (mt5.TIMEFRAME_M2, 2),
    (mt5.TIMEFRAME_M3, 3),
    (mt5.TIMEFRAME_M4, 4),
    (mt5.TIMEFRAME_M5, 5),
    (mt5.TIMEFRAME_M6, 6),
    (mt5.TIMEFRAME_M10, 10),
    (mt5.TIMEFRAME_M12, 12),
    (mt5.TIMEFRAME_M15, 15),
    (mt5.TIMEFRAME_M20, 20),
    (mt5.TIMEFRAME_M30, 30),
    (mt5.TIMEFRAME_H1, 60),
    (mt5.TIMEFRAME_H2, 120),
    (mt5.TIMEFRAME_H3, 180),
    (mt5.TIMEFRAME_H4, 240),
    (mt5.TIMEFRAME_H6, 360),
    (mt5.TIMEFRAME_H8, 480),
    (mt5.TIMEFRAME_H12, 720),
    (mt5.TIMEFRAME_D1, 1440),
    (mt5.TIMEFRAME_W1, 10080),
    (mt5.TIMEFRAME_MN1, 43200)
]

# Convert to a dictionary for easy lookup
TIMEFRAME_MAP = {tf[1]: tf[0] for tf in TIMEFRAMES}
TIMEFRAME_VALUES = sorted(TIMEFRAME_MAP.keys())  # Sorted list of available timeframes


def get_timeframe(current_timeframe: int, step: int = 0):
    """
    Get the appropriate MT5 timeframe.
    
    Parameters:
        current_timeframe (int): The current timeframe in minutes.
        step (int): The number of levels to move up (positive) or down (negative).

    Returns:
        int: Corresponding MT5 timeframe ID, or None if out of range.
    """
    if current_timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Invalid timeframe: {current_timeframe} minutes")

    idx = TIMEFRAME_VALUES.index(current_timeframe)

    # Compute new index with boundary check
    new_idx = max(0, min(len(TIMEFRAME_VALUES) - 1, idx + step))

    return TIMEFRAME_MAP[TIMEFRAME_VALUES[new_idx]]


# Example usage

# get_timeframe(5, 2)   # Moves two levels up → Returns TIMEFRAME_M10
# get_timeframe(30, -1) # Moves one level down → Returns TIMEFRAME_M20
# get_timeframe(1, -2)  # Moves two levels down (stays at lowest) → Returns TIMEFRAME_M1
# get_timeframe(1440, 1) # Moves one level up from 1 day → Returns TIMEFRAME_W1 (1 week)




if __name__ == "__main__":
    timeframe = 5  # 5-minute timeframe
    print("Same:", get_timeframe(timeframe, 0))      # Same timeframe
    print("One level down:", get_timeframe(timeframe, -1))  # One level lower (4 min)
    print("One level up:", get_timeframe(timeframe, 1))     # One level higher (6 min)
    print("Two levels up:", get_timeframe(timeframe, 2))    # Two levels higher (10 min)
    print("Three levels down:", get_timeframe(timeframe, -3))  # Three levels lower (1 min)

