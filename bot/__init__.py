import sys
import time
import logging
from logging.handlers import RotatingFileHandler

try:
    if sys.platform != "win32":
        import uvloop
        uvloop.install()
except ImportError:
    pass

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("adsbot.log", maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("motor").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

__version__ = "1.0.0"

from config import Config

config = Config()
config.check()
tasks = []
boot = time.time()

from bot.core.bot import Bot
app = Bot()

from bot.core.mongo import MongoDB
db = MongoDB()

from bot.core.session import SessionManager
session_manager = SessionManager()


async def stop():
    logger.info("Stopping...")
    for task in tasks:
        task.cancel()
        try:
            await task
        except Exception:
            pass
    await app.exit()
    await db.close()
    logger.info("Stopped.")
