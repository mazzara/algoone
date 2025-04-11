import MetaTrader5 as mt5
from dotenv import load_dotenv
import os
from src.logger_config import logger


load_dotenv()


def connect():
    """
    Connects to the MetaTrader 5 terminal using credentials from .env file.

    Requires the following environment variables:
    YES!! You do have to create a .env file for your own with credentials.
    It is not in the repo. So create it at root level.
    The .env file should contain:
        MT5_BROKER_LOGIN=your_login
        MT5_BROKER_SERVER=your_server
        MT5_BROKER_PASSWORD=your_password

    Provides feedback on connection issues.

    4 digit function signature: 0417
    """
    try:
        login_raw = os.getenv('MT5_BROKER_LOGIN')
        server = os.getenv('MT5_BROKER_SERVER', "").strip()
        password = os.getenv('MT5_BROKER_PASSWORD', "").strip()

        # Validate login
        if not login_raw:
            logger.error(
                "[ERROR 0417] :: "
                "MT5_BROKER_LOGIN is missing in the .env file.")
            return False
        try:
            login = int(login_raw.strip())
        except ValueError:
            logger.error(
                f"[ERROR 0417] :: "
                f"MT5_BROKER_LOGIN '{login_raw}' is not a valid integer."
            )
            return False

        # Validate the remaining credentials
        if not server:
            logger.error(
                "[ERROR 0417] :: "
                "MT5_BROKER_SERVER is missing or empty in the .env file."
            )
            return False
        if not password:
            logger.error(
                "[ERROR 0417] :: "
                "MT5_BROKER_PASSWORD is missing or empty in the .env file."
            )
            return False

        # Initialize MT5 terminal
        if not mt5.initialize(login=login, server=server, password=password):
            error_code, error_msg = mt5.last_error()
            logger.error(
                f"[ERROR 0417] :: "
                f"Failed to initialize MT5: {error_code} - {error_msg}"
            )
            handle_connection_error(error_code, server, login)
            return False

        # Successful initialization log
        logger.info(
            "[INFO 0417] :: "
            f"Ok. Connected to MetaTrader5 | Server: {server} | Login: {login}"
        )

        account_info = mt5.account_info()
        if account_info:
            logger.info(
                "[INFO 0417] :: "
                f"Account Info: {account_info}"
            )
        else:
            logger.warning(
                "[WARNING 0417] :: "
                "Connected, but failed to retrieve account info."
            )

        return True

    except Exception as e:
        logger.exception(
            "[EXCEPTION 0417] :: "
            f"Unexpected error during connection: {e}"
        )
        return False


def disconnect():
    """
    Closes the MT5 connection safely.

    4 digit function signature: 0429
    """
    mt5.shutdown()
    logger.info(
        "[INFO 0429] :: "
        "Disconnected from MetaTrader 5"
    )


def handle_connection_error(error_code, server, login):
    """
    Provides feedback on connection issues.

    4 digit function signature: 0431
    """
    if error_code == -6:
        logger.error(
            "[ERROR 0431] :: "
            "Authorization failed. Check your credentials."
        )
        logger.error(
            "[ERROR 0431] :: "
            f"Server: {server}, Login: {login}"
        )
        logger.error(
            "[ERROR 0431] :: "
            "Check for: Invalid credentials, server down, or invalid server."
        )
    elif error_code == 5:
        logger.error(
            "[ERROR 0431] :: "
            "No connection to trade server. Check your internet connection."
        )
    elif error_code == 10014:
        logger.error(
            "[ERROR 0431] :: "
            "Terminal not connected or already closed."
        )
    else:
        logger.warning(f"[WARNING 0431] :: Connection error: {error_code}")


# Run connection test
if __name__ == "__main__":
    if connect():
        print(mt5.terminal_info())  # Display connection info
        disconnect()

