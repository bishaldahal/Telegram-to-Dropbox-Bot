from bot.filetocloud import CloudBot, filters
from bot import CLEAR_AUTH
from bot.env import clear_auth
import os

AUTHORIZED_USERS = [int(user_id) for user_id in os.environ.get("AUTHORIZED_USERS", "").split()]

@CloudBot.on_message(filters.command("clear_auth") & filters.private & filters.user(AUTHORIZED_USERS))
async def clear_auth_command(client, message):
    print(message)
    if clear_auth():
        await client.send_message(
            chat_id=message.chat.id,
            text=CLEAR_AUTH,
            reply_to_message_id=message.id,
        )
    else:
        await client.send_message(
            chat_id=message.chat.id,
            text="Failed to clear the authentication tokens.",
            reply_to_message_id=message.id,
        )
    