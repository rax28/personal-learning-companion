# Personal Learning Companion

A production-oriented MVP scaffold based on the supplied master project instructions. The implementation keeps the AI intelligence in FastAPI, application/business logic in Express, and UI/offline concerns in React. The MVP is intentionally provider-independent and works without API keys through a deterministic demo model.

## MVP implemented
- Goal creation and listing
- Natural chat flow
- Evidence extraction into structured learner state
- Mastery/confidence tracking
- Gap and misconception detection
- Prerequisite-aware root-gap ranking
- Adaptive teaching strategy selection
- Persistent PostgreSQL schema with pgvector support
- Redis-ready configuration
- Online/local model interfaces with mock fallback and Ollama adapter
- Offline browser cache/event queue foundation
- Sync endpoint foundation with revision-aware merge
- Automated Python intelligence tests and TypeScript backend tests

## Quick start

### 1. Requirements
- Node.js 20+
- npm 10+
- Python 3.11+
- Docker (optional, for PostgreSQL/Redis)

### 2. Install
```bash
npm install
cd ai-backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && cd ..
```

### 3. Start infrastructure
```bash
npm run db:up
```

### 4. Configure
Copy `.env.example` to `.env`. The default mock model requires no API keys.

### 5. Run
```bash
npm run dev
```
Frontend: http://localhost:5173
Express: http://localhost:4000
AI backend: http://localhost:8000/docs

### 6. Test
```bash
npm test
npm run build
```

## Ollama offline model
Install Ollama separately and pull a Qwen model, e.g. `qwen2.5:3b`. Set `LOCAL_MODEL=qwen2.5:3b`. The browser offline layer stores learner state and queues sync events; a future desktop/mobile shell can connect the local model directly.

## Architecture
See `docs/architecture/*` and `docs/ai/*`.

## Natural conversation + external models

The companion now keeps recent conversation history, persists conversations and learner state in `.data/companion.json`, and sends the relevant history + learner state to the AI backend. The AI backend can use OpenAI's Responses API (with optional web search), Gemini, or Ollama/Qwen. Provider choice is configuration-driven; API keys remain server-side.

Set `ONLINE_PROVIDER=openai` and `OPENAI_API_KEY` for an online GPT-powered experience. Set `ONLINE_PROVIDER=gemini` with `GEMINI_API_KEY` for Gemini. For local/offline development use `ONLINE_PROVIDER=ollama` and run Ollama with the configured Qwen model.

The OpenAI integration uses the Responses API and can attach the built-in web search tool when `OPENAI_WEB_SEARCH=true`. OpenAI documents Responses API text generation and built-in web search in its developer quickstart. Gemini's current SDK/API supports `models.generate_content` and chat history/system instructions.

## v6 learning map

The companion now has three separate conversation areas — Education, Self Understanding, and Interview Prep — while sharing one durable learner knowledge graph. The graph is SQLite-backed at `ai-backend/data/knowledge.db` by default and is separate from conversation history. Messages are evidence attached to concepts; individual chat messages are never graph nodes.

The teaching loop is stateful: explain → check understanding → one small practice question → wait → evaluate → adapt. Two Pointers and beginner Integration have deterministic starter practice scaffolding so a small local model such as `llama3.2` does not have to invent the entire learning state.

The frontend includes the persistent pixel-cat companion, three-area floating navigation, and a dedicated Progress Map/tree view. The supplied pixel-cat sprite sheet is used as the base for idle/listening/jump/sleep states.

## V8 Source Lab + compressed offline cache

Source Lab now has a complete MVP retrieval path. A source is chunked and each chunk is stored as a zlib-compressed UTF-8 payload. The frontend automatically caches the source after compression and sends its `sourceId` with chat requests. The AI backend retrieves only matching chunks, decompresses them, and places them in the Llama prompt as source evidence. See `docs/offline-source-cache.md`.

The compression archive remains deterministic and byte-exact. Llama is used for local chat and optional predictability scoring; the current Ollama API integration does not claim to provide the full token-distribution arithmetic codec required to reproduce a neural compressor exactly.

Regression test:
```bash
PYTHONPATH=ai-backend:. python scripts/test-50-scenarios.py
```
Expected: `PASSED 50/50`.


## V9 user-specific deployment

The active persistence path is now PostgreSQL, scoped by the authenticated Google user UUID. Redis is a cache/read accelerator, not the source of truth. The learner knowledge graph, mastery, evidence, conversation state, profiles, conversations, messages and source cache are isolated per user. Google login uses OpenID Connect and an HttpOnly JWT session; Google Classroom uses a separate user-scoped OAuth grant. See `docs/user-specific-deployment.md` for the deployment contract and `.env.example` for required environment variables.
