from __future__ import annotations

from typing import Any

from trading.analysis.market_structure import MarketStructureAnalyzer
from trading.market_data import Candle
from trading.paper_trading import PaperTradingEngine


class BacktestEngine:
    def __init__(self, analyzer: MarketStructureAnalyzer | None = None):
        self.analyzer = analyzer or MarketStructureAnalyzer()

    def run(self, candles: list[Candle], initial_balance: float = 10000.0) -> dict[str, Any]:
        engine = PaperTradingEngine(initial_balance=initial_balance)
        for candle in candles:
            signal = self.analyzer.detect_signal(candles[: candles.index(candle) + 1])
            if signal["signal"] == "LONG":
                engine.open_position(
                    symbol=candle.symbol,
                    side="LONG",
                    entry=candle.close,
                    stop_loss=candle.low,
                    take_profit=candle.close * 1.02,
                    position_size=1,
                    risk=50,
                    strategy="backtest",
                )
            elif signal["signal"] == "SHORT":
                engine.open_position(
                    symbol=candle.symbol,
                    side="SHORT",
                    entry=candle.close,
                    stop_loss=candle.high,
                    take_profit=candle.close * 0.98,
                    position_size=1,
                    risk=50,
                    strategy="backtest",
                )
            engine.tick(candle.close)

        summary = engine.summary()
        summary["total_trades"] = len(engine.closed_trades)
        summary["fee_cost"] = 0.0
        summary["slippage_cost"] = 0.0
        return summary
