# backend/app/strategies/scalping_memecoins.py
from .base import BaseStrategy
import pandas as pd

class ScalpingMemecoins(BaseStrategy):
    metadata = {
        "name": "ScalpingMemecoins",
        "symbols": ["MEME*"],
        "timeframes": ["1m", "5m"],
        "parameters": {"slippage": 0.30}
    }

    def generate_signals(self, df: pd.DataFrame):
        last = df.iloc[-1]
        entry = last["close"]
        sl = last["low"] * (1 - self.metadata["parameters"]["slippage"])
        tp = entry * 1.01
        return [{"entry": entry, "sl": sl, "tp": tp}]
