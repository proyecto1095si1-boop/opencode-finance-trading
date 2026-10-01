from __future__ import annotations

from typing import Any


class PaperTradingEngine:
    def __init__(self, initial_balance: float = 10000.0, commission_rate: float = 0.0005, slippage: float = 0.0001):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.positions: list[dict[str, Any]] = []
        self.closed_trades: list[dict[str, Any]] = []
        self.realized_pnl = 0.0
        self.fees = 0.0
        self.equity_peak = initial_balance
        self.max_drawdown = 0.0
        self.trade_counter = 0

    def _execution_price(self, side: str, price: float) -> float:
        direction = 1 if side == "LONG" else -1
        return price * (1 + (direction * self.slippage))

    def _apply_pnl(self, pnl: float, notional: float) -> None:
        fee = notional * self.commission_rate
        self.fees += fee
        self.realized_pnl += pnl - fee
        self.balance += pnl - fee
        self.equity_peak = max(self.equity_peak, self.balance)
        drawdown = self.equity_peak - self.balance
        self.max_drawdown = max(self.max_drawdown, drawdown)

    def open_position(
        self,
        symbol: str,
        side: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        risk: float,
        strategy: str,
    ) -> dict[str, Any]:
        self.trade_counter += 1
        execution_entry = self._execution_price(side, entry)
        entry_fee = execution_entry * position_size * self.commission_rate
        self.fees += entry_fee
        self.balance -= entry_fee
        self.equity_peak = max(self.equity_peak, self.balance)
        trade = {
            "id": f"paper-{self.trade_counter}",
            "symbol": symbol,
            "side": side,
            "entry": execution_entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "risk": risk,
            "entry_fee": entry_fee,
            "strategy": strategy,
            "status": "OPEN",
            "pnl": 0.0,
        }
        self.positions.append(trade)
        return trade

    def update_stop(self, trade_id: str, new_stop: float) -> dict[str, Any]:
        for trade in self.positions:
            if trade["id"] != trade_id:
                continue
            old_stop = trade["stop_loss"]
            if trade["side"] == "LONG":
                trade["stop_loss"] = max(old_stop, new_stop)
            elif trade["side"] == "SHORT":
                trade["stop_loss"] = min(old_stop, new_stop)
            else:
                raise ValueError(f"Unsupported side: {trade['side']}")
            return {"id": trade_id, "old_stop": old_stop, "new_stop": trade["stop_loss"]}
        raise KeyError(f"Unknown paper trade: {trade_id}")

    def partial_exit(self, trade_id: str, fraction: float, current_price: float) -> dict[str, Any]:
        if not 0 < fraction <= 1:
            raise ValueError("fraction must be between 0 and 1")
        for trade in self.positions:
            if trade["id"] != trade_id:
                continue
            quantity = trade["position_size"] * fraction
            price = self._execution_price(trade["side"], current_price)
            if trade["side"] == "LONG":
                pnl = (price - trade["entry"]) * quantity
            elif trade["side"] == "SHORT":
                pnl = (trade["entry"] - price) * quantity
            else:
                raise ValueError(f"Unsupported side: {trade['side']}")
            self._apply_pnl(pnl, price * quantity)
            trade["position_size"] -= quantity
            event = {
                "id": trade_id,
                "closed_quantity": quantity,
                "price": price,
                "pnl": pnl,
                "status": "PARTIAL_EXIT" if trade["position_size"] > 0 else "CLOSED",
            }
            if trade["position_size"] <= 0:
                trade["status"] = "CLOSED"
                trade["pnl"] = pnl
                self.positions.remove(trade)
                self.closed_trades.append(trade)
            return event
        raise KeyError(f"Unknown paper trade: {trade_id}")

    def tick(self, current_price: float) -> list[dict[str, Any]]:
        closed: list[dict[str, Any]] = []
        remaining: list[dict[str, Any]] = []

        for trade in self.positions:
            if trade["side"] == "LONG":
                if current_price <= trade["stop_loss"]:
                    pnl = (trade["stop_loss"] - trade["entry"]) * trade["position_size"]
                    trade["status"] = "CLOSED"
                    trade["pnl"] = pnl
                    self.closed_trades.append(trade)
                    closed.append(trade)
                    self._apply_pnl(pnl, trade["stop_loss"] * trade["position_size"])
                elif current_price >= trade["take_profit"]:
                    pnl = (trade["take_profit"] - trade["entry"]) * trade["position_size"]
                    trade["status"] = "CLOSED"
                    trade["pnl"] = pnl
                    self.closed_trades.append(trade)
                    closed.append(trade)
                    self._apply_pnl(pnl, trade["take_profit"] * trade["position_size"])
                else:
                    remaining.append(trade)
            elif trade["side"] == "SHORT":
                if current_price >= trade["stop_loss"]:
                    pnl = (trade["entry"] - trade["stop_loss"]) * trade["position_size"]
                    trade["status"] = "CLOSED"
                    trade["pnl"] = pnl
                    self.closed_trades.append(trade)
                    closed.append(trade)
                    self._apply_pnl(pnl, trade["stop_loss"] * trade["position_size"])
                elif current_price <= trade["take_profit"]:
                    pnl = (trade["entry"] - trade["take_profit"]) * trade["position_size"]
                    trade["status"] = "CLOSED"
                    trade["pnl"] = pnl
                    self.closed_trades.append(trade)
                    closed.append(trade)
                    self._apply_pnl(pnl, trade["take_profit"] * trade["position_size"])
                else:
                    remaining.append(trade)

        self.positions = remaining
        return closed

    def summary(self) -> dict[str, Any]:
        wins = [t for t in self.closed_trades if t["pnl"] > 0]
        losses = [t for t in self.closed_trades if t["pnl"] < 0]
        net_pnl = sum(t["pnl"] for t in self.closed_trades)
        return {
            "balance": self.balance,
            "net_pnl": net_pnl,
            "realized_pnl": self.realized_pnl,
            "fees": self.fees,
            "max_drawdown": self.max_drawdown,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / len(self.closed_trades)) if self.closed_trades else 0.0,
            "open_positions": len(self.positions),
        }
