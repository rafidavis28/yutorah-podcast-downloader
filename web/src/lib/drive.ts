/**
 * Google Drive API operations.
 * TypeScript port of google_drive_auth.py using the googleapis npm package.
 */

import { google } from "googleapis";

function getDriveService(accessToken: string) {
  const auth = new google.auth.OAuth2();
  auth.setCredentials({ access_token: accessToken });
  return google.drive({ version: "v3", auth });
}

/**
 * Find an existing folder by name, or create it if it doesn't exist.
 */
export async function findOrCreateFolder(
  accessToken: string,
  folderName: string,
  parentFolderId?: string
): Promise<string | null> {
  const drive = getDriveService(accessToken);

  try {
    let query = `name='${folderName.replace(/'/g, "\\'")}' and mimeType='application/vnd.google-apps.folder' and trashed=false`;
    if (parentFolderId) query += ` and '${parentFolderId}' in parents`;

    const res = await drive.files.list({
      q: query,
      spaces: "drive",
      fields: "files(id, name)",
    });

    const files = res.data.files ?? [];
    if (files.length > 0) return files[0].id!;

    // Create folder
    const created = await drive.files.create({
      requestBody: {
        name: folderName,
        mimeType: "application/vnd.google-apps.folder",
        ...(parentFolderId ? { parents: [parentFolderId] } : {}),
      },
      fields: "id",
    });
    return created.data.id ?? null;
  } catch (err) {
    console.error("findOrCreateFolder error:", err);
    return null;
  }
}

/**
 * Upload a Node.js Readable stream to Google Drive.
 * Accepts a streaming body so the server never buffers the full MP3 in memory.
 * Stores shiurId in the file description for deduplication tracking.
 */
export async function uploadFileToDrive(
  accessToken: string,
  bodyStream: import("stream").Readable,
  filename: string,
  folderId: string,
  shiurId?: string
): Promise<{ id: string; name: string; webViewLink: string } | null> {
  const drive = getDriveService(accessToken);

  try {
    const file = await drive.files.create({
      requestBody: {
        name: filename,
        parents: [folderId],
        ...(shiurId ? { description: `shiurID:${shiurId}` } : {}),
      },
      media: {
        mimeType: "audio/mpeg",
        body: bodyStream,
      },
      fields: "id, name, webViewLink",
    });

    return {
      id: file.data.id!,
      name: file.data.name!,
      webViewLink: file.data.webViewLink!,
    };
  } catch (err) {
    console.error("uploadFileToDrive error:", err);
    return null;
  }
}

/**
 * Get the set of shiur IDs already uploaded to a Drive folder.
 * Reads shiurID from file descriptions (format: "shiurID:1234567").
 */
export async function getUploadedShiurIds(
  accessToken: string,
  folderId: string
): Promise<Set<string>> {
  const drive = getDriveService(accessToken);
  const shiurIds = new Set<string>();

  try {
    let pageToken: string | undefined;
    do {
      const res = await drive.files.list({
        q: `'${folderId}' in parents and trashed=false`,
        spaces: "drive",
        fields: "nextPageToken, files(id, name, description)",
        pageSize: 100,
        ...(pageToken ? { pageToken } : {}),
      });

      for (const f of res.data.files ?? []) {
        const desc = f.description ?? "";
        if (desc.startsWith("shiurID:")) {
          const id = desc.replace("shiurID:", "").trim();
          if (id) shiurIds.add(id);
        }
      }

      pageToken = res.data.nextPageToken ?? undefined;
    } while (pageToken);
  } catch (err) {
    console.error("getUploadedShiurIds error:", err);
  }

  return shiurIds;
}

/**
 * Get the authenticated user's email address from Drive API.
 */
export async function getUserInfo(
  accessToken: string
): Promise<{ emailAddress: string } | null> {
  const drive = getDriveService(accessToken);
  try {
    const res = await drive.about.get({ fields: "user" });
    return res.data.user as { emailAddress: string } | null;
  } catch {
    return null;
  }
}
