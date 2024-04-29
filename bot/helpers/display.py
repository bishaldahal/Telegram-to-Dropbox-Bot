from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import time
from datetime import timedelta, datetime
from ..helpers.timedata import time_data
from bot import LOGGER, state

logger = LOGGER(__name__)
# Assuming you have a global dictionary to track the last edit times for each message
last_edit_time = {}

async def progress(current, total, message: Message):
    download_id = f"{message.chat.id}{message.reply_to_message_id}"
    global start_time
    if state.download_controller.get(download_id):
        raise Exception("Cancellation requested")
    
    if 'start_time' not in globals():
        start_time = time.time()  # Reset start time for each new download

    if current == total:
        await message.edit(text="Upload/Download completed")
        return
    
    # Check if we can edit the message now or need to wait
    now = datetime.now()
    if download_id in last_edit_time:
        elapsed_since_last_edit = now - last_edit_time[download_id]
        if elapsed_since_last_edit < timedelta(seconds=10):  # Adjust the seconds based on your needs
            return  # Skip this update to avoid hitting the rate limit

    time_now = time.time()
    time_diff = max(time_now - start_time, 0.1)
    percent = round(current * 100 / total, 2)
    progress_str = progressBar(percent)
    speed = current / time_diff
    eta = timedelta(seconds=int((total - current) / speed)) if speed > 0 else "Unknown"
    elapsed = timedelta(seconds=int(time_diff))

    progress_details = f"{progress_str} {percent}%\n" \
                       f"{human_readable_size(current)} of {human_readable_size(total)}\n" \
                       f"Speed: {human_readable_size(speed)}/s\n" \
                       f"ETA: {eta}\n" \
                       f"Elapsed: {elapsed}"

    try:
        await message.edit(
                text=progress_details,
                reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Cancel!", f"cncl+{message.chat.id}{message.reply_to_message_id}")]]
                ))
        last_edit_time[download_id] = now 
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        # Consider handling specific exceptions or limiting the frequency of updates to avoid spamming edits

def progressBar(percent):
    done_block = '█'
    empty_block = '░'
    done_blocks = int(percent // 5)
    empty_blocks = 20 - done_blocks
    return f"{done_block * done_blocks}{empty_block * empty_blocks}"

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"