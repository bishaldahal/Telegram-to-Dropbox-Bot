from pyrogram.types import CallbackQuery
from pyrogram.errors import RPCError
from bot import LOGGER
from ..filetocloud import CloudBot

logger = LOGGER(__name__)


async def download_media(client: CloudBot, message: CallbackQuery ) -> str:
    # print("CL: ", client)
    # print("Mess: ",message)
    user_message = await client.edit_message_text(
        chat_id=message.from_user.id,
        message_id=message.message.id,
        text="processing your request...",
    )
    try:
        media_id = message.message.reply_to_message
        await user_message.edit_text("downloading started...")
        download_file_path = await client.download_media(media_id)
        return download_file_path
    except RPCError as e:
        logger.error(e)
        raise Exception(e)
