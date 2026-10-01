from __future__ import annotations


class EmergencyStop:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.events: list[str] = []

    def activate(self) -> None:
        self.enabled = True
        self.events.append("EMERGENCY_STOP_ACTIVATED")

    def deactivate(self) -> None:
        self.enabled = False
        self.events.append("EMERGENCY_STOP_DEACTIVATED")

    def block_new_entries(self) -> bool:
        return self.enabled

    def record(self, reason: str) -> None:
        self.events.append(reason)
