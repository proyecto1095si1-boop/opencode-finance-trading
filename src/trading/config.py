import os
from dataclasses import dataclass
from typing import Literal

Mode = Literal["ANALYSIS", "PAPER", "TESTNET", "LIVE"]
StopMode = Literal["STRUCTURE", "ATR", "STRUCTURE_ATR", "FIXED_TRAILING"]


@dataclass
class TradingConfig:
    mode: Mode = os.getenv("MODE", "PAPER").upper()
    live_enabled: bool = os.getenv("LIVE_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    live_manual_approval: bool = os.getenv("LIVE_MANUAL_APPROVAL", "false").lower() in {"1", "true", "yes", "on"}
    default_timeframe: str = os.getenv("DEFAULT_TIMEFRAME", "15m")
    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")
    capital: float = float(os.getenv("CAPITAL", "10000"))
    max_risk_per_trade: float = float(os.getenv("MAX_RISK_PER_TRADE", "0.01"))
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
    max_open_positions: int = int(os.getenv("MAX_OPEN_POSITIONS", "3"))
    max_position_size: float = float(os.getenv("MAX_POSITION_SIZE", "5000"))
    max_leverage: float = float(os.getenv("MAX_LEVERAGE", "3"))
    max_consecutive_losses: int = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
    cooldown_after_loss: int = int(os.getenv("COOLDOWN_AFTER_LOSS", "30"))
    stop_mode: StopMode = os.getenv("STOP_MODE", "STRUCTURE_ATR")
    swing_length: int = int(os.getenv("SWING_LENGTH", "3"))
    confirmation_candles: int = int(os.getenv("CONFIRMATION_CANDLES", "1"))
    minimum_swing_distance: float = float(os.getenv("MINIMUM_SWING_DISTANCE", "0.5"))
    minimum_structure_move: float = float(os.getenv("MINIMUM_STRUCTURE_MOVE", "0.5"))
    emergency_stop: bool = os.getenv("EMERGENCY_STOP", "false").lower() in {"1", "true", "yes", "on"}
    binance_testnet: bool = os.getenv("BINANCE_TESTNET", "true").lower() in {"1", "true", "yes", "on"}
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")

    @property
    def live_is_authorized(self) -> bool:
        return self.mode == "LIVE" and self.live_enabled and self.live_manual_approval

    @property
    def mode_is_live(self) -> bool:
        return self.mode == "LIVE" and self.live_is_authorized

    @property
    def mode_is_paper(self) -> bool:
        return self.mode in {"PAPER", "ANALYSIS"}
