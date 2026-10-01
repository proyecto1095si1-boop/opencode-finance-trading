from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderIntent:
    symbol: str
    side: str
    type: str = "MARKET"
    quantity: float = 0.0
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    risk: float = 0.0
    reason: str = ""
    timestamp: int | None = None
    idempotency_key: str | None = None


class OrderManager:
    def __init__(self):
        self.orders: list[dict[str, Any]] = []
        self.seen_keys: set[str] = set()

    def is_duplicate(self, key: str) -> bool:
        return key in self.seen_keys

    def register_order(self, order: OrderIntent) -> dict[str, Any]:
        if not order.idempotency_key:
            order.idempotency_key = f"{order.symbol}:{order.side}:{order.price}:{order.timestamp}"
        if self.is_duplicate(order.idempotency_key):
            raise ValueError("Duplicate order rejected by idempotency guard.")
        self.seen_keys.add(order.idempotency_key)
        record = {
            "symbol": order.symbol,
            "side": order.side,
            "type": order.type,
            "quantity": order.quantity,
            "price": order.price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "risk": order.risk,
            "reason": order.reason,
            "idempotency_key": order.idempotency_key,
            "timestamp": order.timestamp,
        }
        self.orders.append(record)
        return record
