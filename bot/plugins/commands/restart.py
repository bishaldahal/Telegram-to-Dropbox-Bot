import sys
from bot.filetocloud import CloudBot, filters

# Example command handler for restarting
@CloudBot.on_message(filters.command("restart"))
async def restart(client, message):
    print(message)
    await client.send_message(
        chat_id=message.chat.id,
        text="Restarting the bot...",
        reply_to_message_id=message.id,
    )
    # Restart the bot by exiting the process
    sys.exit(42)