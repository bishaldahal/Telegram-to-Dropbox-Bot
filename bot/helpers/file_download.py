from pyrogram.types import CallbackQuery
from pyrogram.errors import RPCError
from bot import LOGGER, state
from ..filetocloud import CloudBot
from .display import progress

logger = LOGGER(__name__)

async def download_media(client: CloudBot, message: CallbackQuery) -> str:
    download_id = f"{message.message.chat.id}{message.message.reply_to_message_id}"
    # print (message)
    state.download_controller[download_id] = False  # Initialize cancellation flag

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
            progress_args=(user_message,)  # Pass user_message to progress
        )
        return download_file_path, True
    except Exception as e:  # Catch the cancellation exception
        if str(e) == "Cancellation requested":
            print("Download cancelled.")
            await user_message.edit_text("Download cancelled.")
            return None, False
            # Perform any cleanup if necessary
        else:
            logger.error(e)
            await user_message.edit_text("An error occurred.")
    finally:
        # Clean up the cancellation flag
        if download_id in state.download_controller:
            del state.download_controller[download_id]