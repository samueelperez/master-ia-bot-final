# backend/app/strategies/monday_range.py
from .base import BaseStrategy
import pandas as pd

class MondayRange(BaseStrategy):
    metadata = {
        "name": "MondayRange",
        "symbols": ["BTC","ETH","SOL","APT"],
        "timeframes": ["5m", "1h"],
        "parameters": {}
    }

    def generate_signals(self, df: pd.DataFrame):
        # Asume el DataFrame index está en datetime y ordenado
        monday = df.between_time("00:00", "23:59").iloc[:24]
        hi, lo = monday["high"].max(), monday["low"].min()
        last = df.iloc[-1]
        signals = []
        # rompió el bajo y volvió
        if last["low"] < lo and last["close"] > lo:
            signals.append({"entry": last["close"], "sl": lo - 1, "tp": lo + (hi-lo)})
        # rompió el alto y volvió
        if last["high"] > hi and last["close"] < hi:
            signals.append({"entry": last["close"], "sl": hi + 1, "tp": hi - (hi-lo)})
        return signals
