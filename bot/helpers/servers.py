from bot import LOGGER, DROPBOX_APP_KEY, DROPBOX_APP_SECRET
from ..filetocloud import CloudBot
from ..helpers import download_media
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from hurry.filesize import size
import dropbox 
from dropbox.exceptions import ApiError
from dropbox.files import CommitInfo, UploadSessionCursor,WriteMode
from dropbox.sharing import SharedLinkSettings, RequestedVisibility, LinkAudience
import os
import datetime
import time
from bot.helpers.dbox_authorization import refresh_access_token,get_auth_url
from bot import state
from bot.env import update_env_file
from ..helpers.display import progress

logger = LOGGER(__name__)

link = ""

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


async def upload_large_file(dbx, file_path, dropbox_path, message):
    with open(file_path, "rb") as f:
        file_size = os.path.getsize(file_path)
        chunk_size = 4 * 1024 * 1024  # 4 MB
        uploaded_bytes = 0

        try:
            upload_session_start_result = dbx.files_upload_session_start(f.read(chunk_size))
            cursor = UploadSessionCursor(session_id=upload_session_start_result.session_id, offset=f.tell())
            commit = CommitInfo(path=dropbox_path)
            await progress(uploaded_bytes, file_size, message.message)

            while f.tell() < file_size:
                if (file_size - f.tell()) <= chunk_size:
                    print("Finishing upload...")
                    dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit)
                    uploaded_bytes += chunk_size
                    await progress(uploaded_bytes, file_size, message.message)

                else:
                    print("Uploading chunk...")
                    dbx.files_upload_session_append_v2(f.read(chunk_size), cursor)
                    cursor.offset = f.tell()
                    uploaded_bytes += chunk_size
                    await progress(uploaded_bytes, file_size, message.message)


            # Adjust the shared link settings for view-only access
            link_settings = SharedLinkSettings(
                requested_visibility=RequestedVisibility.public,
                audience=LinkAudience.public
            )

            # Create a shared link with the specified settings
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path, link_settings)
            print("Shared link:", shared_link_metadata.url)
            return shared_link_metadata.url

        except ApiError as e:
            print(f"API error: {e}")
            if 'shared_link_already_exists' in str(e):
                # Attempt to get the existing shared link if it already exists
                shared_links = dbx.sharing_list_shared_links(dropbox_path).links
                if shared_links:
                    return shared_links[0].url
            raise
        except Exception as e:
            print(f"Error: {e}")
            raise

FILE_SIZE_THRESHOLD = 1 * 1024 * 1024  # 150 MB

async def upload_handler(client: CloudBot, message: CallbackQuery, callback_data: str):
    global link
    dbx = dropbox.Dropbox(os.getenv('DROPBOX_ACCESS_TOKEN') or "Your_Default_Access_Token")

    # Determine the file type and size
    if message.message.reply_to_message.video:
        file_name = message.message.reply_to_message.video.file_name
        file_size_bytes = message.message.reply_to_message.video.file_size
    elif message.message.reply_to_message.document:
        file_name = message.message.reply_to_message.document.file_name
        file_size_bytes = message.message.reply_to_message.document.file_size
    elif message.message.reply_to_message.audio:
        file_name = message.message.reply_to_message.audio.file_name
        file_size_bytes = message.message.reply_to_message.audio.file_size
    else:
        await client.send_message(
            chat_id=message.message.chat.id,
            text="Unsupported file type.",
            reply_to_message_id=message.message.reply_to_message.id
        )
        return

    file_size = size(file_size_bytes)  # Convert bytes to a readable format

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
            text="Started uploading...",
            message_id=message.message.id
            # reply_markup=completedKeyboard(dl)
        )

        if callback_data.startswith('dropbox'):
            print("Filepath: ", file_path)
            # Check if the file size exceeds the threshold
            if file_size_bytes > FILE_SIZE_THRESHOLD:
                print("Using chunked upload for large file.")
                response = await upload_large_file(dbx=dbx, file_path=file_path, dropbox_path=f"/{file_name}", message=message)
            else:
                print("Using regular upload.")
                response = upload_dbox(dbx=dbx, path=file_path, overwrite=False)
            link = response

        await client.send_message(
            chat_id=message.message.chat.id,
            text=(f"✅ **Upload Successful**\n\n"
                  f"File Name: `{file_name}`"
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
            DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
            new_access_token, _ = refresh_access_token(DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET)
            dbx = dropbox.Dropbox(new_access_token)
            update_env_file('DROPBOX_ACCESS_TOKEN', new_access_token)

            # Retry the upload or other operation
        except Exception as refresh_error:
            # Handle refresh token expiration or failure
            logger.error(f"Refresh Token Error: {refresh_error}")
            auth_url = "https://www.dropbox.com/oauth2/authorize?client_id={}&response_type=code".format(DROPBOX_APP_KEY)
            set_waiting_for_code(True)
            await client.send_message(
                chat_id=message.message.chat.id,
                text="Refresh Token expired too.\n After authorizing, please paste the authorization code you receive here.",
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

