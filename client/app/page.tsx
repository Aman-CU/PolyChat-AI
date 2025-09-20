"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Composer from "../components/Composer";
import ThinkingIndicator from "../components/ThinkingIndicator";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "../components/ui/select";

type Message = { role: "user" | "assistant" | "system"; content: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const [models, setModels] = useState<Record<string, { name: string; models: { id: string; name: string }[] }>>({});
  const [selectedModel, setSelectedModel] = useState<string>("gpt-4o-mini");
  const listRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  // Load available models from server
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/models`);
        if (!res.ok) return;
        const data = await res.json();
        if (!active) return;
        const incoming = data.providers || {};
        // Fallback minimal list if server provides none
        const fallback = {
          local: {
            name: "Local",
            models: [
              { id: "gpt-4o-mini", name: "GPT-4o mini" },
              { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash" },
            ],
          },
        } as Record<string, { name: string; models: { id: string; name: string }[] }>;
        const finalProviders = Object.keys(incoming).length ? incoming : fallback;
        setModels(finalProviders);
        // set default model if available
        const firstProvider = Object.keys(finalProviders)[0];
        const firstModel = firstProvider ? finalProviders[firstProvider].models?.[0]?.id : undefined;
        if (firstModel) setSelectedModel(firstModel);
      } catch {
        // ignore
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Auto scroll to bottom when messages update
  useEffect(() => {
    // Use smooth scroll only after initial render
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!canSend) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "" }]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversationId: null,
          model: selectedModel,
          messages: [...messages, userMsg],
          temperature: 0.7,
          maxTokens: 256,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`Request failed (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let assistantBuffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split(/\r?\n/);
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice("data: ".length).trim();
          if (!data) continue;
          try {
            const obj = JSON.parse(data);
            if (obj.content) {
              // Ignore server-emitted meta tag like: [model: provider/model]
              if (typeof obj.content === "string" && obj.content.startsWith("[model:")) {
                continue;
              }
              assistantBuffer += obj.content;
              setMessages((prev) => {
                const updated = [...prev];
                // update last assistant message
                for (let i = updated.length - 1; i >= 0; i--) {
                  if (updated[i].role === "assistant") {
                    updated[i] = { ...updated[i], content: assistantBuffer };
                    break;
                  }
                }
                return updated;
              });
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${(err as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [API_BASE, canSend, input, messages, selectedModel]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4 pb-40">
      {/* Landing hero & quick actions */}
      {messages.length === 0 && (
        <section className="mx-auto w-full max-w-3xl space-y-6 px-4 pt-[calc(max(15vh,2.5rem))]">
          <h2 className="text-3xl font-semibold text-foreground">How can I help you?</h2>
          <div className="flex flex-row flex-wrap gap-2.5 text-sm max-sm:justify-evenly">
            <Button
              className="justify-center transition-colors h-8 rounded-full px-4 py-1.5 font-medium backdrop-blur-xl bg-secondary/60 text-foreground shadow-sm hover:bg-secondary flex items-center gap-2"
              onClick={() => setInput("Write a short inspirational poem about the ocean.")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-sparkles"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
              <div>Create</div>
            </Button>
            <Button
              className="justify-center transition-colors h-8 rounded-full px-4 py-1.5 font-medium backdrop-blur-xl bg-secondary/60 text-foreground shadow-sm hover:bg-secondary flex items-center gap-2"
              onClick={() => setInput("Give me 5 ideas to explore this weekend in my city.")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-newspaper"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8V6Z"></path></svg>
              <div>Explore</div>
            </Button>
            <Button
              className="justify-center transition-colors h-8 rounded-full px-4 py-1.5 font-medium backdrop-blur-xl bg-secondary/60 text-foreground shadow-sm hover:bg-secondary flex items-center gap-2"
              onClick={() => setInput("Write a TypeScript function to debounce a callback.")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-code"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
              <div>Code</div>
            </Button>
            <Button
              className="justify-center transition-colors h-8 rounded-full px-4 py-1.5 font-medium backdrop-blur-xl bg-secondary/60 text-foreground shadow-sm hover:bg-secondary flex items-center gap-2"
              onClick={() => setInput("Explain backpropagation in simple terms.")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-graduation-cap"><path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"></path><path d="M22 10v6"></path><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"></path></svg>
              <div>Learn</div>
            </Button>
          </div>
          <div className="flex flex-col text-foreground/85">
            {[
              "How does AI work?",
              "Are black holes real?",
              "How many Rs are in the word 'strawberry'?",
              "What is the meaning of life?",
            ].map((q) => (
              <div key={q} className="border-t border-border/60 py-1 first:border-none">
                <button className="w-full text-left rounded-md py-2 hover:bg-accent/40 sm:px-3 text-muted-foreground hover:text-foreground" onClick={() => setInput(q)}>
                  <span>{q}</span>
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
      {/* Model picker moved into Composer */}

      <div ref={listRef} className="mx-auto w-full max-w-3xl px-4 pb-48">
        <div className="space-y-4">
        {messages.map((m, idx) => {
          if (m.role === "user") {
            return (
              <div key={idx} className="flex justify-end">
                <div className="max-w-[75%] rounded-xl px-3 py-2 bg-secondary/50 border border-border/50 text-foreground text-sm shadow-sm">
                  <span className="whitespace-pre-wrap">{m.content}</span>
                </div>
              </div>
            );
          }
          if (m.role === "assistant") {
            return (
              <div key={idx} className="prose prose-invert max-w-none w-full">
                <div className="whitespace-pre-wrap text-foreground/90">{m.content}</div>
              </div>
            );
          }
          // system
          return (
            <div key={idx} className="text-sm text-muted-foreground bg-muted/30 border border-border/50 rounded-md p-2">
              {m.content}
            </div>
          );
        })}
        {loading && <ThinkingIndicator />}
        <div ref={bottomRef} />
        </div>
      </div>

      {/* Sticky Composer (bottom) */}
      <Composer
        value={input}
        onChange={setInput}
        onSend={handleSend}
        onStop={handleStop}
        loading={loading}
        models={models}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
      />
    </div>
  );
}


