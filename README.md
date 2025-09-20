#PolyChat AI

PolyChat AI is a modern, provider‑agnostic chat interface that brings together the best LLMs behind a clean, responsive UI. It supports streaming chat, model routing, and friendly error handling across OpenAI, Google Gemini, Anthropic (Claude), DeepSeek, and OpenRouter (including free and paid model pools). Built with Next.js (client) and FastAPI (server), PolyChat emphasizes developer ergonomics, a delightful UX, and extensibility.

#Highlights

Provider‑agnostic core: OpenAI, Gemini, Anthropic, DeepSeek, and OpenRouter support out of the box.
Streaming UX: Smooth SSE token streaming with graceful non‑stream fallbacks for tricky providers.
Model routing: Choose models directly or via OpenRouter with strict or fallback behavior.
Free vs Paid: Separate lists for OpenRouter free and paid models; clearly categorized in the UI.
Friendly errors: Human‑readable messages for 400/401/402/429; useful provider details when appropriate.
Modern UI: Beautiful Next.js client with a subtle “Thinking…” indicator and clean model picker UX.

#Tech stack

Client: Next.js 15, TypeScript, Tailwind, shadcn/ui (custom components)
Server: FastAPI (Python), httpx, Pydantic (v2), Pydantic‑Settings
Protocols: SSE for streaming; OpenAI‑compatible request/response shapes

#Use cases

Unified chat experience across multiple model providers
Rapid prototyping of AI assistants with reliable streaming and error handling
Exploring free and paid model options via OpenRouter without provider lock‑in

<img width="1919" height="903" alt="image" src="https://github.com/user-attachments/assets/f64378e0-8633-4e96-baa5-2ccbcbdf90fa" />
