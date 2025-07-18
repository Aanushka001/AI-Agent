from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',  # make sure this file is in the same folder or use full path
    scopes=SCOPES
)
creds = flow.run_local_server(port=0)

print("Access Token:", creds.token)
print("Refresh Token:", creds.refresh_token)
print("Client ID:", creds.client_id)
print("Client Secret:", creds.client_secret)
