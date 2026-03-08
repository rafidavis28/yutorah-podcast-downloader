/**
 * Extract MP3 download URL from a YUTorah episode page.
 * TypeScript port of get_mp3_url_from_page() from download_podcasts.py.
 *
 * Uses 4 fallback strategies:
 * A: lecturePlayerData JS variable
 * B: __NEXT_DATA__ script tag
 * C: Script blob regex + MP3 URL scan
 * D: <audio> / <source> tags
 */

import { extractShiurId } from "./rss";

export interface EpisodeData {
  downloadURL: string | null;
  playerDownloadURL: string | null;
  shiurId: string | null;
  title: string | null;
  duration: string | null;
  durationSeconds: number | null;
  description: string | null;
  teacherName: string | null;
  dateText: string | null;
  failureReason?: string;
  strategiesAttempted: string[];
}

type AudioFields = {
  downloadURL?: string;
  playerDownloadURL?: string;
  shiurID?: string;
  duration?: string;
  durationSeconds?: number;
  title?: string;
  description?: string;
  teacherName?: string;
  shiurURL?: string;
  dateText?: string;
};

export async function getMp3UrlFromPage(
  pageUrl: string
): Promise<EpisodeData> {
  let html: string;
  try {
    const response = await fetch(pageUrl, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    html = await response.text();
  } catch (err) {
    return {
      downloadURL: null,
      playerDownloadURL: null,
      shiurId: extractShiurId(pageUrl),
      title: null,
      duration: null,
      durationSeconds: null,
      description: null,
      teacherName: null,
      dateText: null,
      failureReason: `page_fetch_error: ${err}`,
      strategiesAttempted: [],
    };
  }

  const strategies: [string, (html: string) => AudioFields | null][] = [
    ["lecturePlayerData", extractFromLecturePlayerData],
    ["nextData", extractFromNextData],
    ["scriptBlobs", extractFromScriptBlobs],
    ["audioTags", extractFromAudioTags],
  ];

  const attempted: string[] = [];

  for (const [name, strategy] of strategies) {
    attempted.push(name);
    const result = strategy(html);
    if (result?.downloadURL || result?.playerDownloadURL) {
      return normalizeEpisodeData(result, pageUrl, attempted);
    }
  }

  return {
    downloadURL: null,
    playerDownloadURL: null,
    shiurId: extractShiurId(pageUrl),
    title: null,
    duration: null,
    durationSeconds: null,
    description: null,
    teacherName: null,
    dateText: null,
    failureReason: "no_supported_audio_payload_found",
    strategiesAttempted: attempted,
  };
}

// ─── Strategy A: lecturePlayerData ──────────────────────────────────────────

function extractFromLecturePlayerData(html: string): AudioFields | null {
  const match = html.match(/var\s+lecturePlayerData\s*=\s*(\{[\s\S]*?\});/);
  if (!match) return null;

  try {
    const data = JSON.parse(match[1]);
    return {
      downloadURL: data.downloadURL ?? null,
      playerDownloadURL: data.playerDownloadURL ?? null,
      shiurID: data.shiurID != null ? String(data.shiurID) : undefined,
      title: data.shiurTitle ?? null,
      duration: data.shiurDuration ?? null,
      durationSeconds: data.shiurMediaLengthInSeconds ?? null,
      description: data.shiurDescription ?? null,
      teacherName: data.shiurTeacherFullName ?? null,
      shiurURL: data.shiurURL ?? null,
      dateText: data.shiurDateText ?? null,
    };
  } catch {
    return null;
  }
}

// ─── Strategy B: __NEXT_DATA__ ──────────────────────────────────────────────

function extractFromNextData(html: string): AudioFields | null {
  // Extract all <script type="application/json"> blocks
  const scriptPattern =
    /<script[^>]*?(?:id="([^"]+)")?[^>]*?type="application\/json"[^>]*>([\s\S]*?)<\/script>/gi;
  let m: RegExpExecArray | null;
  while ((m = scriptPattern.exec(html)) !== null) {
    if (m[1] !== "__NEXT_DATA__") continue;
    try {
      const payload = JSON.parse(m[2].trim());
      const results: AudioFields = {};
      walkForAudioFields(payload, results);
      if (results.downloadURL || results.playerDownloadURL) return results;
    } catch {
      // continue
    }
  }
  return null;
}

