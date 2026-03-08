"use client";

import { Episode } from "@/lib/rss";

export type EpisodeStatus =
  | "idle"
  | "downloading"
  | "done_drive"
  | "done_local"
  | "error";

export interface EpisodeWithStatus extends Episode {
  status: EpisodeStatus;
  driveLink?: string;
  errorMessage?: string;
}

interface EpisodeListProps {
  episodes: EpisodeWithStatus[];
  onToggle: (index: number, checked: boolean) => void;
  selected: boolean[];
  onSelectAll: () => void;
  onClearAll: () => void;
  onDownload: (destination: "drive" | "local") => void;
  isDownloading: boolean;
  isAuthenticated: boolean;
}

export default function EpisodeList({
  episodes,
  onToggle,
  selected,
  onSelectAll,
  onClearAll,
  onDownload,
  isDownloading,
  isAuthenticated,
}: EpisodeListProps) {
  const selectedCount = selected.filter(Boolean).length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="rounded-md border border-[#142c54]/25 px-2 py-1 text-xs text-[#142c54]/80 transition hover:bg-[#142c54]/5"
          >
            Select all
          </button>
          <button
            onClick={onClearAll}
            className="rounded-md border border-[#142c54]/25 px-2 py-1 text-xs text-[#142c54]/80 transition hover:bg-[#142c54]/5"
          >
            Clear
          </button>
        </div>
        <span className="text-sm text-[#142c54]/70">{selectedCount} of {episodes.length} selected</span>
      </div>

      <div className="overflow-hidden rounded-xl border border-[#142c54]/20 bg-white/85 shadow-sm">
        <div className="grid grid-cols-[2rem_1fr_6rem_9rem] gap-2 bg-[#142c54] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[#ede0bc]">
          <span />
          <span>Episode</span>
          <span>Shiur ID</span>
          <span>Status</span>
        </div>

        <div className="divide-y divide-[#142c54]/10">
          {episodes.map((ep, i) => (
            <EpisodeRow
              key={ep.pageUrl}
              episode={ep}
              checked={selected[i] ?? false}
              onToggle={(checked) => onToggle(i, checked)}
            />
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {isAuthenticated && (
          <button
            onClick={() => onDownload("drive")}
            disabled={selectedCount === 0 || isDownloading}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#142c54] px-4 py-2 text-sm font-medium text-[#ede0bc] transition hover:bg-[#0f2344] disabled:cursor-not-allowed disabled:opacity-40 sm:flex-none"
          >
            <i className="ph ph-cloud-arrow-up" aria-hidden="true" />
            {isDownloading ? "Processing…" : `Drive (${selectedCount})`}
          </button>
        )}
        <button
          onClick={() => onDownload("local")}
          disabled={selectedCount === 0 || isDownloading}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#f43126] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#d92a20] disabled:cursor-not-allowed disabled:opacity-40 sm:flex-none"
        >
          <i className="ph ph-download-simple" aria-hidden="true" />
          {isDownloading ? "Processing…" : `Local (${selectedCount})`}
        </button>
      </div>
    </div>
  );
}

function EpisodeRow({
  episode,
  checked,
  onToggle,
}: {
  episode: EpisodeWithStatus;
  checked: boolean;
  onToggle: (checked: boolean) => void;
}) {
  const statusBadge = () => {
    switch (episode.status) {
      case "downloading":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-[#142c54]/10 px-2 py-0.5 text-xs text-[#142c54]">
            <i className="ph ph-spinner-gap animate-spin" aria-hidden="true" /> Working
          </span>
        );
      case "done_drive":
        return (
          <span className="flex items-center gap-1.5 text-xs text-[#142c54]">
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-700">
              <i className="ph ph-check-circle" aria-hidden="true" /> Drive
            </span>
            {episode.driveLink && (
              <a href={episode.driveLink} target="_blank" rel="noreferrer" className="text-[#142c54] underline-offset-2 hover:underline">
                Open
              </a>
            )}
          </span>
        );
      case "done_local":
        return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"><i className="ph ph-check" aria-hidden="true" /> Saved</span>;
      case "error":
        return (
          <span title={episode.errorMessage} className="inline-flex cursor-help items-center gap-1 rounded-full bg-[#f43126]/10 px-2 py-0.5 text-xs text-[#f43126]">
            <i className="ph ph-warning-circle" aria-hidden="true" /> Failed
          </span>
        );
      default:
        return <span className="rounded-full border border-[#142c54]/20 px-2 py-0.5 text-xs text-[#142c54]/65">New</span>;
    }
  };

  return (
    <div className="grid grid-cols-[2rem_1fr_6rem_9rem] items-center gap-2 px-3 py-2.5 transition hover:bg-[#ede0bc]/50">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onToggle(e.target.checked)}
        disabled={episode.status === "downloading"}
        className="h-4 w-4 cursor-pointer rounded border-[#142c54]/30 text-[#142c54] focus:ring-[#142c54]"
      />
      <div className="min-w-0">
        <p className="truncate text-sm text-[#142c54]" title={episode.title}>
          {episode.title || "(untitled)"}
        </p>
        <p className="truncate text-xs text-[#142c54]/60">{episode.pageUrl}</p>
      </div>
      <span className="truncate font-mono text-xs text-[#142c54]/70">{episode.shiurId ?? "—"}</span>
      <div>{statusBadge()}</div>
    </div>
  );
}
