import sys
from bot.filetocloud import CloudBot, filters
import os

AUTHORIZED_USERS = [int(user_id) for user_id in os.environ.get("AUTHORIZED_USERS", "").split()]

@CloudBot.on_message(filters.command("restart") & filters.private & filters.user(AUTHORIZED_USERS))
async def restart(client, message):
    print(message)
    await client.send_message(
        chat_id=message.chat.id,
        text="Restarting the bot...",
        reply_to_message_id=message.id,
    )
    # Restart the bot by exiting the process
    sys.exit(42)