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

  // Auto-select first feed on mount
  useEffect(() => {
    if (!selectedFeed && allFeeds.length > 0) {
      onSelect(allFeeds[0]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleAdd() {
    if (!newName.trim()) { setAddError("Name is required"); return; }
    if (!newUrl.trim()) { setAddError("URL is required"); return; }
    const alreadyExists = allFeeds.some((f) => f.url === newUrl.trim());
    if (alreadyExists) { setAddError("This URL is already added"); return; }

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
    if (DEFAULT_FEEDS.some((f) => f.url === feed.url)) return; // protect defaults
    const updated = customFeeds.filter((f) => f.url !== feed.url);
    setCustomFeeds(updated);
    saveCustomFeeds(updated);
    if (selectedFeed?.url === feed.url && allFeeds.length > 1) {
      onSelect(DEFAULT_FEEDS[0] ?? allFeeds[0]);
    }
  }

  return (
    <div className="space-y-2">
      {/* Feed list */}
      <div className="flex flex-wrap gap-2">
        {allFeeds.map((feed) => (
          <div key={feed.url} className="flex items-center gap-1">
            <button
              onClick={() => onSelect(feed)}
              className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
                selectedFeed?.url === feed.url
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {feed.name}
            </button>
            {!DEFAULT_FEEDS.some((d) => d.url === feed.url) && (
              <button
                onClick={() => handleDelete(feed)}
                title="Remove feed"
                className="text-gray-400 hover:text-red-500 transition-colors text-xs px-1"
              >
                ✕
              </button>
            )}
          </div>
        ))}

        <button
          onClick={() => setShowAdd((v) => !v)}
          className="px-3 py-1.5 rounded-md text-sm border border-dashed border-gray-400 dark:border-gray-500 text-gray-500 dark:text-gray-400 hover:border-blue-500 hover:text-blue-500 transition-colors"
        >
          + Add feed
        </button>
      </div>

      {/* Add feed form */}
      {showAdd && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2 bg-white dark:bg-gray-800">
          <input
            type="text"
            placeholder="Teacher / Feed name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="url"
            placeholder="RSS feed URL (https://...)"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {addError && (
            <p className="text-xs text-red-500">{addError}</p>
          )}
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Add
            </button>
            <button
              onClick={() => { setShowAdd(false); setAddError(""); }}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Selected feed URL */}
      {selectedFeed && (
        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
          {selectedFeed.url}
        </p>
      )}
    </div>
  );
}
