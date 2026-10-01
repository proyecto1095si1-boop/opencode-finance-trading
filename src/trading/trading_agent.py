from __future__ import annotations

from typing import Any

from trading.analysis.decision_explainer import DecisionExplainer
from trading.analysis.market_structure import MarketStructureAnalyzer
from trading.audit import AuditLogger
from trading.config import TradingConfig
from trading.execution.dynamic_stop import DynamicStopEngine
from trading.execution.entry_engine import EntryEngine
from trading.execution.execution_engine import ExecutionEngine
from trading.execution.order_manager import OrderIntent
from trading.execution.risk_manager import RiskManager
from trading.paper_trading import PaperTradingEngine
from trading.position_monitor import PositionMonitor, PositionState
from trading.state_machine import TradeState
from trading.strategy.strategy_engine import StrategyEngine


class TradingAgent:
    def __init__(self, config: TradingConfig | None = None):
        self.config = config or TradingConfig()
        self.market_structure = MarketStructureAnalyzer(
            swing_length=self.config.swing_length,
            confirmation_candles=self.config.confirmation_candles,
            minimum_swing_distance=self.config.minimum_swing_distance,
            minimum_structure_move=self.config.minimum_structure_move,
        )
        self.entry_engine = EntryEngine(
            analyzer=self.market_structure,
            risk_manager=RiskManager(
                max_risk_per_trade=self.config.max_risk_per_trade,
                max_daily_loss=self.config.max_daily_loss,
                max_open_positions=self.config.max_open_positions,
                max_position_size=self.config.max_position_size,
                max_leverage=self.config.max_leverage,
                max_consecutive_losses=self.config.max_consecutive_losses,
                cooldown_after_loss=self.config.cooldown_after_loss,
                account_balance=self.config.capital,
            ),
        )
        self.dynamic_stop = DynamicStopEngine(stop_mode=self.config.stop_mode)
        self.paper_trading = PaperTradingEngine(initial_balance=self.config.capital)
        self.execution = ExecutionEngine(config=self.config)
        self.strategy = StrategyEngine(analyzer=self.market_structure)
        self.position_monitor = PositionMonitor(self.dynamic_stop)
        self.audit = AuditLogger(name="trading-agent")
        self.state = TradeState.DETECTED

    def approve_live(self, approved: bool = True) -> bool:
        self.config.live_manual_approval = approved
        self.config.live_enabled = approved
        self.audit.record("LIVE_APPROVAL", approved=approved, mode=self.config.mode)
        return approved

    def analyze_market(self, candles: list) -> dict[str, Any]:
        signal = self.market_structure.detect_signal(candles)
        self.state = TradeState.SIGNAL_CONFIRMED if signal["signal"] != "NONE" else TradeState.DETECTED
        self.audit.record("MARKET_ANALYSIS", signal=signal)
        return signal

    def analyze_binance_snapshot(self, client: Any, symbol: str | None = None, timeframe: str | None = None, limit: int = 100) -> dict[str, Any]:
        from trading.market_data import MarketDataService

        selected_symbol = symbol or self.config.default_symbol
        selected_timeframe = timeframe or self.config.default_timeframe
        raw_klines = client.get_klines(selected_symbol, selected_timeframe, limit)
        market_data = MarketDataService.from_binance_klines(raw_klines, selected_symbol, selected_timeframe)
        plan = self.run_analysis_cycle(
            market_data.candles,
            symbol=selected_symbol,
            capital=self.config.capital,
            risk_percent=self.config.max_risk_per_trade * 100,
        )
        plan["market_snapshot"] = market_data.get_snapshot()
        return plan

    def prepare_order(self, candles: list, side: str, entry_price: float, capital: float | None = None) -> dict[str, Any]:
        capital = capital if capital is not None else self.config.capital
        result = self.entry_engine.evaluate_signal(candles, entry_price, side, capital)
        self.audit.record("ENTRY_PREPARED", result=result, side=side, entry_price=entry_price)
        if result.get("allowed"):
            self.state = TradeState.ENTRY_PENDING
        return result

    def explain_decision(self, signal: str, entry: float, stop: float, risk: float, reason: str, symbol: str = "BTCUSDT") -> dict[str, str | float]:
        return DecisionExplainer.explain_signal(signal, entry, stop, risk, reason, symbol)

    def monitor_position(self, position: PositionState, current_price: float, structural_level: float | None = None, atr: float | None = None) -> dict[str, Any]:
        decision = self.position_monitor.evaluate(position, current_price, structural_level, atr)
        self.audit.record(
            "POSITION_MONITORED",
            trade_id=position.trade_id,
            symbol=position.symbol,
            side=position.side,
            current_price=current_price,
            decision=decision,
        )
        return decision

    def run_analysis_cycle(self, candles: list, symbol: str = "BTCUSDT", capital: float = 10000, risk_percent: float = 1.0, higher_timeframe_candles: list | None = None) -> dict[str, Any]:
        strategy_result = self.strategy.build_trade_plan(
            candles,
            risk_percent=risk_percent,
            higher_timeframe_candles=higher_timeframe_candles,
        )
        if strategy_result["signal"] == "NONE":
            self.audit.record("NO_SIGNAL", structure=strategy_result.get("structure"), symbol=symbol)
            return {
                "signal": "NONE",
                "status": strategy_result.get("status", "neutral"),
                "symbol": symbol,
                "reason": strategy_result["reason"],
                "market_regime": strategy_result.get("market_regime"),
                "higher_timeframe": strategy_result.get("higher_timeframe"),
            }

        entry = strategy_result["entry"]
        stop = strategy_result["stop_loss"]
        target = strategy_result["take_profit"]
        ok, reason, risk_result = self.entry_engine.risk_manager.evaluate_trade(
            entry_price=entry,
            stop_loss=stop,
            risk_percent=risk_percent,
            capital=capital,
        )

        if not ok:
            self.audit.record("RISK_REJECTED", signal=strategy_result["signal"], stop=stop, entry=entry, reason=reason)
            return {
                "signal": strategy_result["signal"],
                "status": "REJECTED",
                "symbol": symbol,
                "entry": entry,
                "stop_loss": stop,
                "take_profit": target,
                "risk_percent": risk_percent,
                "reason": reason,
                "risk": risk_result,
            }

        plan = {
            "signal": strategy_result["signal"],
            "status": "SIGNAL_CONFIRMED",
            "symbol": symbol,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
            "risk_percent": risk_percent,
            "risk": risk_result,
            "reason": strategy_result["reason"],
            "structure": strategy_result["structure"],
            "atr": strategy_result["atr"],
            "volume_ratio": strategy_result["volume_ratio"],
            "market_regime": strategy_result["market_regime"],
            "higher_timeframe": strategy_result["higher_timeframe"],
            "quality_score": strategy_result["quality_score"],
        }
        self.audit.record("ANALYSIS_CYCLE", plan=plan)
        self.state = TradeState.SIGNAL_CONFIRMED
        return plan

    def _guard_execution(self, order: OrderIntent) -> tuple[bool, str]:
        if self.config.emergency_stop:
            return False, "Emergency stop is active. No new positions allowed."
        if self.config.mode == "LIVE" and not self.config.live_is_authorized:
            return False, "LIVE mode is blocked. Explicit manual approval is required."
        if self.config.mode == "ANALYSIS":
            return False, "ANALYSIS mode can inspect only; no execution is allowed."
        if self.config.mode not in {"PAPER", "TESTNET", "LIVE"}:
            return False, "Unsupported execution mode."
        if not order.stop_loss:
            return False, "Execution rejected: stop-loss is required."
        closed = self.paper_trading.closed_trades
        daily_pnl = sum(trade.get("pnl", 0.0) for trade in closed)
        consecutive_losses = 0
        for trade in reversed(closed):
            if trade.get("pnl", 0.0) >= 0:
                break
            consecutive_losses += 1
        portfolio_ok, portfolio_reason = self.entry_engine.risk_manager.evaluate_portfolio(
            open_positions=len(self.paper_trading.positions),
            daily_pnl=daily_pnl,
            consecutive_losses=consecutive_losses,
            cooldown_active=False,
        )
        if not portfolio_ok:
            return False, portfolio_reason
        return True, "OK"

    def execute(self, order: OrderIntent) -> dict[str, Any]:
        allowed, reason = self._guard_execution(order)
        if not allowed:
            self.audit.record("EXECUTION_REJECTED", order=order.__dict__, reason=reason)
            self.state = TradeState.REJECTED
            return {"accepted": False, "reason": reason, "order": order.__dict__}

        if self.config.mode == "PAPER":
            result = {
                "accepted": True,
                "execution": "paper",
                "order": self.paper_trading.open_position(
                    symbol=order.symbol,
                    side=order.side,
                    entry=order.price or 0,
                    stop_loss=order.stop_loss or 0,
                    take_profit=order.take_profit or 0,
                    position_size=order.quantity,
                    risk=order.risk,
                    strategy="agent",
                ),
            }
            self.state = TradeState.ENTERED
            self.audit.record("PAPER_EXECUTION", result=result)
            return result
        if self.config.mode in {"TESTNET", "LIVE"}:
            result = self.execution.execute(order)
            self.state = TradeState.ENTERED if result.get("accepted") else TradeState.REJECTED
            self.audit.record("EXCHANGE_EXECUTION", result=result)
            return result
        return {"accepted": False, "reason": "Only PAPER, TESTNET, or LIVE may execute trades."}

    @property
    def live_blocked(self) -> bool:
        return self.config.mode == "LIVE" and not self.config.live_is_authorized
