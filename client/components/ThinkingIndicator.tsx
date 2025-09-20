"use client";

import { Sparkles } from "lucide-react";

export default function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 w-full">
      <span className="twinkle text-primary/90">
        <Sparkles className="h-4 w-4" />
      </span>
      <span className="text-sm shimmer">Thinking…</span>
      <style jsx>{`
        @keyframes twinkle {
          0% { opacity: .6; transform: scale(0.96) rotate(0deg); filter: drop-shadow(0 0 0px rgba(99,102,241,0.0)) hue-rotate(0deg); }
          50% { opacity: 1; transform: scale(1.08) rotate(5deg); filter: drop-shadow(0 0 8px rgba(99,102,241,0.85)) hue-rotate(25deg); }
          100% { opacity: .7; transform: scale(1) rotate(0deg); filter: drop-shadow(0 0 0px rgba(99,102,241,0.0)) hue-rotate(0deg); }
        }
        .twinkle { display:inline-flex; animation: twinkle 1.1s ease-in-out infinite; transform-origin: center; }

        @keyframes shimmerMove {
          0% { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        .shimmer {
          color: transparent;
          background: linear-gradient(90deg, rgba(156,163,175,0.75) 0%, rgba(255,255,255,1) 50%, rgba(156,163,175,0.75) 100%);
          -webkit-background-clip: text;
          background-clip: text;
          background-size: 200% 100%;
          animation: shimmerMove 1.4s linear infinite;
        }
      `}</style>
    </div>
  );
}
