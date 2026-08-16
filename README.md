# NotrieAI Explain API (Python/FastAPI)

Text-only backend. Paste any confusing or potentially dangerous text
(scam message, medical note, legal/contract language, official letter)
and get back a structured explanation: verdict, summary, key points,
confusing terms explained, and what to do next.

## Endpoints

- `GET /api/health` — health check
- `POST /api/explain` — body: `{ "text": "..." }` (20–30,000 characters)

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

## Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in GEMINI_API_KEY
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
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variable `GEMINI_API_KEY` in the Render dashboard
   (get this from aistudio.google.com — Gemini's free tier has no
   card required and does not expire, unlike xAI's trial credit).

## Frontend

The existing React frontend (NotrieAI) can point its API base URL at
this service once deployed — no UI/CSS changes needed, only the
request/response contract above.
