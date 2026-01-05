# YUTorah Podcast Downloader

A Python application to download podcast episodes from YUTorah RSS feeds with both a command-line interface and a web interface.

## Features

- 🎧 Downloads MP3 files from YUTorah RSS feeds
- ☁️ **Google Drive Integration** - Save podcasts directly to your Google Drive
- 🚀 **No login required** - Downloads work without YUTorah authentication
- ⏱️ Shows episode duration before downloading
- 📊 Tracks downloaded shiurim to avoid re-downloading
- 🌐 Web interface built with Streamlit
- 📝 Manage multiple RSS feeds
- 📈 Progress tracking and detailed logging
- ⚡ Customizable download limits and delays
- 🎯 Command-line interface for automation
- 👤 Per-user Google Drive - each visitor can use their own account

## Installation

1. Install Python 3.7 or higher

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### Google Drive Integration (Web Interface Only)

The web interface supports uploading podcasts directly to your Google Drive! Each user signs in with their own Google account.

**Setup Instructions:** See [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md) for detailed setup instructions.

**Quick Setup:**
1. Create a Google Cloud project
2. Enable Google Drive API
3. Create OAuth 2.0 credentials
4. Add credentials to Streamlit secrets
5. Users sign in with Google when using the app

**Benefits:**
- Files go directly to each user's Google Drive
- No storage needed on Streamlit servers
- Users control their own files
- Automatic folder organization

## Usage

### Web Interface (Recommended)

Launch the Streamlit web interface:
```bash
streamlit run app.py
```

This will open a web browser with an easy-to-use interface where you can:
- Select from multiple RSS feeds
- Add new feeds or delete existing ones
- **Choose which episodes to download** with checkboxes
- Configure download settings (including automatic subfolders per feed)
- See real-time progress
- View download history
- Manage the database of downloaded shiurim

### Command-Line Interface

#### Basic usage (downloads from default RSS feed):
```bash
python download_podcasts.py
```

#### Download from a specific RSS feed URL:
```bash
python download_podcasts.py --rss-url "https://www.yutorah.org/search/rss?q=..."
```

#### Download from a local RSS file:
```bash
python download_podcasts.py --rss-file rss.rss
```

#### Specify output directory:
```bash
python download_podcasts.py --output-dir "my_podcasts"
```

#### Limit number of downloads:
```bash
python download_podcasts.py --limit 10
```

#### Custom delay between downloads (in seconds):
```bash
python download_podcasts.py --delay 2.0
```

#### Use subfolder for a specific feed:
```bash
python download_podcasts.py --feed-name "Rabbi Moshe Weinberger"
```

This will download to `downloads/Rabbi Moshe Weinberger/` instead of `downloads/`

#### Combined options:
```bash
python download_podcasts.py --rss-file rss.rss --output-dir podcasts --feed-name "My Rabbi" --limit 5 --delay 1.5
```

## Command-line Options

- `--rss-url URL`: RSS feed URL to download from
- `--rss-file PATH`: Path to local RSS file (alternative to --rss-url)
- `--output-dir DIR`: Output directory for downloaded files (default: downloads)
- `--feed-name NAME`: Feed name to use for subfolder (optional, creates subfolder in output-dir)
- `--limit N`: Limit number of episodes to download (0 = no limit)
- `--delay SECONDS`: Delay between downloads in seconds (default: 1.0)
- `--db-file PATH`: Path to database file tracking downloaded shiurim (default: downloaded_shiurim.json)

## Examples

**Download all episodes from the default feed:**
```bash
python download_podcasts.py
```

**Download first 20 episodes from local RSS file:**
```bash
python download_podcasts.py --rss-file rss.rss --limit 20
```

**Download to specific folder with 2-second delay:**
```bash
python download_podcasts.py --output-dir "Rabbi Weinberger Shiurim" --delay 2
```

## How It Works

### Shiur Tracking

The application maintains a database file (`downloaded_shiurim.json`) that tracks all downloaded shiur IDs. This ensures:
- No duplicate downloads
- Efficient incremental updates
- Easy resumption after interruptions

Each time you run the script, it:
1. Loads the database of previously downloaded shiur IDs
2. Fetches the RSS feed
3. Filters out episodes that have already been downloaded
4. Downloads only new episodes
5. Updates the database after each successful download

### RSS Feed Management (Web Interface)

The web interface stores RSS feed configurations in `rss_feeds.json`, allowing you to:
- Quickly switch between different rabbis/teachers
- Add custom RSS feeds
- Manage multiple feeds from one place

## Notes

- **No Login Required**: Downloads work without YUTorah authentication - MP3 URLs are extracted from public page data
- **Shiur Tracking**: The script automatically skips shiurim that have already been downloaded (based on shiur ID)
- **Filename Safety**: Special characters (quotes, colons, Hebrew characters, etc.) are handled automatically to ensure cross-platform compatibility
- **Subfolders**: Each feed can have its own subfolder to keep downloads organized
- **Polite Scraping**: A 1-second delay between downloads is used by default to be respectful to the server
- **Resume-Safe**: The database file is updated after each successful download, so you can safely interrupt the process

## Default RSS Feed

The default RSS feed is configured for Rav Moshe Taragin's shiurim:
```
http://www.yutorah.org/rss/RssAudioOnly/teacher/80307
```

You can change this by using the `--rss-url` parameter or editing the `DEFAULT_RSS_URL` in the script.
