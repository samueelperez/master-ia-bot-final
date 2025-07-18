import datetime
import traceback
from importlib import import_module
from app.core.celery_app import celery
from app.services.fetcher import fetch_ohlcv
from app.core.db import SessionLocal
from app.core.models import Strategy, Signal

@celery.task
def backtest_strategy(strategy_id: int, symbol: str, timeframe: str, limit: int = 100):
    session = SessionLocal()
    try:
        # 0. Obtiene la estrategia de la base de datos
        strat = session.query(Strategy).get(strategy_id)
        if not strat:
            return {"error": f"Strategy {strategy_id} not found"}

        # 1. Fetch OHLCV
        df = fetch_ohlcv(symbol, timeframe, limit)

        # 2. Determinar nombre del módulo correctamente
        #    Si module_path termina en .py, quita la extensión y reemplaza '/' por '.'
        module_path = strat.module_path
        if module_path.endswith('.py'):
            module_name = module_path[:-3].replace('/', '.')
        else:
            module_name = module_path

        try:
            module = import_module(module_name)
        except Exception as e:
            tb = traceback.format_exc()
            return {"error": f"ImportError: {e}", "trace": tb}

        # 3. Obtener la clase con el nombre de la estrategia (sin espacios)
        class_name = strat.name.replace(" ", "")
        if not hasattr(module, class_name):
            return {"error": f"Plugin class '{class_name}' not found in {module_name}"}

        StrategyClass = getattr(module, class_name)
        strategy = StrategyClass()

        # 4. Generar señales y guardarlas en la base de datos
        signals = strategy.generate_signals(df)
        results = []
        for s in signals:
            sig = Signal(
                strategy_id=strategy_id,
                symbol=symbol,
                timeframe=timeframe,
                params={},  # parámetros adicionales si se desean almacenar
                ts_enter=datetime.datetime.utcnow(),
                price_enter=s["entry"],
                sl=s["sl"],
                tp=s["tp"]
            )
            session.add(sig)
            results.append(s)
        session.commit()
        return {"strategy_id": strategy_id, "signals": results}

    except Exception as e:
        tb = traceback.format_exc()
        return {"error": f"Unhandled exception: {e}", "trace": tb}

    finally:
        session.close()
