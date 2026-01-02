#!/usr/bin/env python3
"""
YUTorah Podcast Downloader - Streamlit Web Interface

A web interface for downloading podcast episodes from YUTorah RSS feeds.
"""

import streamlit as st
import json
import os
import time
from pathlib import Path
import xml.etree.ElementTree as ET
from download_podcasts import (
    fetch_rss_feed,
    extract_episode_links,
    extract_shiur_id,
    get_mp3_url_from_page,
    download_mp3,
    load_downloaded_shiurim,
    save_downloaded_shiurim,
    sanitize_filename,
    session
)
import google_drive_auth as gd
import streamlit_cookies_manager as cookies

# Configuration file for RSS feeds
FEEDS_CONFIG_FILE = 'rss_feeds.json'

# Default feeds
DEFAULT_FEEDS = {
    "Rav Moshe Taragin": "http://www.yutorah.org/rss/RssAudioOnly/teacher/80307",
}


def download_and_upload_to_drive(mp3_url, title, folder_id):
    """
    Download MP3 file and upload to Google Drive.

    Args:
        mp3_url: URL of the MP3 file
        title: Title of the episode
        folder_id: Google Drive folder ID to upload to

    Returns:
        Dictionary with file info or None
    """
    try:
        # Sanitize filename
        filename = sanitize_filename(title) + '.mp3'

        # Download the file content
        response = session.get(mp3_url, stream=True)
        response.raise_for_status()

        # Read content into memory
        file_content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_content += chunk

        # Upload to Google Drive
        file_info = gd.upload_file_to_drive(
            file_content,
            filename,
            folder_id=folder_id,
            mime_type='audio/mpeg'
        )

        return file_info

    except Exception as e:
        st.error(f"Error downloading/uploading {title}: {e}")
        return None


