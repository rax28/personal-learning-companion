# User-specific production architecture

## Identity
1. Browser opens `/auth/google`.
2. Google OpenID Connect returns the verified Google `sub`.
3. Backend upserts the user in PostgreSQL and creates an HttpOnly JWT session cookie.
4. Every protected request requires that session.
5. The backend passes the authenticated UUID to AI as `X-User-ID` plus the internal service token.

## Persistence
- PostgreSQL is the durable source of truth.
- The learner knowledge graph, mastery, evidence, conversation state, profile, conversations, messages and source cache are keyed by `user_id`.
- Redis is a cache/read accelerator only. Deleting Redis does not delete learner data.
- Source chunks remain losslessly compressed in PostgreSQL JSONB and are cached/retrieved through Redis.

## Google Classroom
Login identity and Classroom authorization are separate grants.
Classroom OAuth tokens are stored per user in `oauth_tokens`; they are never held in a process-global variable.

## Deployment
`docker compose up --build` starts PostgreSQL/pgvector, Redis, FastAPI, Express and the static frontend.
Set `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `AI_INTERNAL_TOKEN`, Google OAuth values and model-provider credentials in the deployment environment.
