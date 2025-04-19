import os
import tempfile
import logging

from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Scopes and file names
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
FOLDER_ID = '1AxWS1DvExOXDu5o-XG3eE1v-pF2N5rKM'  # Your folder ID

logger = logging.getLogger(__name__)


def get_drive_service(code=None):
    """
    Authenticate and return a Google Drive service object.
    Raises FileNotFoundError if credentials file is missing.
    If OAuth is required, returns (None, auth_url).
    """
    creds = None
    token_path = os.path.join(settings.BASE_DIR, TOKEN_FILE)

    # Load existing credentials
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Check validity
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            # Ensure credentials.json exists
            creds_path = os.path.join(settings.BASE_DIR, CREDENTIALS_FILE)
            if not os.path.exists(creds_path):
                msg = f"Google OAuth credentials file not found at {creds_path}. " \
                      "Please place your credentials.json in your project root or configure GOOGLE_APPLICATION_CREDENTIALS."
                logger.error(msg)
                raise FileNotFoundError(msg)

            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path,
                SCOPES,
                redirect_uri='http://localhost:8000/oauth2callback/'
            )
            if code:
                flow.fetch_token(code=code)
                creds = flow.credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            else:
                auth_url, _ = flow.authorization_url(prompt='consent')
                return None, auth_url

    # Build service
    service = build('drive', 'v3', credentials=creds)
    return service, None


def upload_file_to_drive(file, filename, code=None):
    """
    Upload a file to Google Drive and return the file ID.
    Raises FileNotFoundError if credentials missing.
    If OAuth needed, returns (None, auth_url).
    """
    try:
        service, auth_url = get_drive_service(code)
        if auth_url:
            return None, auth_url

        # Prepare MediaFileUpload
        if hasattr(file, 'temporary_file_path'):
            file_path = file.temporary_file_path()
            media = MediaFileUpload(file_path, mimetype=file.content_type)
        else:
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp.write(file.read())
                temp_path = temp.name
            media = MediaFileUpload(temp_path, mimetype=file.content_type)

        # Metadata and upload
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        # Clean up
        if not hasattr(file, 'temporary_file_path'):
            os.remove(temp_path)

        return uploaded.get('id'), None

    except FileNotFoundError:
        # Re-raise for view to handle and show message
        raise
    except Exception as e:
        logger.exception("Error uploading file to Google Drive")
        raise
