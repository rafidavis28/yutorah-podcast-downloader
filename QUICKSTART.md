# Quick Start Guide

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **(Optional) Add your YUTorah credentials** for login-required content:
   - Edit `download_podcasts.py`
   - Update lines 23-24 with your credentials

## Using the Web Interface (Easiest)

1. **Start the web app:**
```bash
streamlit run app.py
```

2. **The app will automatically open in your browser** at http://localhost:8501

3. **Download shiurim:**
   - Select a feed from the sidebar (or add a new one)
   - Configure settings (output directory, enable subfolders, etc.)
   - Click "🔄 Check for New Episodes"
   - **Select which episodes to download** using checkboxes
   - Click "⬇️ Download Selected Episodes"
   - Watch the progress in real-time!

## Using the Command Line

**Download all new episodes:**
```bash
python download_podcasts.py
```

**Download from local RSS file:**
```bash
python download_podcasts.py --rss-file rss.rss
```

**Download only 10 episodes:**
```bash
python download_podcasts.py --limit 10
```

## Key Features

- ✅ **Automatic tracking**: Already downloaded shiurim are remembered and skipped
- ✅ **Selective downloads**: Choose exactly which episodes to download via checkboxes
- ✅ **Auto-organized**: Each feed can have its own subfolder
- ✅ **Multiple feeds**: Manage different rabbis/teachers in the web interface
- ✅ **Safe interruption**: Stop and resume anytime - progress is saved
- ✅ **Progress tracking**: See real-time status in the web interface
- ✅ **Smart filenames**: Handles Hebrew, quotes, and special characters automatically

## Files Created

- `downloads/` - MP3 files are saved here by default
- `downloaded_shiurim.json` - Database of downloaded shiur IDs
- `rss_feeds.json` - Configuration of RSS feeds (web interface only)

## Tips

- Run the script regularly (daily/weekly) to automatically get new shiurim
- Use the web interface to easily manage multiple feeds
- The database prevents re-downloading, so it's safe to run multiple times
- You can change the output directory in settings to organize by rabbi/series

## Getting RSS Feed URLs

To find RSS feeds for other rabbis on YUTorah:

1. Visit https://www.yutorah.org
2. Search for a rabbi or teacher
3. Look for the RSS icon or feed link on their page
4. Copy the RSS URL
5. Add it in the web interface using "➕ Add New Feed"

## Troubleshooting

**No episodes found:**
- Check that the RSS URL is correct
- Make sure you have internet connectivity

**Login required:**
- Add your credentials in `download_podcasts.py` (lines 23-24)

**Port already in use (web interface):**
```bash
streamlit run app.py --server.port 8502
```

Enjoy your shiurim! 🎧
