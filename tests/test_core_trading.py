from trading.analysis.market_structure import MarketStructureAnalyzer
from trading.analysis.candle_analyzer import CandleAnalyzer
from trading.browser.binance_browser import BinanceBrowser
from trading.config import TradingConfig
from trading.execution.dynamic_stop import DynamicStopEngine
from trading.execution.order_manager import OrderIntent
from trading.execution.risk_manager import RiskManager
from trading.market_data import Candle
from trading.position_monitor import PositionMonitor, PositionState
from trading.paper_trading import PaperTradingEngine
from trading.state_machine import TradeState
from trading.trading_agent import TradingAgent


def test_detects_higher_high_and_higher_low():
    candles = [
        Candle(1, 100, 101, 99, 100, 10),
        Candle(2, 101, 103, 100, 102, 12),
        Candle(3, 103, 105, 102, 104, 14),
        Candle(4, 104, 108, 103, 107, 15),
    ]
    analyzer = MarketStructureAnalyzer(swing_length=2, confirmation_candles=1, minimum_swing_distance=1, minimum_structure_move=0.5)
    structure = analyzer.analyze(candles)

    assert structure["trend"] == "bullish"
    assert structure["higher_highs"] >= 1
    assert structure["higher_lows"] >= 1


def test_detects_lower_low_and_lower_high():
    candles = [
        Candle(1, 110, 112, 109, 111, 10),
        Candle(2, 111, 111.5, 108, 108.5, 12),
        Candle(3, 108.5, 109, 104, 105, 14),
        Candle(4, 105, 106, 100, 101, 15),
    ]
    analyzer = MarketStructureAnalyzer(swing_length=2, confirmation_candles=1, minimum_swing_distance=1, minimum_structure_move=0.5)
    structure = analyzer.analyze(candles)

    assert structure["trend"] == "bearish"
    assert structure["lower_lows"] >= 1
    assert structure["lower_highs"] >= 1


def test_dynamic_long_stop_only_moves_up():
    engine = DynamicStopEngine(stop_mode="STRUCTURE_ATR")
    entry = 100.0
    initial_stop = 97.0

    updated = engine.update_long_stop(entry, initial_stop, 105.0, 102.0, 103.0)
    assert updated > initial_stop

    updated_2 = engine.update_long_stop(entry, updated, 110.0, 106.0, 108.0)
    assert updated_2 >= updated


def test_dynamic_short_stop_only_moves_down():
    engine = DynamicStopEngine(stop_mode="STRUCTURE_ATR")
    entry = 100.0
    initial_stop = 103.0

    updated = engine.update_short_stop(entry, initial_stop, 95.0, 97.0, 96.0)
    assert updated < initial_stop

    updated_2 = engine.update_short_stop(entry, updated, 92.0, 94.0, 93.0)
    assert updated_2 <= updated


def test_risk_manager_rejects_excessive_risk():
    rm = RiskManager(max_risk_per_trade=0.01, account_balance=10000)
    ok, reason, result = rm.evaluate_trade(
        entry_price=100,
        stop_loss=97,
        risk_percent=1.0,
        capital=10000,
    )

    assert ok is True
    assert result["position_size"] > 0

    ok_2, _, _ = rm.evaluate_trade(
        entry_price=100,
        stop_loss=50,
        risk_percent=10.0,
        capital=10000,
    )
    assert ok_2 is False


def test_paper_trading_executes_with_stop_and_tp():
    engine = PaperTradingEngine(initial_balance=10000)
    trade = engine.open_position(
        symbol="BTCUSDT",
        side="LONG",
        entry=100,
        stop_loss=97,
        take_profit=106,
        position_size=2,
        risk=100,
        strategy="demo",
    )

    assert trade["side"] == "LONG"
    assert trade["stop_loss"] == 97
    assert trade["take_profit"] == 106
    assert trade["position_size"] == 2

    closed = engine.tick(106)
    assert len(closed) >= 1


def test_live_trade_is_blocked_without_manual_approval():
    config = TradingConfig(mode="LIVE", live_enabled=False, live_manual_approval=False)
    agent = TradingAgent(config=config)
    assert agent.live_blocked is True

    result = agent.execute(OrderIntent(symbol="BTCUSDT", side="LONG", quantity=0.1, price=100, stop_loss=97, take_profit=105, risk=10))
    assert result["accepted"] is False


def test_state_machine_uses_strict_transitions():
    assert TradeState.DETECTED.transition(TradeState.SIGNAL_CONFIRMED) is True
    assert TradeState.DETECTED.transition(TradeState.REJECTED) is True
    assert TradeState.REJECTED.transition(TradeState.ENTERED) is False


def test_analysis_cycle_builds_trade_plan_from_market_structure():
    candles = [
        Candle(1, 100, 101, 99, 100, 10, "15m", "BTCUSDT"),
        Candle(2, 101, 103, 100, 102, 12, "15m", "BTCUSDT"),
        Candle(3, 103, 106, 101, 105, 14, "15m", "BTCUSDT"),
        Candle(4, 105, 108, 104, 107, 15, "15m", "BTCUSDT"),
        Candle(5, 107, 110, 106, 109, 16, "15m", "BTCUSDT"),
    ]
    agent = TradingAgent(config=TradingConfig(mode="PAPER", live_enabled=False))
    plan = agent.run_analysis_cycle(candles, symbol="BTCUSDT", capital=10000)

    assert plan["signal"] == "LONG"
    assert plan["entry"] > 0
    assert plan["stop_loss"] > 0
    assert plan["risk_percent"] > 0


