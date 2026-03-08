import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";

export const metadata: Metadata = {
  title: "YUTorah Podcast Downloader",
  description: "Download shiurim from YUTorah RSS feeds to Google Drive",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <SessionProvider session={session}>{children}</SessionProvider>
      </body>
    </html>
  );
}
