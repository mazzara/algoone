import MetaTrader5 as mt5
from dotenv import load_dotenv
import os
from src.logger_config import logger

load_dotenv()

def connect():
    """
    Connects to the MetaTrader 5 terminal using credentials from .env file.
    """
    try:
        login = int(os.getenv('MT5_PP_DEMO_LOGIN', 0))
        server = os.getenv('MT5_PP_DEMO_SERVER', "").strip()
        password = os.getenv('MT5_PP_DEMO_PASSWORD', "").strip()

        if login == 0 or not server or not password:
            logger.error("Missing MT5 credentials. Check your .env file.")
            return False

        if not mt5.initialize(login=login, server=server, password=password):
            logger.error(f"Failed to initialize MT5: {mt5.last_error()}")
            return False

        logger.info("Connected to MetaTrader 5")
        return True  # Connection successful

    except Exception as e:
        logger.exception(f"Unexpected error during connection: {e}")
        return False


def disconnect():
    """
    Closes the MT5 connection safely.
    """
    mt5.shutdown()
    logger.info("Disconnected from MetaTrader 5")


# Run connection test
if __name__ == "__main__":
    if connect():
        print(mt5.terminal_info())  # Display connection info
        disconnect()

