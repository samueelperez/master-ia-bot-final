from .base import BaseStrategy
import pandas as pd

class HoldingMemecoins(BaseStrategy):
    metadata = {
        "name": "HoldingMemecoins",
        "symbols": ["MEME*"],
        "timeframes": ["4h", "1d"],
        "parameters": {"take_profit_multiplier": 10}
    }

    def generate_signals(self, df: pd.DataFrame):
        last = df.iloc[-1]
        entry = last["close"]
        sl = last["low"]
        tp = entry * self.metadata["parameters"]["take_profit_multiplier"]
        return [{"entry": entry, "sl": sl, "tp": tp}]