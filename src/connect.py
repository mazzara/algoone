import MetaTrader5 as mt5
from dotenv import load_dotenv
import os
from src.logger_config import logger

load_dotenv()

def connect():
    """
    Connects to the MetaTrader 5 terminal using credentials from .env file.
    Provides feedback on connection issues.
    """
    try:
        login_raw = os.getenv('MT5_PP_DEMO_LOGIN')
        server = os.getenv('MT5_PP_DEMO_SERVER', "").strip()
        password = os.getenv('MT5_PP_DEMO_PASSWORD', "").strip()

        # Validate login
        if not login_raw:
            logger.error("MT5_PP_DEMO_LOGIN is missing in the .env file.")
            return False
        
        try:
            login = int(login_raw.strip())
        except ValueError:
            logger.error(f"MT5_PP_DEMO_LOGIN '{login_raw}' is not a valid integer.")
            return False

        # Validate the remaining credentials
        if not server:
            logger.error("MT5_PP_DEMO_SERVER is missing or empty in the .env file.")
            return False
        if not password:
            logger.error("MT5_PP_DEMO_PASSWORD is missing or empty in the .env file.")
            return False

        # Initialize MT5 terminal
        if not mt5.initialize(login=login, server=server, password=password):
            error_code, error_msg = mt5.last_error()
            logger.error(f"Failed to initialize MT5: {error_code} - {error_msg}")
            handle_connection_error(error_code, server, login)
            return False

        # Successful initialization
        logger.info(f"Connected to MetaTrader 5 | Server: {server} | Login: {login}")

        account_info = mt5.account_info()
        if account_info:
            logger.info(f"Account Info: {account_info}")
        else:
            logger.warning("Connected, but failed to retrieve account info.")

        return True

    except Exception as e:
        logger.exception(f"Unexpected error during connection: {e}")
        return False


def disconnect():
    """
    Closes the MT5 connection safely.
    """
    mt5.shutdown()
    logger.info("Disconnected from MetaTrader 5")


def handle_connection_error(error_code, server, login):
    """
    Provides feedback on connection issues.
    """
    if error_code == -6:
        logger.error(f"Authorization failed. Check your credentials.")
        logger.error(f"Server: {server}, Login: {login}")
        logger.error("Possible causes: Invalid credentials, server down, or invalid server.")
    elif error_code == 5:
        logger.error("No connection to trade server. Check your internet connection.")
    elif error_code == 10014:
        logger.error("Terminal not connected or already closed.")
    else:
        logger.warning(f"Connection error: {error_code}")

# Run connection test
if __name__ == "__main__":
    if connect():
        print(mt5.terminal_info())  # Display connection info
        disconnect()

