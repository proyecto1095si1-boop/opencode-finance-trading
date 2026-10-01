from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class AuditLogger:
    def __init__(self, name: str = "trading"):
        self.name = name
        self.entries: list[dict[str, Any]] = []

    def record(self, event: str, **payload: Any) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        self.entries.append(entry)
        return entry

    def dump(self) -> str:
        return json.dumps(self.entries, indent=2)
