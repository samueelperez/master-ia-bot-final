# backend/app/strategies/risk_management.py
from .base import BaseStrategy
import pandas as pd

class RiskManagement(BaseStrategy):
    metadata = {
        "name": "RiskManagement",
        "symbols": ["*"],
        "timeframes": ["*"],
        "parameters": {"max_risk_pct": 0.10}
    }

    def generate_signals(self, df: pd.DataFrame):
        # No genera señales por sí misma
        return []
