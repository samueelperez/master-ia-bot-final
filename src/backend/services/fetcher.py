import ccxt
import pandas as pd

# Inicializa el exchange (aquí Binance; puedes usar otro)
exchange = ccxt.binance({
    'enableRateLimit': True,
})

def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
    """
    Retorna un DataFrame con columnas:
    ['open','high','low','close','volume']
    Indexado por timestamp (DateTimeIndex).
    """
    pair = f"{symbol}/USDT"
    data = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume'])
    # Convierte la columna timestamp a datetime y ponla como índice
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    return df
