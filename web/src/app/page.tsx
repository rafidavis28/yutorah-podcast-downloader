"use client";

import { useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import AuthButton from "@/components/AuthButton";
import FeedSelector from "@/components/FeedSelector";
import EpisodeList, { EpisodeWithStatus } from "@/components/EpisodeList";
import { Feed } from "@/config/feeds";

type PageState = "idle" | "checking" | "ready" | "downloading";

export default function Home() {
  const { data: session } = useSession();
  const isAuthenticated = !!session?.accessToken;

  const [selectedFeed, setSelectedFeed] = useState<Feed | null>(null);
  const [pageState, setPageState] = useState<PageState>("idle");
  const [episodes, setEpisodes] = useState<EpisodeWithStatus[]>([]);
  const [selected, setSelected] = useState<boolean[]>([]);
  const [totalInFeed, setTotalInFeed] = useState<number | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  // ─── Check for new episodes ─────────────────────────────────────────────────
  async function handleCheck() {
    if (!selectedFeed) return;
    setPageState("checking");
    setCheckError(null);
    setEpisodes([]);
    setSelected([]);

    try {
      const res = await fetch("/api/check-episodes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedUrl: selectedFeed.url,
          feedName: selectedFeed.name,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        setCheckError(data.error ?? "Failed to check feed");
        setPageState("idle");
        return;
      }

      const eps: EpisodeWithStatus[] = (data.newEpisodes ?? []).map(
        (ep: { title: string; pageUrl: string; shiurId: string | null }) => ({
          ...ep,
          status: "idle" as const,
        })
      );
      setEpisodes(eps);
      setSelected(eps.map(() => true));
      setTotalInFeed(data.totalInFeed ?? null);
      setPageState("ready");
    } catch (err) {
      setCheckError(String(err));
      setPageState("idle");
    }
  }

  // ─── Selection helpers ───────────────────────────────────────────────────────
  function handleToggle(index: number, checked: boolean) {
    setSelected((prev) => {
      const next = [...prev];
      next[index] = checked;
      return next;
    });
  }

  function handleSelectAll() {
    setSelected(episodes.map(() => true));
  }

  function handleClearAll() {
    setSelected(episodes.map(() => false));
  }

  // ─── Download ────────────────────────────────────────────────────────────────
  async function handleDownload(destination: "drive" | "local") {
    if (!selectedFeed) return;
    setPageState("downloading");

    const toDownload = episodes
      .map((ep, i) => ({ ep, i }))
      .filter(({ i }) => selected[i]);

    for (const { ep, i } of toDownload) {
      // Mark as downloading
      setEpisodes((prev) => {
        const next = [...prev];
        next[i] = { ...next[i], status: "downloading" };
        return next;
      });

      try {
        if (destination === "local") {
          // Local: streaming blob download
          const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              episode: ep,
              destination: "local",
              feedName: selectedFeed.name,
            }),
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error ?? "Download failed");
          }

          // Trigger browser save-file dialog
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          const cd = res.headers.get("Content-Disposition") ?? "";
          const fnMatch = cd.match(/filename="([^"]+)"/);
          a.download = fnMatch
            ? decodeURIComponent(fnMatch[1])
            : `${ep.title}.mp3`;
          a.href = url;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);

          setEpisodes((prev) => {
            const next = [...prev];
            next[i] = { ...next[i], status: "done_local" };
            return next;
          });
        } else {
          // Drive upload
          const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              episode: ep,
              destination: "drive",
              feedName: selectedFeed.name,
            }),
          });

          const data = await res.json();
          if (!res.ok) throw new Error(data.error ?? "Upload failed");

          setEpisodes((prev) => {
            const next = [...prev];
            next[i] = {
              ...next[i],
              status: "done_drive",
              driveLink: data.webViewLink,
            };
            return next;
          });
        }
      } catch (err) {
        setEpisodes((prev) => {
          const next = [...prev];
          next[i] = {
            ...next[i],
            status: "error",
            errorMessage: String(err),
          };
          return next;
        });
      }

      // Small delay between requests to be polite to YUTorah's servers
      if (i < toDownload[toDownload.length - 1].i) {
        await new Promise((r) => setTimeout(r, 800));
      }
    }

    setPageState("ready");
  }

  // ─── Summary counts ──────────────────────────────────────────────────────────
  const doneCount = episodes.filter(
    (e) => e.status === "done_drive" || e.status === "done_local"
  ).length;
  const errorCount = episodes.filter((e) => e.status === "error").length;

  return (
    <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* ─── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            YUTorah Downloader
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Download shiurim to Google Drive or your device
          </p>
        </div>
        <AuthButton />
      </div>

      {/* ─── Auth notice ─────────────────────────────────────────────────────── */}
      {!isAuthenticated && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-700/50 dark:bg-amber-900/20 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          Sign in with Google to save shiurim to your Drive. You can still
          download locally without signing in.
        </div>
      )}

      {/* ─── Session error notice ────────────────────────────────────────────── */}
      {session?.error === "RefreshAccessTokenError" && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-700/50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-800 dark:text-red-200">
          Your Google session expired. Please sign out and sign in again.
        </div>
      )}

      {/* ─── Feed selector ───────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          Feed
        </h2>
        <FeedSelector selectedFeed={selectedFeed} onSelect={setSelectedFeed} />

        <button
          onClick={handleCheck}
          disabled={!selectedFeed || pageState === "checking" || pageState === "downloading"}
          className="mt-1 w-full sm:w-auto px-5 py-2.5 rounded-md bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {pageState === "checking" ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⟳</span> Checking…
            </span>
          ) : (
            "Check for new episodes"
          )}
        </button>

        {checkError && (
          <p className="text-sm text-red-500">{checkError}</p>
        )}
      </section>

      {/* ─── Results ─────────────────────────────────────────────────────────── */}
      {(pageState === "ready" || pageState === "downloading") && (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
              Episodes
            </h2>
            {totalInFeed !== null && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {episodes.length} new / {totalInFeed} total in feed
              </span>
            )}
          </div>

          {episodes.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
              ✓ All caught up — no new episodes.
            </p>
          ) : (
            <EpisodeList
              episodes={episodes}
              onToggle={handleToggle}
              selected={selected}
              onSelectAll={handleSelectAll}
              onClearAll={handleClearAll}
              onDownload={handleDownload}
              isDownloading={pageState === "downloading"}
              isAuthenticated={isAuthenticated}
            />
          )}

          {/* Summary after downloads */}
          {(doneCount > 0 || errorCount > 0) && pageState === "ready" && (
            <div className="flex gap-4 pt-2 border-t border-gray-100 dark:border-gray-700">
              {doneCount > 0 && (
                <span className="text-sm text-green-600 dark:text-green-400">
                  ✓ {doneCount} saved
                </span>
              )}
              {errorCount > 0 && (
                <span className="text-sm text-red-500">
                  ✕ {errorCount} failed — hover the status badge for details
                </span>
              )}
            </div>
          )}
        </section>
      )}

      {/* ─── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="text-center text-xs text-gray-400 dark:text-gray-600 pb-4">
        Downloads public shiurim from YUTorah · No YUTorah account required
      </footer>
    </main>
  );
}
