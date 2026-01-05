# YUTorah Podcast Downloader - Feature Ideas

This document tracks potential future enhancements for the YUTorah podcast downloader.

## Current State (January 2026)

The tool is fully functional with:
- **Web UI (Streamlit)**: Interactive episode selection + Google Drive upload
- **CLI**: Automation-friendly local downloads
- **No login required**: Downloads work without YUTorah authentication
- **Google Drive tracking**: Duplicate detection based on file metadata in Drive

### Technical Implementation

Episode pages contain a `lecturePlayerData` JavaScript object with download URLs:
```javascript
var lecturePlayerData = {
  "downloadURL": "https://download.yutorah.org/2025/4505/1152550/...",
  "shiurDuration": "19min 36s",
  "shiurID": "1152550",
  ...
}
```

MP3 URL pattern: `https://download.yutorah.org/{YEAR}/{SPEAKER_CDN_ID}/{SHIUR_ID}/{title}.mp3`

---

## Future Ideas

### 1. Enhanced Feed Management

**OPML Import/Export**
- Import feeds from other podcast apps via OPML
- Export your feed list for backup/sharing
- Standard format for podcast subscriptions

**Feed Discovery**
- Search YUTorah by speaker name → auto-generate RSS URL
- YUTorah has predictable RSS URL patterns: `/rss/RssAudioOnly/teacher/XXXXX`
- Could add a "Find Speaker" feature that searches their site

**Feed Metadata Storage**
Store more than just the URL:
```json
{
  "feeds": {
    "rav-taragin": {
      "name": "Rav Moshe Taragin",
      "url": "...",
      "added_date": "...",
      "last_checked": "...",
      "total_downloaded": 42,
      "auto_download": true
    }
  }
}
```

**Feed Categories/Tags**
- Group feeds by topic (Parsha, Gemara, Halacha, etc.)
- Filter views by category
- Useful when managing many speakers

---

### 2. Download & Sync Improvements

**Smarter Duplicate Detection**
Current: Track shiur IDs only
Improved:
- Also track by content hash (handles re-uploads)
- Track file size to detect incomplete downloads
- Option to re-download if file was deleted from Drive

**Download Resumption**
- For large files, support resumable downloads
- Track partial downloads and continue from where left off
- HTTP Range headers for continuation

**Batch Download Optimization**
- Parallel downloads (configurable concurrency)
- Connection pooling for faster throughput
- Progress indication with ETA

**Sync Status Dashboard**
- Show which episodes are: downloaded, pending, skipped, failed
- Per-feed statistics
- Last sync timestamp per feed

---

### 3. Metadata & Organization

**ID3 Tag Enhancement**
Add proper MP3 metadata:
- Title (from RSS)
- Artist (speaker name)
- Album (feed name or series)
- Year/Date
- Genre: "Torah/Podcast"
- Cover art (if available from YUTorah)

This makes files searchable and properly organized in music apps.

**Filename Templates**
Configurable naming:
```
{date} - {title}.mp3
{speaker}/{series}/{title}.mp3
{shiur_id} - {title}.mp3
```

**Folder Organization Options**
- By speaker
- By date (Year/Month)
- By series/topic
- Flat (all in one folder)

---

### 4. Scheduling & Automation

**Background Sync Service**
- Run as a background daemon
- Check feeds on configurable schedule
- Auto-download new episodes

**Cron-Friendly Mode**
- Exit codes for success/failure/no-new-episodes
- JSON output mode for scripting
- Quiet mode (errors only)

**Webhook/Notification Support**
- Notify on new downloads (email, Pushover, webhook)
- Daily digest of new episodes
- Error notifications

---

### 5. Alternative Storage Backends

**Local + Cloud Hybrid**
- Download locally first, then upload to cloud
- Keep local cache for quick access
- Configurable retention (delete local after X days)

**Additional Cloud Providers**
- Dropbox integration
- OneDrive integration
- S3/MinIO for self-hosted
- Nextcloud/ownCloud

**Podcast App Integration**
- Generate local RSS feed pointing to downloaded files
- Self-host a mini podcast server
- Compatible with Pocket Casts, Overcast, etc.

---

### 6. User Experience Improvements

**Episode Preview**
- Show episode description/summary from RSS
- Display duration before downloading
- Show file size estimate

**Search Within Feeds**
- Search episode titles
- Filter by date range
- Find episodes by keyword

**Playback Integration**
- Audio player in web UI
- Listen before deciding to download
- Mark as "listened" vs "downloaded"

**Mobile-Friendly UI**
- Responsive design for phone/tablet
- PWA support for home screen install
- Touch-friendly controls

---

### 7. Reliability & Monitoring

**Retry Logic Improvement**
- Exponential backoff for failures
- Configurable retry count
- Different strategies for different error types

**Rate Limiting Respect**
- Detect and respect rate limits
- Automatic throttling when needed
- Configurable download speed limits

**Health Monitoring**
- Track success/failure rates
- Alert on repeated failures
- Feed URL validity checking

**Logging Improvements**
- Structured logging (JSON)
- Log rotation
- Debug mode for troubleshooting

---

### 8. Data Portability

**Export Formats**
- Export download history as CSV/JSON
- Export feed configurations
- Backup entire app state

**Import Capabilities**
- Import from other podcast apps
- Migrate from different instances
- Bulk feed addition

---

## Quick Wins (Low Effort, High Value)

1. ✅ ~~Per-user YUTorah credentials~~ - No longer needed (public access works)
2. ✅ ~~Episode duration display~~ - Implemented
3. **JSON output for CLI** - Enables scripting/automation
4. **Configurable filename template** - Simple but useful

---

## Architecture Notes

For wider distribution:
- **Containerization**: Add Docker Compose for easy deployment
- **Configuration**: Environment variables for flexibility
- **Testing**: Add unit tests for core download logic

