# src/portfolio/total_positions.py
from src.logger_config import logger
import json
import os
import time
# from src.positions.positions import get_positions
from src.data.loaders import fetch_mt5_positions as get_positions
from src.portfolio.position_state_tracker import enrich_positions_with_risk
from src.positions.positions import update_last_closed_timestamps


from src.config import (
    TOTAL_POSITIONS_FILE,
    POSITIONS_FILE,
    CLOSE_PROFIT_THRESHOLD,
    TRAILING_PROFIT_THRESHHOLD
)

############################################################
# Functions Summary in this module - why this?
# to sign if a module gets too overcrowded with functions,
# indicating need to refactoring
############################################################
# load_cached_positions(retries=3, delay=0.2)
# get_total_positions(save=True, use_cache=True)
# save_total_positions(summary)


total_positions_cache = {}
# total_positions_cache = get_total_positions(save=True, use_cache=False)


def load_cached_positions(retries=3, delay=0.2, depth=0):
    """
    Loads cached positions from 'hard_memory/positions.json'.
    4 digit function signature: 6747
    """
    if depth > 3:
        logger.error('[6747:00] :: Maximum retries reached. Returning empty list.')
        return []

    if not os.path.exists(POSITIONS_FILE):
        logger.debug('[6747:10] :: No cashed positions found. File not found.')
        get_positions()
        time.sleep(delay)
        logger.debug('[6747:20] :: Fallback: Positions just pulled from MT5.')
        return load_cached_positions(retries=retries, delay=delay, depth=depth+1)

    file_age = time.time() - os.path.getmtime(POSITIONS_FILE)

    logger.debug(
        f"[6747:30] :: "
        f"Check cached-expire positions age: {file_age:.2f} seconds"
    )

    if file_age > 10:      # X seconds old
        logger.debug('[6747:40] :: Cashed positions are outdated.')
        get_positions()
        time.sleep(delay)
        return load_cached_positions(retries=retries, delay=delay, depth=depth+1)

    for attempt in range(retries):
        try:
            with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
                positions = json.load(f)
            if 'positions' in positions:
                logger.info(
                    f"[6747:60[ :: "
                    f"Positions loaded from cache: {len(positions)}"
                )
                return positions['positions']
            else:
                logger.warning(
                    "[6747:70] :: "
                    "Loaded JSON doen't have 'positions' key. Retrying..."
                )
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(
                f"[6747:80] :: Retry {attempt+1}/{retries}: "
                f"Failed to load cached positions: {e}"
            )
            time.sleep(delay)

    logger.error('[6746:90] :: Multiple Failed to load cached positions.')
    return []


