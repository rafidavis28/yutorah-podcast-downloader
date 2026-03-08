"use client";

import { useState, useCallback } from "react";
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
      {/* Bulk actions */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Select all
          </button>
          <button
            onClick={onClearAll}
            className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Clear
          </button>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {selectedCount} of {episodes.length} selected
        </span>
      </div>

      {/* Episode table */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[2rem_1fr_6rem_7rem] gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-800 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          <span />
          <span>Title</span>
          <span>Shiur ID</span>
          <span>Status</span>
        </div>

        {/* Rows */}
        <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
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

      {/* Download buttons */}
      <div className="flex gap-2 flex-wrap">
        {isAuthenticated && (
          <button
            onClick={() => onDownload("drive")}
            disabled={selectedCount === 0 || isDownloading}
            className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isDownloading ? "Downloading…" : `↑ Drive (${selectedCount})`}
          </button>
        )}
        <button
          onClick={() => onDownload("local")}
          disabled={selectedCount === 0 || isDownloading}
          className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-gray-700 text-white text-sm font-medium hover:bg-gray-800 dark:bg-gray-600 dark:hover:bg-gray-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isDownloading ? "Downloading…" : `⬇ Local (${selectedCount})`}
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
          <span className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
            <span className="animate-spin">⟳</span> Working
          </span>
        );
      case "done_drive":
        return (
          <span className="flex items-center gap-1">
            <span className="text-xs text-green-600 dark:text-green-400">✓ Drive</span>
            {episode.driveLink && (
              <a
                href={episode.driveLink}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                Open ↗
              </a>
            )}
          </span>
        );
      case "done_local":
        return (
          <span className="text-xs text-green-600 dark:text-green-400">✓ Saved</span>
        );
      case "error":
        return (
          <span
            title={episode.errorMessage}
            className="text-xs text-red-500 cursor-help"
          >
            ✕ Failed
          </span>
        );
      default:
        return (
          <span className="text-xs text-gray-400 dark:text-gray-500 rounded-full px-2 py-0.5 border border-gray-200 dark:border-gray-600">
            New
          </span>
        );
    }
  };

  return (
    <div className="grid grid-cols-[2rem_1fr_6rem_7rem] gap-2 px-3 py-2.5 items-center hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onToggle(e.target.checked)}
        disabled={episode.status === "downloading"}
        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
      />
      <div className="min-w-0">
        <p className="text-sm text-gray-800 dark:text-gray-200 truncate" title={episode.title}>
          {episode.title || "(untitled)"}
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
          {episode.pageUrl}
        </p>
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">
        {episode.shiurId ?? "—"}
      </span>
      <div>{statusBadge()}</div>
    </div>
  );
}
