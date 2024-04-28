from bot import DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_ACCESS_TOKEN, DROPBOX_REFRESH_TOKEN
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
import requests
from bot.env import update_env_file

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
    else:
        raise Exception("Failed to refresh token")
    
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
        print('ErrorSDK: %s' % (e,))
        return None, None
