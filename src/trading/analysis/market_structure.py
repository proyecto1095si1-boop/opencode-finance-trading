from __future__ import annotations

from typing import Any

from trading.market_data import Candle


class MarketStructureAnalyzer:
    def __init__(
        self,
        swing_length: int = 3,
        confirmation_candles: int = 1,
        minimum_swing_distance: float = 0.5,
        minimum_structure_move: float = 0.5,
    ):
        self.swing_length = swing_length
        self.confirmation_candles = confirmation_candles
        self.minimum_swing_distance = minimum_swing_distance
        self.minimum_structure_move = minimum_structure_move

    def analyze(self, candles: list[Candle]) -> dict[str, Any]:
        if len(candles) < 2:
            return {
                "trend": "neutral",
                "higher_highs": 0,
                "higher_lows": 0,
                "lower_highs": 0,
                "lower_lows": 0,
                "last_higher_high": None,
                "last_higher_low": None,
                "last_lower_high": None,
                "last_lower_low": None,
            }

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        higher_highs = 0
        higher_lows = 0
        lower_highs = 0
        lower_lows = 0
        last_higher_high = None
        last_higher_low = None
        last_lower_high = None
        last_lower_low = None

        for idx in range(1, len(candles)):
            prev = candles[idx - 1]
            current = candles[idx]

            if current.high > prev.high + self.minimum_swing_distance:
                higher_highs += 1
                last_higher_high = current.high
            if current.high < prev.high - self.minimum_swing_distance:
                lower_highs += 1
                last_lower_high = current.high
            if current.low > prev.low + self.minimum_swing_distance:
                higher_lows += 1
                last_higher_low = current.low
            if current.low < prev.low - self.minimum_swing_distance:
                lower_lows += 1
                last_lower_low = current.low

        bullish = higher_highs >= self.confirmation_candles and higher_lows >= self.confirmation_candles
        bearish = lower_lows >= self.confirmation_candles and lower_highs >= self.confirmation_candles

        if bullish and not bearish:
            trend = "bullish"
        elif bearish and not bullish:
            trend = "bearish"
        else:
            trend = "neutral"

        return {
            "trend": trend,
            "higher_highs": higher_highs,
            "higher_lows": higher_lows,
            "lower_highs": lower_highs,
            "lower_lows": lower_lows,
            "last_higher_high": last_higher_high,
            "last_higher_low": last_higher_low,
            "last_lower_high": last_lower_high,
            "last_lower_low": last_lower_low,
            "recent_high": max(highs[-self.swing_length:]),
            "recent_low": min(lows[-self.swing_length:]),
            "minimum_structure_move": self.minimum_structure_move,
        }

    def detect_signal(self, candles: list[Candle]) -> dict[str, Any]:
        structure = self.analyze(candles)
        if structure["trend"] == "bullish":
            return {
                "signal": "LONG",
                "status": "signal_confirmed",
                "structure": structure,
                "reason": "Higher High and Higher Low sequence confirmed.",
            }
        if structure["trend"] == "bearish":
            return {
                "signal": "SHORT",
                "status": "signal_confirmed",
                "structure": structure,
                "reason": "Lower Low and Lower High sequence confirmed.",
            }
        return {
            "signal": "NONE",
            "status": "neutral",
            "structure": structure,
            "reason": "Structure is not sufficiently directional.",
        }
