# Deploying ClaimShield Desk (live link for the submission form)

The demo runs on the **in-memory backend** — no API keys, no secrets, nothing to
configure on the server. Two services: the FastAPI API and the Next.js cockpit.

## Option A — Render (free, recommended)

1. Sign in at https://render.com with GitHub (account: Shashank-VK).
2. New → Blueprint → pick the `Shashank-VK/ClaimShield` repo → Apply.
3. Render creates `claimshield-api` and `claimshield-web` and wires the URLs
   between them (`FRONTEND_ORIGIN` / `NEXT_PUBLIC_API_URL` are set by the
   blueprint — no manual env vars).
4. Wait for both to show **Live**. The cockpit URL is
   `https://claimshield-web.onrender.com` — that is the **Deployed Project Link**
   for the submission form.

Notes:
- Free services sleep after ~15 min idle — the first load after a sleep takes
  30–60 s to wake. That is normal on the free tier.
- If the cockpit shows "Backend not reachable", check the API service is Live
  and that `NEXT_PUBLIC_API_URL` on the web service is set (it is baked in at
  build time — if it is wrong, redeploy the web service).

## Option B — Docker (any host)

```bash
docker build -t claimshield-api .
docker run -p 8000:8000 claimshield-api
# frontend: cd frontend && NEXT_PUBLIC_API_URL=<api-url> npm install && npm run build && npm start
```

## Local (unchanged)

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000   # from the project root, .venv on
cd frontend && npm run dev                               # :3000
```

Local defaults are untouched: the API is `http://127.0.0.1:8000` unless
`NEXT_PUBLIC_API_URL` is set, and CORS allows `localhost:3000` unless
`FRONTEND_ORIGIN` is set.
