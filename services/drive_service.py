import os
import time 
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import settings  #  Added configuration injection

# Rules defined by Google to allow Read/Write access to files
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """
    Handles the secure OAuth2 connection handshake and returns a valid
    Google Drive API service client.
    """
    creds = None
    # token.json handles session persistence so browser doesn't open every time
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "Missing 'credentials.json' in root directory. "
                    "Please download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def upload_pdf_to_drive(local_file_path: str, folder_id: str = None) -> str:
    """
    Uploads a local PDF to Google Drive, changes its permission to public view-only,
    and returns the direct webViewLink.
    """
    try:
        service = get_drive_service()
        file_name = os.path.basename(local_file_path)
        
        # 1. Define file metadata settings
        file_metadata = {
            'name': file_name,
            'mimeType': 'application/pdf'
        }
        
        #  Fallback to global setting if no folder_id is provided explicitly
        active_folder_id = folder_id or settings.GOOGLE_DRIVE_FOLDER_ID
        if active_folder_id:
            file_metadata['parents'] = [active_folder_id]
            
        media = MediaFileUpload(local_file_path, mimetype='application/pdf', resumable=True)
        
        #  Fixed: Corrected alignment indentation here
        print(f"[{time.strftime('%X')}] Uploading binary asset to Google Drive storage...")
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        file_id = file.get('id')
        
        print(f"[{time.strftime('%X')}] File uploaded successfully. File ID: {file_id}")
        
        # 2. Crucial Step: Change permission layer to 'Anyone with link can read'
        print(f"[{time.strftime('%X')}] Adjusting security rules to permission: Public View-Only...")
        public_permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(fileId=file_id, body=public_permission).execute()
        
        # 3. Retrieve the updated metadata including the webViewLink
        updated_file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
        drive_public_url = updated_file_info.get('webViewLink')
        
        print(f"[{time.strftime('%X')}] Asset tracking link secured: {drive_public_url}")
        return drive_public_url

    except Exception as e:
        print(f"Severe exception caught during Drive processing cycle: {str(e)}")
        raise e