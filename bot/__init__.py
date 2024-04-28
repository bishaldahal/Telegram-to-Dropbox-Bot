#!/usr/bin/env python3
import logging
from .env import get_env
from logging.handlers import RotatingFileHandler

API_ID = get_env('API_ID')
API_HASH = get_env('API_HASH')
BOT_TOKEN = get_env('BOT_TOKEN')
DROPBOX_ACCESS_TOKEN = get_env('DROPBOX_ACCESS_TOKEN')
DROPBOX_REFRESH_TOKEN = get_env('DROPBOX_REFRESH_TOKEN')
DROPBOX_APP_KEY = get_env('DROPBOX_APP_KEY')
DROPBOX_APP_SECRET = get_env('DROPBOX_APP_SECRET')

# global_state.py
class GlobalState:
    def __init__(self):
        self.waiting_for_code = False

# Create a global instance of the state
state = GlobalState()


# Messages
START = "\n\n**~~This bot uploads telegram files to Dropbox. \n\n**"
ERROR = "Something went wrong\n{error}"
HELP = "\n\nUsage: **Send any file or bot. Then select the third-party Cloud you want to upload to.**"


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
