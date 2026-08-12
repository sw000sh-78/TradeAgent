import os
from fastapi import FastAPI, Header, HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.utils import validate_hmac, get_logger, notify_telegram, compute_hmac_hex, append_event_log
from app.structure_state import MarketStructureState
from app.utils import append_event_log

logger = get_logger()
app = FastAPI(title="Trading Agent")
state = MarketStructureState()

# Templates + static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

WEBHOOK_SECRET = os.getenv("SECRET_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class AlertPayload(BaseModel):
    symbol: str
    signal: str
    structure: str
    timeframe: str
    price: float
    side: str
    extra: dict = {}


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.get("/ui")
async def ui(request: Request):
    # show current in-memory states and recent logs
    states = dict(state._states)
    # read recent log lines
    recent = []
    try:
        with open("logs/events.log", "r") as f:
            lines = f.read().strip().splitlines()
            recent = [lines[-50:]] if lines else []
            # flatten to string list
            if recent:
                recent = recent[0]
    except Exception:
        recent = []

    return templates.TemplateResponse("ui.html", {"request": request, "states": states, "recent": recent})


@app.post("/ui/send")
async def ui_send(
    symbol: str = Form(...),
    signal: str = Form(...),
    structure: str = Form(...),
    timeframe: str = Form(...),
    price: float = Form(...),
    side: str = Form("long"),
):
    # apply transition and append a log entry
    transition = state.transition(symbol, structure)
    entry = {
        "symbol": symbol,
        "signal": signal,
        "structure": structure,
        "timeframe": timeframe,
        "price": price,
        "side": side,
        "state": transition,
    }
    append_event_log(entry)
    return RedirectResponse(url="/ui", status_code=303)



@app.post("/ui/trigger")
async def ui_trigger(
    symbol: str = Form(...),
    signal: str = Form(...),
    structure: str = Form(...),
    timeframe: str = Form(...),
    price: float = Form(...),
    side: str = Form("long"),
):
    """Server-side signing + internal POST to /webhook to trigger full flow."""
    payload = {
        "symbol": symbol,
        "signal": signal,
        "structure": structure,
        "timeframe": timeframe,
        "price": price,
        "side": side,
        "extra": {},
    }

    # compute signature using same secret the webhook expects
    secret = WEBHOOK_SECRET or os.getenv("WEBHOOK_SECRET") or os.getenv("SECRET_KEY") or ""
    body = None
    try:
        import json
        body = json.dumps(payload).encode()
    except Exception:
        body = b""

    sig = compute_hmac_hex(secret, body)

    # perform internal POST to our own webhook endpoint
    # prefer loopback address
    host = os.getenv("INTERNAL_HOST", "127.0.0.1")
    port = os.getenv("PORT", "8000")
    url = f"http://{host}:{port}/webhook"

    # try posting and append response to logs
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=body, headers={"x-signature": sig, "Content-Type": "application/json"})
            result_text = f"trigger_resp status={resp.status_code} body={resp.text}"
    except Exception as e:
        result_text = f"trigger_error {e}"

    # append trigger result to logs
    append_event_log({"trigger": payload, "result": result_text})
    return RedirectResponse(url="/ui", status_code=303)

@app.post("/webhook")
async def webhook(request: Request, x_signature: str = Header(None)):
    body = await request.body()
    if not x_signature or not validate_hmac(body, x_signature, WEBHOOK_SECRET):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    alert = AlertPayload(**payload)
    logger.info("Received alert: %s %s %s", alert.symbol, alert.signal, alert.structure)

    transition = state.transition(alert.symbol, alert.structure)
    message = (
        f"TradingView alert received:\n"
        f"Symbol: {alert.symbol}\n"
        f"Signal: {alert.signal}\n"
        f"Structure: {alert.structure}\n"
        f"Timeframe: {alert.timeframe}\n"
        f"Price: {alert.price}\n"
        f"Side: {alert.side}\n"
        f"State: {transition}\n"
    )

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        await notify_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)

    return JSONResponse({"status": "ok", "state": transition})
