from __future__ import annotations

from trading.analysis.market_structure import MarketStructureAnalyzer
from trading.analysis.candle_analyzer import CandleAnalyzer
from trading.analysis.market_regime import MarketRegimeAnalyzer


class StrategyEngine:
    def __init__(self, analyzer: MarketStructureAnalyzer | None = None):
        self.analyzer = analyzer or MarketStructureAnalyzer()
        self.regime_analyzer = MarketRegimeAnalyzer(self.analyzer)

    def evaluate(self, candles):
        signal = self.analyzer.detect_signal(candles)
        if signal["signal"] == "LONG":
            return {
                "direction": "LONG",
                "confidence": 0.7,
                "reason": signal["reason"],
                "structure": signal["structure"],
            }
        if signal["signal"] == "SHORT":
            return {
                "direction": "SHORT",
                "confidence": 0.7,
                "reason": signal["reason"],
                "structure": signal["structure"],
            }
        return {
            "direction": "NONE",
            "confidence": 0.0,
            "reason": "No directional confirmation.",
            "structure": signal["structure"],
        }

    def build_trade_plan(self, candles, entry_price: float | None = None, risk_percent: float = 1.0, higher_timeframe_candles=None):
        signal = self.analyzer.detect_signal(candles)
        if signal["signal"] == "NONE":
            return {"signal": "NONE", "status": "neutral", "reason": "No valid directional structure."}

        market_regime = self.regime_analyzer.analyze(candles)
        higher_regime = self.regime_analyzer.analyze(higher_timeframe_candles) if higher_timeframe_candles else None
        higher_alignment = True
        if higher_regime:
            higher_alignment = higher_regime["trend"] == market_regime["trend"]
            if not higher_alignment:
                return {
                    "signal": "NONE",
                    "status": "FILTERED",
                    "reason": "Primary and higher-timeframe structures disagree.",
                    "market_regime": market_regime["regime"],
                    "higher_timeframe": higher_regime,
                }

        entry = entry_price if entry_price is not None else candles[-1].close
        recent_low = signal["structure"].get("recent_low")
        recent_high = signal["structure"].get("recent_high")
        atr = market_regime["atr"]
        volume_ratio = CandleAnalyzer.volume_ratio(candles)

        if signal["signal"] == "LONG":
            structural_stop = recent_low if recent_low is not None else entry * 0.99
            stop = min(entry * 0.995, structural_stop, entry - (atr * 1.5))
            target = entry + ((entry - stop) * 2.0)
        else:
            structural_stop = recent_high if recent_high is not None else entry * 1.01
            stop = max(entry * 1.005, structural_stop, entry + (atr * 1.5))
            target = entry - ((stop - entry) * 2.0)

        quality_score = 0.5
        if volume_ratio >= 1.0:
            quality_score += 0.15
        if higher_alignment:
            quality_score += 0.2
        if market_regime["regime"] not in {"RANGE", "HIGH_VOLATILITY_RANGE"}:
            quality_score += 0.15

        return {
            "signal": signal["signal"],
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
            "risk_percent": risk_percent,
            "structure": signal["structure"],
            "reason": signal["reason"],
            "atr": atr,
            "volume_ratio": volume_ratio,
            "market_regime": market_regime["regime"],
            "higher_timeframe": higher_regime,
            "quality_score": min(quality_score, 1.0),
        }
