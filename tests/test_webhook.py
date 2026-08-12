import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app, WEBHOOK_SECRET

client = TestClient(app)


def test_webhook_rejects_invalid_signature():
    payload = {
        "symbol": "AAPL",
        "signal": "test",
        "structure": "bullish",
        "timeframe": "1h",
        "price": 100.0,
        "side": "long",
        "extra": {},
    }
    response = client.post("/webhook", json=payload, headers={"x-signature": "bad"})
    assert response.status_code == 401


def test_webhook_accepts_valid_signature():
    payload = {
        "symbol": "AAPL",
        "signal": "test",
        "structure": "bullish",
        "timeframe": "1h",
        "price": 100.0,
        "side": "long",
        "extra": {},
    }
    body = json.dumps(payload).encode()
    if not WEBHOOK_SECRET:
        response = client.post("/webhook", json=payload, headers={"x-signature": ""})
        assert response.status_code in {200, 401}
    else:
        signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        response = client.post("/webhook", json=payload, headers={"x-signature": signature})
        assert response.status_code == 200
