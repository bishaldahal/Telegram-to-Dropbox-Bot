
from bot.filetocloud import DropboxBot, filters
from pyrogram.types import CallbackQuery
from bot import state

@DropboxBot.on_callback_query(filters.regex(r'^cncl'))
async def handle_cancel(client: DropboxBot, query: CallbackQuery):
    _, upload_id = query.data.split('+')
    print("Cancel!", upload_id)
    # Set the cancellation flag
    state.upload_controller[upload_id] = True
    state.download_controller[upload_id] = True
    state.download_status[upload_id] = "cancelled"

    await query.message.edit_text("Upload cancelled.")
    await query.answer("Cancelled", show_alert=False)