from ...filetocloud import DropboxBot
from pyrogram.types import CallbackQuery
from ...helpers.servers import upload_handler


@DropboxBot.on_callback_query()
async def selecting_server(client: DropboxBot, message: CallbackQuery) -> None:
    callback_data = message.data
    await upload_handler(client, message, callback_data)
