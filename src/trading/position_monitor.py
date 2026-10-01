from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trading.execution.dynamic_stop import DynamicStopEngine


@dataclass
class PositionState:
    trade_id: str
    symbol: str
    side: str
    entry: float
    initial_stop: float
    current_stop: float
    quantity: float
    break_even_trigger_r: float = 1.0
    invalidated: bool = False


class PositionMonitor:
    def __init__(self, stop_engine: DynamicStopEngine | None = None):
        self.stop_engine = stop_engine or DynamicStopEngine(stop_mode="STRUCTURE_ATR")

    def evaluate(
        self,
        position: PositionState,
        current_price: float,
        structural_level: float | None = None,
        atr: float | None = None,
    ) -> dict[str, Any]:
        if position.quantity <= 0:
            return {"action": "CLOSED", "reason": "Position quantity is zero."}

        initial_risk = abs(position.entry - position.initial_stop)
        if initial_risk <= 0:
            return {"action": "ERROR", "reason": "Initial stop distance is invalid."}

        if position.side == "LONG":
            achieved_r = (current_price - position.entry) / initial_risk
            if current_price <= position.current_stop:
                return {
                    "action": "CLOSE_INVALIDATED",
                    "reason": "LONG price reached or crossed the protected stop.",
                    "stop": position.current_stop,
                }
            candidate = position.current_stop
            if structural_level is not None:
                candidate = self.stop_engine.update_long_stop(
                    position.entry,
                    candidate,
                    higher_low=structural_level,
                    latest_price=current_price,
                    atr_value=atr,
                )
            candidate = self.stop_engine.apply_break_even(
                position.entry,
                candidate,
                achieved_r,
                "LONG",
                position.initial_stop,
            )
            return self._decision(position, candidate, achieved_r)

        if position.side == "SHORT":
            achieved_r = (position.entry - current_price) / initial_risk
            if current_price >= position.current_stop:
                return {
                    "action": "CLOSE_INVALIDATED",
                    "reason": "SHORT price reached or crossed the protected stop.",
                    "stop": position.current_stop,
                }
            candidate = position.current_stop
            if structural_level is not None:
                candidate = self.stop_engine.update_short_stop(
                    position.entry,
                    candidate,
                    lower_low=structural_level,
                    latest_price=current_price,
                    atr_value=atr,
                )
            candidate = self.stop_engine.apply_break_even(
                position.entry,
                candidate,
                achieved_r,
                "SHORT",
                position.initial_stop,
            )
            return self._decision(position, candidate, achieved_r)

        return {"action": "ERROR", "reason": f"Unsupported side: {position.side}"}

    @staticmethod
    def _decision(position: PositionState, candidate: float, achieved_r: float) -> dict[str, Any]:
        if candidate == position.current_stop:
            return {
                "action": "HOLD",
                "new_stop": position.current_stop,
                "achieved_r": achieved_r,
            }
        return {
            "action": "UPDATE_STOP",
            "old_stop": position.current_stop,
            "new_stop": candidate,
            "achieved_r": achieved_r,
            "reason": "New structure or break-even protection improved the stop.",
        }