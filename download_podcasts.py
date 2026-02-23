#!/usr/bin/env python3
"""
YUTorah Podcast Downloader

This script downloads podcast episodes from a YUTorah RSS feed.
It parses the RSS feed, visits each episode page, and downloads the MP3 files.
No login required - extracts download URLs from public page data.
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

# Default RSS feed URL
DEFAULT_RSS_URL = "http://www.yutorah.org/rss/RssAudioOnly/teacher/80307"

# Session for HTTP requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})


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

    Handles multiple URL formats:
    - https://www.yutorah.org/lectures/details?shiurID=1159876
    - https://www.yutorah.org/lectures/1160274/
    - https://www.yutorah.org/lectures/lecture.cfm/1160032

    Args:
        page_url: URL of the episode page

    Returns:
        Shiur ID as string, or None if not found
    """
    # Format 1: Query parameter - ?shiurID=1159876
    try:
        parsed = urlparse(page_url)
        params = parse_qs(parsed.query)
        if 'shiurID' in params:
            return params['shiurID'][0]
    except:
        pass

    # Format 2: In path - /lectures/1160274/ or /lectures/lecture.cfm/1160032
    # Look for a sequence of digits in the path
    match = re.search(r'/lectures/(?:lecture\.cfm/|details/)?(\d+)', page_url)
    if match:
        return match.group(1)

    # Format 3: shiurID in path or query (legacy fallback)
    match = re.search(r'shiurID[=:](\d+)', page_url)
    if match:
        return match.group(1)

    return None


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
    Visit episode page and extract MP3 download URL from embedded JSON data.

    The page contains a JavaScript variable 'lecturePlayerData' with all episode
    information including the direct download URL. This is publicly accessible
    without authentication.

    Args:
        page_url: URL of the episode page

    Returns:
        Dictionary with episode data including 'downloadURL', 'duration', 'title', etc.
        Returns None if extraction fails.
    """
    try:
        response = session.get(page_url)
        response.raise_for_status()

        html_content = response.text
        strategy_results = []

        strategies = [
            ("lecturePlayerData", _extract_from_lecture_player_data),
            ("nextData", _extract_from_next_data),
            ("scriptBlobs", _extract_from_script_blobs),
            ("audioTags", _extract_from_audio_tags),
        ]

        for strategy_name, strategy in strategies:
            extracted, markers = strategy(html_content)
            strategy_results.append({
                'strategy': strategy_name,
                'markers': markers,
            })
            if extracted:
                normalized = _normalize_episode_data(extracted, page_url)
                normalized['strategies_attempted'] = [
                    entry['strategy'] for entry in strategy_results
                ]
                normalized['strategy_markers'] = {
                    entry['strategy']: entry['markers'] for entry in strategy_results
                }
                return normalized

        return {
            'failure_reason': 'no_supported_audio_payload_found',
            'strategies_attempted': [entry['strategy'] for entry in strategy_results],
            'strategy_markers': {
                entry['strategy']: entry['markers'] for entry in strategy_results
            },
            'downloadURL': None,
            'playerDownloadURL': None,
            'shiurID': extract_shiur_id(page_url),
        }

    except Exception as e:
        print(f"Error fetching page {page_url}: {e}")
        return {
            'failure_reason': f'page_fetch_error: {e}',
            'strategies_attempted': [],
            'strategy_markers': {},
            'downloadURL': None,
            'playerDownloadURL': None,
            'shiurID': extract_shiur_id(page_url),
        }


def _extract_json_script_blocks(html_content):
    """Extract inline JSON from <script> tags, including __NEXT_DATA__ payloads."""
    pattern = r'<script[^>]*?(?:id="([^"]+)")?[^>]*?type="application/json"[^>]*>(.*?)</script>'
    script_blocks = []
    for script_id, script_body in re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE):
        text = script_body.strip()
        if text:
            script_blocks.append({'id': script_id, 'text': text})
    return script_blocks


def _walk_for_audio_fields(data, results):
    """Recursively scan nested JSON for audio-related fields."""
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = key.lower()
            if key in ('downloadURL', 'playerDownloadURL') and isinstance(value, str):
                results[key] = value
            elif 'downloadurl' in key_lower and isinstance(value, str):
                results.setdefault('downloadURL', value)
            elif key_lower in ('shiurid', 'shiurid'):
                results.setdefault('shiurID', str(value))
            elif key_lower in ('duration', 'shiurduration'):
                results.setdefault('duration', value)
            elif key_lower in ('shiurmedialengthinseconds', 'durationseconds'):
                results.setdefault('durationSeconds', value)
            elif key_lower in ('title', 'shiurtitle') and isinstance(value, str):
                results.setdefault('title', value)
            elif key_lower in ('description', 'shiurdescription') and isinstance(value, str):
                results.setdefault('description', value)
            elif key_lower in ('shiurteacherfullname', 'teachername') and isinstance(value, str):
                results.setdefault('teacherName', value)
            elif key_lower in ('shiururl',):
                results.setdefault('shiurURL', value)

            if isinstance(value, str) and value.lower().endswith('.mp3'):
                results.setdefault('downloadURL', value)

            _walk_for_audio_fields(value, results)
    elif isinstance(data, list):
        for item in data:
            _walk_for_audio_fields(item, results)


def _extract_from_lecture_player_data(html_content):
    """Strategy A: parse legacy lecturePlayerData payload."""
    pattern = r'var\s+lecturePlayerData\s*=\s*(\{.*?\});'
    match = re.search(pattern, html_content, re.DOTALL)
    markers = {
        'lecturePlayerData_found': bool(match),
    }

    if not match:
        return None, markers

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        markers['json_error'] = str(e)
        return None, markers

    return {
        'downloadURL': data.get('downloadURL'),
        'playerDownloadURL': data.get('playerDownloadURL'),
        'shiurURL': data.get('shiurURL'),
        'title': data.get('shiurTitle'),
        'duration': data.get('shiurDuration'),
        'durationSeconds': data.get('shiurMediaLengthInSeconds'),
        'description': data.get('shiurDescription'),
        'teacherName': data.get('shiurTeacherFullName'),
        'shiurID': data.get('shiurID'),
        'dateText': data.get('shiurDateText'),
    }, markers


def _extract_from_next_data(html_content):
    """Strategy B: parse modern Next.js app payloads from __NEXT_DATA__."""
    blocks = _extract_json_script_blocks(html_content)
    next_blocks = [block for block in blocks if block['id'] == '__NEXT_DATA__']
    markers = {
        'json_script_blocks': len(blocks),
        'next_data_blocks': len(next_blocks),
    }

    for block in next_blocks:
        try:
            payload = json.loads(block['text'])
        except json.JSONDecodeError:
            continue
        results = {}
        _walk_for_audio_fields(payload, results)
        if results.get('downloadURL') or results.get('playerDownloadURL'):
            return results, markers

    return None, markers


def _extract_from_script_blobs(html_content):
    """Strategy C: parse script/json blobs for known keys and MP3 URL patterns."""
    markers = {
        'downloadURL_key_mentions': len(re.findall(r'downloadURL', html_content, re.IGNORECASE)),
        'shiurID_key_mentions': len(re.findall(r'shiurID', html_content, re.IGNORECASE)),
    }

    snippets = re.findall(r'\{[^{}]*?(?:downloadURL|playerDownloadURL|shiurID)[^{}]*?\}', html_content, re.DOTALL | re.IGNORECASE)
    for snippet in snippets[:30]:
        cleaned = re.sub(r'([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', snippet)
        cleaned = cleaned.replace("'", '"')
        try:
            candidate = json.loads(cleaned)
            results = {}
            _walk_for_audio_fields(candidate, results)
            if results.get('downloadURL') or results.get('playerDownloadURL'):
                return results, markers
        except Exception:
            continue

    mp3_matches = re.findall(r'https?://[^"\'\s>]+\.mp3(?:\?[^"\'\s>]*)?', html_content, re.IGNORECASE)
    if mp3_matches:
        markers['mp3_match_count'] = len(mp3_matches)
        return {'downloadURL': mp3_matches[0], 'playerDownloadURL': mp3_matches[0]}, markers

    return None, markers


def _extract_from_audio_tags(html_content):
    """Strategy D: parse <audio> and <source> tags for MP3 sources."""
    markers = {
        'audio_tag_count': len(re.findall(r'<audio\b', html_content, re.IGNORECASE)),
        'source_tag_count': len(re.findall(r'<source\b', html_content, re.IGNORECASE)),
    }

    candidates = []
    candidates.extend(re.findall(r'<audio[^>]+src="([^"]+)"', html_content, re.IGNORECASE))
    candidates.extend(re.findall(r'<audio[^>]+src=\'([^\']+)\'', html_content, re.IGNORECASE))
    candidates.extend(re.findall(r'<source[^>]+src="([^"]+)"', html_content, re.IGNORECASE))
    candidates.extend(re.findall(r'<source[^>]+src=\'([^\']+)\'', html_content, re.IGNORECASE))

    for url in candidates:
        if '.mp3' in url.lower():
            return {
                'downloadURL': url,
                'playerDownloadURL': url,
            }, markers

    if candidates:
        return {
            'downloadURL': candidates[0],
            'playerDownloadURL': candidates[0],
        }, markers

    return None, markers


def _normalize_episode_data(data, page_url):
    """Normalize extracted payloads to the current downloader schema."""
    normalized = {
        'downloadURL': data.get('downloadURL') or data.get('playerDownloadURL'),
        'playerDownloadURL': data.get('playerDownloadURL') or data.get('downloadURL'),
        'shiurURL': data.get('shiurURL') or page_url,
        'title': data.get('title') or data.get('shiurTitle'),
        'duration': data.get('duration') or data.get('shiurDuration'),
        'durationSeconds': data.get('durationSeconds') or data.get('shiurMediaLengthInSeconds'),
        'description': data.get('description') or data.get('shiurDescription'),
        'teacherName': data.get('teacherName') or data.get('shiurTeacherFullName'),
        'shiurID': str(data.get('shiurID')) if data.get('shiurID') is not None else extract_shiur_id(page_url),
        'dateText': data.get('dateText') or data.get('shiurDateText'),
    }
    return normalized


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

    for i, (title, page_url, shiur_id) in enumerate(new_episodes, 1):
        print(f"[{i}/{len(new_episodes)}] {title}")
        print(f"  Page: {page_url}")
        if shiur_id:
            print(f"  Shiur ID: {shiur_id}")

        # Get MP3 URL from page
        episode_data = get_mp3_url_from_page(page_url)

        if not episode_data or not episode_data.get('downloadURL'):
            print("  Failed: Could not find MP3 download link")
            failed += 1
        else:
            mp3_url = episode_data['downloadURL']
            if episode_data.get('duration'):
                print(f"  Duration: {episode_data['duration']}")
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
    print(f"  Total new episodes: {len(new_episodes)}")


if __name__ == '__main__':
    main()
