#!/usr/bin/env python3
import os
import sys

# Asegúrate de que Python pueda resolver tu paquete app
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(ROOT))

from app.services.tasks import backtest_strategy

if __name__ == "__main__":
    for strat in (3, 4, 5, 6):
        res = backtest_strategy.delay(strat, "BTC", "1h", 200)
        print(f"⏳ Despachada strategy_id={strat} → Task ID: {res.id}")
