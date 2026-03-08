import {
  DownloadSimpleIcon,
  SpinnerIcon,
  UploadSimpleIcon,
} from "@/components/icons";

export type EpisodeStatus =
  | "idle"
  | "downloading"
  | "done_drive"
  | "done_local"
  | "error";

export interface EpisodeWithStatus {
  title: string;
  pageUrl: string;
  shiurId: string | null;
  status: EpisodeStatus;
  driveLink?: string;
  errorMessage?: string;
}

interface EpisodeListProps {
  episodes: EpisodeWithStatus[];
  selected: boolean[];
  onToggle: (index: number, checked: boolean) => void;
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="rounded-full border border-[#142c54]/30 px-3 py-1.5 text-xs font-medium text-[#142c54] transition hover:bg-[#ede0bc]/40"
          >
            Select all
          </button>
          <button
            onClick={onClearAll}
            className="rounded-full border border-[#142c54]/20 px-3 py-1.5 text-xs font-medium text-[#142c54]/70 transition hover:bg-[#ede0bc]/40"
          >
            Clear
          </button>
        </div>
        <span className="text-sm text-[#142c54]/70">
          {selectedCount} of {episodes.length} selected
        </span>
      </div>

      <div className="overflow-hidden rounded-xl border border-[#142c54]/15 bg-white/85 shadow-sm">
        <div className="grid grid-cols-[2rem_1fr_6rem_12rem] gap-2 bg-[#142c54]/5 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[#142c54]/70">
          <span />
          <span>Title</span>
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
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#142c54] px-4 py-2 text-sm font-semibold text-[#ede0bc] transition hover:bg-[#102346] disabled:cursor-not-allowed disabled:opacity-40 sm:flex-none"
          >
            <UploadSimpleIcon className="h-4 w-4" />
            {isDownloading ? "Saving…" : `Save to Drive (${selectedCount})`}
          </button>
        )}
        <button
          onClick={() => onDownload("local")}
          disabled={selectedCount === 0 || isDownloading}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#f43126] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#df2b20] disabled:cursor-not-allowed disabled:opacity-40 sm:flex-none"
        >
          <DownloadSimpleIcon className="h-4 w-4" />
          {isDownloading ? "Downloading…" : `Download local (${selectedCount})`}
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
          <span className="inline-flex items-center gap-1 text-xs text-[#142c54]">
            <SpinnerIcon className="h-3.5 w-3.5 animate-spin" /> Working
          </span>
        );
      case "done_drive":
        return (
          <span className="flex items-center gap-1">
            <span className="text-xs font-medium text-emerald-700">Saved to Drive</span>
            {episode.driveLink && (
              <a
                href={episode.driveLink}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-[#142c54] underline-offset-2 hover:underline"
              >
                Open
              </a>
            )}
          </span>
        );
      case "done_local":
        return <span className="text-xs font-medium text-emerald-700">Saved local</span>;
      case "error":
        return (
          <div className="max-w-full">
            <span className="text-xs font-medium text-[#f43126]">Failed</span>
            {episode.errorMessage && (
              <p className="mt-0.5 break-words text-[11px] leading-4 text-[#f43126]/90" title={episode.errorMessage}>
                {episode.errorMessage}
              </p>
            )}
          </div>
        );
      default:
        return (
          <span className="rounded-full border border-[#142c54]/20 px-2 py-0.5 text-xs text-[#142c54]/65">
            New
          </span>
        );
    }
  };

  return (
    <div className="grid grid-cols-[2rem_1fr_6rem_12rem] items-center gap-2 px-3 py-2.5 transition hover:bg-[#ede0bc]/20">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onToggle(e.target.checked)}
        disabled={episode.status === "downloading"}
        className="h-4 w-4 cursor-pointer rounded border-[#142c54]/40 text-[#f43126] focus:ring-[#f43126]"
      />
      <div className="min-w-0">
        <p className="truncate text-sm text-[#142c54]" title={episode.title}>
          {episode.title || "(untitled)"}
        </p>
        <p className="truncate text-xs text-[#142c54]/50">{episode.pageUrl}</p>
      </div>
      <span className="truncate font-mono text-xs text-[#142c54]/70">{episode.shiurId ?? "—"}</span>
      <div>{statusBadge()}</div>
    </div>
  );
}
