from __future__ import annotations

from typing import Any


class Dashboard:
    def __init__(self):
        self.snapshots: list[dict[str, Any]] = []

    def render(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        self.snapshots.append(snapshot)
        return {
            "balance": snapshot.get("balance", 0.0),
            "equity": snapshot.get("equity", 0.0),
            "pnl": snapshot.get("pnl", 0.0),
            "positions": snapshot.get("positions", []),
            "mode": snapshot.get("mode", "PAPER"),
            "latest_price": snapshot.get("latest_price"),
        }
