from __future__ import annotations

from enum import Enum


class TradeState(str, Enum):
    DETECTED = "DETECTED"
    SIGNAL_CONFIRMED = "SIGNAL_CONFIRMED"
    ENTRY_PENDING = "ENTRY_PENDING"
    ENTERED = "ENTERED"
    PROTECTED = "PROTECTED"
    PROFIT_RUNNING = "PROFIT_RUNNING"
    STOP_UPDATED = "STOP_UPDATED"
    PARTIAL_EXIT = "PARTIAL_EXIT"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"

    @classmethod
    def allowed_transitions(cls, current: "TradeState") -> set["TradeState"]:
        mapping = {
            cls.DETECTED: {cls.SIGNAL_CONFIRMED, cls.REJECTED},
            cls.SIGNAL_CONFIRMED: {cls.ENTRY_PENDING, cls.REJECTED},
            cls.ENTRY_PENDING: {cls.ENTERED, cls.REJECTED, cls.CANCELLED},
            cls.ENTERED: {cls.PROTECTED, cls.ERROR},
            cls.PROTECTED: {cls.PROFIT_RUNNING, cls.STOP_UPDATED, cls.ERROR},
            cls.PROFIT_RUNNING: {cls.STOP_UPDATED, cls.PARTIAL_EXIT, cls.CLOSED},
            cls.STOP_UPDATED: {cls.PROFIT_RUNNING, cls.CLOSED},
            cls.PARTIAL_EXIT: {cls.CLOSED, cls.PROFIT_RUNNING},
            cls.CLOSED: set(),
            cls.REJECTED: set(),
            cls.CANCELLED: set(),
            cls.ERROR: {cls.EMERGENCY_STOP},
            cls.EMERGENCY_STOP: {cls.CLOSED},
        }
        return mapping.get(current, set())

    def transition(self, next_state: "TradeState") -> bool:
        return next_state in self.allowed_transitions(self)
