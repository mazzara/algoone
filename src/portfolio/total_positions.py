# total_positions.py
import MetaTrader5 as mt5
from src.logger_config import logger
import json
import os
import time
from datetime import datetime
from src.positions.positions import get_positions
from src.config import HARD_MEMORY_DIR, TOTAL_POSITIONS_FILE, POSITIONS_FILE

total_positions_cache = {}


def load_cached_positions(retries=3, delay=0.2):
    """
    Loads cached positions from 'hard_memory/positions.json'.
    """
    logger.info("Loading cashed positions................")

    if not os.path.exists(POSITIONS_FILE):
        logger.warning('No cashed positions found. File not found.')
        get_positions()
        time.sleep(delay)
        logger.info('Positions just pulled from MT5.')
        return load_cached_positions(retries=retries, delay=delay)

    file_age = time.time() - os.path.getmtime(POSITIONS_FILE)
    logger.info(f'Check cached-expire positions age: {file_age:.2f} seconds')

    if file_age > 10: # 10 seconds old
        logger.warning('Cashed positions are outdated.')
        get_positions()
        time.sleep(delay)
        logger.info('Positions just pulled from MT5.')
        return load_cached_positions(retries=retries, delay=delay)

    for attempt in range(retries):
        try:
            with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
                positions = json.load(f)
            if 'positions' in positions:
                logger.info(f"Positions loaded from cache: {len(positions)}")
                return positions['positions']
            else:
                logger.warning(f"Loaded JSON does not contain 'positions' key. Retrying...")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Retry {attempt+1}/{retries}: Failed to load cached positions: {e}")
            time.sleep(delay)

    logger.error('Failed to load cached positions after multiple attempts.')
    return []


def get_total_positions(save=True, use_cache=True):
    """
    Calculates the total volume and profit of all open positions.
    """
    global total_positions_cache

    if use_cache and total_positions_cache:
        logger.info("Using cached total positions.")
        logger.info(f"Total positions: {total_positions_cache}")
        save_total_positions(total_positions_cache)
        return total_positions_cache

    if not mt5.initialize():
        logger.error("MT5 is disconnected. Returning empty positions.")
        return {}  # Avoids the NoneType error

    logger.info("Calculating total positions...")
    positions = load_cached_positions()

    if positions is None or len(positions) == 0:
        logger.warning('No positions found. Returning empty summary.')
        return {}

    logger.info(f"Total positions loaded from cache: {len(positions)}")
    if positions is None:
        logger.warning('No cashed positions found. Verify to pull postions from MT5.')
        return None

    summary = {}

    for pos in positions:
        symbol = pos['symbol']
        position_type = "LONG" if pos['type'] == "BUY" else "SHORT"
        volume = pos['volume']
        price_open = pos['price_open']
        price_current = pos['price_current']
        profit = pos['profit']
        time_open = pos['time_open']

        if symbol not in summary:
            summary[symbol] = {
                "LONG": {"SIZE_SUM": 0,
                         "AVG_PRICE": 0,
                         "POSITION_COUNT": 0,
                         "CURRENT_PRICE": price_current,
                         "UNREALIZED_PROFIT": 0,
                         "LAST_POSITION_TIME": None},
                "SHORT": {"SIZE_SUM": 0,
                          "AVG_PRICE": 0,
                          "POSITION_COUNT": 0,
                          "CURRENT_PRICE": price_current,
                          "UNREALIZED_PROFIT": 0,
                          "LAST_POSITION_TIME": None},
            }

        side_data = summary[symbol][position_type]
        side_data["SIZE_SUM"] += volume
        side_data["POSITION_COUNT"] += 1
        side_data["UNREALIZED_PROFIT"] += profit

        if side_data["LAST_POSITION_TIME"] is None or time_open > side_data["LAST_POSITION_TIME"]:
            side_data["LAST_POSITION_TIME"] = time_open

        # side_data["LAST_POSITION_TIME"] = datetime.utcnow().timestamp()

        # side_data["LAST_POSITION_TIME"] = max(side_data["LAST_POSITION_TIME"],
        #                                       time_open) if side_data["LAST_POSITION_TIME"] else time_open
        #
        # Update weighted average price
        total_size = side_data["SIZE_SUM"]
        if total_size > 0:
            side_data["AVG_PRICE"] = ((side_data["AVG_PRICE"] * (total_size - volume)) + (price_open * volume)) / total_size
        # side_data["AVG_PRICE"] = ((side_data["AVG_PRICE"] * (total_size - volume)) + (price_open * volume)) / total_size

    logger.info(f"Total positions calculated for {symbol}.")

    total_positions_cache = summary

    if save:
        save_total_positions(summary)

    return summary


def save_total_positions(summary):
    """
    Saves the summarized positions to 'hard_memory/total_positions.json'.
    """
    logger.info("Saving total positions...")
    logger.info(f"Total positions: {summary}")

    try:
        with open(TOTAL_POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)
        logger.info(f"Total positions saved to {TOTAL_POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save total positions: {e}")


if __name__ == "__main__":
    logger.info("Starting total_positions.py...")
    summary = get_total_positions(save=True)
    if summary:
        save_total_positions(summary)
        logger.info("total_positions.py completed.")
        print(json.dumps(summary, indent=4))
    else:
        logger.error("total_positions.py failed.")

# End of total_positions.py