// ─── Strategy C: script blobs ───────────────────────────────────────────────

function extractFromScriptBlobs(html: string): AudioFields | null {
  // Try to find JSON snippets containing known keys
  const snippetPattern =
    /\{[^{}]*?(?:downloadURL|playerDownloadURL|shiurID)[^{}]*?\}/gi;
  let m: RegExpExecArray | null;
  let count = 0;
  while ((m = snippetPattern.exec(html)) !== null && count < 30) {
    count++;
    let cleaned = m[0]
      .replace(/([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:/g, '$1"$2":')
      .replace(/'/g, '"');
    try {
      const candidate = JSON.parse(cleaned);
      const results: AudioFields = {};
      walkForAudioFields(candidate, results);
      if (results.downloadURL || results.playerDownloadURL) return results;
    } catch {
      // continue
    }
  }

  // Fallback: raw MP3 URL scan
  const mp3Pattern = /https?:\/\/[^"'\s>]+\.mp3(?:\?[^"'\s>]*)?/gi;
  const mp3Matches = html.match(mp3Pattern);
  if (mp3Matches?.length) {
    return { downloadURL: mp3Matches[0], playerDownloadURL: mp3Matches[0] };
  }

  return null;
}

// ─── Strategy D: audio/source tags ──────────────────────────────────────────

function extractFromAudioTags(html: string): AudioFields | null {
  const candidates: string[] = [];
  for (const pattern of [
    /<audio[^>]+src="([^"]+)"/gi,
    /<audio[^>]+src='([^']+)'/gi,
    /<source[^>]+src="([^"]+)"/gi,
    /<source[^>]+src='([^']+)'/gi,
  ]) {
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(html)) !== null) candidates.push(m[1]);
  }

  const mp3 = candidates.find((u) => u.toLowerCase().includes(".mp3"));
  if (mp3) return { downloadURL: mp3, playerDownloadURL: mp3 };
  if (candidates[0])
    return { downloadURL: candidates[0], playerDownloadURL: candidates[0] };

  return null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function walkForAudioFields(data: unknown, results: AudioFields): void {
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const obj = data as Record<string, unknown>;
    for (const [key, value] of Object.entries(obj)) {
      const kl = key.toLowerCase();
      if (
        (key === "downloadURL" || key === "playerDownloadURL") &&
        typeof value === "string"
      ) {
        results[key as "downloadURL" | "playerDownloadURL"] = value;
      } else if (kl.includes("downloadurl") && typeof value === "string") {
        results.downloadURL ??= value;
      } else if (kl === "shiurid" && value != null) {
        results.shiurID ??= String(value);
      } else if ((kl === "duration" || kl === "shiurduration") && typeof value === "string") {
        results.duration ??= value;
      } else if (
        (kl === "shiurmedialengthinseconds" || kl === "durationseconds") &&
        typeof value === "number"
      ) {
        results.durationSeconds ??= value;
      } else if ((kl === "title" || kl === "shiurtitle") && typeof value === "string") {
        results.title ??= value;
      } else if (
        (kl === "description" || kl === "shiurdescription") &&
        typeof value === "string"
      ) {
        results.description ??= value;
      } else if (
        (kl === "shiurteacherfullname" || kl === "teachername") &&
        typeof value === "string"
      ) {
        results.teacherName ??= value;
      }

      if (typeof value === "string" && value.toLowerCase().endsWith(".mp3")) {
        results.downloadURL ??= value;
      }

      walkForAudioFields(value, results);
    }
  } else if (Array.isArray(data)) {
    for (const item of data) walkForAudioFields(item, results);
  }
}

function normalizeEpisodeData(
  data: AudioFields,
  pageUrl: string,
  strategiesAttempted: string[]
): EpisodeData {
  return {
    downloadURL: data.downloadURL ?? data.playerDownloadURL ?? null,
    playerDownloadURL: data.playerDownloadURL ?? data.downloadURL ?? null,
    shiurId:
      data.shiurID != null ? String(data.shiurID) : extractShiurId(pageUrl),
    title: data.title ?? null,
    duration: data.duration ?? null,
    durationSeconds: data.durationSeconds ?? null,
    description: data.description ?? null,
    teacherName: data.teacherName ?? null,
    dateText: data.dateText ?? null,
    strategiesAttempted,
  };
}
