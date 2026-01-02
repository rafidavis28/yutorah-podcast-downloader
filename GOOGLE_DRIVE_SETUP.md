# Google Drive Integration Setup

This guide will walk you through setting up Google Drive integration for the YUTorah Podcast Downloader.

## Prerequisites

- A Google account
- Access to Google Cloud Console
- Streamlit Cloud account (or local Streamlit setup)

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click "New Project"
4. Enter a project name (e.g., "YUTorah Podcast Downloader")
5. Click "Create"

## Step 2: Enable Google Drive API

1. In the Google Cloud Console, select your newly created project
2. Click on the hamburger menu (☰) → "APIs & Services" → "Library"
3. Search for "Google Drive API"
4. Click on "Google Drive API"
5. Click "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. In the Google Cloud Console, go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Click "Configure Consent Screen"
   - Choose "External" user type
   - Fill in the required fields:
     - App name: "YUTorah Podcast Downloader"
     - User support email: Your email
     - Developer contact information: Your email
   - Click "Save and Continue"
   - On the Scopes page, click "Save and Continue"
   - On Test users, add your email and any other users who will test the app
   - Click "Save and Continue"

4. Back on the Credentials page, click "Create Credentials" → "OAuth client ID" again
5. Choose "Web application" as the application type
6. Enter a name (e.g., "YUTorah Podcast Downloader Web Client")
7. Under "Authorized redirect URIs", add your Streamlit app URL:
   - For Streamlit Cloud: `https://your-app-name.streamlit.app`
   - For local development: `http://localhost:8501`

8. Click "Create"
9. Copy the "Client ID" and "Client Secret" that appear - you'll need these!

## Step 4: Configure Streamlit Secrets

### For Streamlit Cloud:

1. Go to your app's dashboard on Streamlit Cloud
2. Click on the three dots (⋮) next to your app
3. Select "Settings"
4. Go to the "Secrets" section
5. Add the following secrets:

```toml
YUTORAH_USERNAME = "your_yutorah_username"
YUTORAH_PASSWORD = "your_yutorah_password"
GOOGLE_CLIENT_ID = "your_google_client_id"
GOOGLE_CLIENT_SECRET = "your_google_client_secret"
GOOGLE_REDIRECT_URI = "https://your-app-name.streamlit.app"
```

### For Local Development:

1. Create a `.streamlit/secrets.toml` file in your project directory
2. Add the following content:

```toml
YUTORAH_USERNAME = "your_yutorah_username"
YUTORAH_PASSWORD = "your_yutorah_password"
GOOGLE_CLIENT_ID = "your_google_client_id"
GOOGLE_CLIENT_SECRET = "your_google_client_secret"
GOOGLE_REDIRECT_URI = "http://localhost:8501"
```

**Note:** Never commit the `secrets.toml` file to version control!

## Step 5: Publish Your OAuth App (Optional)

If you want to make the app available to all users (not just test users):

1. Go to "APIs & Services" → "OAuth consent screen"
2. Click "Publish App"
3. Confirm the publication

**Note:** For personal use or limited users, you can keep it in "Testing" mode.

## Step 6: Test the Integration

1. Start your Streamlit app
2. Click the "Sign in with Google" button in the sidebar
3. You'll be redirected to Google's consent page
4. Review and grant the requested permissions (Google Drive file access)
5. You'll be redirected back to your app
6. You should now see your email address in the sidebar
7. Try downloading a podcast - it should now upload to your Google Drive!

## Troubleshooting

### "Redirect URI mismatch" error

- Make sure the redirect URI in your Google Cloud Console exactly matches your Streamlit app URL
- For Streamlit Cloud, use the full URL including `https://`
- Don't add trailing slashes

### "Access blocked: This app's request is invalid"

- Make sure you've added yourself as a test user in the OAuth consent screen
- Check that the Google Drive API is enabled

### "Invalid client" error

- Double-check that your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
- Make sure there are no extra spaces in your secrets file

### App keeps asking me to sign in

- This can happen if your session state is being cleared
- Try refreshing the page
- Check your browser's cookie settings

## Security Notes

- Never share your Client Secret publicly
- Keep your `secrets.toml` file out of version control
- Regularly review the apps with access to your Google account
- Consider using a separate Google account for testing

## Support

If you encounter any issues:
1. Check the Streamlit app logs for error messages
2. Verify all credentials are correct
3. Make sure all required APIs are enabled
4. Review the OAuth consent screen configuration

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Drive API Documentation](https://developers.google.com/drive)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management)
