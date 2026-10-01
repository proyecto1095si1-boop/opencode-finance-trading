from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "15m"
    symbol: str = "BTCUSDT"

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def wick_up(self) -> float:
        return max(self.high - max(self.open, self.close), 0.0)

    @property
    def wick_down(self) -> float:
        return max(min(self.open, self.close) - self.low, 0.0)

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


class MarketDataService:
    def __init__(self, candles: list[Candle] | None = None):
        self.candles: list[Candle] = candles or []

    @classmethod
    def from_binance_klines(cls, klines: list[list], symbol: str = "BTCUSDT", timeframe: str = "15m") -> "MarketDataService":
        candles: list[Candle] = []
        for item in klines:
            if len(item) < 6:
                continue
            timestamp = int(item[0])
            open_price = float(item[1])
            high = float(item[2])
            low = float(item[3])
            close = float(item[4])
            volume = float(item[5])
            candles.append(
                Candle(
                    timestamp=timestamp,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    timeframe=timeframe,
                    symbol=symbol,
                )
            )
        return cls(candles)

    def add_candles(self, candles: list[Candle]) -> None:
        self.candles.extend(candles)

    def latest(self) -> Candle | None:
        return self.candles[-1] if self.candles else None

    def last_n(self, n: int) -> list[Candle]:
        return self.candles[-n:] if n > 0 else []

    def highs(self) -> list[float]:
        return [c.high for c in self.candles]

    def lows(self) -> list[float]:
        return [c.low for c in self.candles]

    def newest_price(self) -> float | None:
        candle = self.latest()
        return candle.close if candle else None

    def get_snapshot(self) -> dict[str, Any]:
        latest = self.latest()
        return {
            "count": len(self.candles),
            "latest_price": latest.close if latest else None,
            "latest_timestamp": latest.timestamp if latest else None,
            "timeframe": latest.timeframe if latest else "15m",
        }
