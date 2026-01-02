#!/usr/bin/env python3
"""
YUTorah Podcast Downloader

This script downloads podcast episodes from a YUTorah RSS feed.
It parses the RSS feed, visits each episode page, and downloads the MP3 files.
Handles both public and login-required episodes.
"""

import os
import re
import sys
import time
import json
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
import streamlit as st


# Configuration - Update these with your credentials
YUTORAH_USERNAME = st.secrets["YUTORAH_USERNAME"]  # Add your YUTorah username here
YUTORAH_PASSWORD = st.secrets["YUTORAH_PASSWORD"]  # Add your YUTorah password here

# Default RSS feed URL
DEFAULT_RSS_URL = "http://www.yutorah.org/rss/RssAudioOnly/teacher/80307"

# Session for maintaining login state
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

logged_in = False


def load_downloaded_shiurim(db_file):
    """
    Load the set of already downloaded shiur IDs from JSON file.

    Args:
        db_file: Path to the JSON database file

    Returns:
        Set of downloaded shiur IDs
    """
    if os.path.exists(db_file):
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('downloaded_shiurim', []))
        except Exception as e:
            print(f"Warning: Could not load download database: {e}")
            return set()
    return set()


def save_downloaded_shiurim(db_file, downloaded_shiurim):
    """
    Save the set of downloaded shiur IDs to JSON file.

    Args:
        db_file: Path to the JSON database file
        downloaded_shiurim: Set of downloaded shiur IDs
    """
    try:
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump({
                'downloaded_shiurim': sorted(list(downloaded_shiurim)),
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save download database: {e}")


def extract_shiur_id(page_url):
    """
    Extract shiur ID from the episode page URL.

    Args:
        page_url: URL of the episode page

    Returns:
        Shiur ID as string, or None if not found
    """
    # URL format: https://www.yutorah.org/lectures/details?shiurID=1159876
    try:
        parsed = urlparse(page_url)
        params = parse_qs(parsed.query)
        if 'shiurID' in params:
            return params['shiurID'][0]
    except:
        pass

    # Try regex as fallback
    match = re.search(r'shiurID[=:](\d+)', page_url)
    if match:
        return match.group(1)

    return None


def login_to_yutorah():
    """
    Login to YUTorah website to access restricted content.
    """
    global logged_in

    if not YUTORAH_USERNAME or not YUTORAH_PASSWORD:
        print("Warning: No credentials provided. Login-required episodes will be skipped.")
        return False

    if logged_in:
        return True

    print("Logging in to YUTorah...")

    # Get the login page to find any CSRF tokens or form fields
    login_page_url = "https://www.yutorah.org/login"
    try:
        response = session.get(login_page_url)
        response.raise_for_status()

        # Parse the login page to find the form
        soup = BeautifulSoup(response.text, 'html.parser')
        login_form = soup.find('form')

        # Prepare login data
        login_data = {
            'username': YUTORAH_USERNAME,
            'password': YUTORAH_PASSWORD,
        }

        # Add any hidden fields from the form
        if login_form:
            for hidden in login_form.find_all('input', type='hidden'):
                if hidden.get('name'):
                    login_data[hidden['name']] = hidden.get('value', '')

        # Submit login
        login_url = "https://www.yutorah.org/login"
        response = session.post(login_url, data=login_data)
        response.raise_for_status()

        # Check if login was successful
        if 'logout' in response.text.lower() or 'sign out' in response.text.lower():
            print("Successfully logged in to YUTorah")
            logged_in = True
            return True
        else:
            print("Login may have failed. Continuing anyway...")
            logged_in = True  # Try anyway
            return True

    except Exception as e:
        print(f"Error during login: {e}")
        return False


def fetch_rss_feed(rss_url):
    """
    Fetch and parse the RSS feed.

    Args:
        rss_url: URL of the RSS feed

    Returns:
        ElementTree root element
    """
    print(f"Fetching RSS feed from {rss_url}...")
    try:
        response = session.get(rss_url)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)
        print(f"RSS feed fetched successfully")
        return root

    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        sys.exit(1)


def extract_episode_links(rss_root):
    """
    Extract episode links from RSS feed.

    Args:
        rss_root: ElementTree root element

    Returns:
        List of tuples (title, link)
    """
    episodes = []

    for item in rss_root.findall('.//item'):
        title_elem = item.find('title')
        link_elem = item.find('link')

        if title_elem is not None and link_elem is not None:
            # Extract text from CDATA
            title_text = title_elem.text or ''
            link_text = link_elem.text or ''

            # Remove CDATA markers if present
            title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text).strip()
            link = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link_text).strip()

            if link:
                episodes.append((title, link))

    print(f"Found {len(episodes)} episodes in RSS feed")
    return episodes


