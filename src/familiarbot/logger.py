import sys
from pathlib import Path

from loguru import logger as loguru_logger

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.familiarbot.i18n import get_text


def init():
    loguru_logger.debug("Logger initialized.")
    log_dir = ROOT_DIR / "log"
    log_dir.mkdir(exist_ok=True)
    loguru_logger.add(log_dir / "bot_errors.log", rotation="200 MB")

def log_and_reply(bot, message, lang, error_obj, log_context="Error"):
    """Handles sending the user an error message and logging the full traceback."""
    loguru_logger.exception(f"{log_context} for {message.from_user.id}: {error_obj}")
    bot.reply_to(message, get_text(lang, "error_saving"))

def log_exception(error_obj, log_context="Background Error"):
    """Logs the full traceback for background tasks (no user message to reply to)."""
    loguru_logger.exception(f"{log_context}: {error_obj}")

def error(msg):
    loguru_logger.error(msg)

def info(msg):
    loguru_logger.info(msg)

def debug(msg):
    loguru_logger.debug(msg)

if __name__ == "__main__":
    print("LOGGER TEST ENVIRONMENT ACTIVE")
    loguru_logger.debug("Test logger initialized.")
    log_dir = ROOT_DIR / "log"
    log_dir.mkdir(exist_ok=True)
    loguru_logger.add(log_dir / "fake_bot_errors.log", rotation="50 MB")

    try:
        1 / 0
    except Exception:
        loguru_logger.exception("Fake math error for testing")
        print(f"Successful. Your logs were saved to:\n{log_dir}")
