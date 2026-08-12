# Trading Agent

New trading agent repository.
# Market Structure Agent (FastAPI) — GitHub Ready

## What this repo does
Receives TradingView alerts (JSON), validates HMAC signature, updates a simple structure state machine, logs events, and returns a PASS/FAIL advisory.

## Quick start (local)
1. Clone:
   git clone <your-repo-url>
2. Create virtualenv and install:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
3. Set env vars (see .env.example)
4. Run:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Deploy (recommended)
- Push to GitHub.
- Connect repo to Railway or Render (both support auto-deploy from GitHub).
- Set environment variables on the host (WEBHOOK_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).
- Deploy and copy the public URL (e.g., https://your-app.up.railway.app/webhook).

### Deploy to Render (recommended for simplicity)

1. Push your repository to GitHub and ensure `render.yaml` is present (this repo includes `render.yaml`).
2. Sign in to https://render.com and click "New" → "Web Service".
3. Connect your GitHub repo and choose the `main` branch.
4. Select "Docker" (Render will build using the repository `Dockerfile`).
5. In the Render dashboard, set environment variables: `SECRET_KEY` (your webhook secret), `WEBHOOK_SECRET` (optional), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
6. Create the service — Render will build and deploy. When finished, copy the service URL and append `/webhook` for your public webhook endpoint.

After deploy: update your Cloudflare Worker `FORWARD_URL` secret to point to `https://<your-render-service>/webhook` (or configure TradingView directly if you use the worker).

## TradingView alert setup
- Create alert on your indicator.
- Webhook URL: `https://your-app.../webhook`
- Message: paste the JSON payload template (use `{{ticker}}`, `{{interval}}`, `{{close}}`, `{{timenow}}`, and `{{plot_n}}` placeholders that your Pine script exposes).
- TradingView will POST the JSON to your webhook.

## Test with curl
curl -X POST "https://your-app.../webhook" \
  -H "Content-Type: application/json" \
   -H "X-Signature: <hmac-sha256-hex>" \
   -d @tests/sample_payload.json

To compute HMAC:
Option A: use the included helper script:

```bash
# make executable once
chmod +x scripts/compute_hmac.py
# compute signature (reads file bytes exactly as curl will send them)
./scripts/compute_hmac.py -s "YOUR_WEBHOOK_SECRET" tests/sample_payload.json
```

Option B: use Python one-liner:

```bash
python -c "import hmac,hashlib,sys; print(hmac.new(b'WEBHOOK_SECRET', open('tests/sample_payload.json','rb').read(), hashlib.sha256).hexdigest())"
```

Then call curl (replace SIGNATURE with the printed hex):

```bash
curl -X POST "https://your-app.../webhook" \
   -H "Content-Type: application/json" \
   -H "X-Signature: SIGNATURE" \
   -d @tests/sample_payload.json
```

## Security
- Use a strong `WEBHOOK_SECRET` and validate HMAC header `X-Signature`.
- Use HTTPS (host provides it).
- Limit access and monitor logs.

## Next steps
- Replace the example Pine script with your full BOS/CHOCH indicator.
- Expand `structure_state.py` to persist state (Redis / DB).
- Add trade plan generation and manual approval flow.
Additional sample payloads are available in `tests/sample_payload.json` (TradingView-style) and `tests/sample_event.json` (structured event example).

## Cloudflare Worker proxy (optional)

If TradingView cannot include custom headers, use a Cloudflare Worker to compute the HMAC and forward the alert to your app.

Files: `cloudflare/worker.js`, `cloudflare/wrangler.toml` (example).

Quick deploy steps:

1. Install Wrangler: `npm install -g wrangler`.
2. Login: `wrangler login`.
3. Set secrets (example):

```bash
cd cloudflare
wrangler secret put SECRET_KEY
wrangler secret put FORWARD_URL    # https://your-app.example.com/webhook
```

4. Publish the worker:

```bash
wrangler publish
```

Flow: TradingView -> Cloudflare Worker -> Your app

Security notes:
- Keep `SECRET_KEY` secret by using Wrangler secrets.
- Use HTTPS endpoints only.

