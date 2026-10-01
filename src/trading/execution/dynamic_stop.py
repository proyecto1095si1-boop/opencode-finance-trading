from __future__ import annotations

class DynamicStopEngine:
    def __init__(self, stop_mode: str = "STRUCTURE_ATR", atr_multiplier: float = 1.5):
        self.stop_mode = stop_mode
        self.atr_multiplier = atr_multiplier

    def update_long_stop(
        self,
        entry: float,
        current_stop: float,
        higher_high: float | None = None,
        higher_low: float | None = None,
        latest_price: float | None = None,
        atr_value: float | None = None,
    ) -> float:
        if current_stop <= 0:
            return entry

        candidate = current_stop
        if higher_low is not None:
            candidate = max(candidate, higher_low)
        if latest_price is not None and higher_high is not None:
            candidate = max(candidate, latest_price * 0.999)
        if atr_value is not None and self.stop_mode in {"ATR", "STRUCTURE_ATR"}:
            atr_stop = latest_price - (atr_value * self.atr_multiplier) if latest_price is not None else current_stop
            candidate = max(candidate, atr_stop)
        return float(max(current_stop, candidate))

    def update_short_stop(
        self,
        entry: float,
        current_stop: float,
        lower_low: float | None = None,
        lower_high: float | None = None,
        latest_price: float | None = None,
        atr_value: float | None = None,
    ) -> float:
        if current_stop <= 0:
            return entry

        candidate = current_stop
        if lower_high is not None:
            candidate = min(candidate, lower_high)
        if latest_price is not None and lower_low is not None:
            candidate = min(candidate, latest_price * 1.001)
        if atr_value is not None and self.stop_mode in {"ATR", "STRUCTURE_ATR"}:
            atr_stop = latest_price + (atr_value * self.atr_multiplier) if latest_price is not None else current_stop
            candidate = min(candidate, atr_stop)
        return float(min(current_stop, candidate))

    def initial_stop(self, side: str, entry: float, structural_low: float | None = None, structural_high: float | None = None) -> float:
        if side == "LONG":
            if structural_low is None:
                return entry * 0.98
            return max(structural_low * 0.995, entry * 0.98)
        if side == "SHORT":
            if structural_high is None:
                return entry * 1.02
            return min(structural_high * 1.005, entry * 1.02)
        raise ValueError(f"Unsupported side: {side}")

    def break_even_stop(self, entry: float, side: str, r_multiple: float) -> float:
        if side == "LONG":
            return entry
        if side == "SHORT":
            return entry
        raise ValueError(f"Unsupported side: {side}")

    def apply_break_even(
        self,
        entry: float,
        current_stop: float,
        achieved_r: float,
        side: str,
        initial_stop: float,
        trigger_r: float = 1.0,
    ) -> float:
        if achieved_r < trigger_r:
            return current_stop
        breakeven = self.break_even_stop(entry, side, achieved_r)
        if side == "LONG":
            return max(current_stop, breakeven)
        if side == "SHORT":
            return min(current_stop, breakeven)
        raise ValueError(f"Unsupported side: {side}")
