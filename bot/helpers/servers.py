from bot import LOGGER
from ..filetocloud import DropboxBot
from ..helpers import download_media
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from hurry.filesize import size
import dropbox 
from dropbox.exceptions import ApiError, AuthError, BadInputError
from dropbox.files import CommitInfo, UploadSessionCursor
import os
import datetime
import time
from bot.helpers.dbox_authorization import refresh_access_token_if_needed, handle_bad_input_error, handle_auth_error
from bot import state
from ..helpers.display import progress
from ..helpers.create_shared_link import create_shared_link

logger = LOGGER(__name__)

link = ""

def upload_dbox(dbx, path, dropbox_path, overwrite=False):
    """Upload a file to Dropbox.

    :param dbx: Dropbox instance.
    :param path: Full path to the file to upload.
    :return: Dropbox file upload response or None in case of error.
    """

    print("Dropbox Path: ", dropbox_path)
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

    except dropbox.exceptions.BadInputError as e:
        logger.error(f"Bad Input Error: {e}")
        raise e
    except dropbox.exceptions.ApiError as e:
        logger.error(f"API Error: {e}")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e
    # Create or retrieve a shared link
    shared_link_url = create_shared_link(dbx, dropbox_path)
    return shared_link_url


async def upload_large_file(dbx, file_path, dropbox_path, message, upload_message):
    upload_id = f"{message.chat.id}{message.id}"
    state.set_start_time(upload_id, time.perf_counter())

    with open(file_path, "rb") as f:
        file_size = os.path.getsize(file_path)
        chunk_size = 4 * 1024 * 1024  # 4 MB
        uploaded_bytes = 0

        try:
            upload_session_start_result = dbx.files_upload_session_start(f.read(chunk_size))
            cursor = UploadSessionCursor(session_id=upload_session_start_result.session_id, offset=f.tell())
            commit = CommitInfo(path=dropbox_path)
            await progress(uploaded_bytes, file_size, message, user_message=upload_message, operation="upload", )

            while f.tell() < file_size:
                 # Check if the upload has been cancelled
                if state.upload_controller.get(upload_id, False):
                    print("Upload cancelled.")
                    return "Cancelled"
                if (file_size - f.tell()) <= chunk_size:
                    print("Finishing upload...")
                    dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit)
                    uploaded_bytes += chunk_size
                    await progress(uploaded_bytes, file_size, message, user_message=upload_message, operation="upload")

                else:
                    print("Uploading chunk...")
                    dbx.files_upload_session_append_v2(f.read(chunk_size), cursor)
                    cursor.offset = f.tell()
                    uploaded_bytes += chunk_size
                    await progress(uploaded_bytes, file_size, message, user_message=upload_message, operation="upload")


            # Create or retrieve a shared link
            shared_link_url = create_shared_link(dbx, dropbox_path)
            return shared_link_url

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
        finally:
            # Clean up the cancellation flag
            if upload_id in state.upload_controller:
                del state.upload_controller[upload_id]
            if upload_id in state.start_times:
                del state.start_times[upload_id]

FILE_SIZE_THRESHOLD = 4 * 1024 * 1024  # 4 MB

def is_file_uploaded(dbx, dropbox_path):
    try:
        dbx.files_get_metadata(dropbox_path)
        return True
    except dropbox.exceptions.ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            return False
        else:
            raise e

async def attempt_upload(dbx, file_path, dropbox_path, upload_message, file_size_bytes, file_name, message):
    try:
        logger.info(f"File path: {file_path}, Dropbox path: {dropbox_path}, File size: {file_size_bytes}, File name: {file_name}")
        # Try to get metadata for the file
        metadata= dbx.files_get_metadata(dropbox_path)
        logger.info(f"Metadata: {metadata}")
        raise Exception("File already uploaded.")
    except dropbox.exceptions.ApiError as e:
        # If the file doesn't exist, an ApiError will be thrown
        if e.error.is_path() and \
                e.error.get_path().is_not_found():
            if file_size_bytes > FILE_SIZE_THRESHOLD:
                print("Using chunked upload for large file.")
                response = await upload_large_file(dbx, file_path, dropbox_path, message, upload_message)
            else:
                print("Using regular upload.")
                response = upload_dbox(dbx=dbx, path=file_path, dropbox_path=dropbox_path, overwrite=False)
            return response
        else:
            raise e

async def upload_handler(client: DropboxBot, message: Message):
    global link
    dbx = dropbox.Dropbox(os.getenv('DROPBOX_ACCESS_TOKEN') or "Your_Default_Access_Token")
    dbx = await refresh_access_token_if_needed(dbx, message, client)

    # Determine the file type and size
    if message.video:
        file_location = "Videos"
        file_name = message.video.file_name
        file_size_bytes = message.video.file_size
    elif message.document:
        file_location = "Files"
        file_name = message.document.file_name
        file_size_bytes = message.document.file_size
        #if file_name ends with video extension, then it is a video file
        if file_name and file_name.endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.3gp', '.webm')):
            file_location = "Videos"
        #if file_name ends with audio extension, then it is an audio file
        elif file_name and file_name.endswith(('.mp3', '.m4a', '.flac', '.wav', '.wma', '.aac', '.ogg', '.oga', '.opus')):
            file_location = "Audios"
    elif message.audio:
        file_location = "Audios"
        file_name = message.audio.file_name
        file_size_bytes = message.audio.file_size
    else:
        await client.send_message(
            chat_id=message.chat.id,
            text="Unsupported file type.",
            reply_to_message_id=message.id
        )
        return

    file_size = size(file_size_bytes)  # Convert bytes to a readable format
    dropbox_path = f"/{file_location}/{file_name}"

    if is_file_uploaded(dbx, dropbox_path):
        await client.send_message(
            chat_id=message.chat.id,
            text="File already uploaded.",
            reply_to_message_id=message.id
        )
        return

    download_successful = False
    file_path = os.path.join('bot/downloads', file_name)
    if os.path.exists(file_path):
        local_file_size = os.path.getsize(file_path)
        if local_file_size == file_size_bytes:
            download_successful = True

    if not download_successful:
        try:
            file_path, download_successful = await download_media(client, message)
            if not download_successful:
                logger.info("Download was cancelled. Skipping upload.")
                return
        except Exception as e:
            logger.error(f"{e}")
            await client.edit_message_text(
                chat_id=message.from_user.id,
                message_id=message.id,
                text=f"**File downloading error:** `{e}`",
            )
            return
    if download_successful:
        try:
            upload_message = await client.send_message(
                chat_id=message.chat.id,
                text="Started uploading...",
                reply_to_message_id=message.id
            )

            print("Filepath: ", file_path)
            # Initial upload attempt
            link = await attempt_upload(dbx, file_path, dropbox_path, upload_message, file_size_bytes, file_name, message)
            if link == "Cancelled":
                return

            await client.send_message(
                chat_id=message.chat.id,
                text=(f"✅ **Upload Successful**\n\n"
                    f"File Name: `{file_name}`"
                    f"\nFile Size: `{file_size}`"
                    f'\nURL: `{link}`'),
                reply_to_message_id=message.id,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Open Link", url=link)]]
                )
            )
            await upload_message.delete()
        except AuthError as e:
            await handle_auth_error(message, client)
        except BadInputError as e:
            await handle_bad_input_error(message, client)
        except Exception as e:
            logger.error(f'Normal error:{e} ')
            await client.send_message(
                chat_id=message.from_user.id,
                reply_to_message_id=message.id,
                text=f"**File upload failed:** `{e}`",
            )
            return

