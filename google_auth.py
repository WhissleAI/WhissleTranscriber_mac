from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
import datetime
import sys
import os

class GoogleAuthManager:
    # If modifying scopes, delete the token.pickle file
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/userinfo.email'
    ]

    def __init__(self):
        self.creds = None
        self.token_path = 'token.pickle'
        
        # Handle bundled resources in the app
        if getattr(sys, 'frozen', False):
            # Running in a bundle
            bundle_dir = os.path.dirname(sys.executable)
            self.credentials_path = os.path.join(
                bundle_dir, 
                '../Resources/google_client_secret.json'
            )
        else:
            # Running in development
            self.credentials_path = 'google_client_secret.json'

    def get_credentials(self):
        """Gets valid user credentials from storage or initiates OAuth2 flow."""
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        raise FileNotFoundError(
                            f"Credentials file not found at: {self.credentials_path}"
                        )
                    
                    # Configure the OAuth flow for desktop application
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, 
                        self.SCOPES,
                        redirect_uri='http://localhost:0'  # Use dynamic port
                    )
                    
                    # Run local server with specific configurations
                    self.creds = flow.run_local_server(
                        port=0,  # Let the OS pick an available port
                        prompt='consent',  # Force consent screen
                        authorization_prompt_message="Please authorize in your browser",
                        success_message="Authorization successful! You can close this window.",
                        open_browser=True
                    )
                
                # Save the credentials for the next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)

            return self.creds
            
        except Exception as e:
            print(f"Error in get_credentials: {str(e)}")
            if "invalid_client" in str(e):
                print("Invalid client error - check OAuth configuration")
            elif "invalid_request" in str(e):
                print("Invalid request error - check redirect URIs")
            raise

    def get_user_info(self):
        """Get user profile information."""
        service = build('oauth2', 'v2', credentials=self.creds)
        user_info = service.userinfo().get().execute()
        return user_info

    def get_calendar_events(self):
        """Get upcoming calendar events."""
        service = build('calendar', 'v3', credentials=self.creds)
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def get_gmail_messages(self):
        """Get recent Gmail messages."""
        service = build('gmail', 'v1', credentials=self.creds)
        results = service.users().messages().list(
            userId='me',
            maxResults=10
        ).execute()
        return results.get('messages', []) 