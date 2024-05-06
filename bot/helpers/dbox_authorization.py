import os
import dropbox
import requests
from bot import state, LOGGER, DROPBOX_APP_KEY, DROPBOX_APP_SECRET
from dropbox import DropboxOAuth2FlowNoRedirect
from bot.env import update_env_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = LOGGER(__name__)

auth_flow = DropboxOAuth2FlowNoRedirect(DROPBOX_APP_KEY, DROPBOX_APP_SECRET,token_access_type='offline')

def refresh_access_token(refresh_token, app_key, app_secret):
    url = "https://api.dropbox.com/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": app_key,
        "client_secret": app_secret,
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        new_tokens = response.json()
        new_access_token = new_tokens["access_token"]
        new_refresh_token = new_tokens.get("refresh_token", refresh_token)  # Refresh token may not change
        print("New Access Token: ", new_access_token)
        print("New Refresh Token: ", new_refresh_token)

                # Update stored tokens
        update_env_file('DROPBOX_ACCESS_TOKEN', new_access_token)
        update_env_file('DROPBOX_REFRESH_TOKEN', new_refresh_token)
        

        return new_access_token, new_refresh_token
    elif response.status_code == 400:
        logger.error("Failed to refresh access token: Bad request")
        raise dropbox.exceptions.AuthError("Bad request", response.status_code)
    elif response.status_code == 401:
        logger.error("Failed to refresh access token: Unauthorized")
        raise dropbox.exceptions.AuthError("Unauthorized", response.status_code)
    else:
        logger.error("Error: Failed to refresh access token")
        raise Exception("Failed to refresh access token")
        
def get_auth_url():
    auth_url = auth_flow.start()
    return auth_url

def exchange_code_for_tokens(auth_code):
    try:
        oauth_result = auth_flow.finish(auth_code)
        # Update stored tokens
        update_env_file('DROPBOX_ACCESS_TOKEN', oauth_result.access_token)
        update_env_file('DROPBOX_REFRESH_TOKEN', oauth_result.refresh_token)
        
        return oauth_result.access_token, oauth_result.refresh_token
    except Exception as e:
        logger.error(f"Error SDK: {e}")
        return None, None


def set_waiting_for_code(value: bool):
    state.waiting_for_code = True
    return state.waiting_for_code

    
async def refresh_access_token_if_needed(dbx, message, client):
    try:
        dbx.check_user()
    except dropbox.exceptions.AuthError:
        try:
            DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
            new_access_token, _ = refresh_access_token(DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET)
            dbx = dropbox.Dropbox(new_access_token)
            update_env_file('DROPBOX_ACCESS_TOKEN', new_access_token)
        except dropbox.exceptions.AuthError:
            await handle_auth_error(message, client)
    return dbx

async def handle_auth_error(message, client):
    try:
        # auth_url = "https://www.dropbox.com/oauth2/authorize?client_id={}&response_type=code".format(DROPBOX_APP_KEY)
        auth_url = get_auth_url()
        set_waiting_for_code(True)
        await client.send_message(
            chat_id=message.chat.id,
            text="Refresh Token expired too.\n After authorizing, please paste the authorization code you receive here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Authorize", url=auth_url)]
            ])
        )
    except Exception as refresh_error:
        logger.error(f"Refresh Token Error: {refresh_error}")
        await handle_bad_input_error(message, client)

async def handle_bad_input_error(message, client):
    try:
        print("Refreshing token...")
        auth_url = get_auth_url()
        set_waiting_for_code(True)
        await client.send_message(
            chat_id=message.chat.id,
            text="Session expired. Please reauthorize the bot. After authorizing, please paste the authorization code you receive here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Authorize", url=auth_url)]
            ])
        )
    except Exception as auth_error:
        logger.error(f"{auth_error}")
        await client.send_message(
            chat_id=message.chat.id,
            text="Failed to reauthorize the bot. Please try again later."
        )
