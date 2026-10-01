from __future__ import annotations


class DecisionExplainer:
    @staticmethod
    def explain_signal(signal: str, entry: float, stop: float, risk: float, reason: str, symbol: str = "BTCUSDT") -> dict[str, str | float]:
        return {
            "SIGNAL": signal,
            "SYMBOL": symbol,
            "ENTRY": entry,
            "STOP": stop,
            "RISK": risk,
            "REASON": reason,
        }

    @staticmethod
    def explain_stop_update(previous_stop: float, new_stop: float, side: str, reason: str) -> str:
        if side == "LONG":
            return (
                f"Se detectó una nueva estructura alcista y el stop se movió de {previous_stop} a {new_stop}. "
                f"Como la operación es LONG, el stop solo puede subir. Motivo: {reason}."
            )
        if side == "SHORT":
            return (
                f"Se detectó una nueva estructura bajista y el stop se movió de {previous_stop} a {new_stop}. "
                f"Como la operación es SHORT, el stop solo puede bajar. Motivo: {reason}."
            )
        return f"No se aplicó un cambio de stop por motivo: {reason}."
