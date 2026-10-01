from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class TradingLogger:
    def __init__(self, name: str = "trading"):
        self.name = name
        self.history: list[dict[str, Any]] = []

    def log(self, event: str, **payload: Any) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        self.history.append(record)
        return record

    def dump_json(self) -> str:
        return json.dumps(self.history, indent=2)
