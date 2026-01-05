# YUTorah Podcast Downloader - Improvement Plan

## Current State Summary

Your tool has two interfaces:
- **Web UI (Streamlit)**: Interactive episode selection + Google Drive upload
- **CLI**: Automation-friendly local downloads

Authentication:
- **YUTorah Login**: ✅ **NO LONGER REQUIRED** (removed in Jan 2026)
- **Google Drive OAuth**: Per-user, properly isolated

---

## ✅ COMPLETED: Login Dependency Removed (January 2026)

### Key Discovery

Episode pages contain a `lecturePlayerData` JavaScript object with full download URLs,
and this data is **publicly accessible without authentication**!

```javascript
var lecturePlayerData = {
  "downloadURL": "https://download.yutorah.org/2025/4505/1152550/...",
  "playerDownloadURL": "https://shiurim.yutorah.net/2025/4505/1152550.MP3",
  "shiurDuration": "19min 36s",
  "shiurMediaLengthInSeconds": 1176,
  "shiurTitle": "...",
  ...
}
```

### What Was Implemented

1. **Removed all YUTorah login code** - No credentials needed
2. **JSON-based URL extraction** - Parse `lecturePlayerData` from page HTML
3. **Duration display** - Shows episode length before downloading
4. **Simpler codebase** - Removed ~60 lines of login/auth code

### How It Works Now

```
RSS Feed → Episode Page URL → Fetch Page (no auth) → Parse JSON → Download MP3
```

The MP3 URLs at `download.yutorah.org` are publicly accessible.

### URL Pattern Discovered

```
https://download.yutorah.org/{YEAR}/{SPEAKER_CDN_ID}/{SHIUR_ID}/{sanitized-title}.mp3
```

| Speaker | CDN ID | RSS Teacher ID |
|---------|--------|----------------|
| Rabbi Moshe Taragin | 4505 | 80307 |
| Rabbi Shay Schachter | 21648 | - |

---

## Priority 2: Enhanced Feed Management

### 2A. OPML Import/Export
- Import feeds from other podcast apps via OPML
- Export your feed list for backup/sharing
- Standard format for podcast subscriptions

### 2B. Feed Discovery
- Search YUTorah by speaker name → auto-generate RSS URL
- YUTorah has predictable RSS URL patterns: `/rss/RssAudioOnly/teacher/XXXXX`
- Could add a "Find Speaker" feature that searches their site

### 2C. Feed Metadata Storage
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

### 2D. Feed Categories/Tags
- Group feeds by topic (Parsha, Gemara, Halacha, etc.)
- Filter views by category
- Useful when managing many speakers

---

## Priority 3: Download & Sync Improvements

### 3A. Smarter Duplicate Detection
Current: Track shiur IDs only
Improved:
- Also track by content hash (handles re-uploads)
- Track file size to detect incomplete downloads
- Option to re-download if file was deleted from Drive

### 3B. Download Resumption
- For large files, support resumable downloads
- Track partial downloads and continue from where left off
- HTTP Range headers for continuation

### 3C. Batch Download Optimization
- Parallel downloads (configurable concurrency)
- Connection pooling for faster throughput
- Progress indication with ETA

### 3D. Sync Status Dashboard
- Show which episodes are: downloaded, pending, skipped, failed
- Per-feed statistics
- Last sync timestamp per feed

---

## Priority 4: Metadata & Organization

### 4A. ID3 Tag Enhancement
Add proper MP3 metadata:
- Title (from RSS)
- Artist (speaker name)
- Album (feed name or series)
- Year/Date
- Genre: "Torah/Podcast"
- Cover art (if available from YUTorah)

This makes files searchable and properly organized in music apps.

### 4B. Filename Templates
Configurable naming:
```
{date} - {title}.mp3
{speaker}/{series}/{title}.mp3
{shiur_id} - {title}.mp3
```

### 4C. Folder Organization Options
- By speaker
- By date (Year/Month)
- By series/topic
- Flat (all in one folder)

---

## Priority 5: Scheduling & Automation

### 5A. Background Sync Service
- Run as a background daemon
- Check feeds on configurable schedule
- Auto-download new episodes

