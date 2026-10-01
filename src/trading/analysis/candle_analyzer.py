from __future__ import annotations

from math import isfinite
from typing import Any

from trading.market_data import Candle


class CandleAnalyzer:
    """Utilities for interpretation of individual candlesticks and short sequences."""

    @staticmethod
    def analyze(candle: Candle) -> dict[str, Any]:
        return {
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "body": candle.body,
            "wick_up": candle.wick_up,
            "wick_down": candle.wick_down,
            "range": candle.range,
            "bullish": candle.is_bullish,
            "bearish": candle.is_bearish,
            "type": "bullish" if candle.is_bullish else "bearish",
        }

    @staticmethod
    def volatility(candles: list[Candle]) -> float:
        if not candles:
            return 0.0
        ranges = [c.range for c in candles]
        return sum(ranges) / len(ranges)

    @staticmethod
    def true_range(candles: list[Candle]) -> list[float]:
        if not candles:
            return []
        values = [candles[0].range]
        for previous, current in zip(candles, candles[1:]):
            values.append(max(current.range, abs(current.high - previous.close), abs(current.low - previous.close)))
        return values

    @classmethod
    def atr(cls, candles: list[Candle], window: int = 14) -> float:
        if window <= 0:
            raise ValueError("window must be positive")
        ranges = cls.true_range(candles)
        if not ranges:
            return 0.0
        selected = ranges[-window:]
        return sum(selected) / len(selected)

    @staticmethod
    def rsi(candles: list[Candle], window: int = 14) -> float:
        if window <= 0:
            raise ValueError("window must be positive")
        changes = [current.close - previous.close for previous, current in zip(candles, candles[1:])]
        selected = changes[-window:]
        gains = sum(change for change in selected if change > 0)
        losses = sum(abs(change) for change in selected if change < 0)
        if losses == 0:
            return 100.0 if gains else 50.0
        relative_strength = gains / losses
        return 100.0 - (100.0 / (1.0 + relative_strength))

    @staticmethod
    def volume_ratio(candles: list[Candle], window: int = 20) -> float:
        if not candles or window <= 0:
            return 0.0
        baseline = candles[-window:]
        average = sum(candle.volume for candle in baseline) / len(baseline)
        return candles[-1].volume / average if average else 0.0

    @staticmethod
    def moving_average(values: list[float], window: int = 3) -> float:
        if not values:
            return 0.0
        if window <= 0:
            raise ValueError("window must be positive")
        data = values[-window:]
        return sum(data) / len(data)

    @staticmethod
    def is_valid_candle(candle: Candle) -> bool:
        return all(
            isfinite(value)
            for value in [candle.open, candle.high, candle.low, candle.close, candle.volume]
        )
