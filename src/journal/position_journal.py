# src/portfolio/position_journal.py
import os
import json
import time
from datetime import datetime
from src.config import HARD_MEMORY_DIR
from src.logger_config import logger

JOURNAL_FILE = os.path.join(HARD_MEMORY_DIR, "position_journal.json")


def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[JOURNAL 8001] Failed to load journal: {e}")
    return {}

def save_journal(journal):
    try:
        with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(journal, f, indent=4)
        logger.info(f"[JOURNAL 8002] Journal saved to {JOURNAL_FILE}")
    except Exception as e:
        logger.error(f"[JOURNAL 8002] Failed to save journal: {e}")


def log_open_trade(
        ticket,
        symbol,
        direction,
        volume,
        entry_price,
        indicators,
        rationale=None,
        **kwargs):

    journal = load_journal()

    open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    open_dt = datetime.strptime(open_time, "%Y-%m-%d %H:%M:%S")

    journal_entry = {
        "symbol": symbol,
        "direction": direction,
        "volume": volume,
        "entry_price": entry_price,
        "open_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "open_hour": open_dt.hour,
        "open_weekday": open_dt.weekday(),
        "indicators": indicators,
        "rationale": rationale,
        "profit_chain": [],
        "peak_profit": 0,
        "closed": False
    }

    # Inject any optional kwargs directly into the journal entry
    for key, value in kwargs.items():
        if value is not None:
            journal_entry[key] = value

    journal[str(ticket)] = journal_entry
    save_journal(journal)
    logger.info(f"[JOURNAL] Trade opened: {ticket} | {symbol} | {direction}")


def append_tracking(ticket, price_open, price_current, pos_type):
    journal = load_journal()
    ticket_str = str(ticket)
    if ticket_str in journal:
        trade = journal[ticket_str]

        if price_open and price_current:
            if pos_type == "SELL":
                pct_profit = (price_open - price_current) / price_open * 100
            else:
                pct_profit = (price_current - price_open) / price_open * 100

            pct_profit = round(pct_profit, 6)

            # Selfnote: Remember — left this here for later production tuning.
            # Intended to use profit_chain filtered to meaningful movements only, filtering out micromovements.

            # profit_chain = trade.get("profit_chain", [])
            # if not profit_chain or abs(pct_profit - profit_chain[-1]) > 0.01:  # optional: skip noisy ticks
            #     profit_chain.append(pct_profit)
            #     trade["profit_chain"] = profit_chain
            #     trade["peak_profit"] = max(trade.get("peak_profit", pct_profit), pct_profit)

            trade["profit_chain"].append(pct_profit)
            trade["peak_profit"] = max(trade["peak_profit"], pct_profit)
        save_journal(journal)
    else:
        logger.warning(f"[JOURNAL 2053:90] Tried to track unknown ticket {ticket}")


def log_close_trade(ticket, close_reason, final_profit):
    journal = load_journal()
    ticket_str = str(ticket)
    if ticket_str in journal:
        trade = journal[ticket_str]
        trade["closed"] = True
        trade["close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade["close_reason"] = close_reason
        trade["final_profit"] = final_profit
        save_journal(journal)
        logger.info(f"[JOURNAL] Trade closed: {ticket} | Reason: {close_reason} | PnL: {final_profit}")
    else:
        logger.warning(f"[JOURNAL] Tried to close unknown ticket {ticket}")

