from __future__ import annotations

from typing import Any

from trading.analysis.candle_analyzer import CandleAnalyzer
from trading.analysis.market_structure import MarketStructureAnalyzer
from trading.market_data import Candle


class MarketRegimeAnalyzer:
    def __init__(self, structure: MarketStructureAnalyzer | None = None):
        self.structure = structure or MarketStructureAnalyzer()

    def analyze(self, candles: list[Candle]) -> dict[str, Any]:
        structure = self.structure.analyze(candles)
        atr = CandleAnalyzer.atr(candles)
        price = candles[-1].close if candles else 0.0
        volatility_ratio = atr / price if price else 0.0
        trend = structure["trend"]
        if trend == "bullish":
            regime = "HIGH_VOLATILITY_BULLISH" if volatility_ratio >= 0.03 else "BULLISH"
        elif trend == "bearish":
            regime = "HIGH_VOLATILITY_BEARISH" if volatility_ratio >= 0.03 else "BEARISH"
        else:
            regime = "HIGH_VOLATILITY_RANGE" if volatility_ratio >= 0.03 else "RANGE"
        return {
            "regime": regime,
            "trend": trend,
            "atr": atr,
            "volatility_ratio": volatility_ratio,
            "structure": structure,
        }