
from bot.filetocloud import CloudBot, filters
from pyrogram.types import CallbackQuery
from bot import state

@CloudBot.on_callback_query(filters.regex(r'^cncl'))
async def handle_cancel(client: CloudBot, query: CallbackQuery):
    _, upload_id = query.data.split('+')
    upload_id = int(upload_id)  # Convert to int, assuming message_id is used as upload_id

    # Set the cancellation flag
    state.upload_controller[upload_id] = True

    await query.message.edit_text("Upload cancelled.")
    await query.answer("Cancelled", show_alert=True)