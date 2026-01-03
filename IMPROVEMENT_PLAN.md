# YUTorah Podcast Downloader - Improvement Plan

## Current State Summary

Your tool has two interfaces:
- **Web UI (Streamlit)**: Interactive episode selection + Google Drive upload
- **CLI**: Automation-friendly local downloads

Authentication is used in two places:
1. **YUTorah Login**: Only for "download-disabled" episodes (uses your credentials)
2. **Google Drive OAuth**: Per-user, already properly isolated

---

## Priority 1: Remove/Reduce YUTorah Login Dependency

### Issue Analysis
Currently, when an episode page has `class="download-disabled"`, the tool attempts login. However:
- Most episodes appear to be publicly accessible
- Download pages have direct URLs (e.g., `yutorah.org/lectures/lecture.cfm?shiurID=XXXX`)
- The MP3 URLs themselves may be directly accessible without session cookies

### Proposed Improvements

#### 1A. Direct MP3 URL Construction
Investigate if MP3 URLs follow a predictable pattern:
```
https://download.yutorah.org/XXXX/filename.mp3
```
If the pattern is consistent, you could:
- Extract the shiur ID from the RSS feed
- Construct the download URL directly
- Skip the page scraping entirely for public episodes

#### 1B. RSS Feed Direct Links
The RSS feed likely contains `<enclosure>` tags with direct MP3 URLs. Currently you're:
1. Getting episode page URL from RSS
2. Scraping the page for the download link

Instead:
- Parse `<enclosure url="...">` directly from RSS XML
- Many podcast RSS feeds include the actual MP3 URL here
- This would eliminate page scraping entirely for most episodes

#### 1C. Graceful Degradation
For truly restricted episodes:
- Add a "skip restricted" mode (no login attempt)
- Log which episodes were skipped for manual review
- Consider if restricted episodes are even needed

#### 1D. Session-Free Download Test
Test if MP3 URLs work without any session:
- The actual download server (`download.yutorah.org`) may not check cookies
- Only the episode page might require login to *display* the link
- Once you have the URL, the download itself may be unrestricted

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

1. **Check RSS `<enclosure>` for direct MP3 URLs** - Could eliminate login need entirely
2. **Add episode duration/size to UI** - Better user experience
3. **JSON output for CLI** - Enables scripting/automation
4. **Configurable filename template** - Simple but useful
5. **Feed health check command** - Verify feeds are still valid

---

## Investigation Needed

Before implementing, test these assumptions:

1. **Do YUTorah RSS feeds include `<enclosure>` tags with MP3 URLs?**
   - If yes: Major simplification possible

2. **Are MP3 download URLs accessible without session cookies?**
   - If yes: Login truly not needed for most cases

3. **What makes an episode "download-disabled"?**
   - Premium content?
   - Time-limited availability?
   - Certain speakers/series?

4. **Are there API endpoints besides RSS?**
   - YUTorah may have undocumented APIs
   - Could enable better search/discovery

---

## Recommended Implementation Order

### Phase 1: Remove Login Dependency
1. Investigate RSS enclosure tags
2. Test direct MP3 URL access
3. Implement graceful degradation for restricted content

### Phase 2: Core Enhancements
4. ID3 tag support
5. Filename templates
6. Better duplicate detection

### Phase 3: Automation
7. Cron-friendly CLI improvements
8. Scheduling support
9. Notification system

### Phase 4: Extended Features
10. Additional cloud storage
11. OPML import/export
12. Search functionality

---

## Architecture Considerations

If you're keeping this personal, the current Streamlit + Python approach is fine. For sharing more widely:

- **Containerization**: Already have devcontainer, add Docker Compose for easy deployment
- **Configuration**: Move from secrets.toml to environment variables for flexibility
- **Database**: Consider SQLite instead of JSON for larger scale
- **Testing**: Add unit tests for core download logic

