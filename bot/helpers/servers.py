from bot import LOGGER, DROPBOX_APP_KEY, DROPBOX_APP_SECRET
from ..filetocloud import CloudBot
from ..helpers import download_media
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from hurry.filesize import size
import dropbox 
import os
import datetime
import time
from bot.helpers.dbox_authorization import refresh_access_token,exchange_code_for_tokens,get_auth_url
from bot import state

logger = LOGGER(__name__)

link = ""
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN', "Your_Default_Access_Token")
DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN', "Your_Default_Refresh_Token")


def set_waiting_for_code(value: bool):
    # Somewhere in servers.py, when you need to set waiting_for_code to True
    state.waiting_for_code = True
    return state.waiting_for_code


def upload_dbox(dbx, path, overwrite=False):
    """Upload a file to Dropbox.

    :param dbx: Dropbox instance.
    :param path: Full path to the file to upload.
    :return: Dropbox file upload response or None in case of error.
    """

    # Calculate the relative path 
    relative_path = os.path.relpath(path)
    # Replace backslashes with forward slashes for Dropbox compatibility
    dropbox_path = "/" + relative_path.replace("\\", "/")

    # Ensure the Dropbox path does not start with '/../'
    if dropbox_path.startswith("/../"):
        dropbox_path = dropbox_path[3:]

    print("Dropbox Path: ", dropbox_path)
    print("Relative Path: ", relative_path)
    print("Path: ", path)
    
    # Checking file existence and mode (overwrite or add)
    mode = dropbox.files.WriteMode.overwrite if overwrite else dropbox.files.WriteMode.add
    
    # Getting file modification time
    mtime = os.path.getmtime(path)
    
    # Reading file data
    with open(path, 'rb') as f:
        data = f.read()
    
    # Uploading file
    try:
        res = dbx.files_upload(
            data, dropbox_path, mode,
            client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
            mute=True)
        print("Uploaded as", res.name.encode('utf8'))

        # Adjust the shared link settings for view-only access
        link_settings = dropbox.sharing.SharedLinkSettings(
            requested_visibility=dropbox.sharing.RequestedVisibility.public,
            audience=dropbox.sharing.LinkAudience.public
        )

        # Create a shared link with the specified settings
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path, link_settings)
        print("Shared link:", shared_link_metadata.url)
    except dropbox.exceptions.BadInputError as e:
        logger.error(f"Bad Input Error: {e}")
        raise e
    except dropbox.exceptions.ApiError as e:
        logger.error(f"API Error: {e}")
        if e.error.is_shared_link_already_exists():
            # Get the existing shared link
            shared_link_metadata = dbx.sharing_list_shared_links(dropbox_path).links[0]
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e
    
    print('Uploaded as', res.name.encode('utf8'))
    return shared_link_metadata.url


async def upload_handler(client: CloudBot, message: CallbackQuery, callback_data: str):
    global link
    dbx = dropbox.Dropbox(os.getenv('DROPBOX_ACCESS_TOKEN') or DROPBOX_ACCESS_TOKEN)

    if message.message.reply_to_message.video:
        file_name = message.message.reply_to_message.video.file_name
        file_size = size(message.message.reply_to_message.video.file_size)
    elif message.message.reply_to_message.document:
        file_name = message.message.reply_to_message.document.file_name
        file_size = size(message.message.reply_to_message.document.file_size)
    elif message.message.reply_to_message.audio:
        file_name = message.message.reply_to_message.audio.file_name
        file_size = size(message.message.reply_to_message.audio.file_size)

    try:
        file_path = await download_media(client, message)
    except Exception as e:
        logger.error(f"{e}")
        await client.edit_message_text(
            chat_id=message.from_user.id,
            message_id=message.message.id,
            text=f"**File downloading error:** `{e}`",
        )
        return
    try:
        await client.edit_message_text(
            chat_id=message.message.chat.id,
            text="started uploading...",
            message_id=message.message.id
            # reply_markup=completedKeyboard(dl)
        )

        if callback_data.startswith('dropbox'):
            print("Filepath: ",file_path)
            response = upload_dbox(dbx=dbx, path=file_path,overwrite=False)
            link = response

        await client.send_message(
            chat_id=message.message.chat.id,
            text=(f"File Name: `{file_name}`"
                  f"\nFile Size: `{file_size}`"
                  f'\nURL: `{link}`'),
            reply_to_message_id=message.message.reply_to_message.id
        )
        await client.delete_messages(
            chat_id=message.message.chat.id,
            message_ids=message.message.id
        )
    except dropbox.exceptions.AuthError as e:
        # Assuming AuthError is raised on token expiration
        try:
            print("Refreshing token...")
            print("Error: ", e)
            print("Old Access Token: ", DROPBOX_ACCESS_TOKEN, "\nOld Refresh Token: ", DROPBOX_REFRESH_TOKEN, "\nApp Key: ", DROPBOX_APP_KEY, "\nApp Secret: ", DROPBOX_APP_SECRET)
            DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
            new_access_token, _ = refresh_access_token(DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET)
            dbx = dropbox.Dropbox(new_access_token)
            # Retry the upload or other operation
        except Exception as refresh_error:
            # Handle refresh token expiration or failure
            logger.error(f"Refresh Token Error: {refresh_error}")
            auth_url = "https://www.dropbox.com/oauth2/authorize?client_id={}&response_type=code".format(DROPBOX_APP_KEY)
            set_waiting_for_code(True)
            await client.send_message(
                chat_id=message.message.chat.id,
                text="Session expired. Please reauthorize the bot.\n After authorizing, please paste the authorization code you receive here.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Authorize", url=auth_url)]
                ])
            )
            return
    except dropbox.exceptions.BadInputError as e:
        logger.error(f"BBBBBAAAADDDD, {e}")
        try:
            print("Refreshing token...")
            auth_url = get_auth_url()
            set_waiting_for_code(True)
            await client.send_message(
                chat_id=message.message.chat.id,
                text="Session expired. Please reauthorize the bot. After authorizing, please paste the authorization code you receive here.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Authorize", url=auth_url)]
                ])
            )
        except Exception as auth_error:
            logger.error(f"{auth_error}")
            await client.send_message(
                chat_id=message.message.chat.id,
                text="Failed to reauthorize the bot. Please try again later."
            )
        return
    except Exception as e:
        logger.error(f'Normal error:{e}')
        await client.edit_message_text(
            chat_id=message.from_user.id,
            message_id=message.message.id,
            text=f"**File upload failed:** `{e}`",
        )
        return

async def file_io(response):
    return response['link']

