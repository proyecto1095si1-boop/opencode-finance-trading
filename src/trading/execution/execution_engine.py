from __future__ import annotations

from typing import Any

from trading.config import TradingConfig
from trading.execution.order_manager import OrderIntent, OrderManager


class ExecutionEngine:
    def __init__(self, config: TradingConfig | None = None, order_manager: OrderManager | None = None):
        self.config = config or TradingConfig()
        self.order_manager = order_manager or OrderManager()

    def verify_preconditions(self, order: OrderIntent) -> tuple[bool, str]:
        if self.config.mode == "LIVE" and not self.config.live_enabled:
            return False, "LIVE mode is disabled. Manual activation is required."
        if order.symbol is None:
            return False, "Symbol is required."
        if order.quantity <= 0:
            return False, "Quantity must be greater than zero."
        if order.stop_loss is None and order.side in {"LONG", "SHORT"}:
            return False, "Stop-loss is required before entry."
        return True, "OK"

    def execute(self, order: OrderIntent) -> dict[str, Any]:
        ok, reason = self.verify_preconditions(order)
        if not ok:
            return {"accepted": False, "reason": reason, "order": order.__dict__}
        return {
            "accepted": True,
            "order": self.order_manager.register_order(order),
            "reason": "Order registered for execution",
            "mode": self.config.mode,
        }
