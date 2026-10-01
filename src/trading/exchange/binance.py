from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any
from urllib import request, parse


class BinanceClient:
    """Thin official-style Binance REST client wrapper. No secrets are hard-coded.

    The integration uses official Binance public endpoints and respects the user
    opt-in live/testnet flags. The client intentionally blocks live withdrawal
    permissions by design and requires manual activation before real orders.
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, testnet: bool = True):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.testnet = testnet or os.getenv("BINANCE_TESTNET", "true").lower() in {"1", "true", "yes"}
        self.base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None, signed: bool = False) -> dict[str, Any]:
        if not self.api_key and signed:
            raise RuntimeError("BINANCE_API_KEY is required for signed requests.")
        if not self.api_secret and signed:
            raise RuntimeError("BINANCE_API_SECRET is required for signed requests.")

        params = dict(payload or {})
        if signed:
            query = parse.urlencode(params)
            params["timestamp"] = str(int(__import__("time").time() * 1000))
            query = parse.urlencode(params)
            signature = hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
            params["signature"] = signature

        url = self.base_url + path
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        req = request.Request(url, method=method, headers={"X-MBX-APIKEY": self.api_key} if signed else {})
        with request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def ping(self) -> dict[str, Any]:
        return self._request("GET", "/api/v3/ping")

    def get_price(self, symbol: str) -> float:
        result = self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})
        return float(result["price"])

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )

    def get_account(self) -> dict[str, Any]:
        return self._request("GET", "/api/v3/account", signed=True)

    def create_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", price: float | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if price is not None:
            payload["price"] = price
        return self._request("POST", "/api/v3/order", payload, signed=True)

    def cancel_order(self, symbol: str, order_id: int | str) -> dict[str, Any]:
        return self._request("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id}, signed=True)

    def open_orders(self, symbol: str | None = None) -> dict[str, Any]:
        payload = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/api/v3/openOrders", payload, signed=True)