def load_feeds_config():
    """Load RSS feeds configuration from file."""
    if os.path.exists(FEEDS_CONFIG_FILE):
        try:
            with open(FEEDS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_FEEDS.copy()


def save_feeds_config(feeds):
    """Save RSS feeds configuration to file."""
    try:
        with open(FEEDS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(feeds, f, indent=2)
    except Exception as e:
        st.error(f"Error saving feeds configuration: {e}")


def main():
    st.set_page_config(
        page_title="YUTorah Podcast Downloader",
        page_icon="🎧",
        layout="wide"
    )

    # Initialize cookie manager for persistent authentication
    cookie_manager = cookies.CookieManager()
    gd.set_cookie_manager(cookie_manager)

    # Wait for cookie manager to be ready
    if not cookie_manager.ready():
        st.stop()

    # Initialize authentication from cookies
    gd.init_auth_from_cookies()

    st.title("🎧 YUTorah Podcast Downloader")
    st.markdown("Download shiurim from YUTorah RSS feeds")

    # Initialize session state
    if 'new_episodes' not in st.session_state:
        st.session_state.new_episodes = []
    if 'selected_episodes' not in st.session_state:
        st.session_state.selected_episodes = {}
    if 'feed_checked' not in st.session_state:
        st.session_state.feed_checked = False

    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Settings")

        # Google Drive Authentication
        st.subheader("☁️ Google Drive")

        # Handle OAuth callback
        query_params = st.query_params
        if 'code' in query_params:
            auth_code = query_params['code']
            gd.handle_oauth_callback(auth_code)
            # Clear query params
            st.query_params.clear()
            st.rerun()

        if gd.is_authenticated():
            user_info = gd.get_user_info()
            if user_info:
                st.success(f"✅ Signed in as: {user_info.get('emailAddress', 'Unknown')}")
            else:
                st.success("✅ Signed in to Google Drive")

            if st.button("🚪 Sign Out", use_container_width=True):
                gd.sign_out()
                st.rerun()
        else:
            st.warning("⚠️ Not signed in to Google Drive")
            st.caption("Sign in to download podcasts to your Google Drive")

            auth_url = gd.get_auth_url()
            if auth_url:
                st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)
            else:
                st.error("Google OAuth not configured. Please contact administrator.")

        st.divider()

        # Load feeds
        feeds = load_feeds_config()

        # Manage feeds
        st.subheader("RSS Feeds")

        # Select existing feed
        feed_name = st.selectbox(
            "Select Feed",
            options=list(feeds.keys()),
            key="feed_select"
        )

        # Add new feed
        with st.expander("➕ Add New Feed"):
            new_feed_name = st.text_input("Feed Name", key="new_feed_name")
            new_feed_url = st.text_input("RSS Feed URL", key="new_feed_url")

            if st.button("Add Feed"):
                if new_feed_name and new_feed_url:
                    feeds[new_feed_name] = new_feed_url
                    save_feeds_config(feeds)
                    st.success(f"Added feed: {new_feed_name}")
                    st.rerun()
                else:
                    st.error("Please provide both name and URL")

        # Delete feed
        if len(feeds) > 1:
            with st.expander("🗑️ Delete Feed"):
                feed_to_delete = st.selectbox(
                    "Select feed to delete",
                    options=list(feeds.keys()),
                    key="delete_feed_select"
                )
                if st.button("Delete Feed"):
                    if feed_to_delete in feeds:
                        del feeds[feed_to_delete]
                        save_feeds_config(feeds)
                        st.success(f"Deleted feed: {feed_to_delete}")
                        st.rerun()

        st.divider()

        # Download settings
        st.subheader("Download Settings")

        if gd.is_authenticated():
            st.info("📂 Files will be saved to your Google Drive")

            drive_base_folder = st.text_input(
                "Google Drive Folder",
                value="YUTorah Podcasts",
                help="Main folder in Google Drive for podcasts"
            )

            use_subfolders = st.checkbox(
                "Use feed-specific subfolders",
                value=True,
                help="Create a subfolder for each feed"
            )
        else:
            st.warning("⚠️ Files will be saved to Streamlit server (not recommended)")
            st.caption("Please sign in to Google Drive to save files to your account")

            output_base_dir = st.text_input(
                "Base Output Directory",
                value="downloads",
                help="Base directory where feed subfolders will be created",
                disabled=True
            )

            use_subfolders = st.checkbox(
                "Use feed-specific subfolders",
                value=True,
                help="Create a subfolder for each feed"
            )

            drive_base_folder = None

        delay = st.slider(
            "Delay Between Downloads (seconds)",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Time to wait between downloads"
        )

        db_file = st.text_input(
            "Database File",
            value="downloaded_shiurim.json",
            help="File to track downloaded shiurim"
        )

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header(f"📚 {feed_name}")
        if feed_name in feeds:
            st.code(feeds[feed_name], language=None)

    with col2:
        # Stats
        downloaded_shiurim = load_downloaded_shiurim(db_file)
        st.metric("Total Downloaded", len(downloaded_shiurim))

        if os.path.exists(db_file):
            try:
                with open(db_file, 'r') as f:
                    data = json.load(f)
                    last_updated = data.get('last_updated', 'Never')
                    st.caption(f"Last updated: {last_updated}")
            except:
                pass

    st.divider()

    # Check for episodes button
    if st.button("🔄 Check for New Episodes", type="primary", use_container_width=True):
        if feed_name not in feeds:
            st.error("Please select a valid feed")
            return

        rss_url = feeds[feed_name]

        # Progress tracking
        status_text = st.empty()

        try:
            # Fetch RSS feed
            status_text.text("Fetching RSS feed...")
            rss_root = fetch_rss_feed(rss_url)

            # Extract episodes
            status_text.text("Extracting episodes...")
            episodes = extract_episode_links(rss_root)

            if not episodes:
                st.warning("No episodes found in RSS feed")
                return

            # Filter out already downloaded
            downloaded_shiurim = load_downloaded_shiurim(db_file)
            new_episodes = []
            for title, page_url in episodes:
                shiur_id = extract_shiur_id(page_url)
                if shiur_id and shiur_id in downloaded_shiurim:
                    continue
                new_episodes.append((title, page_url, shiur_id))

            st.session_state.new_episodes = new_episodes
            st.session_state.feed_checked = True
            # Initialize all as selected
            st.session_state.selected_episodes = {i: True for i in range(len(new_episodes))}

            status_text.empty()
            st.success(f"✅ Found {len(episodes)} total episodes, {len(new_episodes)} new episodes")

        except Exception as e:
            st.error(f"Error: {e}")
            import traceback
            st.code(traceback.format_exc())

    # Display episodes for selection
    if st.session_state.feed_checked and st.session_state.new_episodes:
        st.divider()
        st.subheader(f"📋 Select Episodes to Download ({len(st.session_state.new_episodes)} new)")

        # Initialize selection state if needed
        if 'selection_state_version' not in st.session_state:
            st.session_state.selection_state_version = 0

        # Select all / Deselect all buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("✅ Select All", key=f"select_all_{st.session_state.selection_state_version}"):
                for i in range(len(st.session_state.new_episodes)):
                    st.session_state.selected_episodes[i] = True
                st.session_state.selection_state_version += 1
                st.rerun()
        with col2:
            if st.button("❌ Deselect All", key=f"deselect_all_{st.session_state.selection_state_version}"):
                for i in range(len(st.session_state.new_episodes)):
                    st.session_state.selected_episodes[i] = False
                st.session_state.selection_state_version += 1
                st.rerun()

        st.divider()

        # Display episodes with checkboxes
        for i, (title, page_url, shiur_id) in enumerate(st.session_state.new_episodes):
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                # Initialize if not present
                if i not in st.session_state.selected_episodes:
                    st.session_state.selected_episodes[i] = True

                # Use unique key based on version to force re-render
                selected = st.checkbox(
                    "Select",
                    value=st.session_state.selected_episodes[i],
                    key=f"episode_{i}_v{st.session_state.selection_state_version}",
                    label_visibility="collapsed"
                )
                # Update the session state based on checkbox
                st.session_state.selected_episodes[i] = selected
            with col2:
                st.markdown(f"**{title}**")
                st.caption(f"Shiur ID: {shiur_id if shiur_id else 'Unknown'}")

        st.divider()

        # Count selected episodes
        selected_count = sum(1 for v in st.session_state.selected_episodes.values() if v)

        # Download button
        if st.button(f"⬇️ Download Selected Episodes ({selected_count})", type="primary", use_container_width=True, disabled=selected_count == 0):
            # Check if user is authenticated
            if not gd.is_authenticated():
                st.error("❌ Please sign in to Google Drive first!")
                st.stop()

            # Set up Google Drive folders
            base_folder_id = None
            target_folder_id = None

            if drive_base_folder:
                # Create or find base folder
                base_folder_id = gd.find_or_create_folder(drive_base_folder)
                if not base_folder_id:
                    st.error("Failed to create/find base folder in Google Drive")
                    st.stop()

                if use_subfolders:
                    # Create or find feed-specific subfolder
                    safe_feed_name = sanitize_filename(feed_name)
                    target_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                else:
                    target_folder_id = base_folder_id
            else:
                # No base folder, use root
                if use_subfolders:
                    safe_feed_name = sanitize_filename(feed_name)
                    target_folder_id = gd.find_or_create_folder(safe_feed_name)

            if use_subfolders:
                st.info(f"📁 Uploading to Google Drive: `{drive_base_folder}/{sanitize_filename(feed_name)}`")
            else:
                st.info(f"📁 Uploading to Google Drive: `{drive_base_folder or 'Root'}`")

            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.container()

            # Download selected episodes
            successful = 0
            failed = 0
            skipped = 0

            selected_episodes = [
                (i, ep) for i, ep in enumerate(st.session_state.new_episodes)
                if st.session_state.selected_episodes.get(i, False)
            ]

            for idx, (i, (title, page_url, shiur_id)) in enumerate(selected_episodes):
                progress = (idx + 1) / len(selected_episodes)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx+1}/{len(selected_episodes)}: {title[:50]}...")

                with log_container:
                    with st.expander(f"[{idx+1}/{len(selected_episodes)}] {title}", expanded=(idx == 0)):
                        st.write(f"**Page:** {page_url}")
                        if shiur_id:
                            st.write(f"**Shiur ID:** {shiur_id}")

                        # Get MP3 URL
                        mp3_url, requires_login = get_mp3_url_from_page(page_url)

                        if not mp3_url:
                            if requires_login:
                                st.warning("⚠️ Skipped: Requires login")
                                skipped += 1
                            else:
                                st.error("❌ Failed: Could not find MP3 download link")
                                failed += 1
                        else:
                            st.write(f"**MP3 URL:** {mp3_url}")

                            # Upload to Google Drive
                            file_info = download_and_upload_to_drive(mp3_url, title, target_folder_id)

                            if file_info:
                                st.success(f"✅ Uploaded to Google Drive: {file_info.get('name', title)}")
                                if 'webViewLink' in file_info:
                                    st.caption(f"[Open in Drive]({file_info['webViewLink']})")
                                successful += 1

                                # Mark as downloaded
                                if shiur_id:
                                    downloaded_shiurim = load_downloaded_shiurim(db_file)
                                    downloaded_shiurim.add(shiur_id)
                                    save_downloaded_shiurim(db_file, downloaded_shiurim)
                            else:
                                st.error("❌ Upload failed")
                                failed += 1

                # Delay between requests
                if idx < len(selected_episodes) - 1:
                    time.sleep(delay)

            # Summary
            progress_bar.progress(1.0)
            status_text.text("Upload complete!")

            st.divider()
            st.success("✅ Upload to Google Drive Complete!")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", len(selected_episodes))
            with col2:
                st.metric("Successful", successful, delta=successful, delta_color="normal")
            with col3:
                st.metric("Failed", failed, delta=failed if failed > 0 else None, delta_color="inverse")
            with col4:
                st.metric("Skipped", skipped, delta=skipped if skipped > 0 else None, delta_color="off")

            # Clear the selection after download
            st.session_state.new_episodes = []
            st.session_state.selected_episodes = {}
            st.session_state.feed_checked = False

    elif st.session_state.feed_checked and not st.session_state.new_episodes:
        st.info("✅ All episodes have already been downloaded!")

    # View downloaded shiurim
    st.divider()
    with st.expander("📋 View Downloaded Shiurim Database"):
        downloaded_shiurim = load_downloaded_shiurim(db_file)
        if downloaded_shiurim:
            st.write(f"Total downloaded: {len(downloaded_shiurim)}")
            shiur_list = sorted(list(downloaded_shiurim), reverse=True)

            # Show in columns
            cols = st.columns(5)
            for i, shiur_id in enumerate(shiur_list):
                col_idx = i % 5
                with cols[col_idx]:
                    st.caption(shiur_id)
        else:
            st.info("No shiurim downloaded yet")

        # Clear database option
        if st.button("🗑️ Clear Database", type="secondary"):
            if st.checkbox("Are you sure? This cannot be undone!"):
                save_downloaded_shiurim(db_file, set())
                st.success("Database cleared")
                st.rerun()


if __name__ == '__main__':
    main()
