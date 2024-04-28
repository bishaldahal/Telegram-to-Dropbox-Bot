from pyrogram import filters
from bot.helpers.dbox_authorization import exchange_code_for_tokens
from bot import state
from bot.filetocloud import CloudBot
# Handler for messages that might contain the authorization code

@CloudBot.on_message(filters.text & filters.private)
async def authorization_code_handler(client, message):
    print("Authorization Code Handler")
    # Assuming 'waiting_for_code' is a flag that indicates you're expecting an authorization code
    if state.waiting_for_code:
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


