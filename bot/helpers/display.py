#!/usr/bin/env python3


from pyrogram.types import Message
import time
from ..helpers.timedata import time_data
from bot import LOGGER
logger = LOGGER(__name__)


start_time = time.time()

async def progress(current, total, message: Message, ):
    if current is total:
        await message.edit(
            text=f"Download completed"
        )
    await message.edit(
        text=f"start downloading..."
    )

    time_now = time.time()
    time_diff = time_now - start_time
    percent = round(current * 100 // total)
    progress_ = "{0} {1}%".format(
        progressBar(percent),
        f"{current * 100 / total:.1f}"
    )
    time_ = "Time: {0}".format(
        time_data(start_time)
    )
    
    speed_ = "Speed: {0}".format(
        human_readable_size(size=current / time_diff)
    )
    download_ = "{0} of {1}".format(
        human_readable_size(current),
        human_readable_size(total)
    )
    try:
    
        await message.edit(
            text=f"{progress_}\n{download_}\n{speed_}    {time_}"
        )
    
    except Exception as e:
        await message.edit(
            text=f"ERROR: {e}"
        )
        logger.error(f"Error updating download progress: {e}")



def progressBar(percent):
    done_block = '█'
    empty_block = '░'
    return f"{done_block * int(percent / 5)}{empty_block * int(20 - int(percent / 5))}"


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f}{unit}"
