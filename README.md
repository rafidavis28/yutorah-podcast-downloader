# YUTorah Podcast Downloader

Download shiurim from YUTorah RSS feeds directly to your Google Drive.

## Features

- **Google Drive Integration** - Saves directly to your Drive
- **No login required** - Downloads work without YUTorah authentication
- **Duplicate detection** - Tracks uploaded shiurim in Drive metadata
- **Web UI** - Easy-to-use Streamlit interface
- **CLI** - Command-line for automation

## Quick Start

### Web Interface

```bash
pip install -r requirements.txt
streamlit run app.py
```

1. Sign in with Google
2. Select RSS feed
3. Check for new episodes
4. Download selected episodes

### Command Line

```bash
python download_podcasts.py --rss-url "https://www.yutorah.org/rss/RssAudioOnly/teacher/80307"
```

Options:
- `--rss-url URL` - RSS feed URL
- `--output-dir DIR` - Output directory (default: downloads)
- `--limit N` - Max episodes to download
- `--delay SECONDS` - Delay between downloads (default: 1.0)

## Google Drive Setup

See [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md) for OAuth configuration.

## How It Works

1. Fetches RSS feed for episode links
2. Extracts MP3 URLs from episode page data (`lecturePlayerData` JSON)
3. Downloads and uploads to Google Drive
4. Stores shiur ID in file metadata for tracking
