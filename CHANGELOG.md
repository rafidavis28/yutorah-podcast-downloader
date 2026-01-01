# Changelog

## Version 2.0 - Enhanced Features

### New Features

#### 1. Selective Episode Downloads (Web Interface)
- **Checkbox selection**: Before downloading, you can now see all new episodes and select which ones to download
- **Select All / Deselect All**: Quickly toggle all selections
- **Smart UI**: Episodes display with their titles and shiur IDs for easy identification
- **Separate download action**: Check for episodes first, then choose what to download

#### 2. Automatic Subfolders Per Feed
- **Web Interface**: Toggle "Use feed-specific subfolders" in settings
  - When enabled, creates a subfolder for each feed (e.g., `downloads/Rabbi Moshe Weinberger/`)
  - Keeps your downloads organized by rabbi/teacher
- **CLI**: Use `--feed-name "Feed Name"` to create a subfolder
  - Example: `python download_podcasts.py --feed-name "Rabbi Weinberger"`

#### 3. Enhanced Filename Sanitization
- **Fixed special character handling**:
  - Double quotes (`"`) are replaced with single quotes (`'`)
  - Colons (`:`) are replaced with dashes (`-`)
  - Other invalid characters are removed
  - Leading/trailing spaces and periods are stripped
- **Hebrew character support**: Hebrew filenames now work correctly on Windows
- **Path length protection**: Automatically truncates long filenames while preserving extensions
- **Cross-platform compatibility**: Filenames work on Windows, Mac, and Linux

### Bug Fixes

- Fixed: `[Errno 22] Invalid argument` errors with special characters in filenames
- Fixed: Hebrew characters causing download failures on Windows
- Fixed: Quotes and apostrophes in filenames breaking downloads
- Fixed: Long filenames exceeding Windows path limits

### Improvements

- Better error messages for filename issues
- Improved logging in web interface
- Enhanced progress tracking
- More robust filename handling

## Version 1.0 - Initial Release

### Features
- Download podcast episodes from YUTorah RSS feeds
- Track downloaded shiurim to avoid re-downloading
- Web interface built with Streamlit
- Command-line interface for automation
- Multiple RSS feed management
- Login support for restricted content
- Progress tracking and detailed logging
