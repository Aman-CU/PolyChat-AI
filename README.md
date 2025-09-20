<<<<<<< HEAD
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
=======
## PolyChat

Multi‑provider LLM chat app (t3.chat‑style) with a Next.js client and Python/FastAPI server in a single repo. Secure, fast streaming, and minimal ops.

### Features
- **Multi‑provider models**: OpenAI, Anthropic, Google, OpenRouter, DeepSeek (extensible)
- **Streaming chat (SSE)** with stop/regenerate, markdown + code blocks
- **Model picker** grouped by provider with search
- **Conversations & history** stored server‑side
- **Auth** via NextAuth (JWT); optional guest mode with strict IP limits
- **Rate limits** per user/IP and per model; token budgets
- **Secure by default**: server‑only keys, input validation, redacted logs

### Tech stack
- Client: Next.js 15 (App Router), TypeScript, shadcn/ui, Tailwind CSS, React Query
- Server: FastAPI (Python 3.11+), httpx, SQLModel/SQLAlchemy, Alembic, Redis (rate limit)
- DB: SQLite (dev) → Postgres (Neon in prod)
- Infra: Docker Compose for dev; Vercel (client) + Fly.io/Render (server) for prod
- Shared types: Generated TypeScript types from FastAPI OpenAPI

### Project structure (expanded)
```
polychat/
  client/                                  # Next.js (TypeScript)
    app/
      layout.tsx
      page.tsx
      (chat)/
        layout.tsx
        page.tsx
    components/
      chat/
        ChatComposer.tsx
        ChatMessage.tsx
        ChatStream.tsx
      ui/                                   # shadcn components
    lib/
      api.ts                                # fetch helpers / EventSource
      formatting.ts                          # markdown/code rendering utils
      auth.ts                                # NextAuth client helpers
    public/
    package.json
    tsconfig.json
    next.config.js
    postcss.config.js
    tailwind.config.ts

  server/                                  # FastAPI (Python)
    app/
      api/
        v1/
          chat.py                           # POST /api/v1/chat/stream
          models.py                         # GET /api/v1/models
          conversations.py                  # CRUD
      providers/
        base.py
        openai.py
        anthropic.py
        google.py
        openrouter.py
        deepseek.py
        router.py
      core/
        config.py                           # pydantic-settings env loading
        auth.py                             # JWT verification (NextAuth)
        ratelimit.py                        # Redis limits
        security.py                         # key encryption, redaction
        sse.py                              # SSE utilities
        logging.py                          # structured logs
      db/
        models.py                           # SQLModel entities
        session.py                          # async engine/session
        crud.py
      schemas/
        chat.py
        common.py
      main.py                               # FastAPI app, routers, CORS
    pyproject.toml
    alembic/
      env.py
      versions/
    Dockerfile

  shared/
    api-types/
      package.json
      src/
        index.ts                             # generated via OpenAPI

  docker-compose.yml                         # dev: client, server, db, redis
  .env.example                               # combined env template
  README.md
  implementation.md
```

### API overview
- `GET /api/v1/models` — list available models grouped by provider
- `POST /api/v1/chat/stream` — SSE streaming chat completion
- `GET|POST|PATCH /api/v1/conversations` — basic CRUD
- `GET|POST|DELETE /api/v1/messages` — optional, usually implicit via chat

Request example (chat):
```json
{
  "conversationId": null,
  "model": "gpt-4o-mini",
  "messages": [
    { "role": "user", "content": "Hello!" }
  ],
  "temperature": 0.7,
  "maxTokens": 512
}
```

SSE response: `text/event-stream` with `data:` chunks containing `{ content, done?, usage? }`.

### Provider abstraction (server)
```python
class ChatProvider(Protocol):
    id: str
    async def list_models(self) -> list[ModelInfo]: ...
    async def stream(self, input: ChatInput) -> AsyncIterator[ProviderChunk]: ...
```
Adapters: `openai.py`, `anthropic.py`, `google.py`, `openrouter.py`, `deepseek.py`. A `router.py` resolves `model → provider` and enforces provider constraints.

### Security checklist
- Server‑only provider keys; optional user keys encrypted at rest (NaCl/Fernet)
- Strict Pydantic validation; request size and token caps; per‑request timeouts
- Per‑user and per‑IP rate limiting; per‑model caps; 429 with Retry‑After
- JWT verification (NextAuth shared secret); guest mode with tighter limits
- CORS restricted to client origin; HTTPS only in prod; secure cookies on client
- Redacted structured logs; no PII or secrets in logs

### Environment
Copy `.env.example` to `.env` files for client and server.
- Client: `NEXT_PUBLIC_API_BASE_URL`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL`
- Server: `API_PORT`, `CORS_ORIGINS`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, ...)

### Local development
Option A: Docker Compose (recommended)
```
docker compose up --build
```
Client at `http://localhost:3000`, API at `http://localhost:8000`. Redis and Postgres available in the network.

Option B: Manual
1) Server
```
cd server
uv sync  # or: pip install -e . && pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```
2) Client
```
cd client
pnpm i
pnpm dev
```

Generate TS types from OpenAPI (after API is running):
```
cd client
pnpm gen:api
```

### Deployment (suggested)
- Client: Vercel
- Server: Fly.io/Render/Hetzner (Uvicorn workers)
- DB: Neon Postgres; migrations via Alembic
- Redis: Upstash

### License
MIT


>>>>>>> 11ce76f (initial commit)
