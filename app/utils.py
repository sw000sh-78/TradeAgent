import hashlib
import hmac
import logging
import os
from typing import Any

import httpx


def get_logger() -> logging.Logger:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return logging.getLogger("trading_agent")


def validate_hmac(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


async def notify_telegram(token: str, chat_id: str, message: str) -> Any:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json={"chat_id": chat_id, "text": message})
        response.raise_for_status()
        return response.json()


def append_event_log(entry: dict):
    """Append an event line to logs/events.log as JSON (best-effort).

    Keep this minimal and not raise on error so UI or webhook don't crash.
    """
    try:
        import json
        os.makedirs("logs", exist_ok=True)
        with open("logs/events.log", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def compute_hmac_hex(secret: str, data: bytes) -> str:
    """Return HMAC-SHA256 hex for given secret and data."""
    try:
        return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
    except Exception:
        return ""