def load_total_positions_accounting():
    if os.path.exists(TOTAL_POSITIONS_FILE):
        try:
            with open(TOTAL_POSITIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load total positions: {e}")
    return {}



def aggregate_risk_by_symbol(positions: list) -> dict:
    """
    Aggregates total `risk_at_sl` per symbol and side from enriched positions.

    Args:
        positions (list): List of enriched position dicts

    Returns:
        dict: {symbol: {"LONG": float, "SHORT": float}}
    """
    risk_summary = {}

    for pos in positions:
        symbol = pos["symbol"]
        side = "LONG" if pos["type"] == "BUY" else "SHORT"
        risk = pos.get("risk_at_sl", 0.0)

        if symbol not in risk_summary:
            risk_summary[symbol] = {"LONG": 0.0, "SHORT": 0.0}
        risk_summary[symbol][side] += risk

    return risk_summary


def process_positions(positions):
    """
    Processes raw positions into detailed arrays for each symbol and side.
    """
    processed = {}
    for pos in positions:
        symbol = pos['symbol']
        side = "LONG" if pos['type'] == "BUY" else "SHORT"

        if symbol not in processed:
            processed[symbol] = {
                "LONG": {"TICKETS": [],
                         "SIZES": [],
                         "PRICES": [],
                         "CURRENT_PRICES": [],
                         "UNREALIZED_PROFITS": [],
                         "POSITION_TIMES": [],
                         "POSITION_TIMES_RAW": []},
                "SHORT": {"TICKETS": [],
                          "SIZES": [],
                          "PRICES": [],
                          "CURRENT_PRICES": [],
                          "UNREALIZED_PROFITS": [],
                          "POSITION_TIMES": [],
                          "POSITION_TIMES_RAW": []}
            }

        side_data = processed[symbol][side]
        side_data["TICKETS"].append(pos["ticket"])
        side_data["SIZES"].append(pos["volume"])
        side_data["PRICES"].append(pos["price_open"])
        side_data["CURRENT_PRICES"].append(pos["price_current"])
        side_data["UNREALIZED_PROFITS"].append(pos["profit"])
        side_data["POSITION_TIMES"].append(pos["time_open"])
        side_data["POSITION_TIMES_RAW"].append(pos["time_raw"])

    return processed


def aggregate_helper_compute_summary(processed):
    """
    Helper function to aggregate position data for a single symbol.
    """
    summary = {}
    for symbol, sides in processed.items():
        summary[symbol] = {}
        for side, data in sides.items():
            position_count = len(data["TICKETS"])
            size_sum = sum(data["SIZES"])
            # Compute weighted average price
            total_weight = sum(data["SIZES"])
            if total_weight > 0:
                weighted_sum = sum(
                    p * s for p, s in zip(data["PRICES"], data["SIZES"])
                )
                avg_price = weighted_sum / total_weight
            else:
                avg_price = 0

            unrealized_profit = sum(data["UNREALIZED_PROFITS"])

            summary[symbol][side] = {
                "SIZE_SUM": size_sum,
                "POSITION_COUNT": position_count,
                "AVG_PRICE": avg_price,
                "UNREALIZED_PROFIT": unrealized_profit,
            }
    return summary


def aggregate_helper_compute_time(processed):
    """
    Compute the most recent trade's time for each symbol/side.
    """
    summary = {}
    for symbol, sides in processed.items():
        summary[symbol] = {}
        for side, data in sides.items():
            if data["POSITION_TIMES_RAW"]:
                max_index = data["POSITION_TIMES_RAW"].index(max(data["POSITION_TIMES_RAW"]))
                last_position_time = data["POSITION_TIMES"][max_index]
                last_position_time_raw = data["POSITION_TIMES_RAW"][max_index]
                current_price = data["CURRENT_PRICES"][max_index]
            else:
                last_position_time = ""  # Using empty string to avoid None errors when formatting
                last_position_time_raw = 0
                current_price = None

            summary[symbol][side] = {
                "LAST_POSITION_TIME": last_position_time,
                "LAST_POSITION_TIME_RAW": last_position_time_raw,
                "CURRENT_PRICE": current_price,
            }
    return summary

def aggregate_position_data(processed):
    summary_values = aggregate_helper_compute_summary(processed)
    summary_times = aggregate_helper_compute_time(processed)

    summary = {}
    for symbol in processed.keys():
        summary[symbol] = {}
        for side in ('LONG', 'SHORT'):
            base = summary_values[symbol].get(side, {})
            times = summary_times[symbol].get(side, {})
            summary[symbol][side] = {**base, **times}

        # Compute NET side using same logic as before, but extracting from cleaned base
        long_data = summary[symbol].get("LONG", {})
        short_data = summary[symbol].get("SHORT", {})

        long_size = long_data.get("SIZE_SUM", 0)
        short_size = short_data.get("SIZE_SUM", 0)
        net_size = long_size - short_size
        net_count = long_data.get("POSITION_COUNT", 0) + short_data.get("POSITION_COUNT", 0)
        net_unrealized_profit = long_data.get("UNREALIZED_PROFIT", 0) + short_data.get("UNREALIZED_PROFIT", 0)

        if net_size != 0:
            weighted_long = long_size * long_data.get("AVG_PRICE", 0)
            weighted_short = short_size * short_data.get("AVG_PRICE", 0)
            net_weighted = weighted_long - weighted_short
            net_avg_price = net_weighted / net_size
        else:
            net_avg_price = 0

        # Net last update time
        if long_data.get("LAST_POSITION_TIME_RAW", 0) >= short_data.get("LAST_POSITION_TIME_RAW", 0):
            net_last_time = long_data.get("LAST_POSITION_TIME", "")
            net_last_time_raw = long_data.get("LAST_POSITION_TIME_RAW", 0)
            net_current_price = long_data.get("CURRENT_PRICE", None)
        else:
            net_last_time = short_data.get("LAST_POSITION_TIME", "")
            net_last_time_raw = short_data.get("LAST_POSITION_TIME_RAW", 0)
            net_current_price = short_data.get("CURRENT_PRICE", None)

        summary[symbol]["NET"] = {
            "SIZE_SUM": net_size,
            "POSITION_COUNT": net_count,
            "AVG_PRICE": net_avg_price,
            "CURRENT_PRICE": net_current_price,
            "UNREALIZED_PROFIT": net_unrealized_profit,
            "LAST_POSITION_TIME": net_last_time,
            "LAST_POSITION_TIME_RAW": net_last_time_raw,
        }

        # Compute NET risk
        net_risk = long_data.get("RISK_AT_SL", 0.0) + short_data.get("RISK_AT_SL", 0.0)
        summary[symbol]["NET"]["RISK_AT_SL"] = round(net_risk, 2)


    return summary


def merge_snapshot_into_history(snapshot_summary, historical_summary):
    for symbol, sides in snapshot_summary.items():
        if symbol not in historical_summary:
            # New symbol: take the snapshot and initialize extreme records.
            historical_summary[symbol] = sides
            for side in ('LONG', 'SHORT', 'NET'):
                if side in historical_summary[symbol]:
                    # Initialize extremes with the current total side position.
                    historical_summary[symbol][side]["PROFIT_RECORD_TRACK"] = historical_summary[symbol][side]["UNREALIZED_PROFIT"]
                    historical_summary[symbol][side]["LOSS_RECORD_TRACK"] = historical_summary[symbol][side]["UNREALIZED_PROFIT"]
                    historical_summary[symbol][side]["GOAL_MET"] = False
                    historical_summary[symbol][side]["TRAILING_CROSSED"] = False
                    historical_summary[symbol][side]["CLOSE_SIGNAL"] = False
        else:
            for side in ('LONG', 'SHORT', 'NET'):
                snap = sides.get(side, {})
                hist = historical_summary[symbol].get(side, {})

                if "RISK_AT_SL" in snap:
                    hist["RISK_AT_SL"] = snap["RISK_AT_SL"]

                # Initialize missing extreme fields with the current aggregated unrealized profit.
                if "PROFIT_RECORD_TRACK" not in hist:
                    hist["PROFIT_RECORD_TRACK"] = snap.get("UNREALIZED_PROFIT", 0)
                if "LOSS_RECORD_TRACK" not in hist:
                    hist["LOSS_RECORD_TRACK"] = snap.get("UNREALIZED_PROFIT", 0)

                # Update persistent extreme records based on the aggregated (total) unrealized profit.
                hist["PROFIT_RECORD_TRACK"] = max(
                    hist.get("PROFIT_RECORD_TRACK", snap.get("UNREALIZED_PROFIT", 0)),
                    snap.get("UNREALIZED_PROFIT", 0)
                )
                hist["LOSS_RECORD_TRACK"] = min(
                    hist.get("LOSS_RECORD_TRACK", snap.get("UNREALIZED_PROFIT", 0)),
                    snap.get("UNREALIZED_PROFIT", 0)
                )

                # Overwrite snapshot-dependent fields.
                hist["SIZE_SUM"] = snap["SIZE_SUM"]
                hist["POSITION_COUNT"] = snap["POSITION_COUNT"]
                hist["AVG_PRICE"] = snap["AVG_PRICE"]
                hist["CURRENT_PRICE"] = snap["CURRENT_PRICE"]
                hist["UNREALIZED_PROFIT"] = snap["UNREALIZED_PROFIT"]
                hist["LAST_POSITION_TIME"] = snap["LAST_POSITION_TIME"]
                hist["LAST_POSITION_TIME_RAW"] = snap["LAST_POSITION_TIME_RAW"]
    return historical_summary


def compute_target_profit(snap, threshold):
    size = snap.get("SIZE_SUM", 0)
    avg_price = snap.get("AVG_PRICE", 0)
    return size * avg_price * threshold


def get_total_positions(save=True, use_cache=True, report=False):
    """
    Finalizes the processing: builds the detailed snapshot from positions,
    aggregates them, and then updates persistent records as needed.
    """
    # Get the raw positions from cache or MT5
    positions = load_cached_positions()
    if not positions:
        logger.warning("No positions found. Returning empty summary.")
        return {}

    # Enrich with stop-loss risk
    positions = enrich_positions_with_risk(positions)

    # Load last known snapshot to infer closures
    prev_data = load_total_positions_accounting()
    prev_positions = prev_data.get("_last_positions", [])

    # Risk aggregation per symbol/side
    risk_summary = aggregate_risk_by_symbol(positions)

    processed = process_positions(positions)
    snapshot_summary = aggregate_position_data(processed)

    # Inject RISK_AT_SL after snapshot aggregation 
    for symbol in snapshot_summary:
        snapshot_summary[symbol]["LONG"]["RISK_AT_SL"] = round(risk_summary.get(symbol, {}).get("LONG", 0.0), 2)
        snapshot_summary[symbol]["SHORT"]["RISK_AT_SL"] = round(risk_summary.get(symbol, {}).get("SHORT", 0.0), 2)
        snapshot_summary[symbol]["NET"]["RISK_AT_SL"] = round(risk_summary.get(symbol, {}).get("LONG", 0.0) + risk_summary.get(symbol, {}).get("SHORT", 0.0), 2)

    # Inject RISK_AT_SL into snapshot summary
    # for symbol, sides in risk_summary.items():
    #     for side in ('LONG', 'SHORT'):
    #         if symbol in snapshot_summary and side in snapshot_summary[symbol]:
    #             snapshot_summary[symbol][side]["RISK_AT_SL"] = round(sides[side], 2)

    historical_summary = load_total_positions_accounting()

    historical_summary = merge_snapshot_into_history(
        snapshot_summary, historical_summary)

    historical_summary = update_last_closed_timestamps(
        prev_positions=prev_positions,
        current_positions=positions,
        total_summary=historical_summary
    )
    
    #  Save latest raw position state for next diff
    historical_summary["_last_positions"] = positions

    for symbol, sides in historical_summary.items():
        if symbol.startswith("_"):
            continue  # skip reserved metadata like _last_positions

        for side in ('LONG', 'SHORT', 'NET'):
            hist = sides.get(side, {})
            size = hist.get("SIZE_SUM", 0)
            # avg_price = hist.get("AVG_PRICE", 0)

            # Set/reset target profits
            if size == 0:
                hist.update({
                    "PROFIT_RECORD_TRACK": 0,
                    "LOSS_RECORD_TRACK": 0,
                    "PROFIT_GOAL": 0,
                    "TRAILING_PROFIT": 0,
                    "GOAL_MET": False,
                    "TRAILING_CROSSED": False,
                    "CLOSE_SIGNAL": False
                })
            else:
                hist["PROFIT_GOAL"] = compute_target_profit(hist, CLOSE_PROFIT_THRESHOLD)
                hist["TRAILING_PROFIT"] = compute_target_profit(hist, TRAILING_PROFIT_THRESHHOLD)
                hist["GOAL_MET"] = hist["UNREALIZED_PROFIT"] >= hist["PROFIT_GOAL"]
                hist["TRAILING_CROSSED"] = hist["UNREALIZED_PROFIT"] >= hist["TRAILING_PROFIT"]
                hist["CLOSE_SIGNAL"] = hist["GOAL_MET"] and hist["TRAILING_CROSSED"]

            sides[side] = hist  # reassign to ensure it's updated

    if save:
        save_total_positions(historical_summary)

    if report:
        logger.debug("[SUMMARY 1649] ====== POSITIONS - Total positions summary ======")
        for symbol, sides in snapshot_summary.items():
            logger.debug(f"[INFO 1649] Symbol: {symbol}")
            for side, data in sides.items():
                logger.debug(f"[INFO 1649]  {side}: {data}")

    return snapshot_summary


def save_total_positions(summary):
    """
    Saves the summarized positions to 'hard_memory/total_positions.json'.
    """
    logger.debug(f"[1749:20] :: Saving Total positions: {summary}")

    try:
        with open(TOTAL_POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)
        logger.debug(f"[1749:30] :: Total positions saved to {TOTAL_POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"[1749:40] :: Failed to save total positions: {e}")


if __name__ == "__main__":
    logger.info("Starting total_positions.py...")
    summary = get_total_positions(save=True, use_cache=False)
    if summary:
        total_positions_cache.clear()
        total_positions_cache.update(summary)
        save_total_positions(summary)
        logger.info("total_positions.py completed.")
        print(json.dumps(summary, indent=4))
    else:
        logger.error("total_positions.py failed.")

# End of total_positions.py
