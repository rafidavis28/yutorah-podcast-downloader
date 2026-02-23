#!/usr/bin/env python3
"""
YUTorah Podcast Downloader - Streamlit Web Interface

A web interface for downloading podcast episodes from YUTorah RSS feeds.
"""

import json
import os
import time
import streamlit as st
import streamlit_cookies_manager as cookies

import google_drive_auth as gd
from download_podcasts import (
    download_mp3,
    extract_episode_links,
    extract_shiur_id,
    fetch_rss_feed,
    get_mp3_url_from_page,
    load_downloaded_shiurim,
    sanitize_filename,
    save_downloaded_shiurim,
    session,
)

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
        Dict with keys: ok (bool), file_info (dict|None), error_stage (str|None), error (str|None)
    """
    # Sanitize filename
    filename = sanitize_filename(title) + '.mp3'

    # Download the file content
    try:
    """Download MP3 file and upload to Google Drive."""
    try:
        filename = sanitize_filename(title) + '.mp3'
        response = session.get(mp3_url, stream=True)
        response.raise_for_status()

        file_content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_content += chunk
    except Exception as e:
        return {
            'ok': False,
            'file_info': None,
            'error_stage': 'download',
            'error': str(e),
        }

    # Prepare description with shiur ID for tracking
    description = None
    if shiur_id:
        description = f"shiurID:{shiur_id}"

    # Upload to Google Drive
    try:
        file_info = gd.upload_file_to_drive(

        description = f"shiurID:{shiur_id}" if shiur_id else None

        return gd.upload_file_to_drive(
            file_content,
            filename,
            folder_id=folder_id,
            mime_type='audio/mpeg',
            description=description,
        )
    except Exception as e:
        return {
            'ok': False,
            'file_info': None,
            'error_stage': 'upload',
            'error': str(e),
        }

    if not file_info:
        return {
            'ok': False,
            'file_info': None,
            'error_stage': 'upload',
            'error': 'No file info returned from Google Drive API',
        }

    return {
        'ok': True,
        'file_info': file_info,
        'error_stage': None,
        'error': None,
    }


def load_feeds_config():
    """Load RSS feeds configuration from file."""
    if os.path.exists(FEEDS_CONFIG_FILE):
        try:
            with open(FEEDS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_FEEDS.copy()


def save_feeds_config(feeds):
    """Save RSS feeds configuration to file."""
    try:
        with open(FEEDS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(feeds, f, indent=2)
    except Exception as e:
        st.error(f"Error saving feeds configuration: {e}")


def resolve_drive_folder(base_folder, feed_name, use_subfolders):
    """Return target Google Drive folder ID for a feed using Base/<Feed> strategy when enabled."""
    base_folder_id = gd.find_or_create_folder(base_folder) if base_folder else None
    if use_subfolders:
        safe_feed_name = sanitize_filename(feed_name)
        return gd.find_or_create_folder(safe_feed_name, base_folder_id)
    return base_folder_id


def resolve_local_folder(base_output_dir, feed_name, use_subfolders):
    """Return local output folder path for a feed using Base/<Feed> strategy when enabled."""
    target_dir = base_output_dir
    if use_subfolders:
        target_dir = os.path.join(base_output_dir, sanitize_filename(feed_name))
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def check_feed(feed_name, rss_url, is_drive_mode, drive_base_folder, use_subfolders, db_file):
    """Check one feed and return a result bundle for summary/download."""
    rss_root = fetch_rss_feed(rss_url)
    episodes = extract_episode_links(rss_root)

    uploaded_shiur_ids = set()
    target_folder_id = None

    if is_drive_mode and drive_base_folder:
        target_folder_id = resolve_drive_folder(drive_base_folder, feed_name, use_subfolders)
        if target_folder_id:
            uploaded_shiur_ids = gd.get_uploaded_shiur_ids(target_folder_id)
    else:
        uploaded_shiur_ids = load_downloaded_shiurim(db_file)

    new_episodes = []
    for title, page_url in episodes:
        shiur_id = extract_shiur_id(page_url)
        if shiur_id and shiur_id in uploaded_shiur_ids:
            continue
        new_episodes.append((title, page_url, shiur_id))

    return {
        'feed_name': feed_name,
        'total_episodes': len(episodes),
        'new_episodes': new_episodes,
        'uploaded_shiur_ids': uploaded_shiur_ids,
        'target_folder_id': target_folder_id,
    }


def main():
    st.set_page_config(page_title="YUTorah Podcast Downloader", page_icon="🎧", layout="wide")

    cookie_manager = cookies.CookieManager()
    gd.set_cookie_manager(cookie_manager)
    if not cookie_manager.ready():
        st.stop()

    gd.init_auth_from_cookies()

    apply_custom_styles()

    st.title("YUTorah Podcast Downloader")
    st.caption("Download shiurim from YUTorah RSS feeds")

    if 'new_episodes' not in st.session_state:
        st.session_state.new_episodes = []
    if 'selected_episodes' not in st.session_state:
        st.session_state.selected_episodes = {}
    if 'feed_checked' not in st.session_state:
        st.session_state.feed_checked = False
    if 'storage_mode' not in st.session_state:
        st.session_state.storage_mode = "Google Drive"
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = {}

    with st.sidebar:
        st.header("⚙️ Settings")
        st.subheader("☁️ Google Drive")
        st.header("Settings")

        storage_mode = st.radio(
            "Storage Mode",
            options=["Google Drive", "Local Files"],
            key="storage_mode",
            horizontal=True
        )

        use_google_drive = storage_mode == "Google Drive"

        # Google Drive Authentication
        if use_google_drive:
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
        # Google Drive Authentication
        st.subheader("Drive")

        query_params = st.query_params
        if 'code' in query_params:
            gd.handle_oauth_callback(query_params['code'])
            st.query_params.clear()
            st.rerun()

        if gd.is_authenticated():
            user_info = gd.get_user_info()
            if user_info:
                st.success(f"Signed in as {user_info.get('emailAddress', 'Unknown')}")
            else:
                st.success("✅ Signed in to Google Drive")
            if st.button("🚪 Sign Out", use_container_width=True):
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
                st.warning("⚠️ Not signed in to Google Drive")
                st.caption("Sign in to download podcasts to your Google Drive")

                auth_url = gd.get_auth_url()
                if auth_url:
                    st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)
                else:
                    st.error("Google OAuth not configured. Please contact administrator.")

        st.divider()

        feeds = load_feeds_config()
        st.subheader("RSS Feeds")

        run_mode = st.radio(
            "Run mode",
            options=["Focused (single feed)", "Batch (multiple feeds)"],
            help="Focused keeps episode-by-episode selection. Batch checks/downloads selected feeds together.",
        )

        feed_name = st.selectbox("Select Feed", options=list(feeds.keys()), key="feed_select")
        selected_feeds = st.multiselect(
            "Select feeds for batch actions",
            options=list(feeds.keys()),
            default=[feed_name] if feed_name in feeds else [],
            key="feed_multi_select",
        )

        with st.expander("➕ Add New Feed"):
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

        if len(feeds) > 1:
            with st.expander("🗑️ Delete Feed"):
                feed_to_delete = st.selectbox("Select feed to delete", options=list(feeds.keys()), key="delete_feed_select")
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
        st.subheader("Download Settings")

        if use_google_drive:
            st.info("📂 Files will be saved to your Google Drive")
            drive_base_folder = st.text_input("Google Drive Folder", value="YUTorah Podcasts")
            base_output_dir = "downloads"
        else:
            st.warning("⚠️ Files will be saved locally on the server")
            base_output_dir = st.text_input("Base Output Directory", value="downloads")
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
            output_base_dir = None
        else:
            st.info("💾 Files will be saved to local files")
            st.warning("Files will be saved to this server (not recommended)")
            st.caption("Please sign in to Google Drive to save files to your account")

            output_base_dir = st.text_input(
                "Base Output Directory",
                value="downloads",
                help="Base directory where feed subfolders will be created"
            )

            use_subfolders = st.checkbox(
                "Use feed-specific subfolders",
                value=True,
                help="Create a subfolder for each feed"
            )

            drive_base_folder = None

        use_subfolders = st.checkbox(
            "Use feed-specific subfolders (Base/<Speaker Feed Name>/...)",
            value=True,
            help="When enabled, files are placed under Base/<Speaker Feed Name>/... in both local and Drive modes.",
        )

        delay = st.slider("Delay Between Downloads (seconds)", 0.5, 5.0, 1.0, 0.5)
        db_file = st.text_input("Database File", value="downloaded_shiurim.json") if not gd.is_authenticated() else "downloaded_shiurim.json"

    is_drive_mode = gd.is_authenticated()

    st.header("📚 Feed Selection")
    if run_mode == "Focused (single feed)":
        st.code(feeds.get(feed_name, ""), language=None)
    else:
        st.write(f"Batch-selected feeds: **{len(selected_feeds)}**")
        # Only show local database option for local storage mode
        if not use_google_drive:
        delay = st.slider("Delay Between Downloads (seconds)", 0.5, 5.0, 1.0, 0.5)
        db_file = st.text_input("Database File", value="downloaded_shiurim.json") if not gd.is_authenticated() else "downloaded_shiurim.json"

    is_drive_mode = gd.is_authenticated()

    st.header("📚 Feed Selection")
    if run_mode == "Focused (single feed)":
        st.code(feeds.get(feed_name, ""), language=None)
    else:
        st.write(f"Batch-selected feeds: **{len(selected_feeds)}**")
        # Only show local database option when not using Google Drive
        if not gd.is_authenticated():
            db_file = st.text_input(
                "Database File",
                value="downloaded_shiurim.json",
                help="File to track downloaded shiurim when using Local Files"
            )
        else:
            db_file = "downloaded_shiurim.json"  # Default value used for compatibility

    # Main content area
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Feeds")
        st.markdown(f"**{feed_name}**")
        if feed_name in feeds:
            st.caption(feeds[feed_name])

    with col2:
        # Stats - shows Google Drive count when authenticated, otherwise local count
        if use_google_drive:
            st.caption("☁️ Google Drive tracking enabled")
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

    if run_mode == "Batch (multiple feeds)":
        col_check, col_download = st.columns(2)

        with col_check:
            if st.button("🔄 Check selected feeds", type="primary", use_container_width=True):
                if not selected_feeds:
                    st.error("Please select at least one feed.")
                else:
                    batch_results = {}
                    status_text = st.empty()
                    for idx, feed in enumerate(selected_feeds, 1):
                        status_text.text(f"Checking feed {idx}/{len(selected_feeds)}: {feed}")
                        try:
                            batch_results[feed] = check_feed(
                                feed,
                                feeds[feed],
                                is_drive_mode,
                                drive_base_folder,
                                use_subfolders,
                                db_file,
                            )
                        except Exception as e:
                            st.error(f"Error checking {feed}: {e}")
                    status_text.empty()
                    st.session_state.batch_results = batch_results
                    st.success(f"Checked {len(batch_results)} feeds.")

        with col_download:
            can_download = bool(st.session_state.batch_results)
            if st.button("⬇️ Download selected feeds", use_container_width=True, disabled=not can_download):
                download_summary = {}
                downloaded_shiurim = load_downloaded_shiurim(db_file)

                for feed in selected_feeds:
                    feed_result = st.session_state.batch_results.get(feed)
                    if not feed_result:
                        continue

                    episodes = feed_result['new_episodes']
                    successful = 0
                    failed = 0

                    target_folder_id = feed_result.get('target_folder_id')
                    target_local_dir = resolve_local_folder(base_output_dir, feed, use_subfolders)

                    for idx, (title, page_url, shiur_id) in enumerate(episodes):
                        data = get_mp3_url_from_page(page_url)
                        if not data or not data.get('downloadURL'):
                            failed += 1
                            continue

                        actual_shiur_id = str(data.get('shiurID')) if data.get('shiurID') else shiur_id

                        if is_drive_mode:
                            if not target_folder_id:
                                failed += 1
                                continue
                            file_info = download_and_upload_to_drive(data['downloadURL'], title, target_folder_id, actual_shiur_id)
                            if file_info:
                                successful += 1
                            else:
                                failed += 1
                        else:
                            if download_mp3(data['downloadURL'], title, target_local_dir):
                                successful += 1
                            else:
                                failed += 1

                        if actual_shiur_id and successful + failed > 0:
                            downloaded_shiurim.add(str(actual_shiur_id))

                        if idx < len(episodes) - 1:
                            time.sleep(delay)

                    download_summary[feed] = {
                        'total_episodes': feed_result['total_episodes'],
                        'new_episodes': len(episodes),
                        'successful': successful,
                        'failed': failed,
                    }

                save_downloaded_shiurim(db_file, downloaded_shiurim)
                st.session_state.batch_download_summary = download_summary
                st.success("Batch download complete.")

        if st.session_state.batch_results:
            st.subheader("Batch Check Summary")
            for feed, result in st.session_state.batch_results.items():
                st.markdown(
                    f"- **{feed}**: total episodes **{result['total_episodes']}**, "
                    f"new episodes **{len(result['new_episodes'])}**"
                )

        if st.session_state.get('batch_download_summary'):
            st.subheader("Batch Download Summary (per feed)")
            for feed, summary in st.session_state.batch_download_summary.items():
                st.markdown(
                    f"- **{feed}**: total **{summary['total_episodes']}**, new **{summary['new_episodes']}**, "
                    f"success **{summary['successful']}**, failed **{summary['failed']}**"
                )

    else:
        # Focused single-feed mode (episode-level selection remains available)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.header(f"📚 {feed_name}")
            if feed_name in feeds:
                st.code(feeds[feed_name], language=None)
        with col2:
            if is_drive_mode:
                st.caption("☁️ Google Drive tracking enabled")
            else:
                downloaded_shiurim = load_downloaded_shiurim(db_file)
                st.metric("Local DB Count", len(downloaded_shiurim))

        if st.button("🔄 Check for New Episodes", type="primary", use_container_width=True):
            if feed_name not in feeds:
                st.error("Please select a valid feed")
            else:
                try:
                    result = check_feed(feed_name, feeds[feed_name], is_drive_mode, drive_base_folder, use_subfolders, db_file)
                    st.session_state.new_episodes = result['new_episodes']
                    st.session_state.feed_checked = True
                    st.session_state.selected_episodes = {i: True for i in range(len(result['new_episodes']))}
                    st.success(
                        f"✅ Found {result['total_episodes']} total episodes, {len(result['new_episodes'])} new"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.feed_checked and st.session_state.new_episodes:
            st.subheader(f"📋 Select Episodes to Download ({len(st.session_state.new_episodes)} new)")

            if 'selection_state_version' not in st.session_state:
                st.session_state.selection_state_version = 0

            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("✅ Select All", key=f"select_all_{st.session_state.selection_state_version}"):
                    for i in range(len(st.session_state.new_episodes)):
                        st.session_state.selected_episodes[i] = True
                    st.session_state.selection_state_version += 1
                    st.rerun()
            with c2:
                if st.button("❌ Deselect All", key=f"deselect_all_{st.session_state.selection_state_version}"):
                    for i in range(len(st.session_state.new_episodes)):
                        st.session_state.selected_episodes[i] = False
                    st.session_state.selection_state_version += 1
                    st.rerun()

    if run_mode == "Batch (multiple feeds)":
        col_check, col_download = st.columns(2)

        with col_check:
            if st.button("🔄 Check selected feeds", type="primary", use_container_width=True):
                if not selected_feeds:
                    st.error("Please select at least one feed.")
                else:
                    batch_results = {}
                    status_text = st.empty()
                    for idx, feed in enumerate(selected_feeds, 1):
                        status_text.text(f"Checking feed {idx}/{len(selected_feeds)}: {feed}")
                        try:
                            batch_results[feed] = check_feed(
                                feed,
                                feeds[feed],
                                is_drive_mode,
                                drive_base_folder,
                                use_subfolders,
                                db_file,
                            )
                        except Exception as e:
                            st.error(f"Error checking {feed}: {e}")
                    status_text.empty()
                    st.session_state.batch_results = batch_results
                    st.success(f"Checked {len(batch_results)} feeds.")

        with col_download:
            can_download = bool(st.session_state.batch_results)
            if st.button("⬇️ Download selected feeds", use_container_width=True, disabled=not can_download):
                download_summary = {}
                downloaded_shiurim = load_downloaded_shiurim(db_file)

                for feed in selected_feeds:
                    feed_result = st.session_state.batch_results.get(feed)
                    if not feed_result:
                        continue

                    episodes = feed_result['new_episodes']
                    successful = 0
                    failed = 0

                    target_folder_id = feed_result.get('target_folder_id')
                    target_local_dir = resolve_local_folder(base_output_dir, feed, use_subfolders)

                    for idx, (title, page_url, shiur_id) in enumerate(episodes):
                        data = get_mp3_url_from_page(page_url)
                        if not data or not data.get('downloadURL'):
                            failed += 1
                            continue

                        actual_shiur_id = str(data.get('shiurID')) if data.get('shiurID') else shiur_id

                        if is_drive_mode:
                            if not target_folder_id:
                                failed += 1
                                continue
                            file_info = download_and_upload_to_drive(data['downloadURL'], title, target_folder_id, actual_shiur_id)
                            if file_info:
                                successful += 1
                            else:
                                failed += 1
                        else:
                            if download_mp3(data['downloadURL'], title, target_local_dir):
                                successful += 1
                            else:
                                failed += 1

                        if actual_shiur_id and successful + failed > 0:
                            downloaded_shiurim.add(str(actual_shiur_id))

                        if idx < len(episodes) - 1:
                            time.sleep(delay)

                    download_summary[feed] = {
                        'total_episodes': feed_result['total_episodes'],
                        'new_episodes': len(episodes),
                        'successful': successful,
                        'failed': failed,
                    }

                save_downloaded_shiurim(db_file, downloaded_shiurim)
                st.session_state.batch_download_summary = download_summary
                st.success("Batch download complete.")

        if st.session_state.batch_results:
            st.subheader("Batch Check Summary")
            for feed, result in st.session_state.batch_results.items():
                st.markdown(
                    f"- **{feed}**: total episodes **{result['total_episodes']}**, "
                    f"new episodes **{len(result['new_episodes'])}**"
                )

        if st.session_state.get('batch_download_summary'):
            st.subheader("Batch Download Summary (per feed)")
            for feed, summary in st.session_state.batch_download_summary.items():
                st.markdown(
                    f"- **{feed}**: total **{summary['total_episodes']}**, new **{summary['new_episodes']}**, "
                    f"success **{summary['successful']}**, failed **{summary['failed']}**"
                )

    else:
        # Focused single-feed mode (episode-level selection remains available)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.header(f"📚 {feed_name}")
            if feed_name in feeds:
                st.code(feeds[feed_name], language=None)
        with col2:
            if is_drive_mode:
                st.caption("☁️ Google Drive tracking enabled")
            else:
                downloaded_shiurim = load_downloaded_shiurim(db_file)
                st.metric("Local DB Count", len(downloaded_shiurim))

        if st.button("🔄 Check for New Episodes", type="primary", use_container_width=True):
            if feed_name not in feeds:
                st.error("Please select a valid feed")
            else:
                try:
                    result = check_feed(feed_name, feeds[feed_name], is_drive_mode, drive_base_folder, use_subfolders, db_file)
                    st.session_state.new_episodes = result['new_episodes']
                    st.session_state.feed_checked = True
                    st.session_state.selected_episodes = {i: True for i in range(len(result['new_episodes']))}
                    st.success(
                        f"✅ Found {result['total_episodes']} total episodes, {len(result['new_episodes'])} new"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.feed_checked and st.session_state.new_episodes:
            st.subheader(f"📋 Select Episodes to Download ({len(st.session_state.new_episodes)} new)")

            if 'selection_state_version' not in st.session_state:
                st.session_state.selection_state_version = 0

            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("✅ Select All", key=f"select_all_{st.session_state.selection_state_version}"):
                    for i in range(len(st.session_state.new_episodes)):
                        st.session_state.selected_episodes[i] = True
                    st.session_state.selection_state_version += 1
                    st.rerun()
            with c2:
                if st.button("❌ Deselect All", key=f"deselect_all_{st.session_state.selection_state_version}"):
                    for i in range(len(st.session_state.new_episodes)):
                        st.session_state.selected_episodes[i] = False
                    st.session_state.selection_state_version += 1
                    st.rerun()

            for i, (title, _, shiur_id) in enumerate(st.session_state.new_episodes):
                col_cb, col_title = st.columns([0.1, 0.9])
                with col_cb:
                    current = st.session_state.selected_episodes.get(i, True)
                    st.session_state.selected_episodes[i] = st.checkbox(
                        "Select",
                        value=current,
                        key=f"episode_{i}_v{st.session_state.selection_state_version}",
                        label_visibility="collapsed",
                    )
                with col_title:
                    st.markdown(f"**{title}**")
                    st.caption(f"Shiur ID: {shiur_id if shiur_id else 'Unknown'}")
            for i, (title, _, shiur_id) in enumerate(st.session_state.new_episodes):
                col_cb, col_title = st.columns([0.1, 0.9])
                with col_cb:
                    current = st.session_state.selected_episodes.get(i, True)
                    st.session_state.selected_episodes[i] = st.checkbox(
                        "Select",
                        value=current,
                        key=f"episode_{i}_v{st.session_state.selection_state_version}",
                        label_visibility="collapsed",
                    )
                with col_title:
                    st.markdown(f"**{title}**")
                    st.caption(f"Shiur ID: {shiur_id if shiur_id else 'Unknown'}")
    # Check for episodes button
    if st.button("Check for new episodes", type="primary", use_container_width=True):
        if feed_name not in feeds:
            st.error("Please select a valid feed.")
            return

        if use_google_drive and not gd.is_authenticated():
            st.error("❌ Please sign in to Google Drive to check for new episodes in Drive mode.")
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

            if use_google_drive:
                status_text.text("Checking Google Drive for existing uploads...")
                check_folder_id = None

                if drive_base_folder:
                    # Find the target folder to check
                    base_folder_id = gd.find_or_create_folder(drive_base_folder)
                    if base_folder_id:
                        if use_subfolders:
                            safe_feed_name = sanitize_filename(feed_name)
                            check_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                        else:
                            check_folder_id = base_folder_id
                elif use_subfolders:
                    safe_feed_name = sanitize_filename(feed_name)
                    check_folder_id = gd.find_or_create_folder(safe_feed_name)

                if check_folder_id:
                    uploaded_shiur_ids = gd.get_uploaded_shiur_ids(check_folder_id)
                    st.session_state.target_folder_id = check_folder_id  # Cache for download
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

            if use_google_drive:
                st.success(f"✅ Found {len(episodes)} total episodes, {len(new_episodes)} new (checked Google Drive: {len(uploaded_shiur_ids)} already uploaded)")
            else:
                st.success(f"✅ Found {len(episodes)} total episodes, {len(new_episodes)} new episodes")
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

        # Download button
        if st.button(f"⬇️ Download Selected Episodes ({selected_count})", type="primary", use_container_width=True, disabled=selected_count == 0):
            # Check Drive authentication only in Drive mode
            if use_google_drive and not gd.is_authenticated():
                st.error("❌ Please sign in to Google Drive first!")
                st.stop()

            # Set up Google Drive folders when needed
        if st.button(f"Download selected ({selected_count})", type="primary", use_container_width=True, disabled=selected_count == 0):
            if not gd.is_authenticated():
                st.error("Please sign in to Google Drive first so files can be saved safely.")
                st.stop()

            base_folder_id = None
            target_folder_id = None
            target_output_dir = None

            if use_google_drive:
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
            if drive_base_folder:
                base_folder_id = gd.find_or_create_folder(drive_base_folder)
                if not base_folder_id:
                    st.error("We couldn't access your main Drive folder. Please verify folder permissions and try again.")
                    st.stop()

                if use_subfolders:
                    safe_feed_name = sanitize_filename(feed_name)
                    target_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                else:
                    st.info(f"📁 Uploading to Google Drive: `{drive_base_folder or 'Root'}`")
            else:
                safe_feed_name = sanitize_filename(feed_name)
                if use_subfolders:
                    target_output_dir = os.path.join(output_base_dir, safe_feed_name)
                else:
                    target_output_dir = output_base_dir

                Path(target_output_dir).mkdir(parents=True, exist_ok=True)
                st.info(f"💾 Saving to local folder: `{target_output_dir}`")
            st.caption(f"Destination: {drive_base_folder or 'Drive root'}")

            st.markdown("<div class='sticky-progress'>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            status_text = st.empty()
            st.markdown("</div>", unsafe_allow_html=True)
            log_container = st.container()

            successful = 0
            parse_failures = 0
            download_failures = 0
            upload_failures = 0
            failed = 0
            event_log = []

            selected_episodes = [
                ep for i, ep in enumerate(st.session_state.new_episodes)
                if st.session_state.selected_episodes.get(i, False)
            ]
            selected_count = len(selected_episodes)

            if st.button(
                f"⬇️ Download Selected Episodes ({selected_count})",
                type="primary",
                use_container_width=True,
                disabled=selected_count == 0,
            ):
                successful = 0
                failed = 0
                downloaded_shiurim = load_downloaded_shiurim(db_file)

                target_folder_id = resolve_drive_folder(drive_base_folder, feed_name, use_subfolders) if is_drive_mode else None
                target_local_dir = resolve_local_folder(base_output_dir, feed_name, use_subfolders)

                for idx, (title, page_url, shiur_id) in enumerate(selected_episodes):
                    data = get_mp3_url_from_page(page_url)
                    if not data or not data.get('downloadURL'):
                        failed += 1
                        continue

                    actual_shiur_id = str(data.get('shiurID')) if data.get('shiurID') else shiur_id

                    if is_drive_mode:
                        file_info = download_and_upload_to_drive(data['downloadURL'], title, target_folder_id, actual_shiur_id)
                        if file_info:
                            successful += 1
                        else:
                            failed += 1
                    else:
                        if download_mp3(data['downloadURL'], title, target_local_dir):
                            successful += 1
                        else:
                            failed += 1

                    if actual_shiur_id:
                        downloaded_shiurim.add(str(actual_shiur_id))

                    if idx < len(selected_episodes) - 1:
                        time.sleep(delay)

                        episode_status = st.empty()
                        episode_status.info("⏳ Processing...")

                        # Get MP3 URL from page data
                        episode_data = get_mp3_url_from_page(page_url) or {}
                        parser_meta = episode_data.get('_parser_meta', {})

                        if not episode_data.get('downloadURL'):
                            parse_failures += 1
                            failure_reason = parser_meta.get('failure_reason') or "Could not find MP3 download link"
                            st.error(f"❌ Parse failed: {failure_reason}")
                            episode_status.error("Parse failed")
                            st.markdown(f"Lecture page: [{page_url}]({page_url})")
                            st.markdown(
                                "**Manual fallback:** 1) Open the lecture page above 2) Find/copy the direct MP3 link (if available) 3) Upload manually."
                            )
                            debug_payload = {
                                'page_url': page_url,
                                'failure_reason': failure_reason,
                                'attempts': parser_meta.get('attempts', []),
                                'detected_markers': parser_meta.get('detected_markers', {}),
                            }
                            st.caption("Copy debug info")
                            st.code(json.dumps(debug_payload, separators=(',', ':'), ensure_ascii=False), language="json")
                        else:
                            mp3_url = episode_data['downloadURL']
                            if episode_data.get('duration'):
                                st.write(f"**Duration:** {episode_data['duration']}")
                            st.write(f"**MP3 URL:** {mp3_url}")
                save_downloaded_shiurim(db_file, downloaded_shiurim)
                st.success("✅ Download complete!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", selected_count)
                c2.metric("Successful", successful)
                c3.metric("Failed", failed)

                st.session_state.new_episodes = []
                st.session_state.selected_episodes = {}
                st.session_state.feed_checked = False

        elif st.session_state.feed_checked and not st.session_state.new_episodes:
            st.info("✅ All episodes have already been downloaded!")

                    if actual_shiur_id:
                        downloaded_shiurim.add(str(actual_shiur_id))

                    if idx < len(selected_episodes) - 1:
                        time.sleep(delay)

                save_downloaded_shiurim(db_file, downloaded_shiurim)
                st.success("✅ Download complete!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", selected_count)
                c2.metric("Successful", successful)
                c3.metric("Failed", failed)

                st.session_state.new_episodes = []
                st.session_state.selected_episodes = {}
                st.session_state.feed_checked = False

                            if use_google_drive:
                                # Upload to Google Drive (with shiur ID in description for tracking)
                                file_info = download_and_upload_to_drive(mp3_url, title, target_folder_id, actual_shiur_id)

                                if file_info:
                                    st.success(f"✅ Uploaded to Google Drive: {file_info.get('name', title)}")
                                    if 'webViewLink' in file_info:
                                        st.caption(f"[Open in Drive]({file_info['webViewLink']})")
                                    successful += 1
                                else:
                                    st.error("❌ Upload failed")
                                    failed += 1
                            else:
                                if download_mp3(mp3_url, title, target_output_dir):
                                    st.success("✅ Saved locally")
                                    successful += 1
                                else:
                                    st.error("❌ Local download failed")
                                    failed += 1

                            # Mark as downloaded in local JSON DB only for local mode
                            actual_shiur_id = episode_data.get('shiurID')
                            if actual_shiur_id:
                                actual_shiur_id = str(actual_shiur_id)  # Convert to string for consistency
                            else:
                                actual_shiur_id = shiur_id  # Fallback to URL-extracted ID

                            # Upload to Google Drive (with shiur ID in description for tracking)
                            transfer_result = download_and_upload_to_drive(mp3_url, title, target_folder_id, actual_shiur_id)

                            if transfer_result.get('ok'):
                                file_info = transfer_result.get('file_info', {})
                                st.success(f"✅ Uploaded to Google Drive: {file_info.get('name', title)}")
                                if 'webViewLink' in file_info:
                                    st.caption(f"[Open in Drive]({file_info['webViewLink']})")
                                successful += 1
                                episode_status.success("Uploaded")
                            if actual_shiur_id and not use_google_drive:
                                downloaded_shiurim = load_downloaded_shiurim(db_file)
                                downloaded_shiurim.add(actual_shiur_id)
                                save_downloaded_shiurim(db_file, downloaded_shiurim)
                                st.caption(f"✓ Marked shiur {actual_shiur_id} as downloaded")
        elif st.session_state.feed_checked and not st.session_state.new_episodes:
            st.info("✅ All episodes have already been downloaded!")

    st.divider()
    with st.expander("📋 View Uploaded Shiurim"):
        downloaded_shiurim = load_downloaded_shiurim(db_file)
        if downloaded_shiurim:
            st.write(f"Total tracked shiurim: {len(downloaded_shiurim)}")
        else:
            st.info("No shiurim tracked yet.")

            for idx, (i, (title, page_url, shiur_id)) in enumerate(selected_episodes):
                progress = (idx + 1) / len(selected_episodes)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx+1}/{len(selected_episodes)}")

                                if actual_shiur_id:
                                    downloaded_shiurim = load_downloaded_shiurim(db_file)
                                    downloaded_shiurim.add(actual_shiur_id)
                                    save_downloaded_shiurim(db_file, downloaded_shiurim)
                                    st.caption(f"✓ Marked shiur {actual_shiur_id} as downloaded")
                            else:
                                error_stage = transfer_result.get('error_stage')
                                error_message = transfer_result.get('error') or 'Unknown error'
                                if error_stage == 'download':
                                    st.error(f"❌ Download failed: {error_message}")
                                    episode_status.error("Download failed")
                                    download_failures += 1
                                else:
                                    st.error(f"❌ Upload failed: {error_message}")
                                    episode_status.error("Upload failed")
                                    upload_failures += 1
                episode_data = get_mp3_url_from_page(page_url)

                if not episode_data or not episode_data.get('downloadURL'):
                    failed += 1
                    event_log.append(f"Could not find an MP3 link for '{title[:42]}'.")
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
            status_text.text("Upload complete!")

            st.divider()
            if use_google_drive:
                st.success("✅ Upload to Google Drive Complete!")
            else:
                st.success("✅ Local download complete!")
            status_text.text("Done")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", len(selected_episodes))
            with col2:
                st.metric("Successes", successful, delta=successful, delta_color="normal")
            with col3:
                total_failures = parse_failures + download_failures + upload_failures
                st.metric("Failures", total_failures, delta=total_failures if total_failures > 0 else None, delta_color="inverse")
            with col4:
                st.metric("Parse Failures", parse_failures)

            st.subheader("Final Summary")
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
            with summary_col1:
                st.metric("parse failures", parse_failures)
            with summary_col2:
                st.metric("download failures", download_failures)
            with summary_col3:
                st.metric("upload failures", upload_failures)
            with summary_col4:
                st.metric("successes", successful)

            # Clear the selection after download
            st.success("Download run finished.")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(selected_episodes))
            col2.metric("Successful", successful)
            col3.metric("Failed", failed)

            if failed:
                st.info("Some episodes were skipped. Common reasons: missing MP3 link, temporary network issue, or Drive permission timeout.")

            st.session_state.new_episodes = []
            st.session_state.selected_episodes = {}
            st.session_state.feed_checked = False

    elif st.session_state.feed_checked and not st.session_state.new_episodes:
        st.info("You're all caught up. No new episodes to download right now.")
    else:
        st.caption("Start by clicking 'Check for new episodes'.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    with st.expander("📋 View Uploaded Shiurim"):
        downloaded_shiurim = load_downloaded_shiurim(db_file)
        if downloaded_shiurim:
            st.write(f"Total tracked shiurim: {len(downloaded_shiurim)}")
        else:
            st.info("No shiurim tracked yet.")
        if use_google_drive:
            if not gd.is_authenticated():
                st.info("Sign in to Google Drive to view uploaded shiur tracking in Drive mode.")
            else:
                st.info("📂 Checking Google Drive for uploaded shiurim...")

                check_folder_id = None
                if drive_base_folder:
                    base_folder_id = gd.find_or_create_folder(drive_base_folder)
                    if base_folder_id:
                        if use_subfolders:
                            safe_feed_name = sanitize_filename(feed_name)
                            check_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                        else:
                            check_folder_id = base_folder_id
                elif use_subfolders:
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
                    check_folder_id = gd.find_or_create_folder(safe_feed_name)

                if check_folder_id:
                    uploaded_shiur_ids = gd.get_uploaded_shiur_ids(check_folder_id)
                    if uploaded_shiur_ids:
                        st.write(f"Total uploaded to `{feed_name}` folder: {len(uploaded_shiur_ids)}")
                        shiur_list = sorted(list(uploaded_shiur_ids), reverse=True)

                        cols = st.columns(5)
                        for i, shiur_id in enumerate(shiur_list):
                            col_idx = i % 5
                            with cols[col_idx]:
                                st.caption(shiur_id)
                    else:
                        st.info("No shiurim uploaded to this folder yet")
                else:
                    st.warning("Could not find/create target Google Drive folder")
        else:
            downloaded_shiurim = load_downloaded_shiurim(db_file)
            if downloaded_shiurim:
                st.write(f"Total in local database: {len(downloaded_shiurim)}")
                shiur_list = sorted(list(downloaded_shiurim), reverse=True)

                cols = st.columns(5)
                for i, shiur_id in enumerate(shiur_list):
                    col_idx = i % 5
                    with cols[col_idx]:
                        st.caption(shiur_id)

                if st.button("🗑️ Clear Local Database", type="secondary"):
                # Clear database option (only for local mode)
                if st.button("Clear local database", type="secondary"):
                    if st.checkbox("Are you sure? This cannot be undone!"):
                        save_downloaded_shiurim(db_file, set())
                        st.success("Database cleared")
                        st.rerun()
            else:
                st.info("No shiurim in local database yet.")
                st.info("No saved history yet. Sign in to Google Drive to track uploads automatically.")


    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