def get_mp3_url_from_page(page_url):
    """
    Visit episode page and extract MP3 download URL.

    Args:
        page_url: URL of the episode page

    Returns:
        Tuple of (mp3_url, requires_login)
    """
    try:
        response = session.get(page_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # First check for download-disabled (requires login)
        download_disabled = soup.find('li', class_='download-disabled')
        if download_disabled:
            # Need to login
            if not logged_in:
                if not login_to_yutorah():
                    return None, True
                # Retry fetching the page after login
                response = session.get(page_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

        # Look for the download link
        download_li = soup.find('li', class_='download')
        if download_li:
            download_link = download_li.find('a', href=True)
            if download_link:
                mp3_url = download_link['href']
                # Make sure it's an absolute URL
                if not mp3_url.startswith('http'):
                    mp3_url = urljoin(page_url, mp3_url)
                return mp3_url, False

        return None, False

    except Exception as e:
        print(f"Error fetching page {page_url}: {e}")
        return None, False


def sanitize_filename(filename):
    """
    Sanitize filename to remove invalid characters for Windows/Unix filesystems.
    Handles Hebrew characters, special punctuation, and ensures cross-platform compatibility.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for all filesystems
    """
    # First, replace all types of quotation marks with single quotes
    # This includes: ASCII quotes, smart quotes, Hebrew quotes, etc.
    quote_chars = [
        '"',   # ASCII double quote (U+0022)
        '"',   # Left double quotation mark (U+201C)
        '"',   # Right double quotation mark (U+201D)
        '״',   # Hebrew punctuation gershayim (U+05F4) - looks like quotes
        '‟',   # Double high-reversed-9 quotation mark (U+201F)
        '„',   # Double low-9 quotation mark (U+201E)
        '«',   # Left-pointing double angle quotation mark (U+00AB)
        '»',   # Right-pointing double angle quotation mark (U+00BB)
    ]
    for quote in quote_chars:
        filename = filename.replace(quote, "'")

    # Replace colons with dashes (including special Unicode colons)
    filename = filename.replace(':', '-')  # ASCII colon
    filename = filename.replace('׃', '-')  # Hebrew punctuation sof pasuq (looks like colon)

    # Remove Windows-invalid characters: < > / \ | ? *
    # Use a more comprehensive regex that catches all variations
    filename = re.sub(r'[<>/\\|?*]', '', filename)

    # Replace multiple spaces/dashes with single ones
    filename = re.sub(r'\s+', ' ', filename)
    filename = re.sub(r'-+', '-', filename)

    # Remove leading/trailing spaces, periods, and dashes (Windows doesn't allow these)
    filename = filename.strip('. -')

    # Trim to reasonable length (Windows has 260 char path limit)
    # Leave room for directory path
    if len(filename) > 180:
        # Keep extension if present
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            filename = name[:180-len(ext)-1] + '.' + ext
        else:
            filename = filename[:180]

    # Ensure we have a valid filename
    if not filename or filename == '.':
        filename = 'untitled'

    return filename


def download_mp3(mp3_url, title, output_dir):
    """
    Download MP3 file.

    Args:
        mp3_url: URL of the MP3 file
        title: Title of the episode
        output_dir: Directory to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get filename from URL
        parsed_url = urlparse(mp3_url)
        url_filename = os.path.basename(parsed_url.path)

        # Use URL filename if available, otherwise create from title
        # IMPORTANT: Always sanitize the filename, even if it comes from the URL
        if url_filename and url_filename.endswith('.mp3'):
            filename = sanitize_filename(url_filename)
        else:
            filename = sanitize_filename(title) + '.mp3'

        filepath = os.path.join(output_dir, filename)

        # Skip if file already exists
        if os.path.exists(filepath):
            print(f"  File already exists: {filename}")
            return True

        print(f"  Downloading: {filename}")

        # Download with progress
        response = session.get(mp3_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(filepath, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Simple progress indicator
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Progress: {percent:.1f}%", end='')
                print()  # New line after progress

        print(f"  Downloaded successfully: {filename}")
        return True

    except Exception as e:
        print(f"  Error downloading {mp3_url}: {e}")
        # Clean up partial download
        if os.path.exists(filepath):
            os.remove(filepath)
        return False


def main():
    """
    Main function to orchestrate the download process.
    """
    parser = argparse.ArgumentParser(
        description='Download podcast episodes from YUTorah RSS feed'
    )
    parser.add_argument(
        '--rss-url',
        default=DEFAULT_RSS_URL,
        help='RSS feed URL (default: Rabbi Moshe Weinberger feed)'
    )
    parser.add_argument(
        '--rss-file',
        help='Path to local RSS file (alternative to --rss-url)'
    )
    parser.add_argument(
        '--output-dir',
        default='downloads',
        help='Output directory for downloaded files (default: downloads)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of episodes to download'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between downloads in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--db-file',
        default='downloaded_shiurim.json',
        help='Path to database file tracking downloaded shiurim (default: downloaded_shiurim.json)'
    )
    parser.add_argument(
        '--feed-name',
        help='Feed name to use for subfolder (if not specified, no subfolder is created)'
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)

    # Add subfolder if feed name is specified
    if args.feed_name:
        safe_feed_name = sanitize_filename(args.feed_name)
        output_dir = output_dir / safe_feed_name

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir.absolute()}")
    print()

    # Load already downloaded shiurim
    downloaded_shiurim = load_downloaded_shiurim(args.db_file)
    print(f"Already downloaded: {len(downloaded_shiurim)} shiurim")
    print()

    # Fetch RSS feed
    if args.rss_file:
        print(f"Reading RSS feed from local file: {args.rss_file}")
        with open(args.rss_file, 'r', encoding='utf-8') as f:
            rss_root = ET.fromstring(f.read())
    else:
        rss_root = fetch_rss_feed(args.rss_url)

    # Extract episode links
    episodes = extract_episode_links(rss_root)

    if not episodes:
        print("No episodes found in RSS feed")
        sys.exit(1)

    # Filter out already downloaded episodes
    new_episodes = []
    for title, page_url in episodes:
        shiur_id = extract_shiur_id(page_url)
        if shiur_id and shiur_id in downloaded_shiurim:
            continue  # Skip already downloaded
        new_episodes.append((title, page_url, shiur_id))

    print(f"Found {len(episodes)} total episodes, {len(new_episodes)} new episodes to download")

    if not new_episodes:
        print("All episodes have already been downloaded!")
        sys.exit(0)

    # Apply limit if specified
    if args.limit:
        new_episodes = new_episodes[:args.limit]
        print(f"Limiting to {args.limit} episodes")

    print()
    print("=" * 80)
    print()

    # Download each episode
    successful = 0
    failed = 0
    skipped = 0

    for i, (title, page_url, shiur_id) in enumerate(new_episodes, 1):
        print(f"[{i}/{len(new_episodes)}] {title}")
        print(f"  Page: {page_url}")
        if shiur_id:
            print(f"  Shiur ID: {shiur_id}")

        # Get MP3 URL from page
        mp3_url, requires_login = get_mp3_url_from_page(page_url)

        if not mp3_url:
            if requires_login:
                print("  Skipped: Requires login (no credentials provided)")
                skipped += 1
            else:
                print("  Failed: Could not find MP3 download link")
                failed += 1
        else:
            print(f"  MP3 URL: {mp3_url}")

            # Download the MP3
            if download_mp3(mp3_url, title, output_dir):
                successful += 1
                # Mark as downloaded
                if shiur_id:
                    downloaded_shiurim.add(shiur_id)
                    save_downloaded_shiurim(args.db_file, downloaded_shiurim)
            else:
                failed += 1

        print()

        # Delay between requests to be polite
        if i < len(new_episodes):
            time.sleep(args.delay)

    # Summary
    print("=" * 80)
    print(f"Download complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Total new episodes: {len(new_episodes)}")


if __name__ == '__main__':
    main()
