"use client";

import { useState, useEffect } from "react";
import { DEFAULT_FEEDS, Feed } from "@/config/feeds";

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

    const addedFeed = { name: newName.trim(), url: newUrl.trim() };
    const updated = [...customFeeds, addedFeed];
    setCustomFeeds(updated);
    saveCustomFeeds(updated);
    onSelect(addedFeed);
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
        {allFeeds.map((feed) => {
          const isSelected = selectedFeed?.url === feed.url;
          const isDefault = DEFAULT_FEEDS.some((d) => d.url === feed.url);

          return (
            <div key={feed.url} className="flex items-center gap-1">
              <button
                onClick={() => onSelect(feed)}
                className={`rounded-lg border px-3 py-1.5 text-sm transition ${
                  isSelected
                    ? "border-[#142c54] bg-[#142c54] text-[#ede0bc]"
                    : "border-[#142c54]/25 bg-white/70 text-[#142c54] hover:border-[#142c54]/55 hover:bg-white"
                }`}
              >
                {feed.name}
              </button>
              {!isDefault && (
                <button
                  onClick={() => handleDelete(feed)}
                  title="Remove feed"
                  className="rounded-md p-1 text-[#142c54]/50 transition hover:bg-[#f43126]/10 hover:text-[#f43126]"
                >
                  <i className="ph ph-x" aria-hidden="true" />
                </button>
              )}
            </div>
          );
        })}

        <button
          onClick={() => setShowAdd((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-[#142c54]/40 px-3 py-1.5 text-sm text-[#142c54]/80 transition hover:border-[#f43126] hover:text-[#f43126]"
        >
          <i className="ph ph-plus-circle" aria-hidden="true" /> Add feed
        </button>
      </div>

      {showAdd && (
        <div className="space-y-2 rounded-xl border border-[#142c54]/20 bg-white/80 p-3">
          <input
            type="text"
            placeholder="Teacher / Feed name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full rounded-lg border border-[#142c54]/25 bg-white px-3 py-2 text-sm text-[#142c54] placeholder:text-[#142c54]/50 focus:border-[#142c54] focus:outline-none"
          />
          <input
            type="url"
            placeholder="RSS feed URL (https://...)"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            className="w-full rounded-lg border border-[#142c54]/25 bg-white px-3 py-2 text-sm text-[#142c54] placeholder:text-[#142c54]/50 focus:border-[#142c54] focus:outline-none"
          />
          {addError && <p className="text-xs text-[#f43126]">{addError}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              className="rounded-lg bg-[#142c54] px-3 py-1.5 text-sm font-medium text-[#ede0bc] transition hover:bg-[#0f2344]"
            >
              Save feed
            </button>
            <button
              onClick={() => {
                setShowAdd(false);
                setAddError("");
              }}
              className="rounded-lg border border-[#142c54]/25 px-3 py-1.5 text-sm text-[#142c54]/80 transition hover:bg-[#142c54]/5"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {selectedFeed && (
        <p className="truncate text-xs text-[#142c54]/65">{selectedFeed.url}</p>
      )}
    </div>
  );
}
