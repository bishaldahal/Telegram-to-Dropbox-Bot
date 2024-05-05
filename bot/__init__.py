#!/usr/bin/env python3
import logging
from .env import get_env
from logging.handlers import RotatingFileHandler
import time

API_ID = get_env('API_ID')
API_HASH = get_env('API_HASH')
BOT_TOKEN = get_env('BOT_TOKEN')
DROPBOX_ACCESS_TOKEN = get_env('DROPBOX_ACCESS_TOKEN')
DROPBOX_REFRESH_TOKEN = get_env('DROPBOX_REFRESH_TOKEN')
DROPBOX_APP_KEY = get_env('DROPBOX_APP_KEY')
DROPBOX_APP_SECRET = get_env('DROPBOX_APP_SECRET')

class GlobalState:
    def __init__(self):
        self.start_times = {}
        self.last_edit_times = {}
        self.waiting_for_code = False
        self.upload_controller = {}
        self.download_controller = {}
        self.bot_start_time = time.time()
        self.download_status = {}

    def get_start_time(self, download_id, default=None):
        return self.start_times.get(download_id, default)

    def set_start_time(self, download_id, start_time):
        self.start_times[download_id] = start_time

    def remove_start_time(self, download_id):
        if download_id in self.start_times:
            del self.start_times[download_id]

    def update_last_edit_time(self, download_id, edit_time):
        self.last_edit_times[download_id] = edit_time

    def is_time_to_update(self, download_id, now):
        if download_id not in self.last_edit_times:
            self.last_edit_times[download_id] = now
            return True
        last_edit = self.last_edit_times[download_id]
        if (now - last_edit).total_seconds() > 5:  # Adjust the threshold as needed
            return True
        return False

# Create a global instance of the state
state = GlobalState()


# Messages
START = "\n\n**~~This bot uploads telegram files to Dropbox. \n\n**"
ERROR = "Something went wrong\n{error}"
HELP = "\n\nUsage: **Send any file. Then select the third-party Cloud you want to upload to.**"
CLEAR_AUTH = "Authentication tokens have been cleared."


# LOGGER

LOGGER_FILE_NAME = "DropboxUploader_log.txt"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOGGER_FILE_NAME, maxBytes=50000000, backupCount=10),
        logging.StreamHandler()
    ])
logging.getLogger('pyrogram').setLevel(logging.WARNING)


def LOGGER(log: str) -> logging.Logger:
    """Logger function"""
    return logging.getLogger(log)
