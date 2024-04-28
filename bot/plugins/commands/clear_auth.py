from bot.filetocloud import CloudBot, filters
from bot import CLEAR_AUTH
from bot.env import clear_auth

@CloudBot.on_message(filters.command("clear_auth"))
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
    