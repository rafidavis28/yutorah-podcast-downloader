import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { fetchRSSFeed, extractEpisodeLinks, Episode } from "@/lib/rss";
import { findOrCreateFolder, getUploadedShiurIds } from "@/lib/drive";
import { sanitizeFilename } from "@/lib/sanitize";
import { DRIVE_BASE_FOLDER } from "@/config/feeds";

interface CheckEpisodesRequest {
  feedUrl: string;
  feedName: string;
  driveFolderName?: string;
  useSubfolders?: boolean;
}

interface CheckEpisodesResponse {
  newEpisodes: Episode[];
  totalInFeed: number;
  error?: string;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const session = await auth();

  const body: CheckEpisodesRequest = await req.json();
  const { feedUrl, feedName, driveFolderName, useSubfolders = true } = body;

  if (!feedUrl) {
    return NextResponse.json({ error: "feedUrl is required" }, { status: 400 });
  }

  try {
    // 1. Fetch and parse the RSS feed
    const rawItems = await fetchRSSFeed(feedUrl);
    const allEpisodes = extractEpisodeLinks(rawItems);

    // 2. If authenticated, check Drive for already-uploaded shiur IDs
    let uploadedShiurIds = new Set<string>();

    if (session?.accessToken) {
      const baseFolderName = driveFolderName ?? DRIVE_BASE_FOLDER;
      const baseFolderId = await findOrCreateFolder(
        session.accessToken,
        baseFolderName
      );

      if (baseFolderId) {
        let checkFolderId = baseFolderId;
        if (useSubfolders) {
          const safeName = sanitizeFilename(feedName);
          const subFolderId = await findOrCreateFolder(
            session.accessToken,
            safeName,
            baseFolderId
          );
          if (subFolderId) checkFolderId = subFolderId;
        }
        uploadedShiurIds = await getUploadedShiurIds(
          session.accessToken,
          checkFolderId
        );
      }
    }

    // 3. Filter to only new episodes
    const newEpisodes = allEpisodes.filter((ep) => {
      if (ep.shiurId && uploadedShiurIds.has(ep.shiurId)) return false;
      return true;
    });

    const response: CheckEpisodesResponse = {
      newEpisodes,
      totalInFeed: allEpisodes.length,
    };

    return NextResponse.json(response);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
