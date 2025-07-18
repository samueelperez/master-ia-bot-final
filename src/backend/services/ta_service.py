import pandas as pd
from typing import Dict, Any, Optional, List, Union, Set

# Importar los módulos de indicadores
from .indicators.trend import compute_trend_indicators
from .indicators.momentum import compute_momentum_indicators
from .indicators.volatility import compute_volatility_indicators
from .indicators.volume import compute_volume_indicators
from .indicators.support_resistance import compute_support_resistance
from .indicators.patterns import detect_patterns

# Definir perfiles predefinidos de indicadores
INDICATOR_PROFILES = {
    "basic": {
        "trend": ["sma_50", "ema_50", "ema_200"],
        "momentum": ["rsi_14", "macd"],
        "volatility": ["bbands"],
        "volume": ["vwap"],
        "support_resistance": ["pivot_daily"],
        "patterns": ["candlestick_basic"]
    },
    "intermediate": {
        "trend": ["sma_50", "ema_50", "ema_200", "adx_14", "parabolic_sar"],
        "momentum": ["rsi_14", "macd", "stochastic", "williams_r"],
        "volatility": ["bbands", "atr_14", "keltner"],
        "volume": ["vwap", "obv", "cmf_20"],
        "support_resistance": ["pivot_daily", "fibonacci"],
        "patterns": ["candlestick_basic", "chart_patterns_basic"]
    },
    "advanced": {
        "trend": ["sma_50", "ema_50", "ema_200", "adx_14", "parabolic_sar", "ichimoku", "tema", "dema", "vortex"],
        "momentum": ["rsi_14", "macd", "stochastic", "williams_r", "cci", "tsi", "ultimate"],
        "volatility": ["bbands", "atr_14", "keltner", "donchian", "starc"],
        "volume": ["vwap", "obv", "cmf_20", "mfi", "force_index", "volume_oscillator"],
        "support_resistance": ["pivot_daily", "pivot_weekly", "fibonacci", "demand_zones"],
        "patterns": ["candlestick_all", "chart_patterns_all", "harmonic_patterns", "divergences"]
    }
}

