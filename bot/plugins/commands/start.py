from bot.filetocloud import DropboxBot, filters
from bot import START

@DropboxBot.on_message(filters.command("start"))
async def start_message(client, message):
    await client.send_message(
        chat_id=message.chat.id,
        text=f"Hey {message.from_user.first_name},{START}",
        reply_to_message_id=message.id,
    )
