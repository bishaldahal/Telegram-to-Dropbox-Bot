from bot.filetocloud import DropboxBot, filters
from bot import HELP


@DropboxBot.on_message(filters.command(["help", "h"]))
async def help_message(client, message):
    print(message)
    await client.send_message(
        chat_id=message.chat.id,
        text=f"Hey {message.from_user.first_name},{HELP}",
        reply_to_message_id=message.id,
    )
