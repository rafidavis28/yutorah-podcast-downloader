#!/usr/bin/env python3
"""
YUTorah Podcast Downloader - Streamlit Web Interface

A web interface for downloading podcast episodes from YUTorah RSS feeds.
"""

import streamlit as st
import json
import os
import re
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


def run_lecture_parser_diagnostics(page_url):
    """Run lecture parser strategies and return a structured diagnostics report."""
    report = {
        "lecture_url": page_url,
        "http_status": None,
        "success": False,
        "successful_strategy": None,
        "downloadURL": None,
        "shiurID": None,
        "strategies": [],
    }

    try:
        response = session.get(page_url)
        report["http_status"] = response.status_code
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        report["error"] = f"HTTP fetch failed: {e}"
        return report

    # Strategy 1: lecturePlayerData JSON blob
    strategy_json = {
        "name": "lecturePlayerData_json",
        "success": False,
    }
    pattern = r'var\s+lecturePlayerData\s*=\s*(\{.*?\});'
    match = re.search(pattern, html_content, re.DOTALL)

    if not match:
        strategy_json["error"] = "lecturePlayerData variable not found"
    else:
        try:
            data = json.loads(match.group(1))
            strategy_json["extracted_downloadURL"] = data.get("downloadURL")
            strategy_json["extracted_shiurID"] = data.get("shiurID")
            if data.get("downloadURL"):
                strategy_json["success"] = True
                report["success"] = True
                report["successful_strategy"] = strategy_json["name"]
                report["downloadURL"] = data.get("downloadURL")
                report["shiurID"] = data.get("shiurID")
            else:
                strategy_json["error"] = "downloadURL missing in lecturePlayerData"
        except json.JSONDecodeError as e:
            strategy_json["error"] = f"JSON decode error: {e}"

    report["strategies"].append(strategy_json)

    # Strategy 2: audio tag src fallback
    strategy_audio = {
        "name": "audio_tag_src",
        "success": False,
    }
    audio_match = re.search(r'<audio[^>]+src="([^"]+)"', html_content)
    if audio_match:
        strategy_audio["extracted_downloadURL"] = audio_match.group(1)
        strategy_audio["success"] = True
        if not report["success"]:
            report["success"] = True
            report["successful_strategy"] = strategy_audio["name"]
            report["downloadURL"] = audio_match.group(1)
            report["shiurID"] = extract_shiur_id(page_url)
    else:
        strategy_audio["error"] = "audio src not found"

    report["strategies"].append(strategy_audio)

    return report


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

        # Download the file content
        response = session.get(mp3_url, stream=True)
        response.raise_for_status()

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

        # Only show local database option when not using Google Drive
        if not gd.is_authenticated():
            db_file = st.text_input(
                "Database File",
                value="downloaded_shiurim.json",
                help="File to track downloaded shiurim (not used with Google Drive)"
            )
        else:
            db_file = "downloaded_shiurim.json"  # Default value, but not used


    # Diagnostics panel
    with st.sidebar.expander("🧪 Diagnostics", expanded=False):
        st.caption("Troubleshoot RSS and lecture parsing behavior.")

        selected_feed_url = feeds.get(feed_name, "")
        rss_diag_url = st.text_input(
            "RSS URL",
            value=selected_feed_url,
            key="diag_rss_url",
            help="Prefilled from the currently selected feed. You can override for testing.",
        )

        lecture_override = st.text_input(
            "Lecture URL override (optional)",
            value="",
            key="diag_lecture_url",
            help="If empty, first lecture link from RSS test results will be used.",
        )

        if "diag_report" not in st.session_state:
            st.session_state.diag_report = {}

        if st.button("Test RSS fetch + parse", key="diag_rss_test", use_container_width=True):
            rss_report = {
                "rss_url": rss_diag_url,
                "http_status": None,
                "item_count": 0,
                "first_three_lecture_links": [],
            }

            try:
                response = session.get(rss_diag_url)
                rss_report["http_status"] = response.status_code
                response.raise_for_status()

                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                rss_report["item_count"] = len(items)

                links = []
                for item in items[:3]:
                    link_elem = item.find('link')
                    if link_elem is not None and link_elem.text:
                        links.append(link_elem.text.strip())
                rss_report["first_three_lecture_links"] = links
            except Exception as e:
                rss_report["error"] = str(e)

            st.session_state.diag_report["rss_test"] = rss_report

        if st.button("Test lecture parse (MP3 extraction only)", key="diag_lecture_test", use_container_width=True):
            lecture_url = lecture_override.strip()
            rss_data = st.session_state.diag_report.get("rss_test", {})
            if not lecture_url:
                first_links = rss_data.get("first_three_lecture_links", [])
                if first_links:
                    lecture_url = first_links[0]

            if not lecture_url:
                st.warning("No lecture URL available. Provide an override or run RSS test first.")
            else:
                lecture_report = run_lecture_parser_diagnostics(lecture_url)
                st.session_state.diag_report["lecture_test"] = lecture_report

        rss_data = st.session_state.diag_report.get("rss_test")
        if rss_data:
            st.markdown("**RSS test result**")
            st.write(f"HTTP status: `{rss_data.get('http_status')}`")
            st.write(f"Item count: `{rss_data.get('item_count', 0)}`")
            st.write("First 3 lecture links:")
            for link in rss_data.get("first_three_lecture_links", []):
                st.code(link, language=None)
            if rss_data.get("error"):
                st.error(rss_data["error"])

        lecture_data = st.session_state.diag_report.get("lecture_test")
        if lecture_data:
            st.markdown("**Lecture parse result**")
            if lecture_data.get("success"):
                st.success(f"Strategy: {lecture_data.get('successful_strategy')}")
                st.write(f"downloadURL: `{lecture_data.get('downloadURL')}`")
                st.write(f"shiurID: `{lecture_data.get('shiurID')}`")
            else:
                st.error("No extraction strategy succeeded.")
                if lecture_data.get("error"):
                    st.error(lecture_data["error"])
                for strat in lecture_data.get("strategies", []):
                    st.write(f"- {strat.get('name')}: {strat.get('error', 'failed')}")

        if st.session_state.diag_report:
            report_json = json.dumps(st.session_state.diag_report, indent=2, ensure_ascii=False)
            st.download_button(
                "Download parser report",
                data=report_json,
                file_name="parser_diagnostics_report.json",
                mime="application/json",
                use_container_width=True,
            )

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header(f"📚 {feed_name}")
        if feed_name in feeds:
            st.code(feeds[feed_name], language=None)

    with col2:
        # Stats - shows Google Drive count when authenticated, otherwise local count
        if gd.is_authenticated():
            st.caption("☁️ Google Drive tracking enabled")
        else:
            downloaded_shiurim = load_downloaded_shiurim(db_file)
            st.metric("Local DB Count", len(downloaded_shiurim))
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

            # Get already uploaded shiur IDs
            # For Google Drive mode, check the actual Drive folder
            # For local mode, use the JSON database
            uploaded_shiur_ids = set()

            if gd.is_authenticated() and drive_base_folder:
                status_text.text("Checking Google Drive for existing uploads...")
                # Find the target folder to check
                base_folder_id = gd.find_or_create_folder(drive_base_folder)
                if base_folder_id:
                    if use_subfolders:
                        safe_feed_name = sanitize_filename(feed_name)
                        check_folder_id = gd.find_or_create_folder(safe_feed_name, base_folder_id)
                    else:
                        check_folder_id = base_folder_id

                    if check_folder_id:
                        uploaded_shiur_ids = gd.get_uploaded_shiur_ids(check_folder_id)
                        st.session_state.target_folder_id = check_folder_id  # Cache for download
            else:
                # Fallback to local JSON database
                uploaded_shiur_ids = load_downloaded_shiurim(db_file)

            # Filter out already uploaded
            new_episodes = []
            for title, page_url in episodes:
                shiur_id = extract_shiur_id(page_url)
                if shiur_id and shiur_id in uploaded_shiur_ids:
                    continue
                new_episodes.append((title, page_url, shiur_id))

            st.session_state.new_episodes = new_episodes
            st.session_state.feed_checked = True
            # Initialize all as selected
            st.session_state.selected_episodes = {i: True for i in range(len(new_episodes))}

            status_text.empty()

            if gd.is_authenticated():
                st.success(f"✅ Found {len(episodes)} total episodes, {len(new_episodes)} new (checked Google Drive: {len(uploaded_shiur_ids)} already uploaded)")
            else:
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

                        # Get MP3 URL from page data
                        episode_data = get_mp3_url_from_page(page_url)

                        if not episode_data or not episode_data.get('downloadURL'):
                            st.error("❌ Failed: Could not find MP3 download link")
                            failed += 1
                        else:
                            mp3_url = episode_data['downloadURL']
                            if episode_data.get('duration'):
                                st.write(f"**Duration:** {episode_data['duration']}")
                            st.write(f"**MP3 URL:** {mp3_url}")

                            # Get the shiur ID - prefer from JSON data (more reliable)
                            actual_shiur_id = episode_data.get('shiurID')
                            if actual_shiur_id:
                                actual_shiur_id = str(actual_shiur_id)  # Convert to string for consistency
                            else:
                                actual_shiur_id = shiur_id  # Fallback to URL-extracted ID

                            # Upload to Google Drive (with shiur ID in description for tracking)
                            file_info = download_and_upload_to_drive(mp3_url, title, target_folder_id, actual_shiur_id)

                            if file_info:
                                st.success(f"✅ Uploaded to Google Drive: {file_info.get('name', title)}")
                                if 'webViewLink' in file_info:
                                    st.caption(f"[Open in Drive]({file_info['webViewLink']})")
                                successful += 1

                                # Mark as downloaded - prefer shiurID from JSON data (more reliable)
                                actual_shiur_id = episode_data.get('shiurID')
                                if actual_shiur_id:
                                    actual_shiur_id = str(actual_shiur_id)  # Convert to string for consistency
                                else:
                                    actual_shiur_id = shiur_id  # Fallback to URL-extracted ID

                                if actual_shiur_id:
                                    downloaded_shiurim = load_downloaded_shiurim(db_file)
                                    downloaded_shiurim.add(actual_shiur_id)
                                    save_downloaded_shiurim(db_file, downloaded_shiurim)
                                    st.caption(f"✓ Marked shiur {actual_shiur_id} as downloaded")
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

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", len(selected_episodes))
            with col2:
                st.metric("Successful", successful, delta=successful, delta_color="normal")
            with col3:
                st.metric("Failed", failed, delta=failed if failed > 0 else None, delta_color="inverse")

            # Clear the selection after download
            st.session_state.new_episodes = []
            st.session_state.selected_episodes = {}
            st.session_state.feed_checked = False

    elif st.session_state.feed_checked and not st.session_state.new_episodes:
        st.info("✅ All episodes have already been downloaded!")

    # View uploaded shiurim
    st.divider()
    with st.expander("📋 View Uploaded Shiurim"):
        # Check Google Drive if authenticated
        if gd.is_authenticated() and drive_base_folder:
            st.info("📂 Checking Google Drive for uploaded shiurim...")

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
                if st.button("🗑️ Clear Local Database", type="secondary"):
                    if st.checkbox("Are you sure? This cannot be undone!"):
                        save_downloaded_shiurim(db_file, set())
                        st.success("Database cleared")
                        st.rerun()
            else:
                st.info("No shiurim in local database. Sign in to Google Drive to track uploads.")


if __name__ == '__main__':
    main()
