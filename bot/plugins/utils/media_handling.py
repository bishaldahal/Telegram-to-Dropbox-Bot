from ...filetocloud import DropboxBot, filters
from bot import LOGGER
from ...helpers import upload_handler
import os

AUTHORIZED_USERS = [int(user_id) for user_id in os.environ.get("AUTHORIZED_USERS", "").split()]

VIDEO = filters.video & filters.user(AUTHORIZED_USERS)
DOCUMENT = filters.document & filters.user(AUTHORIZED_USERS)
AUDIO = filters.audio & filters.user(AUTHORIZED_USERS)

logger = LOGGER(__name__)


@DropboxBot.on_message(VIDEO)
async def user_video(client, bot):
    logger.info(f"{bot.chat.id} - {bot.video.file_name}")
    await upload_handler(client, bot)


@DropboxBot.on_message(DOCUMENT)
async def user_document(client, bot):
    logger.info(f"{bot.chat.id} - {bot.document.file_name}")
    await upload_handler(client, bot)



@DropboxBot.on_message(AUDIO)
async def user_audio(client, bot):
    logger.info(f"{bot.chat.id} - {bot.audio.file_name}")
    await upload_handler(client, bot)

