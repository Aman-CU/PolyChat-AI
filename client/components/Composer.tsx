"use client";

import { useEffect, useRef } from "react";
import { Button } from "./ui/button";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "./ui/select";
import { ArrowUp, Search, Paperclip, SlidersHorizontal, Sparkles } from "lucide-react";

type ModelsMap = Record<string, { name: string; models: { id: string; name: string }[] }>;

export default function Composer({
  value,
  onChange,
  onSend,
  onStop,
  loading,
  models,
  selectedModel,
  setSelectedModel,
  disabled = false,
  disabledMessage,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
  loading: boolean;
  models: ModelsMap;
  selectedModel: string;
  setSelectedModel: (v: string) => void;
  disabled?: boolean;
  disabledMessage?: string;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    // Auto-resize textarea height
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = el.scrollHeight + "px";
  }, [value]);

  return (
    <div className="fixed bottom-0 left-0 right-0 md:pl-64 px-4 pb-6 pt-2">
      <div className="relative mx-auto max-w-3xl rounded-2xl border border-border/40 shadow-2xl bg-background/30 backdrop-blur-xl ring-1 ring-border/40">
        {/* Textarea */}
        <div className="flex flex-col gap-2 p-4 pb-20">
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={1}
            placeholder={disabled ? (disabledMessage || "Sign in to continue...") : "Type your message here..."}
            onKeyDown={(e) => {
              if (!disabled && e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
            readOnly={disabled}
            className={`w-full resize-none bg-transparent outline-none px-2 py-2 text-[15px] text-foreground placeholder:text-muted-foreground ${disabled ? "opacity-60" : ""}`}
          />
        </div>

        {/* Footer controls inside composer */}
        <div className="absolute inset-x-0 bottom-0 px-4 pt-3 pb-4">
          <div className="flex items-center gap-2">
            {/* Model Select */}
            <Select value={selectedModel} onValueChange={(v) => setSelectedModel(v)}>
              <SelectTrigger className="h-7 min-w-[4rem] rounded-md px-2 text-xs sm:text-[12px] text-foreground/90 bg-white/10 border border-white/20 backdrop-blur-xl ring-1 ring-white/10 data-[state=open]:bg-white/15">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent align="start" className="max-h-[60vh] w-[24rem] bg-white/10 backdrop-blur-xl border border-white/15">
                {Object.keys(models).length === 0 ? (
                  <div className="px-3 py-2 text-sm text-muted-foreground">No models available</div>
                ) : (
                  Object.entries(models).flatMap(([providerId, group]) =>
                    (group.models || []).map((m) => (
                      <SelectItem key={`${providerId}-${m.id}`} value={m.id}>
                        <span className="inline-flex items-center gap-2">
                          <Sparkles className="h-3.5 w-3.5 text-primary/90" />
                          <span>{m.name || m.id}</span>
                        </span>
                      </SelectItem>
                    ))
                  )
                )}
              </SelectContent>
            </Select>

            {/* Utility buttons */}
            <Button variant="ghost" size="sm" className="h-8 rounded-full text-foreground/90 bg-white/10 border border-white/20 backdrop-blur-xl hover:bg-white/15">
              <Search className="h-4 w-4 mr-1" />
              Search
            </Button>
            <Button variant="ghost" size="sm" className="h-8 rounded-full text-foreground/90 bg-white/10 border border-white/20 backdrop-blur-xl hover:bg-white/15">
              <Paperclip className="h-4 w-4 mr-1" />
              Attach
            </Button>
            <Button variant="ghost" size="sm" className="h-8 rounded-full text-foreground/90 bg-white/10 border border-white/20 backdrop-blur-xl hover:bg-white/15">
              <SlidersHorizontal className="h-4 w-4 mr-1" />
              Filters
            </Button>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Arrow-up submit button */}
            {!loading ? (
              <Button
                onClick={onSend}
                disabled={disabled || !value.trim()}
                aria-label="Send"
                className="h-14 w-14 rounded-md p-0 bg-primary/30 hover:bg-primary/40 disabled:opacity-50 backdrop-blur-xl shadow-md"
              >
                <ArrowUp className="h-7 w-7" />
              </Button>
            ) : (
              <Button onClick={onStop} aria-label="Stop" className="h-14 w-14 rounded-md p-0 bg-red-600/70 hover:bg-red-600 backdrop-blur-xl">
                ||
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
