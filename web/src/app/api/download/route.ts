import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { getMp3UrlFromPage } from "@/lib/yutorah";
import { findOrCreateFolder, uploadFileToDrive } from "@/lib/drive";
import { sanitizeFilename } from "@/lib/sanitize";
import { DRIVE_BASE_FOLDER } from "@/config/feeds";

interface DownloadRequest {
  episode: {
    title: string;
    pageUrl: string;
    shiurId: string | null;
    audioUrl?: string | null;
  };
  destination: "drive" | "local";
  feedName: string;
  driveFolderName?: string;
  useSubfolders?: boolean;
}

const MP3_FETCH_HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
};

export async function POST(req: NextRequest): Promise<NextResponse> {
  const session = await auth();

  const body: DownloadRequest = await req.json();
  const {
    episode,
    destination,
    feedName,
    driveFolderName,
    useSubfolders = true,
  } = body;

  // 1. Resolve MP3 URL (prefer RSS enclosure; fallback to page extraction)
  let mp3Url = episode.audioUrl ?? null;
  let shiurId = episode.shiurId;

  if (!mp3Url) {
    const episodeData = await getMp3UrlFromPage(episode.pageUrl);

    if (!episodeData.downloadURL) {
      return NextResponse.json(
        {
          error: `Could not find MP3 URL for "${episode.title}": ${episodeData.failureReason ?? "unknown"}`,
          strategiesAttempted: episodeData.strategiesAttempted,
          strategyMarkers: episodeData.strategyMarkers,
          pageUrl: episode.pageUrl,
        },
        { status: 422 }
      );
    }

    mp3Url = episodeData.downloadURL;
    shiurId = episodeData.shiurId ?? episode.shiurId;
  }
  const filename = sanitizeFilename(episode.title) + ".mp3";

  // 2a. Local download — proxy-stream MP3 directly to the browser (no memory buffer)
  if (destination === "local") {
    let mp3Res: Response;
    try {
      mp3Res = await fetch(mp3Url, { headers: MP3_FETCH_HEADERS });
      if (!mp3Res.ok) throw new Error(`MP3 fetch failed: ${mp3Res.status}`);
    } catch (err) {
      return NextResponse.json(
        { error: `Failed to download MP3: ${err}` },
        { status: 502 }
      );
    }

    const headers: Record<string, string> = {
      "Content-Type": "audio/mpeg",
      "Content-Disposition": `attachment; filename="${encodeURIComponent(filename)}"`,
    };
    const contentLength = mp3Res.headers.get("content-length");
    if (contentLength) headers["Content-Length"] = contentLength;

    // Stream response body directly — never buffers the full file in memory
    return new NextResponse(mp3Res.body, { status: 200, headers });
  }

  // 2b. Drive upload — stream MP3 from YUTorah → Drive (no buffer)
  if (!session?.accessToken) {
    return NextResponse.json(
      { error: "Not authenticated with Google Drive" },
      { status: 401 }
    );
  }

  // Resolve Drive folder before starting the download
  const baseFolderName = driveFolderName ?? DRIVE_BASE_FOLDER;
  const baseFolderId = await findOrCreateFolder(
    session.accessToken,
    baseFolderName
  );
  if (!baseFolderId) {
    return NextResponse.json(
      { error: "Could not find or create Drive folder" },
      { status: 500 }
    );
  }

  let targetFolderId = baseFolderId;
  if (useSubfolders) {
    const safeName = sanitizeFilename(feedName);
    const subFolderId = await findOrCreateFolder(
      session.accessToken,
      safeName,
      baseFolderId
    );
    if (subFolderId) targetFolderId = subFolderId;
  }

  // Fetch MP3 as a stream
  let mp3Res: Response;
  try {
    mp3Res = await fetch(mp3Url, { headers: MP3_FETCH_HEADERS });
    if (!mp3Res.ok) throw new Error(`MP3 fetch failed: ${mp3Res.status}`);
  } catch (err) {
    return NextResponse.json(
      { error: `Failed to download MP3: ${err}` },
      { status: 502 }
    );
  }

  // Convert Web ReadableStream → Node.js Readable → stream into Drive
  const { Readable } = await import("stream");
  const nodeStream = Readable.fromWeb(
    mp3Res.body as import("stream/web").ReadableStream
  );

  const fileInfo = await uploadFileToDrive(
    session.accessToken,
    nodeStream,
    filename,
    targetFolderId,
    shiurId ?? undefined
  );

  if (!fileInfo) {
    return NextResponse.json(
      { error: "Drive upload failed" },
      { status: 500 }
    );
  }

  return NextResponse.json({
    success: true,
    fileId: fileInfo.id,
    fileName: fileInfo.name,
    webViewLink: fileInfo.webViewLink,
    shiurId,
  });
}
