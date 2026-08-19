# NotrieAI Explain API (Python/FastAPI)

Paste any confusing or potentially dangerous text (scam message, medical
note, legal/contract language, official letter) or upload a photo/screenshot
of one, and get back a structured explanation: verdict, summary, key points,
confusing terms explained, and what to do next.

## AI providers

Two providers can generate the explanation: **OpenAI (GPT-5.6 Luna)** and
**Gemini (`gemini-flash-latest`)**. Both are toggled on/off from the admin
Settings page (stored in `app_settings` in the database, keys
`provider_openai_enabled` / `provider_gemini_enabled` — both default to on).

- If both are enabled: OpenAI is tried first; if it fails or is overloaded,
  Gemini is used as the fallback.
- If only one is enabled, that one is used exclusively.
- If neither is enabled, `/api/explain` returns an error asking an admin to
  turn one on.

## Endpoints

- `GET /api/health` — health check (no auth)
- `POST /api/auth/signup` — body: `{ "email": "...", "password": "..." }` (password min 8 chars). Returns a JWT + user info. If `email` matches the `ADMIN_EMAIL` env var (case-insensitive), the new account is created as admin automatically.
- `POST /api/auth/login` — body: `{ "email": "...", "password": "..." }`. Returns a JWT + user info.
- `POST /api/explain` — **requires** `Authorization: Bearer <token>` header. Body: `{ "text": "..." }` (20–30,000 characters) and/or `{ "image_base64": "...", "image_mime_type": "..." }`. On success, also saves a row to that user's history (see below).
- `GET /api/history` — **requires auth**. This user's saved analyses, newest first (id, verdict, summary, a short input preview, whether it had an image, created_at). Only ever returns the current user's own rows.
- `GET /api/history/{history_id}` — **requires auth**. Full detail for one saved analysis (same shape as `/api/explain`'s response, plus id/created_at). 404 if it doesn't exist or isn't owned by the requesting user.
- `DELETE /api/history/{history_id}` — **requires auth**. Deletes one saved analysis. 404 if it doesn't exist or isn't owned by the requesting user.
- `DELETE /api/history` — **requires auth**. Deletes every saved analysis for the requesting user.
- `GET /api/settings/public` — no auth. Returns only keys prefixed `theme_`, `site_`, or `brand_` (for the login/signup screens, before a user has a token).
- `GET /api/admin/settings` — **admin only**. Returns every key in `app_settings`.
- `PUT /api/admin/settings` — **admin only**. Body: `{ "key": "value", ... }` — upserts any number of keys at once. There is no fixed list of allowed keys: any setting (a new color, a new toggle, a new piece of copy) can be introduced from the admin UI with no backend code change.
- `DELETE /api/admin/settings/{key}` — **admin only**. Removes a key (reverts to its hardcoded default, if one exists in code - e.g. the provider toggles).
- `GET /api/admin/users` — **admin only**. Lists every registered user (id, email, is_admin, created_at).
- `PATCH /api/admin/users/{user_id}` — **admin only**. Body: `{ "is_admin": true|false }` — promote/demote a user. Blocked: changing your own admin status, or removing the last remaining admin.
- `DELETE /api/admin/users/{user_id}` — **admin only**. Deletes a user account. Blocked: deleting your own account, or deleting the last remaining admin.

Response shape:

```json
{
  "verdict": "safe | suspicious | likely_scam | needs_clarification",
  "verdict_reason": "...",
  "summary": "...",
  "key_points": ["..."],
  "confusing_terms": [{ "term": "...", "explanation": "..." }],
  "what_you_should_do": ["..."]
}
```

## Database (Neon Postgres)

This service uses Postgres (tested against [Neon](https://neon.tech)'s
free tier) via SQLAlchemy (async) + Alembic migrations.

1. Create a Neon project and copy its connection string.
2. Set `DATABASE_URL` (in `.env` locally, or as a Render env var in
   production) to that string, e.g.
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`.
3. Run migrations:
   ```bash
   alembic upgrade head
   ```
   This creates the `users` and `app_settings` tables and seeds default
   theme colors + AI provider toggles into `app_settings`.

To create a new migration after changing `app/models.py`:
```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in DATABASE_URL, OPENAI_API_KEY, GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`. Test it:

```bash
curl -X POST http://localhost:8000/api/explain \
  -H "Content-Type: application/json" \
  -d '{"text": "Paste at least 20 characters of scam/medical/legal text here."}'
```

## Deploy to Render

1. Push this repo to GitHub.
2. On Render: New → Web Service → connect the repo.
3. Render will read `render.yaml` automatically (or set manually):
   - Build command: `pip install -r requirements.txt`
   - Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add these environment variables in the Render dashboard:
   - `DATABASE_URL` — your Neon connection string
   - `ADMIN_EMAIL` — the email that should automatically become admin on signup
   - `OPENAI_API_KEY` — from platform.openai.com
   - `GEMINI_API_KEY` — from aistudio.google.com (free tier, no card required)
   - `JWT_SECRET` — Render can auto-generate this (see `render.yaml`)

## Frontend

The existing React frontend (NotrieAI) can point its API base URL at
this service once deployed — no UI/CSS changes needed, only the
request/response contract above.
