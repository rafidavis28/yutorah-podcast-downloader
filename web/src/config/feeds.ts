/**
 * Default RSS feeds.
 * These are pre-loaded into the app.
 * Users can add more feeds via the UI (stored in localStorage).
 */

export interface Feed {
  name: string;
  url: string;
}

export const DEFAULT_FEEDS: Feed[] = [
  {
    name: "Rav Moshe Taragin",
    url: "http://www.yutorah.org/rss/RssAudioOnly/teacher/80307",
  },
];

export const DRIVE_BASE_FOLDER = "YUTorah Podcasts";
