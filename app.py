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


def download_and_upload_to_drive(mp3_url, title, folder_id, shiur_id=None):
    """Download MP3 file and upload to Google Drive."""
    try:
        filename = sanitize_filename(title) + '.mp3'
        response = session.get(mp3_url, stream=True)
        response.raise_for_status()

        file_content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_content += chunk

        description = f"shiurID:{shiur_id}" if shiur_id else None

        return gd.upload_file_to_drive(
            file_content,
            filename,
            folder_id=folder_id,
            mime_type='audio/mpeg',
            description=description,
        )
    except Exception as e:
        st.error(f"Error downloading/uploading {title}: {e}")
        return None


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

    st.title("🎧 YUTorah Podcast Downloader")
    st.markdown("Download shiurim from YUTorah RSS feeds")

    if 'new_episodes' not in st.session_state:
        st.session_state.new_episodes = []
    if 'selected_episodes' not in st.session_state:
        st.session_state.selected_episodes = {}
    if 'feed_checked' not in st.session_state:
        st.session_state.feed_checked = False
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = {}

    with st.sidebar:
        st.header("⚙️ Settings")
        st.subheader("☁️ Google Drive")

        query_params = st.query_params
        if 'code' in query_params:
            gd.handle_oauth_callback(query_params['code'])
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
                if st.button("Delete Feed"):
                    if feed_to_delete in feeds:
                        del feeds[feed_to_delete]
                        save_feeds_config(feeds)
                        st.success(f"Deleted feed: {feed_to_delete}")
                        st.rerun()

        st.divider()
        st.subheader("Download Settings")

        if gd.is_authenticated():
            st.info("📂 Files will be saved to your Google Drive")
            drive_base_folder = st.text_input("Google Drive Folder", value="YUTorah Podcasts")
            base_output_dir = "downloads"
        else:
            st.warning("⚠️ Files will be saved locally on the server")
            base_output_dir = st.text_input("Base Output Directory", value="downloads")
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

    st.divider()

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

    st.divider()
    with st.expander("📋 View Uploaded Shiurim"):
        downloaded_shiurim = load_downloaded_shiurim(db_file)
        if downloaded_shiurim:
            st.write(f"Total tracked shiurim: {len(downloaded_shiurim)}")
        else:
            st.info("No shiurim tracked yet.")


if __name__ == '__main__':
    main()
