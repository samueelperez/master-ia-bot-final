"""
Indicadores de volatilidad para análisis técnico de criptomonedas.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Union

def compute_volatility_indicators(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calcula los indicadores de volatilidad para el DataFrame proporcionado.
    
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
            'bbands', 'atr', 'keltner', 'donchian', 'vwap', 'volatility',
            'natr', 'chaikin', 'massi', 'starc', 'accbands'
        ]
    
    # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
    indicators = [ind.lower() for ind in indicators]
    
    # Bollinger Bands
    if 'bbands' in indicators or 'all' in indicators:
        for length in [20]:
            for std in [2.0, 2.5, 3.0]:
                key_prefix = f'bb_{length}_{std}'
                try:
                    bb = ta.bbands(close, length=length, std=std)
                    result[f'{key_prefix}_upper'] = float(bb[f'BBU_{length}_{std}.0'].iloc[-1]) if not bb.empty else None
                    result[f'{key_prefix}_mid'] = float(bb[f'BBM_{length}_{std}.0'].iloc[-1]) if not bb.empty else None
                    result[f'{key_prefix}_lower'] = float(bb[f'BBL_{length}_{std}.0'].iloc[-1]) if not bb.empty else None
                    
                    # Añadir interpretación de las Bollinger Bands
                    if all(v is not None for v in [result[f'{key_prefix}_upper'], result[f'{key_prefix}_mid'], result[f'{key_prefix}_lower']]):
                        current_price = close.iloc[-1]
                        
                        # Calcular ancho de banda (indicador de volatilidad)
                        band_width = (result[f'{key_prefix}_upper'] - result[f'{key_prefix}_lower']) / result[f'{key_prefix}_mid']
                        result[f'{key_prefix}_width'] = band_width
                        
                        # Determinar posición relativa dentro de las bandas
                        if current_price > result[f'{key_prefix}_upper']:
                            result[f'{key_prefix}_position'] = 'above'
                        elif current_price < result[f'{key_prefix}_lower']:
                            result[f'{key_prefix}_position'] = 'below'
                        else:
                            # Calcular porcentaje dentro de las bandas (0% = lower, 100% = upper)
                            band_range = result[f'{key_prefix}_upper'] - result[f'{key_prefix}_lower']
                            if band_range > 0:
                                position_pct = (current_price - result[f'{key_prefix}_lower']) / band_range * 100
                                result[f'{key_prefix}_position_pct'] = position_pct
                                
                                if position_pct > 80:
                                    result[f'{key_prefix}_position'] = 'upper_zone'
                                elif position_pct < 20:
                                    result[f'{key_prefix}_position'] = 'lower_zone'
                                else:
                                    result[f'{key_prefix}_position'] = 'middle_zone'
                            else:
                                result[f'{key_prefix}_position'] = 'middle_zone'
                                result[f'{key_prefix}_position_pct'] = 50
                    else:
                        result[f'{key_prefix}_width'] = None
                        result[f'{key_prefix}_position'] = None
                        result[f'{key_prefix}_position_pct'] = None
                except Exception:
                    result[f'{key_prefix}_upper'] = None
                    result[f'{key_prefix}_mid'] = None
                    result[f'{key_prefix}_lower'] = None
                    result[f'{key_prefix}_width'] = None
                    result[f'{key_prefix}_position'] = None
                    result[f'{key_prefix}_position_pct'] = None
    
    # ATR - Average True Range
    if 'atr' in indicators or 'all' in indicators:
        for length in [14, 20]:
            key = f'atr_{length}'
            try:
                series = ta.atr(high, low, close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
                
                # Calcular ATR como porcentaje del precio
                if result[key] is not None:
                    current_price = close.iloc[-1]
                    result[f'{key}_pct'] = (result[key] / current_price) * 100
                else:
                    result[f'{key}_pct'] = None
            except Exception:
                result[key] = None
                result[f'{key}_pct'] = None
    
    # NATR - Normalized ATR
    if 'natr' in indicators or 'all' in indicators:
        for length in [14, 20]:
            key = f'natr_{length}'
            try:
                series = ta.natr(high, low, close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
            except Exception:
                result[key] = None
    
    # Keltner Channels
    if 'keltner' in indicators or 'all' in indicators:
        for length in [20]:
            key_prefix = f'kc_{length}'
            try:
                kc = ta.kc(high, low, close, length=length)
                result[f'{key_prefix}_upper'] = float(kc[f'KCU_{length}_2.0'].iloc[-1]) if not kc.empty else None
                result[f'{key_prefix}_mid'] = float(kc[f'KCB_{length}_2.0'].iloc[-1]) if not kc.empty else None
                result[f'{key_prefix}_lower'] = float(kc[f'KCL_{length}_2.0'].iloc[-1]) if not kc.empty else None
                
                # Añadir interpretación de los Keltner Channels
                if all(v is not None for v in [result[f'{key_prefix}_upper'], result[f'{key_prefix}_mid'], result[f'{key_prefix}_lower']]):
                    current_price = close.iloc[-1]
                    
                    # Calcular ancho de canal (indicador de volatilidad)
                    channel_width = (result[f'{key_prefix}_upper'] - result[f'{key_prefix}_lower']) / result[f'{key_prefix}_mid']
                    result[f'{key_prefix}_width'] = channel_width
                    
                    # Determinar posición relativa dentro del canal
                    if current_price > result[f'{key_prefix}_upper']:
                        result[f'{key_prefix}_position'] = 'above'
                    elif current_price < result[f'{key_prefix}_lower']:
                        result[f'{key_prefix}_position'] = 'below'
                    else:
                        # Calcular porcentaje dentro del canal (0% = lower, 100% = upper)
                        channel_range = result[f'{key_prefix}_upper'] - result[f'{key_prefix}_lower']
                        if channel_range > 0:
                            position_pct = (current_price - result[f'{key_prefix}_lower']) / channel_range * 100
                            result[f'{key_prefix}_position_pct'] = position_pct
                            
                            if position_pct > 80:
                                result[f'{key_prefix}_position'] = 'upper_zone'
                            elif position_pct < 20:
                                result[f'{key_prefix}_position'] = 'lower_zone'
                            else:
                                result[f'{key_prefix}_position'] = 'middle_zone'
                        else:
                            result[f'{key_prefix}_position'] = 'middle_zone'
                            result[f'{key_prefix}_position_pct'] = 50
                else:
                    result[f'{key_prefix}_width'] = None
                    result[f'{key_prefix}_position'] = None
                    result[f'{key_prefix}_position_pct'] = None
            except Exception:
                result[f'{key_prefix}_upper'] = None
                result[f'{key_prefix}_mid'] = None
                result[f'{key_prefix}_lower'] = None
                result[f'{key_prefix}_width'] = None
                result[f'{key_prefix}_position'] = None
                result[f'{key_prefix}_position_pct'] = None
    
    # Donchian Channels
    if 'donchian' in indicators or 'all' in indicators:
        for length in [20]:
            key_prefix = f'dc_{length}'
            try:
                dc = ta.donchian(high, low, lower_length=length, upper_length=length)
                result[f'{key_prefix}_upper'] = float(dc[f'DCU_{length}_{length}'].iloc[-1]) if not dc.empty else None
                result[f'{key_prefix}_mid'] = float(dc[f'DCM_{length}_{length}'].iloc[-1]) if not dc.empty else None
                result[f'{key_prefix}_lower'] = float(dc[f'DCL_{length}_{length}'].iloc[-1]) if not dc.empty else None
                
                # Añadir interpretación de los Donchian Channels
                if all(v is not None for v in [result[f'{key_prefix}_upper'], result[f'{key_prefix}_mid'], result[f'{key_prefix}_lower']]):
                    current_price = close.iloc[-1]
                    
                    # Calcular ancho de canal (indicador de volatilidad)
                    channel_width = (result[f'{key_prefix}_upper'] - result[f'{key_prefix}_lower']) / result[f'{key_prefix}_mid']
                    result[f'{key_prefix}_width'] = channel_width
                    
                    # Determinar posición relativa dentro del canal
                    if current_price > result[f'{key_prefix}_upper']:
                        result[f'{key_prefix}_position'] = 'above'
                    elif current_price < result[f'{key_prefix}_lower']:
                        result[f'{key_prefix}_position'] = 'below'
                    else:
                        # Calcular porcentaje dentro del canal (0% = lower, 100% = upper)
                        channel_range = result[f'{key_prefix}_upper'] - result[f'{key_prefix}_lower']
                        if channel_range > 0:
                            position_pct = (current_price - result[f'{key_prefix}_lower']) / channel_range * 100
                            result[f'{key_prefix}_position_pct'] = position_pct
                            
                            if position_pct > 80:
                                result[f'{key_prefix}_position'] = 'upper_zone'
                            elif position_pct < 20:
                                result[f'{key_prefix}_position'] = 'lower_zone'
                            else:
                                result[f'{key_prefix}_position'] = 'middle_zone'
                        else:
                            result[f'{key_prefix}_position'] = 'middle_zone'
                            result[f'{key_prefix}_position_pct'] = 50
                else:
                    result[f'{key_prefix}_width'] = None
                    result[f'{key_prefix}_position'] = None
                    result[f'{key_prefix}_position_pct'] = None
            except Exception:
                result[f'{key_prefix}_upper'] = None
                result[f'{key_prefix}_mid'] = None
                result[f'{key_prefix}_lower'] = None
                result[f'{key_prefix}_width'] = None
                result[f'{key_prefix}_position'] = None
                result[f'{key_prefix}_position_pct'] = None
    
    # VWAP - Volume Weighted Average Price
    if 'vwap' in indicators or 'all' in indicators:
        try:
            vwap = ta.vwap(high, low, close, volume)
            result['vwap'] = float(vwap.iloc[-1]) if not vwap.empty else None
            
            # Añadir interpretación del VWAP
            if result['vwap'] is not None:
                current_price = close.iloc[-1]
                if current_price > result['vwap']:
                    result['vwap_position'] = 'above'
                else:
                    result['vwap_position'] = 'below'
                
                # Calcular distancia al VWAP como porcentaje
                result['vwap_distance_pct'] = ((current_price / result['vwap']) - 1) * 100
            else:
                result['vwap_position'] = None
                result['vwap_distance_pct'] = None
        except Exception:
            result['vwap'] = None
            result['vwap_position'] = None
            result['vwap_distance_pct'] = None
    
    # Volatility (Histórica)
    if 'volatility' in indicators or 'all' in indicators:
        for length in [10, 20, 30]:
            key = f'volatility_{length}'
            try:
                # Calcular volatilidad como desviación estándar de los retornos
                returns = close.pct_change().dropna()
                if len(returns) >= length:
                    vol = returns.rolling(window=length).std().iloc[-1] * 100  # Convertir a porcentaje
                    result[key] = float(vol)
                else:
                    result[key] = None
            except Exception:
                result[key] = None
    
    # Chaikin Volatility
    if 'chaikin' in indicators or 'all' in indicators:
        for length in [10, 20]:
            key = f'chaikin_vol_{length}'
            try:
                chaikin = ta.chaikin_vol(high, low, length=length)
                result[key] = float(chaikin.iloc[-1]) if not chaikin.empty else None
            except Exception:
                result[key] = None
    
    # Mass Index
    if 'massi' in indicators or 'all' in indicators:
        try:
            massi = ta.massi(high, low, fast=9, slow=25)
            result['massi'] = float(massi.iloc[-1]) if not massi.empty else None
            
            # Añadir interpretación del Mass Index
            if result['massi'] is not None:
                if result['massi'] > 27:
                    result['massi_signal'] = 'reversal_possible'
                else:
                    result['massi_signal'] = 'no_reversal'
            else:
                result['massi_signal'] = None
        except Exception:
            result['massi'] = None
            result['massi_signal'] = None
    
    # STARC Bands
    if 'starc' in indicators or 'all' in indicators:
        try:
            starc = ta.starc(high, low, close, length=10)
            result['starc_upper'] = float(starc['STARCU_10_2.0'].iloc[-1]) if not starc.empty else None
            result['starc_lower'] = float(starc['STARCL_10_2.0'].iloc[-1]) if not starc.empty else None
            
            # Añadir interpretación de las STARC Bands
            if result['starc_upper'] is not None and result['starc_lower'] is not None:
                current_price = close.iloc[-1]
                if current_price > result['starc_upper']:
                    result['starc_position'] = 'above'
                elif current_price < result['starc_lower']:
                    result['starc_position'] = 'below'
                else:
                    result['starc_position'] = 'inside'
            else:
                result['starc_position'] = None
        except Exception:
            result['starc_upper'] = None
            result['starc_lower'] = None
            result['starc_position'] = None
    
    # Acceleration Bands
    if 'accbands' in indicators or 'all' in indicators:
        try:
            accbands = ta.accbands(high, low, close, length=20)
            result['accbands_upper'] = float(accbands['ACCU_20_2.0'].iloc[-1]) if not accbands.empty else None
            result['accbands_mid'] = float(accbands['ACCM_20_2.0'].iloc[-1]) if not accbands.empty else None
            result['accbands_lower'] = float(accbands['ACCL_20_2.0'].iloc[-1]) if not accbands.empty else None
            
            # Añadir interpretación de las Acceleration Bands
            if all(v is not None for v in [result['accbands_upper'], result['accbands_mid'], result['accbands_lower']]):
                current_price = close.iloc[-1]
                if current_price > result['accbands_upper']:
                    result['accbands_position'] = 'above'
                elif current_price < result['accbands_lower']:
                    result['accbands_position'] = 'below'
                else:
                    result['accbands_position'] = 'inside'
            else:
                result['accbands_position'] = None
        except Exception:
            result['accbands_upper'] = None
            result['accbands_mid'] = None
            result['accbands_lower'] = None
            result['accbands_position'] = None
    
    return result
