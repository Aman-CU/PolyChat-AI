"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import ThemeToggle from "./ThemeToggle";
import { useSession, signIn, signOut } from "next-auth/react";

type Conversation = {
  id: number;
  title: string;
  updated_at?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function Sidebar() {
  const { data: session } = useSession();
  const [query, setQuery] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>("");
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeId = useMemo(() => {
    const c = searchParams.get("c");
    return c ? Number(c) : null;
  }, [searchParams]);

  // Load conversations on mount and when notified to refresh
  useEffect(() => {
    let alive = true;
    const fetchConversations = async (showLoading: boolean = false) => {
      try {
        if (showLoading) setLoading(true);
        const res = await fetch(`${API_BASE}/api/v1/conversations`);
        if (!res.ok) return;
        const data = await res.json();
        if (!alive) return;
        // Only update state if changed to avoid unnecessary re-renders
        const same = JSON.stringify(conversations) === JSON.stringify(data);
        if (!same) setConversations(data);
      } finally {
        if (showLoading) setLoading(false);
      }
    };
    // Initial load shows loading state
    fetchConversations(true);
    // Throttle background refresh during streaming bursts
    let last = 0;
    let scheduled: ReturnType<typeof setTimeout> | null = null;
    const onRefresh = () => {
      const now = performance.now();
      const delta = now - last;
      // If events are too frequent, coalesce to one fetch after 800ms
      if (delta < 800) {
        if (scheduled) clearTimeout(scheduled);
        scheduled = setTimeout(() => {
          last = performance.now();
          fetchConversations(false);
        }, 800 - delta);
        return;
      }
      last = now;
      fetchConversations(false);
    };
    if (typeof window !== "undefined") {
      window.addEventListener("conversations:refresh", onRefresh);
    }
    return () => {
      alive = false;
      if (typeof window !== "undefined") {
        window.removeEventListener("conversations:refresh", onRefresh);
        if (scheduled) clearTimeout(scheduled);
      }
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = conversations.slice().sort((a, b) => {
      const at = a.updated_at ? new Date(a.updated_at).getTime() : 0;
      const bt = b.updated_at ? new Date(b.updated_at).getTime() : 0;
      return bt - at;
    });
    if (!q) return list;
    return list.filter((c) => c.title.toLowerCase().includes(q));
  }, [conversations, query]);

  const handleSelect = (id: number) => {
    const params = new URLSearchParams(Array.from(searchParams.entries()));
    params.set("c", String(id));
    router.push(`/?${params.toString()}`);
  };

  // Start a fresh chat: clear selection and let server auto-create & title on first send
  const handleNewChat = () => {
    const params = new URLSearchParams(Array.from(searchParams.entries()));
    params.delete("c");
    router.push(`/?${params.toString()}`);
  };

  const startRename = (c: Conversation) => {
    setEditingId(c.id);
    setEditingTitle(c.title);
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditingTitle("");
  };

  const submitRename = async (id: number) => {
    if (!editingTitle.trim()) return cancelRename();
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/v1/conversations/${id}?title=${encodeURIComponent(editingTitle.trim())}`, {
        method: "PATCH",
      });
      if (!res.ok) return;
      const obj = await res.json();
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: obj.title } : c)));
    } finally {
      cancelRename();
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    const ok = typeof window !== "undefined" ? window.confirm("Delete this conversation?") : true;
    if (!ok) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/v1/conversations/${id}`, { method: "DELETE" });
      if (!res.ok) return;
      setConversations((prev) => prev.filter((c) => c.id !== id));
      // If the deleted one is active, clear selection or pick the most recent remaining
      if (activeId === id) {
        const params = new URLSearchParams(Array.from(searchParams.entries()));
        params.delete("c");
        router.push(`/?${params.toString()}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="hidden md:flex fixed inset-y-0 left-0 w-64 z-40 p-2">
      <div className="flex h-full w-full flex-col rounded-lg shadow-sm border border-border bg-card/70 backdrop-blur-sm">
        <header className="p-3 border-b border-border/60">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-foreground">
              <Link href="/" className="inline-flex items-center">
                <span className="tracking-wide">PolyChat AI</span>
              </Link>
            </h1>
            <div className="ml-auto">
              <ThemeToggle />
            </div>
          </div>
        </header>
        <div className="p-3">
          <Button className="w-full" onClick={handleNewChat} disabled={loading}>
            New Chat
          </Button>
        </div>
        <div className="px-3 pb-2 border-b border-border/60">
          <div className="flex items-center gap-2 rounded-md px-2 py-2 bg-background/40 border border-border/60">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-search text-gray-500"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search your threads..."
              className="border-0 bg-transparent focus-visible:ring-0 p-0 h-7"
            />
          </div>
        </div>
        <div className="flex-1 overflow-auto small-scrollbar p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="text-xs text-muted-foreground px-2">{loading ? "Loading..." : "No conversations yet"}</div>
          ) : (
            filtered.map((c) => (
              <div
                key={c.id}
                className={`w-full rounded-md px-2 py-2 hover:bg-accent/40 ${activeId === c.id ? "bg-accent/30" : ""}`}
                title={c.title}
              >
                {editingId === c.id ? (
                  <div className="flex items-center gap-2">
                    <Input
                      autoFocus
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") submitRename(c.id);
                        if (e.key === "Escape") cancelRename();
                      }}
                      className="h-7"
                    />
                    <Button size="sm" className="h-7 px-2" onClick={() => submitRename(c.id)} disabled={loading}>Save</Button>
                    <Button size="sm" variant="secondary" className="h-7 px-2" onClick={cancelRename}>Cancel</Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleSelect(c.id)} className="flex-1 text-left min-w-0">
                      <div className="truncate text-sm text-foreground/90">{c.title}</div>
                      {c.updated_at ? (
                        <div className="text-[10px] text-muted-foreground mt-0.5 truncate">{new Date(c.updated_at).toLocaleString()}</div>
                      ) : null}
                    </button>
                    {/* Right-side icon group with fixed width to prevent overflow */}
                    <div className="flex flex-none items-center gap-1 pl-1">
                      <button
                        className="p-1 rounded hover:bg-accent/60"
                        title="Rename"
                        onClick={() => startRename(c)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-pencil"><path d="M18 2a2.828 2.828 0 1 1 4 4L7 21l-4 1 1-4Z"></path></svg>
                      </button>
                      <button
                        className="p-1 rounded hover:bg-accent/60"
                        title="Delete"
                        onClick={() => handleDelete(c.id)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-trash"><path d="M3 6h18"></path><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        <footer className="p-2 border-t border-border/60">
          {session?.user ? (
            <button onClick={() => signOut()} className="flex items-center gap-2 text-muted-foreground hover:text-foreground px-2 py-2 rounded-md hover:bg-accent/40 w-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-log-out"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" x2="9" y1="12" y2="12"></line></svg>
              <span>Logout</span>
            </button>
          ) : (
            <button onClick={() => signIn("google")} className="flex items-center gap-2 text-muted-foreground hover:text-foreground px-2 py-2 rounded-md hover:bg-accent/40 w-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-log-in"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" x2="3" y1="12" y2="12"></line></svg>
              <span>Login</span>
            </button>
          )}
        </footer>
      </div>
    </aside>
  );
}
