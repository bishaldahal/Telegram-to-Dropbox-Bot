#!/usr/bin/env python3
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def server_select(file_size: int):
    upload_selection = [
        [
            InlineKeyboardButton(
                "dropbox.com",
                callback_data=f"dropbox"
            )
        ],
    ]
    if file_size < 1e+8:
        # 1e+8 is 100000000.0
        upload_selection.append([
            InlineKeyboardButton(
                "File.io",
                callback_data=f"fileio"
            )
        ])
    return InlineKeyboardMarkup(upload_selection)
