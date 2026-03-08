"use client";

import { useState } from "react";
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
        body: JSON.stringify({ feedUrl: selectedFeed.url, feedName: selectedFeed.name }),
      });
      const data = await res.json();

      if (!res.ok) {
        setCheckError(data.error ?? "Failed to check feed");
        setPageState("idle");
        return;
      }

      const eps: EpisodeWithStatus[] = (data.newEpisodes ?? []).map(
        (ep: { title: string; pageUrl: string; shiurId: string | null }) => ({ ...ep, status: "idle" as const })
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

    const toDownload = episodes.map((ep, i) => ({ ep, i })).filter(({ i }) => selected[i]);

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
            body: JSON.stringify({ episode: ep, destination: "local", feedName: selectedFeed.name }),
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error ?? "Download failed");
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
            body: JSON.stringify({ episode: ep, destination: "drive", feedName: selectedFeed.name }),
          });

          const data = await res.json();
          if (!res.ok) throw new Error(data.error ?? "Upload failed");

          setEpisodes((prev) => {
            const next = [...prev];
            next[i] = { ...next[i], status: "done_drive", driveLink: data.webViewLink };
            return next;
          });
        }
      } catch (err) {
        setEpisodes((prev) => {
          const next = [...prev];
          next[i] = { ...next[i], status: "error", errorMessage: String(err) };
          return next;
        });
      }

      if (i < toDownload[toDownload.length - 1].i) {
        await new Promise((r) => setTimeout(r, 800));
      }
    }

    setPageState("ready");
  }

  const doneCount = episodes.filter((e) => e.status === "done_drive" || e.status === "done_local").length;
  const errorCount = episodes.filter((e) => e.status === "error").length;

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="inline-flex items-center gap-1 rounded-full bg-[#142c54] px-3 py-1 text-xs font-medium uppercase tracking-wide text-[#ede0bc]">
            <i className="ph ph-waveform" aria-hidden="true" /> YUTorah Toolkit
          </p>
          <h1 className="mt-2 text-3xl font-bold text-[#142c54]">Podcast Downloader</h1>
          <p className="mt-1 text-sm text-[#142c54]/75">Find new shiurim quickly and save them to Google Drive or your device.</p>
        </div>
        <AuthButton />
      </div>

      {!isAuthenticated && (
        <div className="rounded-xl border border-[#f43126]/25 bg-white/75 px-4 py-3 text-sm text-[#142c54]">
          <span className="inline-flex items-center gap-1.5 font-medium text-[#f43126]"><i className="ph ph-info" aria-hidden="true" /> Tip:</span>{" "}
          Sign in with Google to enable Drive uploads. Local downloads work without sign-in.
        </div>
      )}

      {session?.error === "RefreshAccessTokenError" && (
        <div className="rounded-xl border border-[#f43126]/30 bg-[#f43126]/10 px-4 py-3 text-sm text-[#142c54]">
          Your Google session expired. Please sign out and sign in again.
        </div>
      )}

      <section className="space-y-4 rounded-2xl border border-[#142c54]/20 bg-white/70 p-5 shadow-sm backdrop-blur-sm">
        <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[#142c54]/80">
          <i className="ph ph-rss" aria-hidden="true" /> Feed selection
        </div>
        <FeedSelector selectedFeed={selectedFeed} onSelect={setSelectedFeed} />

        <button
          onClick={handleCheck}
          disabled={!selectedFeed || pageState === "checking" || pageState === "downloading"}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#142c54] px-5 py-2.5 text-sm font-semibold text-[#ede0bc] transition hover:bg-[#0f2344] disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
        >
          {pageState === "checking" ? (
            <>
              <i className="ph ph-spinner-gap animate-spin" aria-hidden="true" /> Checking...
            </>
          ) : (
            <>
              <i className="ph ph-magnifying-glass" aria-hidden="true" /> Check for new episodes
            </>
          )}
        </button>

        {checkError && <p className="text-sm text-[#f43126]">{checkError}</p>}
      </section>

      {(pageState === "ready" || pageState === "downloading") && (
        <section className="space-y-3 rounded-2xl border border-[#142c54]/20 bg-white/75 p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#142c54]/80">Episodes</h2>
            {totalInFeed !== null && (
              <span className="rounded-full bg-[#142c54]/10 px-2.5 py-1 text-xs text-[#142c54]/80">
                {episodes.length} new / {totalInFeed} total
              </span>
            )}
          </div>

          {episodes.length === 0 ? (
            <p className="rounded-xl bg-[#142c54]/5 py-6 text-center text-sm text-[#142c54]/70">All caught up — no new episodes.</p>
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
            <div className="flex gap-4 border-t border-[#142c54]/10 pt-2">
              {doneCount > 0 && <span className="text-sm text-emerald-700">{doneCount} saved</span>}
              {errorCount > 0 && <span className="text-sm text-[#f43126]">{errorCount} failed — hover for details</span>}
            </div>
          )}
        </section>
      )}

      <footer className="pb-4 text-center text-xs text-[#142c54]/60">
        Downloads public shiurim from YUTorah · No YUTorah account required
      </footer>
    </main>
  );
}
