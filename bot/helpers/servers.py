from bot import LOGGER
from ..filetocloud import CloudBot
from ..helpers import download_media
from pyrogram.types import Message
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

FILE_SIZE_THRESHOLD = 1 * 1024 * 1024  # 150 MB

def is_file_uploaded(dbx, dropbox_path):
    try:
        dbx.files_get_metadata(dropbox_path)
        return True
    except dropbox.exceptions.ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            return False
        else:
            raise e

async def attempt_upload(dbx, file_path, dropbox_path, upload_message, file_size_bytes, file_name,message):
    try:
        # Try to get metadata for the file
        metadata= dbx.files_get_metadata(dropbox_path)
        logger.info(f"Metadata: {metadata}")
        return "File already uploaded."
    except dropbox.exceptions.ApiError as e:
        # If the file doesn't exist, an ApiError will be thrown
        if e.error.is_path() and \
                e.error.get_path().is_not_found():
            if file_size_bytes > FILE_SIZE_THRESHOLD:
                print("Using chunked upload for large file.")
                response = await upload_large_file(dbx=dbx, file_path=file_path, dropbox_path=f"/{file_name}", message=message, upload_message=upload_message)
            else:
                print("Using regular upload.")
                response = upload_dbox(dbx=dbx, path=file_path, overwrite=False)
            return response
        else:
            raise e

async def upload_handler(client: CloudBot, message: Message):
    global link
    dbx = dropbox.Dropbox(os.getenv('DROPBOX_ACCESS_TOKEN') or "Your_Default_Access_Token")
    dbx = await refresh_access_token_if_needed(dbx, message, client)

    # Determine the file type and size
    if message.video:
        file_name = message.video.file_name
        file_size_bytes = message.video.file_size
    elif message.document:
        file_name = message.document.file_name
        file_size_bytes = message.document.file_size
    elif message.audio:
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

    if is_file_uploaded(dbx, f"/{file_name}"):
        await client.send_message(
            chat_id=message.chat.id,
            text="File already uploaded.",
            reply_to_message_id=message.id
        )
        return

    download_successful = False
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
            link = await attempt_upload(dbx, file_path, f"/{file_name}", upload_message, file_size_bytes, file_name, message)
            if link == "Cancelled":
                return

            await client.send_message(
                chat_id=message.chat.id,
                text=(f"✅ **Upload Successful**\n\n"
                    f"File Name: `{file_name}`"
                    f"\nFile Size: `{file_size}`"
                    f'\nURL: `{link}`'),
                reply_to_message_id=message.id
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

async def file_io(response):
    return response['link']

