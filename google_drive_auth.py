#!/usr/bin/env python3
"""
Google Drive Authentication and Upload Module

Handles OAuth2 authentication for Google Drive and file uploads.
"""

import os
import io
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import json


# Google OAuth2 settings
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Cookie manager will be set by app.py
_cookie_manager = None


def set_cookie_manager(cookie_manager):
    """
    Set the cookie manager for persistent authentication.

    Args:
        cookie_manager: streamlit_cookies_manager.CookieManager instance
    """
    global _cookie_manager
    _cookie_manager = cookie_manager

# OAuth credentials - these should be set in Streamlit secrets
# To get these:
# 1. Go to https://console.cloud.google.com/
# 2. Create a new project or select existing
# 3. Enable Google Drive API
# 4. Create OAuth 2.0 credentials (Web application)
# 5. Add authorized redirect URI: your streamlit app URL + ?auth_callback=1
# 6. Copy client_id and client_secret to Streamlit secrets


def get_google_oauth_flow():
    """
    Create and return a Google OAuth2 flow object.

    Returns:
        Flow object for OAuth2 authentication
    """
    # Check if credentials are in secrets
    if "GOOGLE_CLIENT_ID" not in st.secrets or "GOOGLE_CLIENT_SECRET" not in st.secrets:
        st.error("Google OAuth credentials not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to Streamlit secrets.")
        return None

    client_config = {
        "web": {
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    )

    return flow


def get_auth_url():
    """
    Get the Google OAuth2 authorization URL.

    Returns:
        Authorization URL string
    """
    flow = get_google_oauth_flow()
    if not flow:
        return None

    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # Store state in session for verification
    st.session_state.oauth_state = state

    return auth_url


def load_credentials_from_cookies():
    """
    Load credentials from cookies if available.

    Returns:
        Credentials dict or None
    """
    if _cookie_manager is None:
        return None

    try:
        creds_json = _cookie_manager.get('google_credentials')
        if creds_json:
            return json.loads(creds_json)
    except Exception as e:
        print(f"Error loading credentials from cookies: {e}")

    return None


def save_credentials_to_cookies(credentials_dict):
    """
    Save credentials to cookies for persistence.

    Args:
        credentials_dict: Dictionary representation of credentials
    """
    if _cookie_manager is None:
        return

    try:
        _cookie_manager['google_credentials'] = json.dumps(credentials_dict)
        _cookie_manager.save()
    except Exception as e:
        print(f"Error saving credentials to cookies: {e}")


def handle_oauth_callback(auth_code):
    """
    Handle the OAuth callback and exchange code for credentials.

    Args:
        auth_code: Authorization code from OAuth callback

    Returns:
        Credentials object or None
    """
    flow = get_google_oauth_flow()
    if not flow:
        return None

    try:
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials

        # Store credentials in session state
        creds_dict = credentials_to_dict(credentials)
        st.session_state.google_credentials = creds_dict
        st.session_state.google_authenticated = True

        # Save to cookies for persistence
        save_credentials_to_cookies(creds_dict)

        return credentials
    except Exception as e:
        st.error(f"Error during authentication: {e}")
        return None


def credentials_to_dict(credentials):
    """
    Convert Credentials object to dictionary for storage.

    Args:
        credentials: Credentials object

    Returns:
        Dictionary representation of credentials
    """
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


def dict_to_credentials(creds_dict):
    """
    Convert dictionary to Credentials object.

    Args:
        creds_dict: Dictionary representation of credentials

    Returns:
        Credentials object
    """
    return Credentials(
        token=creds_dict['token'],
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict['token_uri'],
        client_id=creds_dict['client_id'],
        client_secret=creds_dict['client_secret'],
        scopes=creds_dict['scopes']
    )


def get_drive_service():
    """
    Get an authenticated Google Drive service.

    Returns:
        Google Drive service object or None
    """
    if 'google_credentials' not in st.session_state:
        return None

    try:
        credentials = dict_to_credentials(st.session_state.google_credentials)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Error creating Drive service: {e}")
        return None


def get_user_info():
    """
    Get authenticated user's Google account information.

    Returns:
        Dictionary with user info or None
    """
    service = get_drive_service()
    if not service:
        return None

    try:
        about = service.about().get(fields="user").execute()
        return about.get('user', {})
    except Exception as e:
        st.error(f"Error getting user info: {e}")
        return None


def create_folder(folder_name, parent_folder_id=None):
    """
    Create a folder in Google Drive.

    Args:
        folder_name: Name of the folder to create
        parent_folder_id: ID of parent folder (None for root)

    Returns:
        Folder ID or None
    """
    service = get_drive_service()
    if not service:
        return None

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]

    try:
        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        return folder.get('id')
    except Exception as e:
        st.error(f"Error creating folder: {e}")
        return None


