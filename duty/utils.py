import os
import io
import logging
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
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
    If OAuth flow is required, returns (None, auth_url).
    Raises FileNotFoundError if credentials file is missing.
    """
    creds = None
    token_path = os.path.join(settings.BASE_DIR, TOKEN_FILE)

    # Load existing credentials
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or initiate OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            creds_path = os.path.join(settings.BASE_DIR, CREDENTIALS_FILE)
            if not os.path.exists(creds_path):
                msg = (
                    f"Google OAuth credentials file not found at {creds_path}."
                    " Please place your credentials.json in your project root or set GOOGLE_APPLICATION_CREDENTIALS."
                )
                logger.error(msg)
                raise FileNotFoundError(msg)

            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path,
                SCOPES,
                redirect_uri='http://127.0.0.1:8000/oauth2callback/'
            )
            if code:
                flow.fetch_token(code=code)
                creds = flow.credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            else:
                auth_url, _ = flow.authorization_url(prompt='consent')
                return None, auth_url

    service = build('drive', 'v3', credentials=creds)
    return service, None


def upload_file_to_drive(file, filename, code=None):
    """
    Upload a Django UploadedFile to Google Drive and return the file ID.
    Handles both TemporaryUploadedFile (disk-based) and InMemoryUploadedFile (memory-based)
    without leaving locked temp files on Windows.
    """
    service, auth_url = get_drive_service(code)
    if auth_url:
        return None, auth_url

    try:
        if hasattr(file, 'temporary_file_path'):
            file_path = file.temporary_file_path()
            media = MediaFileUpload(file_path, mimetype=file.content_type)
        else:
            file.seek(0)
            stream = io.BytesIO(file.read())
            stream.seek(0)
            media = MediaIoBaseUpload(stream, mimetype=file.content_type)

        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields='id')
            .execute()
        )

        file_id = uploaded.get('id')
        permission = {'type': 'anyone', 'role': 'reader'}
        try:
            service.permissions().create(fileId=file_id, body=permission).execute()
        except Exception as e:
            logger.warning(f"Failed to set permissions for file {file_id}: {e}")
            permissions = service.permissions().list(fileId=file_id).execute()
            has_reader = any(
                p for p in permissions.get('permissions', [])
                if p['type'] == 'anyone' and p['role'] == 'reader'
            )
            if not has_reader:
                logger.error(f"File {file_id} is not publicly viewable.")
                raise

        return file_id, None

    except FileNotFoundError:
        logger.error("Credentials file not found for Google Drive API.")
        raise
    except Exception:
        logger.exception("Error uploading file to Google Drive")
        raise


def get_drive_file_url(file_id):
    """
    Generate a direct-download link for a Drive file so the browser
    treats it as an image and doesn’t block it.
    """
    if not file_id:
        logger.error("File ID is None or empty.")
        return None

    # Return the raw image bytes rather than an HTML “view” wrapper
    return f"https://docs.google.com/uc?export=download&id={file_id}"
