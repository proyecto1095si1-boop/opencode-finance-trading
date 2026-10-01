from __future__ import annotations


class PortfolioManager:
    def __init__(self, balance: float = 10000.0):
        self.balance = balance
        self.positions = []

    def snapshot(self):
        return {
            "balance": self.balance,
            "positions": self.positions,
        }
