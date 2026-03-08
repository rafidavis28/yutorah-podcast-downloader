"use client";

import { useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import AuthButton from "@/components/AuthButton";
import FeedSelector from "@/components/FeedSelector";
import EpisodeList, { EpisodeWithStatus } from "@/components/EpisodeList";
import { Feed } from "@/config/feeds";
import { DownloadSimpleIcon, SpinnerIcon } from "@/components/icons";

type PageState = "idle" | "checking" | "ready" | "downloading";

function formatDownloadApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;

  const typed = data as {
    error?: string;
    strategiesAttempted?: string[];
    strategyMarkers?: Record<string, Record<string, number | boolean | string>>;
  };

  const pieces: string[] = [];
  if (typed.error) pieces.push(typed.error);

  if (typed.strategiesAttempted?.length) {
    pieces.push(`strategies: ${typed.strategiesAttempted.join(" -> ")}`);
  }

  if (typed.strategyMarkers && Object.keys(typed.strategyMarkers).length > 0) {
    pieces.push(`markers: ${JSON.stringify(typed.strategyMarkers)}`);
  }

  return pieces.join(" | ") || fallback;
}

export default function Home() {
  const { data: session } = useSession();
  const isAuthenticated = !!session?.accessToken;

  const [selectedFeed, setSelectedFeed] = useState<Feed | null>(null);
  const [pageState, setPageState] = useState<PageState>("idle");
  const [episodes, setEpisodes] = useState<EpisodeWithStatus[]>([]);
  const [selected, setSelected] = useState<boolean[]>([]);
  const [totalInFeed, setTotalInFeed] = useState<number | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

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

  async function handleDownload(destination: "drive" | "local") {
    if (!selectedFeed) return;
    setPageState("downloading");

    const toDownload = episodes
      .map((ep, i) => ({ ep, i }))
      .filter(({ i }) => selected[i]);

    for (const { ep, i } of toDownload) {
      setEpisodes((prev) => {
        const next = [...prev];
        next[i] = { ...next[i], status: "downloading" };
        return next;
      });

      try {
        if (destination === "local") {
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
            const err = await res.json().catch(() => null);
            throw new Error(formatDownloadApiError(err, "Download failed"));
          }

          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          const cd = res.headers.get("Content-Disposition") ?? "";
          const fnMatch = cd.match(/filename="([^"]+)"/);
          a.download = fnMatch ? decodeURIComponent(fnMatch[1]) : `${ep.title}.mp3`;
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
          const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              episode: ep,
              destination: "drive",
              feedName: selectedFeed.name,
            }),
          });

          const data = await res.json().catch(() => null);
          if (!res.ok) throw new Error(formatDownloadApiError(data, "Upload failed"));

          setEpisodes((prev) => {
            const next = [...prev];
            next[i] = {
              ...next[i],
              status: "done_drive",
              driveLink: (data as { webViewLink?: string } | null)?.webViewLink,
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

      if (i < toDownload[toDownload.length - 1].i) {
        await new Promise((r) => setTimeout(r, 800));
      }
    }

    setPageState("ready");
  }

  const doneCount = episodes.filter(
    (e) => e.status === "done_drive" || e.status === "done_local"
  ).length;
  const errorCount = episodes.filter((e) => e.status === "error").length;

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="space-y-6 rounded-3xl border border-[#142c54]/15 bg-white/55 p-5 shadow-lg backdrop-blur-sm sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#142c54]/60">
              YUTorah Podcast Toolkit
            </p>
            <h1 className="mt-1 text-3xl font-bold text-[#142c54]">YUTorah Downloader</h1>
            <p className="mt-1 text-sm text-[#142c54]/75">
              Find the latest shiurim and save them to Drive or download locally.
            </p>
          </div>
          <AuthButton />
        </div>

        {!isAuthenticated && (
          <div className="rounded-xl border border-[#f43126]/30 bg-[#f43126]/10 px-4 py-3 text-sm text-[#142c54]">
            Connect Google only if you want one-click Drive uploads. Local downloads are available without signing in.
          </div>
        )}

        {session?.error === "RefreshAccessTokenError" && (
          <div className="rounded-xl border border-[#f43126]/35 bg-[#f43126]/10 px-4 py-3 text-sm text-[#f43126]">
            Your Google session expired. Please sign out and sign in again.
          </div>
        )}

        <section className="space-y-4 rounded-2xl border border-[#142c54]/15 bg-[#ede0bc]/40 p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#142c54]/70">Feed</h2>
          <FeedSelector selectedFeed={selectedFeed} onSelect={setSelectedFeed} />

          <button
            onClick={handleCheck}
            disabled={!selectedFeed || pageState === "checking" || pageState === "downloading"}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#142c54] px-5 py-3 text-sm font-semibold text-[#ede0bc] transition hover:bg-[#102346] disabled:cursor-not-allowed disabled:opacity-45 sm:w-auto"
          >
            {pageState === "checking" ? (
              <>
                <SpinnerIcon className="h-4 w-4 animate-spin" />
                Checking feed…
              </>
            ) : (
              <>
                <DownloadSimpleIcon className="h-4 w-4" />
                Check for new episodes
              </>
            )}
          </button>

          {checkError && <p className="text-sm text-[#f43126]">{checkError}</p>}
        </section>

        {(pageState === "ready" || pageState === "downloading") && (
          <section className="space-y-3 rounded-2xl border border-[#142c54]/15 bg-[#ede0bc]/25 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-[#142c54]/70">Episodes</h2>
              {totalInFeed !== null && (
                <span className="rounded-full bg-white/70 px-3 py-1 text-xs text-[#142c54]/70">
                  {episodes.length} new / {totalInFeed} total
                </span>
              )}
            </div>

            {episodes.length === 0 ? (
              <p className="rounded-xl bg-white/80 py-6 text-center text-sm text-[#142c54]/70">
                You&apos;re all caught up — no new episodes.
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

            {(doneCount > 0 || errorCount > 0) && pageState === "ready" && (
              <div className="flex flex-wrap gap-3 border-t border-[#142c54]/15 pt-3 text-sm">
                {doneCount > 0 && <span className="text-emerald-700">{doneCount} saved successfully</span>}
                {errorCount > 0 && (
                  <span className="text-[#f43126]">{errorCount} failed — hover badges for details</span>
                )}
              </div>
            )}
          </section>
        )}

        <footer className="text-center text-xs text-[#142c54]/60">
          Downloads public shiurim from YUTorah · No YUTorah account required
        </footer>
      </div>
    </main>
  );
}