### 5B. Cron-Friendly Mode
- Exit codes for success/failure/no-new-episodes
- JSON output mode for scripting
- Quiet mode (errors only)

### 5C. Webhook/Notification Support
- Notify on new downloads (email, Pushover, webhook)
- Daily digest of new episodes
- Error notifications

---

## Priority 6: Alternative Storage Backends

### 6A. Local + Cloud Hybrid
- Download locally first, then upload to cloud
- Keep local cache for quick access
- Configurable retention (delete local after X days)

### 6B. Additional Cloud Providers
- Dropbox integration
- OneDrive integration
- S3/MinIO for self-hosted
- Nextcloud/ownCloud

### 6C. Podcast App Integration
- Generate local RSS feed pointing to downloaded files
- Self-host a mini podcast server
- Compatible with Pocket Casts, Overcast, etc.

---

## Priority 7: User Experience Improvements

### 7A. Episode Preview
- Show episode description/summary from RSS
- Display duration before downloading
- Show file size estimate

### 7B. Search Within Feeds
- Search episode titles
- Filter by date range
- Find episodes by keyword

### 7C. Playback Integration
- Audio player in web UI
- Listen before deciding to download
- Mark as "listened" vs "downloaded"

### 7D. Mobile-Friendly UI
- Responsive design for phone/tablet
- PWA support for home screen install
- Touch-friendly controls

---

## Priority 8: Reliability & Monitoring

### 8A. Retry Logic Improvement
- Exponential backoff for failures
- Configurable retry count
- Different strategies for different error types

### 8B. Rate Limiting Respect
- Detect and respect rate limits
- Automatic throttling when needed
- Configurable download speed limits

### 8C. Health Monitoring
- Track success/failure rates
- Alert on repeated failures
- Feed URL validity checking

### 8D. Logging Improvements
- Structured logging (JSON)
- Log rotation
- Debug mode for troubleshooting

---

## Priority 9: Data Portability

### 9A. Export Formats
- Export download history as CSV/JSON
- Export feed configurations
- Backup entire app state

### 9B. Import Capabilities
- Import from other podcast apps
- Migrate from different instances
- Bulk feed addition

---

## Quick Wins (Low Effort, High Value)

1. **Per-user YUTorah credentials in UI** - Each user enters their own login
2. **"Skip restricted" toggle** - Graceful degradation when no credentials
3. **Add episode duration/size to UI** - Better user experience (if available in RSS)
4. **JSON output for CLI** - Enables scripting/automation
5. **Configurable filename template** - Simple but useful

---

## Investigation Completed (January 2026)

| Question | Answer |
|----------|--------|
| Do RSS feeds have `<enclosure>` tags? | ❌ No - only episode page links |
| What makes episodes "download-disabled"? | Not logged in (all users can download when logged in) |
| Are there other API endpoints? | ❌ No - RSS only |

### Still To Test (requires external access)

1. **Are MP3 download URLs accessible without session cookies?**
   - Get an MP3 URL while logged in
   - Try accessing it in incognito/different browser
   - If yes: Could cache URLs to avoid repeated logins

---

## Recommended Implementation Order

### Phase 1: Address Login Concern (Immediate)
1. Add per-user YUTorah credentials option in web UI
2. Add "Skip login-required episodes" toggle
3. Test if MP3 URLs work without session (manual test)
4. If MP3 URLs are sessionless: add URL caching for speed

### Phase 2: Core Enhancements
5. ID3 tag support
6. Filename templates
7. Better duplicate detection

### Phase 3: Automation
8. Cron-friendly CLI improvements (JSON output, exit codes)
9. Scheduling support
10. Notification system

### Phase 4: Extended Features (If Needed)
11. Additional cloud storage backends
12. Search functionality
13. Feed discovery by speaker name

---

## Architecture Considerations

If you're keeping this personal, the current Streamlit + Python approach is fine. For sharing more widely:

- **Containerization**: Already have devcontainer, add Docker Compose for easy deployment
- **Configuration**: Move from secrets.toml to environment variables for flexibility
- **Database**: Consider SQLite instead of JSON for larger scale
- **Testing**: Add unit tests for core download logic

