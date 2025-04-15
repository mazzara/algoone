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

def log_open_trade(ticket, symbol, direction, volume, entry_price, indicators, rationale=None):
    journal = load_journal()
    journal[str(ticket)] = {
        "symbol": symbol,
        "direction": direction,
        "volume": volume,
        "entry_price": entry_price,
        "open_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "indicators": indicators,
        "rationale": rationale,
        "profit_chain": [],
        "peak_profit": 0,
        "closed": False
    }
    save_journal(journal)
    logger.info(f"[JOURNAL] Trade opened: {ticket} | {symbol} | {direction}")

def append_tracking(ticket, current_profit):
    journal = load_journal()
    ticket_str = str(ticket)
    if ticket_str in journal:
        trade = journal[ticket_str]
        trade["profit_chain"].append(current_profit)
        trade["peak_profit"] = max(trade["peak_profit"], current_profit)
        save_journal(journal)
    else:
        logger.warning(f"[JOURNAL] Tried to track unknown ticket {ticket}")

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

