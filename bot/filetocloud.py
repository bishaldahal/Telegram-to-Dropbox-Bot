
from pyrogram import *
import datetime
from bot import (
    BOT_TOKEN,
    API_ID,
    API_HASH,
    LOGGER
)

class DropboxBot(Client):
    def __init__(self):
        name = self.__class__.__name__.lower()
        self.logger = LOGGER(__name__)

        super().__init__(
            name,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={
                "root": "bot/plugins"
            },
            workers=6,
            max_concurrent_transmissions=3
        )
        self.counter = 0
        self.DOWNLOAD_WORKERS = 4

    async def start(self):
        await super().start()
        self.logger.info(f"BOT IS STARTED {datetime.datetime.now()}")

    async def stop(self, *args):
        await super().stop()
        self.logger.info(f"BOT IS STOPPED {datetime.datetime.now()}")
