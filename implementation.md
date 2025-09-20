## Implementation Plan

A pragmatic, phased roadmap to ship a secure, multi‑provider LLM chat with a Next.js client and FastAPI server in a single repo (`client/` + `server/`). Keep it lean; add complexity only as needed.

### Phase 0 — Scaffold & Foundations
- Initialize repo with `client/`, `server/`, `shared/` and root configs
- Add Docker Compose (client, server, Redis, Postgres)
- Server: FastAPI skeleton with CORS, health, OpenAPI
- Client: Next.js 15 with Tailwind + shadcn/ui, basic layout
- Env validation and `.env.example`

Deliverables
- Project boots locally: `docker compose up`
- Health check: `GET /healthz` returns 200

### Phase 1 — MVP Chat (OpenAI + Anthropic)
- Server
  - Pydantic schemas for chat and models
  - Providers: `openai.py`, `anthropic.py` implementing `ChatProvider`
  - Router: model→provider resolution; basic constraints
  - Endpoints: `GET /api/v1/models`, `POST /api/v1/chat/stream` (SSE)
  - Rate limits: per‑IP (guest) and per‑user (placeholder) with Redis
  - SQLite dev DB; SQLModel models for `User`, `Conversation`, `Message`
  - Basic logging with redaction
- Client
  - Use firecrawl for making UI layout and components similar to t3.chat but better design. 
  - Chat UI: sidebar conversations, main chat view, composer
  - Model picker with provider grouping
  - SSE streaming via `EventSource`
  - Markdown rendering with code blocks + copy

Deliverables
- End‑to‑end: send a prompt, see streaming response
- Models list populates model picker

### Phase 2 — Persistence & Auth
- Server
  - CRUD: conversations/messages; persist streams to DB
  - JWT verification (NextAuth shared secret) for authenticated calls
  - User table and minimal auth hooks (email/OAuth handled by client)
  - Per‑user rate limits; monthly counters in Redis + DB
- Client
  - NextAuth setup (credentials/email or Google/GitHub)
  - Auth‑guarded routes; sync conversations to account
  - Regenerate/Stop; delete messages; rename chats

Deliverables
- Authenticated users have synced histories across devices
- Limits enforced per user and IP

### Phase 3 — More Providers & Safety
- Server
  - Add Google, OpenRouter, DeepSeek adapters
  - Encrypted user‑provided API keys (NaCl/Fernet), decrypt per request
  - Token usage tracking and simple cost estimation per model
  - Output moderation hooks; basic abuse filters
- Client
  - Settings to add user API keys (optional)
  - Cost/usage hints in UI; model caps surfaced

Deliverables
- 5+ providers available; user keys supported securely
- Visible usage and caps

### Phase 4 — Reliability & Operations
- Observability: structured logs, error reporting, optional OpenTelemetry traces
- Backpressure and timeouts tuned; cancel provider call on disconnect
- Admin toggles for enabling/disabling models and setting limits
- Migrations to Postgres (Neon) and production config

Deliverables
- Stable production deployment (client + server)
- Admin controls for models/limits

### Phase 5 — Advanced (Optional)
- Tools/function calling (JSON mode)
- File uploads with presigned S3 URLs
- Shared links/export
- Payments/tiers (Stripe/Lemon Squeezy)

---

## Task Breakdown (engineering‑oriented)

1) Repo & Dev Env
- Root README + implementation plan
- docker‑compose with services and `.env.example`

2) Server MVP
- FastAPI `main.py` with CORS, router includes
- Schemas: chat, models
- Providers base + OpenAI, Anthropic
- `/api/v1/models`, `/api/v1/chat/stream` (SSE)
- Redis limit: 10 req/5min per IP (configurable)

3) Client MVP
- Next.js app shell (sidebar + chat panel)
- shadcn components + Tailwind setup
- Models fetch and picker
- Chat composer + SSE renderer

4) Persistence & Auth
- SQLModel entities; SQLite dev; CRUD endpoints
- Persist messages per token chunk or after completion
- NextAuth JWT; server verification middleware
- Per‑user limits; monthly counters

5) Providers Expansion & Security
- Google/OpenRouter/DeepSeek adapters
- Encrypted user API keys; secrets handling
- Token usage metering; cost hints
- Moderation hooks

6) Shipping & Ops
- Alembic migrations; switch to Neon
- CI: lint/test/typecheck; OpenAPI → TS generation
- Deployment docs/scripts

## Acceptance Criteria (per phase)
- P0: Local boot + health
- P1: Streamed response from at least two providers
- P2: Authenticated history sync; rate limits enforced
- P3: 5 providers + user keys + usage tracking
- P4: Production deploy with admin toggles

## Risks & Mitigations
- Provider API changes → abstract via adapters; add contract tests
- Streaming differences (SSE vs chunks) → normalize to common chunk format
- Cost blowups → strict per‑model caps, monthly quotas, backoff on 429/5xx
- Security leaks → no client‑side keys; redaction; dependency scanning; minimal logs


