/**
 * Sanitize a filename to be safe across Windows and Unix filesystems.
 * Direct TypeScript port of sanitize_filename() from download_podcasts.py.
 */
export function sanitizeFilename(filename: string): string {
  // Replace all types of quotation marks with single quote
  const quoteChars = [
    '"',   // ASCII double quote
    '\u201C', // left double quotation mark
    '\u201D', // right double quotation mark
    '\u05F4', // Hebrew punctuation gershayim
    '\u201F', // double high-reversed-9 quotation mark
    '\u201E', // double low-9 quotation mark
    '\u00AB', // left-pointing double angle quotation mark
    '\u00BB', // right-pointing double angle quotation mark
  ];
  for (const q of quoteChars) {
    filename = filename.replaceAll(q, "'");
  }

  // Replace colons with dashes
  filename = filename.replace(/:/g, '-');
  filename = filename.replace(/\u05C3/g, '-'); // Hebrew sof pasuq

  // Remove Windows-invalid characters: < > / \ | ? *
  filename = filename.replace(/[<>/\\|?*]/g, '');

  // Collapse whitespace and dashes
  filename = filename.replace(/\s+/g, ' ');
  filename = filename.replace(/-+/g, '-');

  // Trim leading/trailing spaces, periods, dashes
  filename = filename.replace(/^[. -]+|[. -]+$/g, '');

  // Trim to 180 chars (leave room for path prefix on Windows)
  if (filename.length > 180) {
    const dotIdx = filename.lastIndexOf('.');
    if (dotIdx > 0) {
      const ext = filename.slice(dotIdx);
      filename = filename.slice(0, 180 - ext.length) + ext;
    } else {
      filename = filename.slice(0, 180);
    }
  }

  if (!filename || filename === '.') filename = 'untitled';

  return filename;
}
