import { XMLParser } from "fast-xml-parser";

export interface Episode {
  title: string;
  pageUrl: string;
  shiurId: string | null;
}

/**
 * Fetch and parse a YUTorah RSS feed.
 * Returns raw channel items.
 */
export async function fetchRSSFeed(
  rssUrl: string
): Promise<{ title: string; link: string }[]> {
  const response = await fetch(rssUrl, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
    next: { revalidate: 0 },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch RSS feed: ${response.status} ${response.statusText}`);
  }

  const xml = await response.text();

  const parser = new XMLParser({
    ignoreAttributes: false,
    cdataPropName: "__cdata",
  });
  const parsed = parser.parse(xml);

  const items: Record<string, unknown>[] =
    parsed?.rss?.channel?.item ?? [];

  const episodes: { title: string; link: string }[] = [];
  for (const item of items) {
    const titleRaw = item.title as string | { __cdata: string } | undefined;
    const linkRaw = item.link as string | { __cdata: string } | undefined;

    const title =
      typeof titleRaw === "object" && titleRaw !== null
        ? titleRaw.__cdata
        : (titleRaw ?? "");
    const link =
      typeof linkRaw === "object" && linkRaw !== null
        ? linkRaw.__cdata
        : (linkRaw ?? "");

    if (link) {
      episodes.push({ title: title.trim(), link: link.trim() });
    }
  }

  return episodes;
}

/**
 * Extract shiur ID from a YUTorah episode page URL.
 * Handles multiple URL formats used by the site.
 */
export function extractShiurId(pageUrl: string): string | null {
  try {
    const url = new URL(pageUrl);

    // Format 1: ?shiurID=1159876
    const shiurIdParam = url.searchParams.get("shiurID");
    if (shiurIdParam) return shiurIdParam;

    // Format 2: /lectures/1160274/ or /lectures/lecture.cfm/1160032
    const pathMatch = url.pathname.match(
      /\/lectures\/(?:lecture\.cfm\/|details\/)?(\d+)/
    );
    if (pathMatch) return pathMatch[1];
  } catch {
    // fall through to regex
  }

  // Format 3: shiurID in path or query (legacy)
  const match = pageUrl.match(/shiurID[=:](\d+)/);
  if (match) return match[1];

  return null;
}

/**
 * Convert raw RSS items to typed Episode objects.
 */
export function extractEpisodeLinks(
  items: { title: string; link: string }[]
): Episode[] {
  return items.map((item) => ({
    title: item.title,
    pageUrl: item.link,
    shiurId: extractShiurId(item.link),
  }));
}
