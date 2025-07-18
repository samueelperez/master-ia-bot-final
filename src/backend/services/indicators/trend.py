"""
Indicadores de tendencia para análisis técnico de criptomonedas.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Union

def compute_trend_indicators(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calcula los indicadores de tendencia para el DataFrame proporcionado.
    
    Args:
        df: DataFrame con datos OHLCV
        indicators: Lista de indicadores específicos a calcular. Si es None, calcula todos.
    
    Returns:
        Diccionario con los valores de los indicadores calculados
    """
    result = {}
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    # Si no se especifican indicadores, calcular todos
    if indicators is None:
        indicators = [
            'sma', 'ema', 'tema', 'dema', 'wma', 'hma', 'kama', 'ichimoku',
            'adx', 'dmi', 'vortex', 'trix', 'mass', 'sar', 'supertrend'
        ]
    
    # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
    indicators = [ind.lower() for ind in indicators]
    
    # SMA - Simple Moving Average
    if 'sma' in indicators or 'all' in indicators:
        for length in [9, 20, 50, 100, 200]:
            key = f'sma_{length}'
            try:
                series = ta.sma(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # EMA - Exponential Moving Average
    if 'ema' in indicators or 'all' in indicators:
        for length in [9, 20, 50, 100, 200]:
            key = f'ema_{length}'
            try:
                series = ta.ema(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # TEMA - Triple Exponential Moving Average
    if 'tema' in indicators or 'all' in indicators:
        for length in [9, 20, 50]:
            key = f'tema_{length}'
            try:
                series = ta.tema(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # DEMA - Double Exponential Moving Average
    if 'dema' in indicators or 'all' in indicators:
        for length in [9, 20, 50]:
            key = f'dema_{length}'
            try:
                series = ta.dema(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # WMA - Weighted Moving Average
    if 'wma' in indicators or 'all' in indicators:
        for length in [9, 20, 50]:
            key = f'wma_{length}'
            try:
                series = ta.wma(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # HMA - Hull Moving Average
    if 'hma' in indicators or 'all' in indicators:
        for length in [9, 20, 50]:
            key = f'hma_{length}'
            try:
                series = ta.hma(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # KAMA - Kaufman Adaptive Moving Average
    if 'kama' in indicators or 'all' in indicators:
        for length in [10, 20, 30]:
            key = f'kama_{length}'
            try:
                series = ta.kama(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # ADX - Average Directional Index
    if 'adx' in indicators or 'all' in indicators:
        for length in [14, 20]:
            key = f'adx_{length}'
            try:
                adx = ta.adx(high, low, close, length=length)
                result[key] = float(adx[f'ADX_{length}'].iloc[-1]) if not adx.empty else None
                result[f'dip_{length}'] = float(adx[f'DMP_{length}'].iloc[-1]) if not adx.empty else None
                result[f'din_{length}'] = float(adx[f'DMN_{length}'].iloc[-1]) if not adx.empty else None
            except Exception:
                result[key] = None
                result[f'dip_{length}'] = None
                result[f'din_{length}'] = None
    
    # Parabolic SAR
    if 'sar' in indicators or 'all' in indicators:
        try:
            sar = ta.psar(high, low, close)
            result['psar'] = float(sar['PSARl_0.02_0.2'].iloc[-1]) if not sar.empty else None
            result['psar_af'] = float(sar['PSARaf_0.02_0.2'].iloc[-1]) if not sar.empty else None
            result['psar_direction'] = 'up' if result['psar'] < close.iloc[-1] else 'down'
        except Exception:
            result['psar'] = None
            result['psar_af'] = None
            result['psar_direction'] = None
    
    # Ichimoku Cloud
    if 'ichimoku' in indicators or 'all' in indicators:
        try:
            ichimoku = ta.ichimoku(high, low, close)
            result['tenkan_sen'] = float(ichimoku['ITS_9'].iloc[-1]) if not ichimoku.empty else None
            result['kijun_sen'] = float(ichimoku['IKS_26'].iloc[-1]) if not ichimoku.empty else None
            result['senkou_span_a'] = float(ichimoku['ISA_9_26'].iloc[-1]) if not ichimoku.empty else None
            result['senkou_span_b'] = float(ichimoku['ISB_9_26'].iloc[-1]) if not ichimoku.empty else None
            result['chikou_span'] = float(ichimoku['ICS_26'].iloc[-1]) if not ichimoku.empty else None
            
            # Determinar posición relativa al cloud
            if result['senkou_span_a'] is not None and result['senkou_span_b'] is not None:
                current_price = close.iloc[-1]
                cloud_top = max(result['senkou_span_a'], result['senkou_span_b'])
                cloud_bottom = min(result['senkou_span_a'], result['senkou_span_b'])
                
                if current_price > cloud_top:
                    result['cloud_position'] = 'above'
                elif current_price < cloud_bottom:
                    result['cloud_position'] = 'below'
                else:
                    result['cloud_position'] = 'inside'
            else:
                result['cloud_position'] = None
        except Exception:
            result['tenkan_sen'] = None
            result['kijun_sen'] = None
            result['senkou_span_a'] = None
            result['senkou_span_b'] = None
            result['chikou_span'] = None
            result['cloud_position'] = None
    
    # Vortex Indicator
    if 'vortex' in indicators or 'all' in indicators:
        for length in [14, 20]:
            try:
                vortex = ta.vortex(high, low, close, length=length)
                result[f'vortex_pos_{length}'] = float(vortex[f'VIP_{length}'].iloc[-1]) if not vortex.empty else None
                result[f'vortex_neg_{length}'] = float(vortex[f'VIN_{length}'].iloc[-1]) if not vortex.empty else None
                
                # Determinar señal
                if (result[f'vortex_pos_{length}'] is not None and 
                    result[f'vortex_neg_{length}'] is not None):
                    if result[f'vortex_pos_{length}'] > result[f'vortex_neg_{length}']:
                        result[f'vortex_signal_{length}'] = 'bullish'
                    else:
                        result[f'vortex_signal_{length}'] = 'bearish'
                else:
                    result[f'vortex_signal_{length}'] = None
            except Exception:
                result[f'vortex_pos_{length}'] = None
                result[f'vortex_neg_{length}'] = None
                result[f'vortex_signal_{length}'] = None
    
    # TRIX - Triple Exponential Average
    if 'trix' in indicators or 'all' in indicators:
        for length in [9, 14, 30]:
            key = f'trix_{length}'
            try:
                trix = ta.trix(close, length=length)
                result[key] = float(trix[f'TRIX_{length}_9'].iloc[-1]) if not trix.empty else None
                result[f'trix_signal_{length}'] = float(trix[f'TRIXs_{length}_9'].iloc[-1]) if not trix.empty else None
            except Exception:
                result[key] = None
                result[f'trix_signal_{length}'] = None
    
    # Supertrend
    if 'supertrend' in indicators or 'all' in indicators:
        try:
            supertrend = ta.supertrend(high, low, close, length=10, multiplier=3.0)
            result['supertrend'] = float(supertrend['SUPERT_10_3.0'].iloc[-1]) if not supertrend.empty else None
            result['supertrend_direction'] = float(supertrend['SUPERTd_10_3.0'].iloc[-1]) if not supertrend.empty else None
            result['supertrend_signal'] = 'bullish' if result['supertrend_direction'] == 1 else 'bearish'
        except Exception:
            result['supertrend'] = None
            result['supertrend_direction'] = None
            result['supertrend_signal'] = None
    
    # Añadir cruces de medias móviles
    if all(k in result and result[k] is not None for k in ['ema_9', 'ema_20']):
        result['ema_9_20_cross'] = 'bullish' if result['ema_9'] > result['ema_20'] else 'bearish'
    
    if all(k in result and result[k] is not None for k in ['ema_50', 'ema_200']):
        result['ema_50_200_cross'] = 'bullish' if result['ema_50'] > result['ema_200'] else 'bearish'
        result['golden_cross'] = result['ema_50'] > result['ema_200']
        result['death_cross'] = result['ema_50'] < result['ema_200']
    
    return result
