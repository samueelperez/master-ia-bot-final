"""
Paquete de indicadores técnicos para análisis de criptomonedas.
Organizado por categorías:
- trend: Indicadores de tendencia (SMA, EMA, etc.)
- momentum: Indicadores de momentum (RSI, MACD, etc.)
- volatility: Indicadores de volatilidad (Bollinger Bands, ATR, etc.)
- volume: Indicadores de volumen (OBV, Chaikin, etc.)
- support_resistance: Indicadores de soporte/resistencia (Fibonacci, Pivotes, etc.)
- patterns: Reconocimiento de patrones chartistas y de velas
"""

from .trend import compute_trend_indicators
from .momentum import compute_momentum_indicators
from .volatility import compute_volatility_indicators
from .volume import compute_volume_indicators
from .support_resistance import compute_support_resistance
from .patterns import detect_patterns

__all__ = [
    'compute_trend_indicators',
    'compute_momentum_indicators',
    'compute_volatility_indicators',
    'compute_volume_indicators',
    'compute_support_resistance',
    'detect_patterns'
]
