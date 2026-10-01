from __future__ import annotations


class RiskManager:
    def __init__(
        self,
        max_risk_per_trade: float = 0.01,
        max_daily_loss: float = 0.05,
        max_open_positions: int = 3,
        max_position_size: float = 5000,
        max_leverage: float = 3,
        max_consecutive_losses: int = 3,
        cooldown_after_loss: int = 30,
        account_balance: float = 10000,
    ):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_open_positions = max_open_positions
        self.max_position_size = max_position_size
        self.max_leverage = max_leverage
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_after_loss = cooldown_after_loss
        self.account_balance = account_balance

    def evaluate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        risk_percent: float,
        capital: float,
        max_position_size: float | None = None,
        max_leverage: float | None = None,
    ) -> tuple[bool, str, dict]:
        distance = abs(entry_price - stop_loss)
        if distance <= 0:
            return False, "Stop-loss distance must be greater than zero.", {}
        if risk_percent <= 0:
            return False, "Risk percent must be positive.", {}
        if risk_percent > (self.max_risk_per_trade * 100):
            return False, "Risk exceeds the configured per-trade limit.", {}

        risk_amount = capital * (risk_percent / 100.0)
        position_size = risk_amount / distance
        max_size = max_position_size if max_position_size is not None else self.max_position_size
        max_lev = max_leverage if max_leverage is not None else self.max_leverage
        if position_size > max_size:
            return False, "Position size exceeds the configured maximum.", {}
        if max_lev <= 0:
            return False, "Leverage must be positive.", {}

        return True, "OK", {
            "risk_amount": risk_amount,
            "position_size": position_size,
            "risk_percent": risk_percent,
            "distance": distance,
            "capital": capital,
            "max_position_size": max_size,
            "max_leverage": max_lev,
        }

    def check_daily_loss(self, daily_pnl: float) -> bool:
        return daily_pnl >= -(self.max_daily_loss * self.account_balance)

    def evaluate_portfolio(
        self,
        open_positions: int,
        daily_pnl: float,
        consecutive_losses: int,
        cooldown_active: bool,
    ) -> tuple[bool, str]:
        if open_positions >= self.max_open_positions:
            return False, "Maximum open positions reached."
        if not self.check_daily_loss(daily_pnl):
            return False, "Maximum daily loss reached."
        if consecutive_losses >= self.max_consecutive_losses:
            return False, "Maximum consecutive losses reached."
        if cooldown_active:
            return False, "Loss cooldown is active."
        return True, "OK"
