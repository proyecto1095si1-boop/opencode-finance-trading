from __future__ import annotations

from typing import Any

from trading.analysis.market_structure import MarketStructureAnalyzer
from trading.execution.dynamic_stop import DynamicStopEngine
from trading.execution.risk_manager import RiskManager


class EntryEngine:
    def __init__(
        self,
        analyzer: MarketStructureAnalyzer | None = None,
        risk_manager: RiskManager | None = None,
        dynamic_stop: DynamicStopEngine | None = None,
    ):
        self.analyzer = analyzer or MarketStructureAnalyzer()
        self.risk_manager = risk_manager or RiskManager()
        self.dynamic_stop = dynamic_stop or DynamicStopEngine()

    def evaluate_signal(self, candles: list, entry_price: float, side: str, capital: float = 10000) -> dict[str, Any]:
        signal = self.analyzer.detect_signal(candles)
        if signal["signal"] == "NONE":
            return {"allowed": False, "reason": "No valid directional structure."}

        if signal["signal"] != side:
            return {"allowed": False, "reason": f"Signal {signal['signal']} does not match requested side {side}."}

        structural_low = signal["structure"].get("recent_low")
        structural_high = signal["structure"].get("recent_high")
        stop = self.dynamic_stop.initial_stop(side, entry_price, structural_low, structural_high)
        ok, reason, risk_result = self.risk_manager.evaluate_trade(
            entry_price=entry_price,
            stop_loss=stop,
            risk_percent=1.0,
            capital=capital,
        )
        if not ok:
            return {"allowed": False, "reason": reason, "risk": risk_result}

        return {
            "allowed": True,
            "signal": signal,
            "stop_loss": stop,
            "risk": risk_result,
            "strategy": "example_structure_breakout",
            "reason": "Bullish or bearish market structure was confirmed before entry.",
        }
