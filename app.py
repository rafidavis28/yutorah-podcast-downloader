#!/usr/bin/env python3
"""
YUTorah Podcast Downloader - Streamlit Web Interface

A web interface for downloading podcast episodes from YUTorah RSS feeds.
"""

import streamlit as st
import json
import os
import time
from download_podcasts import (
    fetch_rss_feed,
    extract_episode_links,
    extract_shiur_id,
    get_mp3_url_from_page,
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


def apply_custom_styles():
    """Apply a minimal visual system for spacing and section cards."""
    st.markdown(
        """
        <style>
            .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
            h1 {font-size: 1.8rem !important; margin-bottom: 0.35rem !important;}
            h2, h3 {margin-top: 0.35rem !important; margin-bottom: 0.6rem !important;}
            .section-card {
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 10px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.8rem;
                background: rgba(250, 250, 250, 0.35);
            }
            .status-pill {
                display: inline-block;
                padding: 0.15rem 0.5rem;
                border-radius: 999px;
                font-size: 0.78rem;
                line-height: 1.4;
                border: 1px solid rgba(128, 128, 128, 0.35);
            }
            .status-new {background: rgba(76, 175, 80, 0.12); color: #1b5e20;}
            .status-unknown {background: rgba(128, 128, 128, 0.12); color: #37474f;}
            .sticky-progress {
                position: sticky;
                top: 0.5rem;
                z-index: 50;
                background: var(--background-color);
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 10px;
                padding: 0.55rem 0.75rem;
                margin-bottom: 0.55rem;
            }
            .event-log {font-size: 0.86rem; color: #4a4a4a; margin-bottom: 0.25rem;}
        </style>
        """,
        unsafe_allow_html=True
    )


def status_pill(label, css_class):
    return f"<span class='status-pill {css_class}'>{label}</span>"


def download_and_upload_to_drive(mp3_url, title, folder_id, shiur_id=None):
    """
    Download MP3 file and upload to Google Drive.

    Args:
        mp3_url: URL of the MP3 file
        title: Title of the episode
        folder_id: Google Drive folder ID to upload to
        shiur_id: Optional shiur ID to store in file description for tracking

    Returns:
        Dictionary with file info or None
    """
    try:
        # Sanitize filename
        filename = sanitize_filename(title) + '.mp3'

        # Download the file content with a couple retries for transient failures
        last_error = None
        response = None
        for attempt in range(3):
            try:
                response = session.get(mp3_url, stream=True, timeout=60)
                response.raise_for_status()
                break
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))

        if response is None:
            raise RuntimeError(f"Failed to download MP3 after retries: {last_error}")

        # Read content into memory
        file_content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_content += chunk

        # Prepare description with shiur ID for tracking
        description = None
        if shiur_id:
            description = f"shiurID:{shiur_id}"

        # Upload to Google Drive
        file_info = gd.upload_file_to_drive(
            file_content,
            filename,
            folder_id=folder_id,
            mime_type='audio/mpeg',
            description=description
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

    apply_custom_styles()

    st.title("YUTorah Podcast Downloader")
    st.caption("Download shiurim from YUTorah RSS feeds")

    # Initialize session state
    if 'new_episodes' not in st.session_state:
        st.session_state.new_episodes = []
    if 'selected_episodes' not in st.session_state:
        st.session_state.selected_episodes = {}
    if 'feed_checked' not in st.session_state:
        st.session_state.feed_checked = False

    # Sidebar for configuration
    with st.sidebar:
        st.header("Settings")

        # Google Drive Authentication
        st.subheader("Drive")

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
                st.success(f"Signed in as {user_info.get('emailAddress', 'Unknown')}")
            else:
                st.success("Signed in to Google Drive")

            if st.button("Sign out", use_container_width=True):
                gd.sign_out()
                st.rerun()
        else:
            st.warning("Not signed in to Google Drive")
            st.caption("Sign in to download podcasts to your Google Drive")

            auth_url = gd.get_auth_url()
            if auth_url:
                st.link_button("Sign in with Google", auth_url, use_container_width=True)
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
        with st.expander("Add feed"):
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
            with st.expander("Delete feed"):
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
            st.info("Files will be saved to your Google Drive")

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
            st.warning("Files will be saved to this server (not recommended)")
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

        # Only show local database option when not using Google Drive
        if not gd.is_authenticated():
            db_file = st.text_input(
                "Database File",
                value="downloaded_shiurim.json",
                help="File to track downloaded shiurim (not used with Google Drive)"
            )
        else:
            db_file = "downloaded_shiurim.json"  # Default value, but not used

    # Main content area
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Feeds")
        st.markdown(f"**{feed_name}**")
        if feed_name in feeds:
            st.caption(feeds[feed_name])

    with col2:
        st.subheader("Diagnostics")
        if gd.is_authenticated():
            st.caption("Drive sync is enabled.")
        else:
            downloaded_shiurim = load_downloaded_shiurim(db_file)
            st.metric("Local history", len(downloaded_shiurim))
            if os.path.exists(db_file):
                try:
                    with open(db_file, 'r') as f:
                        data = json.load(f)
                        last_updated = data.get('last_updated', 'Never')
                        st.caption(f"Last updated: {last_updated}")
                except:
                    pass
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("Downloads")

    # Check for episodes button
    if st.button("Check for new episodes", type="primary", use_container_width=True):
        if feed_name not in feeds:
            st.error("Please select a valid feed.")
            return

        rss_url = feeds[feed_name]
        status_text = st.empty()

        try:
            status_text.text("Fetching feed...")
            rss_root = fetch_rss_feed(rss_url)

            status_text.text("Reading episodes...")
            episodes = extract_episode_links(rss_root)

            if not episodes:
                st.info("No episodes were found in this feed right now.")
                return

            uploaded_shiur_ids = set()

            if gd.is_authenticated() and drive_base_folder:
                status_text.text("Checking your Drive history...")
                base_folder_id = gd.find_or_create_folder(drive_base_folder)
                if base_folder_id:
                    if use_subfolders:
                        safe_feed_name = sanitize_filename(feed_name)
                        check_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                    else:
                        check_folder_id = base_folder_id

                    if check_folder_id:
                        uploaded_shiur_ids = gd.get_uploaded_shiur_ids(check_folder_id)
                        st.session_state.target_folder_id = check_folder_id
            else:
                uploaded_shiur_ids = load_downloaded_shiurim(db_file)

            new_episodes = []
            for title, page_url in episodes:
                shiur_id = extract_shiur_id(page_url)
                if shiur_id and shiur_id in uploaded_shiur_ids:
                    continue
                new_episodes.append((title, page_url, shiur_id))

            st.session_state.new_episodes = new_episodes
            st.session_state.feed_checked = True
            st.session_state.selected_episodes = {i: True for i in range(len(new_episodes))}

            status_text.empty()
            st.success(f"Found {len(new_episodes)} new episodes out of {len(episodes)} total.")

        except Exception as e:
            st.error("We couldn't finish checking the feed. Please try again in a minute.")
            st.caption(f"Details: {e}")

    if st.session_state.feed_checked and st.session_state.new_episodes:
        st.markdown(f"{len(st.session_state.new_episodes)} episodes are available.")

        if 'selection_state_version' not in st.session_state:
            st.session_state.selection_state_version = 0

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Select all", key=f"select_all_{st.session_state.selection_state_version}"):
                for i in range(len(st.session_state.new_episodes)):
                    st.session_state.selected_episodes[i] = True
                st.session_state.selection_state_version += 1
                st.rerun()
        with col2:
            if st.button("Clear selection", key=f"deselect_all_{st.session_state.selection_state_version}"):
                for i in range(len(st.session_state.new_episodes)):
                    st.session_state.selected_episodes[i] = False
                st.session_state.selection_state_version += 1
                st.rerun()

        head_cols = st.columns([0.08, 0.58, 0.14, 0.2])
        head_cols[0].markdown("**Pick**")
        head_cols[1].markdown("**Title**")
        head_cols[2].markdown("**shiurID**")
        head_cols[3].markdown("**Status / Action**")

        for i, (title, page_url, shiur_id) in enumerate(st.session_state.new_episodes):
            if i not in st.session_state.selected_episodes:
                st.session_state.selected_episodes[i] = True

            row_cols = st.columns([0.08, 0.58, 0.14, 0.2])
            selected = row_cols[0].checkbox(
                "Select",
                value=st.session_state.selected_episodes[i],
                key=f"episode_{i}_v{st.session_state.selection_state_version}",
                label_visibility="collapsed"
            )
            st.session_state.selected_episodes[i] = selected
            row_cols[1].markdown(title)
            row_cols[1].caption(page_url)
            row_cols[2].markdown(str(shiur_id) if shiur_id else "—")
            row_cols[3].markdown(status_pill("New", "status-new") if shiur_id else status_pill("ID missing", "status-unknown"), unsafe_allow_html=True)

        selected_count = sum(1 for v in st.session_state.selected_episodes.values() if v)
        if st.button(f"Download selected ({selected_count})", type="primary", use_container_width=True, disabled=selected_count == 0):
            if not gd.is_authenticated():
                st.error("Please sign in to Google Drive first so files can be saved safely.")
                st.stop()

            base_folder_id = None
            target_folder_id = None

            if drive_base_folder:
                base_folder_id = gd.find_or_create_folder(drive_base_folder)
                if not base_folder_id:
                    st.error("We couldn't access your main Drive folder. Please verify folder permissions and try again.")
                    st.stop()

                if use_subfolders:
                    safe_feed_name = sanitize_filename(feed_name)
                    target_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                else:
                    target_folder_id = base_folder_id
            else:
                if use_subfolders:
                    safe_feed_name = sanitize_filename(feed_name)
                    target_folder_id = gd.find_or_create_folder(safe_feed_name)

            st.caption(f"Destination: {drive_base_folder or 'Drive root'}")

            st.markdown("<div class='sticky-progress'>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            status_text = st.empty()
            st.markdown("</div>", unsafe_allow_html=True)
            log_container = st.container()

            successful = 0
            failed = 0
            event_log = []

            selected_episodes = [
                (i, ep) for i, ep in enumerate(st.session_state.new_episodes)
                if st.session_state.selected_episodes.get(i, False)
            ]

            for idx, (i, (title, page_url, shiur_id)) in enumerate(selected_episodes):
                progress = (idx + 1) / len(selected_episodes)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx+1}/{len(selected_episodes)}")

                episode_data = get_mp3_url_from_page(page_url)

                if not episode_data or not episode_data.get('downloadURL'):
                    failed += 1
                    failure_reason = (episode_data or {}).get('failure_reason', 'unknown reason')
                    event_log.append(f"Could not find an MP3 link for '{title[:42]}': {failure_reason}.")
                else:
                    mp3_url = episode_data['downloadURL']
                    actual_shiur_id = str(episode_data.get('shiurID')) if episode_data.get('shiurID') else shiur_id
                    file_info = download_and_upload_to_drive(mp3_url, title, target_folder_id, actual_shiur_id)

                    if file_info:
                        successful += 1
                        event_log.append(f"Saved: {file_info.get('name', title)[:48]}")
                        if actual_shiur_id:
                            downloaded_shiurim = load_downloaded_shiurim(db_file)
                            downloaded_shiurim.add(str(actual_shiur_id))
                            save_downloaded_shiurim(db_file, downloaded_shiurim)
                    else:
                        failed += 1
                        event_log.append("Upload failed. This can happen if Drive permissions expire.")

                with log_container:
                    st.markdown("#### Recent events")
                    for entry in event_log[-8:]:
                        st.markdown(f"<div class='event-log'>• {entry}</div>", unsafe_allow_html=True)

                if idx < len(selected_episodes) - 1:
                    time.sleep(delay)

            progress_bar.progress(1.0)
            status_text.text("Done")

            st.success("Download run finished.")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(selected_episodes))
            col2.metric("Successful", successful)
            col3.metric("Failed", failed)

            if failed:
                st.warning("Some episodes failed. See Recent events for per-episode error reasons (missing MP3 source, network timeout, or Drive permission expiry).")

            st.session_state.new_episodes = []
            st.session_state.selected_episodes = {}
            st.session_state.feed_checked = False

    elif st.session_state.feed_checked and not st.session_state.new_episodes:
        st.info("You're all caught up. No new episodes to download right now.")
    else:
        st.caption("Start by clicking 'Check for new episodes'.")

    st.markdown("</div>", unsafe_allow_html=True)

    # View uploaded shiurim
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("History")
    with st.expander("View uploaded shiurim", expanded=True):
        # Check Google Drive if authenticated
        if gd.is_authenticated() and drive_base_folder:
            st.info("Checking Google Drive for uploaded shiurim...")

            # Find the folder to check
            base_folder_id = gd.find_or_create_folder(drive_base_folder)
            if base_folder_id:
                if use_subfolders:
                    safe_feed_name = sanitize_filename(feed_name)
                    check_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                else:
                    check_folder_id = base_folder_id

                if check_folder_id:
                    uploaded_shiur_ids = gd.get_uploaded_shiur_ids(check_folder_id)
                    if uploaded_shiur_ids:
                        st.write(f"Total uploaded to `{feed_name}` folder: {len(uploaded_shiur_ids)}")
                        shiur_list = sorted(list(uploaded_shiur_ids), reverse=True)

                        # Show in columns
                        cols = st.columns(5)
                        for i, shiur_id in enumerate(shiur_list):
                            col_idx = i % 5
                            with cols[col_idx]:
                                st.caption(shiur_id)
                    else:
                        st.info("No shiurim uploaded to this folder yet")
                else:
                    st.warning("Could not find/create feed folder")
            else:
                st.warning("Could not find/create base folder")
        else:
            # Fallback to local database
            downloaded_shiurim = load_downloaded_shiurim(db_file)
            if downloaded_shiurim:
                st.write(f"Total in local database: {len(downloaded_shiurim)}")
                shiur_list = sorted(list(downloaded_shiurim), reverse=True)

                # Show in columns
                cols = st.columns(5)
                for i, shiur_id in enumerate(shiur_list):
                    col_idx = i % 5
                    with cols[col_idx]:
                        st.caption(shiur_id)

                # Clear database option (only for local mode)
                if st.button("Clear local database", type="secondary"):
                    if st.checkbox("Are you sure? This cannot be undone!"):
                        save_downloaded_shiurim(db_file, set())
                        st.success("Database cleared")
                        st.rerun()
            else:
                st.info("No saved history yet. Sign in to Google Drive to track uploads automatically.")


    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
