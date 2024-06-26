from pyrogram import filters
from bot.helpers.dbox_authorization import exchange_code_for_tokens
from bot import state
from bot.filetocloud import DropboxBot
import os

AUTHORIZED_USERS = [int(user_id) for user_id in os.environ.get("AUTHORIZED_USERS", "").split()]

@DropboxBot.on_message(filters.text & filters.private & filters.user(AUTHORIZED_USERS))
async def authorization_code_handler(client, message):
    # Assuming 'waiting_for_code' is a flag that indicates you're expecting an authorization code
    if state.waiting_for_code:
        print("Authorization Code Handler")
        code = message.text
        print("Code: ", code)
        access_token, refresh_token = exchange_code_for_tokens(code)
        if access_token and refresh_token:
            # Update stored tokens here
            await message.reply("Authorization successful.")
            # Reset the flag
            state.waiting_for_code = False
        else:
            await message.reply("Failed to authorize. Please check the code and try again.")


