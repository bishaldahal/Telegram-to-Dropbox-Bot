from pyrogram.types import CallbackQuery
from pyrogram.errors import RPCError
from bot import LOGGER
from ..filetocloud import CloudBot
from .display import progress

logger = LOGGER(__name__)

async def download_media(client: CloudBot, message: CallbackQuery) -> str:
    user_message = await client.edit_message_text(
        chat_id=message.from_user.id,
        message_id=message.message.id,
        text="Processing your request...",
    )
    try:
        media_id = message.message.reply_to_message
        await user_message.edit_text("Downloading started...")
        download_file_path = await client.download_media(
            media_id,
            progress=progress,
            progress_args=(user_message,)  # Adjusted to pass user_message correctly
        )
        return download_file_path
    except RPCError as e:
        logger.error(e)
        raise Exception(e)