def compute_indicators(
    df: pd.DataFrame, 
    categories: Optional[List[str]] = None,
    specific_indicators: Optional[Dict[str, List[str]]] = None,
    profile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calcula los indicadores técnicos para el DataFrame proporcionado.
    
    Args:
        df: DataFrame con datos OHLCV
        categories: Lista de categorías de indicadores a calcular. Si es None, calcula todos.
            Opciones: 'trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'patterns'
        specific_indicators: Diccionario con categorías como claves y listas de indicadores específicos como valores.
            Ejemplo: {'trend': ['sma_50', 'ema_200'], 'momentum': ['rsi_14']}
        profile: Perfil predefinido de indicadores ('basic', 'intermediate', 'advanced')
    
    Returns:
        Diccionario con los valores de los indicadores calculados
    """
    result = {}
    
    # Determinar qué indicadores calcular basado en el perfil, categorías y específicos
    indicators_to_compute = {}
    
    # Si se especifica un perfil, usar esa configuración
    if profile and profile.lower() in INDICATOR_PROFILES:
        indicators_to_compute = INDICATOR_PROFILES[profile.lower()]
    
    # Si se especifican categorías pero no indicadores específicos, calcular todos los indicadores de esas categorías
    elif categories and not specific_indicators:
        # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
        categories = [cat.lower() for cat in categories]
        
        # Incluir todas las categorías especificadas
        for category in categories:
            indicators_to_compute[category] = None  # None significa "todos los indicadores de esta categoría"
    
    # Si se especifican indicadores específicos, usarlos
    elif specific_indicators:
        indicators_to_compute = {k.lower(): v for k, v in specific_indicators.items()}
    
    # Si no se especifica nada, calcular todos los indicadores de todas las categorías
    else:
        categories = [
            'trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'patterns'
        ]
        for category in categories:
            indicators_to_compute[category] = None
    
    # Calcular indicadores de tendencia
    if 'trend' in indicators_to_compute:
        trend_indicators = compute_trend_indicators(df, indicators=indicators_to_compute['trend'])
        result.update(trend_indicators)
    
    # Calcular indicadores de momentum
    if 'momentum' in indicators_to_compute:
        momentum_indicators = compute_momentum_indicators(df, indicators=indicators_to_compute['momentum'])
        result.update(momentum_indicators)
    
    # Calcular indicadores de volatilidad
    if 'volatility' in indicators_to_compute:
        volatility_indicators = compute_volatility_indicators(df, indicators=indicators_to_compute['volatility'])
        result.update(volatility_indicators)
    
    # Calcular indicadores de volumen
    if 'volume' in indicators_to_compute:
        volume_indicators = compute_volume_indicators(df, indicators=indicators_to_compute['volume'])
        result.update(volume_indicators)
    
    # Calcular niveles de soporte y resistencia
    if 'support_resistance' in indicators_to_compute:
        sr_indicators = compute_support_resistance(df, indicators=indicators_to_compute['support_resistance'])
        result.update(sr_indicators)
    
    # Detectar patrones
    if 'patterns' in indicators_to_compute:
        pattern_indicators = detect_patterns(df, indicators=indicators_to_compute['patterns'])
        result.update(pattern_indicators)
    
    return result

def compute_basic_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula un conjunto básico de indicadores para compatibilidad con versiones anteriores.
    
    Args:
        df: DataFrame con datos OHLCV
    
    Returns:
        Diccionario con los valores de los indicadores básicos
    """
    # Usar el perfil básico predefinido
    return compute_indicators(df, profile="basic")

def get_available_indicators() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Devuelve información sobre todos los indicadores disponibles en el sistema.
    
    Returns:
        Diccionario con categorías como claves y listas de indicadores como valores,
        incluyendo información sobre cada indicador (nombre, descripción, popularidad, etc.)
    """
    # Esta es una versión simplificada. En una implementación real, esta información
    # podría venir de metadatos en los módulos de indicadores o de una base de datos.
    
    indicators = {
        "trend": [
            {"name": "sma", "full_name": "Media Móvil Simple (SMA)", "popularity": "Alta"},
            {"name": "ema", "full_name": "Media Móvil Exponencial (EMA)", "popularity": "Alta"},
            {"name": "wma", "full_name": "Media Móvil Ponderada (WMA)", "popularity": "Baja"},
            {"name": "hma", "full_name": "Hull Moving Average (HMA)", "popularity": "Baja"},
            {"name": "tema", "full_name": "Triple EMA (TEMA)", "popularity": "Baja"},
            {"name": "dema", "full_name": "Doble EMA (DEMA)", "popularity": "Baja"},
            {"name": "vwap", "full_name": "Volume Weighted Average Price (VWAP)", "popularity": "Media"},
            {"name": "adx", "full_name": "Average Directional Index (ADX)", "popularity": "Media"},
            {"name": "parabolic_sar", "full_name": "SAR Parabólico", "popularity": "Media"},
            {"name": "ichimoku", "full_name": "Ichimoku Cloud", "popularity": "Intermedio"},
            {"name": "supertrend", "full_name": "Supertrend", "popularity": "Media"},
            {"name": "kama", "full_name": "Kaufman Adaptive Moving Average", "popularity": "Baja"},
            {"name": "vortex", "full_name": "Vortex Indicator (VTX)", "popularity": "Baja"},
            {"name": "dmi", "full_name": "Directional Movement Index (DMI)", "popularity": "Media"}
        ],
        "momentum": [
            {"name": "rsi", "full_name": "Índice de Fuerza Relativa (RSI)", "popularity": "Alta"},
            {"name": "macd", "full_name": "MACD", "popularity": "Alta"},
            {"name": "stochastic", "full_name": "Estocástico", "popularity": "Media"},
            {"name": "stochastic_fast", "full_name": "Oscilador Estocástico Rápido", "popularity": "Media"},
            {"name": "stochastic_slow", "full_name": "Oscilador Estocástico Lento", "popularity": "Media"},
            {"name": "williams_r", "full_name": "Williams %R", "popularity": "Media"},
            {"name": "cci", "full_name": "Commodity Channel Index (CCI)", "popularity": "Intermedio"},
            {"name": "momentum", "full_name": "Momentum", "popularity": "Media"},
            {"name": "roc", "full_name": "Rate of Change (ROC)", "popularity": "Media"},
            {"name": "tsi", "full_name": "True Strength Index (TSI)", "popularity": "Baja"},
            {"name": "ultimate", "full_name": "Ultimate Oscillator", "popularity": "Baja"},
            {"name": "fisher", "full_name": "Fisher Transform", "popularity": "Baja"},
            {"name": "eom", "full_name": "Ease of Movement", "popularity": "Baja"}
        ],
        "volatility": [
            {"name": "bbands", "full_name": "Bollinger Bands (BB)", "popularity": "Alta"},
            {"name": "atr", "full_name": "Average True Range (ATR)", "popularity": "Intermedio"},
            {"name": "keltner", "full_name": "Keltner Channels", "popularity": "Baja"},
            {"name": "donchian", "full_name": "Donchian Channels", "popularity": "Baja"},
            {"name": "starc", "full_name": "STARC Bands", "popularity": "Baja"},
            {"name": "volatility_chaikin", "full_name": "Oscilador Chaikin", "popularity": "Baja"},
            {"name": "volatility_balance", "full_name": "Balance de volatilidad", "popularity": "Baja"}
        ],
        "volume": [
            {"name": "obv", "full_name": "On Balance Volume (OBV)", "popularity": "Media"},
            {"name": "cmf", "full_name": "Chaikin Money Flow", "popularity": "Media"},
            {"name": "force_index", "full_name": "Force Index", "popularity": "Media"},
            {"name": "mfi", "full_name": "Money Flow Index", "popularity": "Media"},
            {"name": "vwap", "full_name": "Volume Weighted Average Price", "popularity": "Media"},
            {"name": "volume_oscillator", "full_name": "Volume Oscillator", "popularity": "Media"},
            {"name": "klinger", "full_name": "Klinger Volume Oscillator", "popularity": "Baja"},
            {"name": "nvi", "full_name": "Negative Volume Index", "popularity": "Baja"},
            {"name": "pvi", "full_name": "Positive Volume Index", "popularity": "Baja"}
        ],
        "support_resistance": [
            {"name": "fibonacci", "full_name": "Fibonacci Retracements", "popularity": "Media"},
            {"name": "pivot_daily", "full_name": "Pivotes Diarios", "popularity": "Alta"},
            {"name": "pivot_weekly", "full_name": "Pivotes Semanales", "popularity": "Media"},
            {"name": "pivot_monthly", "full_name": "Pivotes Mensuales", "popularity": "Media"},
            {"name": "gann", "full_name": "Gann Lines", "popularity": "Baja"},
            {"name": "demand_zones", "full_name": "Zonas de Oferta y Demanda", "popularity": "Media"}
        ],
        "patterns": [
            {"name": "candlestick_basic", "full_name": "Patrones de Velas Básicos", "popularity": "Media"},
            {"name": "candlestick_all", "full_name": "Todos los Patrones de Velas", "popularity": "Media"},
            {"name": "chart_patterns_basic", "full_name": "Patrones Chartistas Básicos", "popularity": "Media"},
            {"name": "chart_patterns_all", "full_name": "Todos los Patrones Chartistas", "popularity": "Media"},
            {"name": "harmonic_patterns", "full_name": "Patrones Armónicos", "popularity": "Baja"},
            {"name": "divergences", "full_name": "Divergencias", "popularity": "Media"}
        ]
    }
    
    return indicators
