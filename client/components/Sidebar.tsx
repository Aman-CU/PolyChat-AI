"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar() {
  const [query, setQuery] = useState("");
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
          <Link href="/" className="block w-full">
            <Button className="w-full">New Chat</Button>
          </Link>
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
        <div className="flex-1 overflow-auto small-scrollbar p-2 space-y-2">
          {/* Thread list placeholder */}
          <div className="text-xs text-muted-foreground px-2">No conversations yet</div>
        </div>
        <footer className="p-2 border-t border-border/60">
          <Link href="/auth" className="flex items-center gap-2 text-muted-foreground hover:text-foreground px-2 py-2 rounded-md hover:bg-accent/40">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-log-in"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" x2="3" y1="12" y2="12"></line></svg>
            <span>Login</span>
          </Link>
        </footer>
      </div>
    </aside>
  );
}
