"use client";

import { useState, useEffect } from "react";
import { DEFAULT_FEEDS, Feed } from "@/config/feeds";
import { LinkSimpleIcon, PlusCircleIcon, TrashIcon } from "@/components/icons";

const LOCAL_STORAGE_KEY = "yutorah_feeds";

interface FeedSelectorProps {
  selectedFeed: Feed | null;
  onSelect: (feed: Feed) => void;
}

function loadCustomFeeds(): Feed[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveCustomFeeds(feeds: Feed[]) {
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(feeds));
}

export default function FeedSelector({ selectedFeed, onSelect }: FeedSelectorProps) {
  const [customFeeds, setCustomFeeds] = useState<Feed[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [addError, setAddError] = useState("");

  useEffect(() => {
    setCustomFeeds(loadCustomFeeds());
  }, []);

  const allFeeds = [...DEFAULT_FEEDS, ...customFeeds];

  useEffect(() => {
    if (!selectedFeed && allFeeds.length > 0) {
      onSelect(allFeeds[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleAdd() {
    if (!newName.trim()) {
      setAddError("Name is required");
      return;
    }
    if (!newUrl.trim()) {
      setAddError("URL is required");
      return;
    }
    const alreadyExists = allFeeds.some((f) => f.url === newUrl.trim());
    if (alreadyExists) {
      setAddError("This URL is already added");
      return;
    }

    const updated = [...customFeeds, { name: newName.trim(), url: newUrl.trim() }];
    setCustomFeeds(updated);
    saveCustomFeeds(updated);
    onSelect({ name: newName.trim(), url: newUrl.trim() });
    setNewName("");
    setNewUrl("");
    setAddError("");
    setShowAdd(false);
  }

  function handleDelete(feed: Feed) {
    if (DEFAULT_FEEDS.some((f) => f.url === feed.url)) return;
    const updated = customFeeds.filter((f) => f.url !== feed.url);
    setCustomFeeds(updated);
    saveCustomFeeds(updated);
    if (selectedFeed?.url === feed.url && allFeeds.length > 1) {
      onSelect(DEFAULT_FEEDS[0] ?? allFeeds[0]);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {allFeeds.map((feed) => (
          <div key={feed.url} className="flex items-center gap-1">
            <button
              onClick={() => onSelect(feed)}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                selectedFeed?.url === feed.url
                  ? "border-[#142c54] bg-[#142c54] text-[#ede0bc]"
                  : "border-[#142c54]/30 bg-white text-[#142c54] hover:border-[#142c54]/60 hover:bg-[#ede0bc]/40"
              }`}
            >
              {feed.name}
            </button>
            {!DEFAULT_FEEDS.some((d) => d.url === feed.url) && (
              <button
                onClick={() => handleDelete(feed)}
                title="Remove feed"
                className="rounded-md p-1 text-[#142c54]/50 transition hover:bg-[#f43126]/10 hover:text-[#f43126]"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}

        <button
          onClick={() => setShowAdd((v) => !v)}
          className="inline-flex items-center gap-2 rounded-full border border-dashed border-[#142c54]/50 px-4 py-2 text-sm font-medium text-[#142c54]/70 transition hover:border-[#142c54] hover:text-[#142c54]"
        >
          <PlusCircleIcon className="h-4 w-4" />
          Add feed
        </button>
      </div>

      {showAdd && (
        <div className="space-y-2 rounded-xl border border-[#142c54]/20 bg-white/80 p-3 shadow-sm">
          <input
            type="text"
            placeholder="Teacher / Feed name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full rounded-lg border border-[#142c54]/25 bg-white px-3 py-2 text-sm text-[#142c54] outline-none ring-[#f43126] placeholder:text-[#142c54]/40 focus:ring-2"
          />
          <input
            type="url"
            placeholder="RSS feed URL (https://...)"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            className="w-full rounded-lg border border-[#142c54]/25 bg-white px-3 py-2 text-sm text-[#142c54] outline-none ring-[#f43126] placeholder:text-[#142c54]/40 focus:ring-2"
          />
          {addError && <p className="text-xs text-[#f43126]">{addError}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              className="rounded-lg bg-[#142c54] px-3 py-1.5 text-sm font-semibold text-[#ede0bc] transition hover:bg-[#102346]"
            >
              Add
            </button>
            <button
              onClick={() => {
                setShowAdd(false);
                setAddError("");
              }}
              className="rounded-lg border border-[#142c54]/25 px-3 py-1.5 text-sm text-[#142c54]/80 transition hover:bg-[#ede0bc]/50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {selectedFeed && (
        <p className="inline-flex max-w-full items-center gap-1.5 truncate rounded-full bg-white/75 px-3 py-1 text-xs text-[#142c54]/70">
          <LinkSimpleIcon className="h-3.5 w-3.5 shrink-0" />
          {selectedFeed.url}
        </p>
      )}
    </div>
  );
}
