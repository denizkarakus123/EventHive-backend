from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json
import os

# Define the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_credentials():
    """Get credentials for Gmail API, refreshing them if needed."""
    # Check if token.json exists
    if os.path.exists('token.json'):
        # Load credentials from token.json
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        # Refresh the token if it's expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the updated token back to token.json
            with open('token.json', 'w') as token_file:
                token_data = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }
                json.dump(token_data, token_file)
        return creds

    # If no token.json exists, initiate OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=8000, access_type='offline', prompt='consent')

    # Save the credentials, including the refresh token, to token.json
    with open('token.json', 'w') as token_file:
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        json.dump(token_data, token_file)

    return creds

if __name__ == "__main__":
    creds = get_credentials()
    print("Token is valid and ready to use.")