def test_dynamic_stop_break_even_and_structure_never_worsen_protection():
    engine = DynamicStopEngine(stop_mode="STRUCTURE_ATR")

    long_stop = engine.update_long_stop(100, 97, higher_low=103, latest_price=105)
    assert long_stop >= 103
    assert engine.apply_break_even(100, 100, 1.0, "LONG", 97) == 100

    short_stop = engine.update_short_stop(100, 103, lower_high=97, latest_price=95)
    assert short_stop <= 97
    assert engine.apply_break_even(100, 100, 1.0, "SHORT", 103) == 100


def test_paper_trading_supports_partial_exit_and_fees():
    engine = PaperTradingEngine(initial_balance=10000, commission_rate=0.001, slippage=0.0)
    engine.open_position("BTCUSDT", "LONG", 100, 95, 110, 10, 50, "demo")

    partial = engine.partial_exit("paper-1", 0.25, 105)
    assert partial["closed_quantity"] == 2.5
    assert partial["pnl"] > 0
    assert len(engine.positions) == 1
    assert engine.positions[0]["position_size"] == 7.5
    assert engine.summary()["fees"] > 0


def test_browser_blocks_order_selectors_without_confirmation():
    assert BinanceBrowser._is_order_action("button[data-testid='buy-button']") is True
    assert BinanceBrowser._is_order_action("input[name='quantity']") is False


def test_portfolio_risk_blocks_daily_loss_streak_and_position_limit():
    rm = RiskManager(
        max_daily_loss=0.05,
        max_open_positions=2,
        max_consecutive_losses=2,
        account_balance=10000,
    )

    allowed, reason = rm.evaluate_portfolio(open_positions=2, daily_pnl=0, consecutive_losses=0, cooldown_active=False)
    assert allowed is False
    assert "positions" in reason.lower()

    allowed, reason = rm.evaluate_portfolio(open_positions=0, daily_pnl=-600, consecutive_losses=0, cooldown_active=False)
    assert allowed is False
    assert "daily" in reason.lower()

    allowed, reason = rm.evaluate_portfolio(open_positions=0, daily_pnl=0, consecutive_losses=2, cooldown_active=False)
    assert allowed is False
    assert "loss" in reason.lower()


def test_position_monitor_protects_long_and_rejects_worsening_stop():
    monitor = PositionMonitor()
    position = PositionState(
        trade_id="paper-1",
        symbol="BTCUSDT",
        side="LONG",
        entry=100,
        initial_stop=97,
        current_stop=97,
        quantity=1,
    )

    update = monitor.evaluate(position, current_price=105, structural_level=102, atr=2)
    assert update["action"] == "UPDATE_STOP"
    assert update["new_stop"] > 97

    position.current_stop = update["new_stop"]
    worsening = monitor.evaluate(position, current_price=104, structural_level=99, atr=2)
    assert worsening["action"] == "HOLD"
    assert worsening["new_stop"] == position.current_stop


def test_position_monitor_detects_short_invalidation():
    monitor = PositionMonitor()
    position = PositionState(
        trade_id="paper-2",
        symbol="BTCUSDT",
        side="SHORT",
        entry=100,
        initial_stop=103,
        current_stop=101,
        quantity=1,
    )

    decision = monitor.evaluate(position, current_price=102, structural_level=104, atr=2)
    assert decision["action"] == "CLOSE_INVALIDATED"


def test_candle_analyzer_calculates_atr_rsi_and_volume_ratio():
    candles = [
        Candle(1, 100, 104, 98, 103, 10),
        Candle(2, 103, 108, 101, 107, 20),
        Candle(3, 107, 111, 105, 109, 30),
    ]

    assert CandleAnalyzer.atr(candles, window=2) > 0
    assert 0 <= CandleAnalyzer.rsi(candles, window=2) <= 100
    assert CandleAnalyzer.volume_ratio(candles, window=2) > 1


def test_trade_plan_reports_quality_and_higher_timeframe_alignment():
    primary = [
        Candle(1, 100, 101, 99, 100, 10, "15m", "BTCUSDT"),
        Candle(2, 101, 103, 100, 102, 12, "15m", "BTCUSDT"),
        Candle(3, 103, 106, 101, 105, 14, "15m", "BTCUSDT"),
        Candle(4, 105, 108, 104, 107, 15, "15m", "BTCUSDT"),
        Candle(5, 107, 110, 106, 109, 16, "15m", "BTCUSDT"),
    ]
    higher = [
        Candle(1, 90, 95, 88, 94, 100, "1h", "BTCUSDT"),
        Candle(2, 94, 100, 92, 99, 120, "1h", "BTCUSDT"),
        Candle(3, 99, 106, 97, 105, 140, "1h", "BTCUSDT"),
        Candle(4, 105, 112, 103, 111, 150, "1h", "BTCUSDT"),
    ]
    agent = TradingAgent(config=TradingConfig(mode="PAPER", live_enabled=False))
    plan = agent.run_analysis_cycle(primary, symbol="BTCUSDT", capital=10000, higher_timeframe_candles=higher)

    assert plan["signal"] == "LONG"
    assert plan["quality_score"] >= 0.5
    assert plan["market_regime"] in {"BULLISH", "HIGH_VOLATILITY_BULLISH"}