def find_or_create_folder(folder_name, parent_folder_id=None):
    """
    Find existing folder or create new one.

    Args:
        folder_name: Name of the folder
        parent_folder_id: ID of parent folder (None for root)

    Returns:
        Folder ID or None
    """
    service = get_drive_service()
    if not service:
        return None

    try:
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])

        if files:
            return files[0]['id']
        else:
            return create_folder(folder_name, parent_folder_id)
    except Exception as e:
        st.error(f"Error finding/creating folder: {e}")
        return None


def upload_file_to_drive(file_content, filename, folder_id=None, mime_type='audio/mpeg', description=None):
    """
    Upload a file to Google Drive.

    Args:
        file_content: File content as bytes
        filename: Name for the file
        folder_id: ID of folder to upload to (None for root)
        mime_type: MIME type of the file
        description: Optional description (used to store shiur ID for tracking)

    Returns:
        File info dict or None
    """
    service = get_drive_service()
    if not service:
        return None

    file_metadata = {
        'name': filename
    }

    if folder_id:
        file_metadata['parents'] = [folder_id]

    if description:
        file_metadata['description'] = description

    try:
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype=mime_type,
            resumable=True
        )

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, description'
        ).execute()

        return file
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None


def init_auth_from_cookies():
    """
    Initialize authentication from cookies if available.
    Call this at app startup to restore saved login state.
    """
    # Check if already authenticated in session
    if st.session_state.get('google_authenticated', False):
        return

    # Try to load from cookies
    creds_dict = load_credentials_from_cookies()
    if creds_dict:
        st.session_state.google_credentials = creds_dict
        st.session_state.google_authenticated = True


def is_authenticated():
    """
    Check if user is authenticated with Google Drive.

    Returns:
        Boolean indicating authentication status
    """
    # First check session state
    if st.session_state.get('google_authenticated', False):
        return True

    # If not in session, try to restore from cookies
    init_auth_from_cookies()

    return st.session_state.get('google_authenticated', False)


def list_files_in_folder(folder_id):
    """
    List all files in a Google Drive folder.

    Args:
        folder_id: ID of the folder to list files from

    Returns:
        List of file dictionaries with 'id', 'name', 'description' fields
    """
    service = get_drive_service()
    if not service:
        return []

    try:
        query = f"'{folder_id}' in parents and trashed=false"
        all_files = []
        page_token = None

        while True:
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, description)',
                pageToken=page_token,
                pageSize=100
            ).execute()

            all_files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')

            if not page_token:
                break

        return all_files
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def get_uploaded_shiur_ids(folder_id):
    """
    Get set of shiur IDs that have already been uploaded to a folder.
    Extracts shiur IDs from file descriptions (where we store them).

    Args:
        folder_id: ID of the folder to check

    Returns:
        Set of shiur ID strings
    """
    files = list_files_in_folder(folder_id)
    shiur_ids = set()

    for f in files:
        # Check description for shiur ID
        desc = f.get('description', '')
        if desc and desc.startswith('shiurID:'):
            shiur_id = desc.replace('shiurID:', '').strip()
            if shiur_id:
                shiur_ids.add(shiur_id)

    return shiur_ids


def sign_out():
    """
    Sign out from Google Drive and clear cookies.
    """
    # Clear session state
    if 'google_credentials' in st.session_state:
        del st.session_state.google_credentials
    if 'google_authenticated' in st.session_state:
        del st.session_state.google_authenticated
    if 'oauth_state' in st.session_state:
        del st.session_state.oauth_state

    # Clear cookies
    if _cookie_manager is not None:
        try:
            if 'google_credentials' in _cookie_manager:
                del _cookie_manager['google_credentials']
            _cookie_manager.save()
        except Exception as e:
            print(f"Error clearing cookies: {e}")
