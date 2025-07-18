"""
Indicadores de momentum para análisis técnico de criptomonedas.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Union

def compute_momentum_indicators(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calcula los indicadores de momentum para el DataFrame proporcionado.
    
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
            'rsi', 'macd', 'stoch', 'cci', 'williams', 'ultimate', 'fisher',
            'momentum', 'roc', 'tsi', 'stochrsi', 'dpo', 'kst', 'ppo'
        ]
    
    # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
    indicators = [ind.lower() for ind in indicators]
    
    # RSI - Relative Strength Index
    if 'rsi' in indicators or 'all' in indicators:
        for length in [6, 14, 21]:
            key = f'rsi_{length}'
            try:
                series = ta.rsi(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
                
                # Añadir interpretación del RSI
                if result[key] is not None:
                    if result[key] > 70:
                        result[f'{key}_signal'] = 'overbought'
                    elif result[key] < 30:
                        result[f'{key}_signal'] = 'oversold'
                    else:
                        result[f'{key}_signal'] = 'neutral'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # MACD - Moving Average Convergence Divergence
    if 'macd' in indicators or 'all' in indicators:
        try:
            macd = ta.macd(close, fast=12, slow=26, signal=9)
            result['macd_line'] = float(macd['MACD_12_26_9'].iloc[-1]) if not macd.empty else None
            result['macd_signal'] = float(macd['MACDs_12_26_9'].iloc[-1]) if not macd.empty else None
            result['macd_hist'] = float(macd['MACDh_12_26_9'].iloc[-1]) if not macd.empty else None
            
            # Añadir interpretación del MACD
            if all(v is not None for v in [result['macd_line'], result['macd_signal'], result['macd_hist']]):
                if result['macd_line'] > result['macd_signal']:
                    result['macd_trend'] = 'bullish'
                else:
                    result['macd_trend'] = 'bearish'
                
                # Detectar divergencia
                if len(close) > 20 and len(macd) > 20:
                    price_direction = 'up' if close.iloc[-1] > close.iloc[-10] else 'down'
                    macd_direction = 'up' if result['macd_line'] > float(macd['MACD_12_26_9'].iloc[-10]) else 'down'
                    
                    if price_direction != macd_direction:
                        result['macd_divergence'] = f'{macd_direction}_divergence'
                    else:
                        result['macd_divergence'] = 'none'
                else:
                    result['macd_divergence'] = None
            else:
                result['macd_trend'] = None
                result['macd_divergence'] = None
        except Exception:
            result.update({
                'macd_line': None, 
                'macd_signal': None, 
                'macd_hist': None,
                'macd_trend': None,
                'macd_divergence': None
            })
    
    # Stochastic Oscillator
    if 'stoch' in indicators or 'all' in indicators:
        try:
            stoch = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
            result['stoch_k'] = float(stoch['STOCHk_14_3_3'].iloc[-1]) if not stoch.empty else None
            result['stoch_d'] = float(stoch['STOCHd_14_3_3'].iloc[-1]) if not stoch.empty else None
            
            # Añadir interpretación del Estocástico
            if result['stoch_k'] is not None and result['stoch_d'] is not None:
                if result['stoch_k'] > 80 and result['stoch_d'] > 80:
                    result['stoch_signal'] = 'overbought'
                elif result['stoch_k'] < 20 and result['stoch_d'] < 20:
                    result['stoch_signal'] = 'oversold'
                else:
                    result['stoch_signal'] = 'neutral'
                
                # Detectar cruces
                if result['stoch_k'] > result['stoch_d']:
                    result['stoch_cross'] = 'bullish'
                else:
                    result['stoch_cross'] = 'bearish'
            else:
                result['stoch_signal'] = None
                result['stoch_cross'] = None
        except Exception:
            result.update({
                'stoch_k': None, 
                'stoch_d': None,
                'stoch_signal': None,
                'stoch_cross': None
            })
    
    # CCI - Commodity Channel Index
    if 'cci' in indicators or 'all' in indicators:
        for length in [14, 20]:
            key = f'cci_{length}'
            try:
                series = ta.cci(high, low, close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
                
                # Añadir interpretación del CCI
                if result[key] is not None:
                    if result[key] > 100:
                        result[f'{key}_signal'] = 'overbought'
                    elif result[key] < -100:
                        result[f'{key}_signal'] = 'oversold'
                    else:
                        result[f'{key}_signal'] = 'neutral'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # Williams %R
    if 'williams' in indicators or 'all' in indicators:
        for length in [14, 20]:
            key = f'williams_{length}'
            try:
                series = ta.willr(high, low, close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
                
                # Añadir interpretación del Williams %R
                if result[key] is not None:
                    if result[key] > -20:
                        result[f'{key}_signal'] = 'overbought'
                    elif result[key] < -80:
                        result[f'{key}_signal'] = 'oversold'
                    else:
                        result[f'{key}_signal'] = 'neutral'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # Ultimate Oscillator
    if 'ultimate' in indicators or 'all' in indicators:
        try:
            uo = ta.uo(high, low, close)
            result['uo'] = float(uo.iloc[-1]) if not uo.empty else None
            
            # Añadir interpretación del Ultimate Oscillator
            if result['uo'] is not None:
                if result['uo'] > 70:
                    result['uo_signal'] = 'overbought'
                elif result['uo'] < 30:
                    result['uo_signal'] = 'oversold'
                else:
                    result['uo_signal'] = 'neutral'
            else:
                result['uo_signal'] = None
        except Exception:
            result['uo'] = None
            result['uo_signal'] = None
    
    # Fisher Transform
    if 'fisher' in indicators or 'all' in indicators:
        try:
            fisher = ta.fisher(high, low, length=9)
            result['fisher'] = float(fisher['FISHERT_9'].iloc[-1]) if not fisher.empty else None
            result['fisher_signal'] = float(fisher['FISHERTs_9'].iloc[-1]) if not fisher.empty else None
            
            # Añadir interpretación del Fisher Transform
            if result['fisher'] is not None and result['fisher_signal'] is not None:
                if result['fisher'] > result['fisher_signal']:
                    result['fisher_trend'] = 'bullish'
                else:
                    result['fisher_trend'] = 'bearish'
            else:
                result['fisher_trend'] = None
        except Exception:
            result['fisher'] = None
            result['fisher_signal'] = None
            result['fisher_trend'] = None
    
    # Momentum
    if 'momentum' in indicators or 'all' in indicators:
        for length in [10, 14]:
            key = f'mom_{length}'
            try:
                series = ta.mom(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
                
                # Añadir interpretación del Momentum
                if result[key] is not None:
                    if result[key] > 0:
                        result[f'{key}_signal'] = 'bullish'
                    else:
                        result[f'{key}_signal'] = 'bearish'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # Rate of Change (ROC)
    if 'roc' in indicators or 'all' in indicators:
        for length in [10, 14]:
            key = f'roc_{length}'
            try:
                series = ta.roc(close, length=length)
                result[key] = float(series.iloc[-1]) if not series.empty else None
                
                # Añadir interpretación del ROC
                if result[key] is not None:
                    if result[key] > 0:
                        result[f'{key}_signal'] = 'bullish'
                    else:
                        result[f'{key}_signal'] = 'bearish'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # True Strength Index (TSI)
    if 'tsi' in indicators or 'all' in indicators:
        try:
            tsi = ta.tsi(close, fast=13, slow=25, signal=13)
            result['tsi'] = float(tsi['TSI_13_25'].iloc[-1]) if not tsi.empty else None
            result['tsi_signal'] = float(tsi['TSIs_13_25_13'].iloc[-1]) if not tsi.empty else None
            
            # Añadir interpretación del TSI
            if result['tsi'] is not None:
                if result['tsi'] > 0:
                    result['tsi_trend'] = 'bullish'
                else:
                    result['tsi_trend'] = 'bearish'
                
                if result['tsi_signal'] is not None:
                    if result['tsi'] > result['tsi_signal']:
                        result['tsi_cross'] = 'bullish'
                    else:
                        result['tsi_cross'] = 'bearish'
                else:
                    result['tsi_cross'] = None
            else:
                result['tsi_trend'] = None
                result['tsi_cross'] = None
        except Exception:
            result['tsi'] = None
            result['tsi_signal'] = None
            result['tsi_trend'] = None
            result['tsi_cross'] = None
    
    # Stochastic RSI
    if 'stochrsi' in indicators or 'all' in indicators:
        try:
            stochrsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
            result['stochrsi_k'] = float(stochrsi['STOCHRSIk_14_14_3_3'].iloc[-1]) if not stochrsi.empty else None
            result['stochrsi_d'] = float(stochrsi['STOCHRSId_14_14_3_3'].iloc[-1]) if not stochrsi.empty else None
            
            # Añadir interpretación del Stochastic RSI
            if result['stochrsi_k'] is not None and result['stochrsi_d'] is not None:
                if result['stochrsi_k'] > 80 and result['stochrsi_d'] > 80:
                    result['stochrsi_signal'] = 'overbought'
                elif result['stochrsi_k'] < 20 and result['stochrsi_d'] < 20:
                    result['stochrsi_signal'] = 'oversold'
                else:
                    result['stochrsi_signal'] = 'neutral'
                
                # Detectar cruces
                if result['stochrsi_k'] > result['stochrsi_d']:
                    result['stochrsi_cross'] = 'bullish'
                else:
                    result['stochrsi_cross'] = 'bearish'
            else:
                result['stochrsi_signal'] = None
                result['stochrsi_cross'] = None
        except Exception:
            result.update({
                'stochrsi_k': None, 
                'stochrsi_d': None,
                'stochrsi_signal': None,
                'stochrsi_cross': None
            })
    
    # Percentage Price Oscillator (PPO)
    if 'ppo' in indicators or 'all' in indicators:
        try:
            ppo = ta.ppo(close, fast=12, slow=26, signal=9)
            result['ppo'] = float(ppo['PPO_12_26_9'].iloc[-1]) if not ppo.empty else None
            result['ppo_signal'] = float(ppo['PPOs_12_26_9'].iloc[-1]) if not ppo.empty else None
            result['ppo_hist'] = float(ppo['PPOh_12_26_9'].iloc[-1]) if not ppo.empty else None
            
            # Añadir interpretación del PPO
            if all(v is not None for v in [result['ppo'], result['ppo_signal']]):
                if result['ppo'] > result['ppo_signal']:
                    result['ppo_trend'] = 'bullish'
                else:
                    result['ppo_trend'] = 'bearish'
            else:
                result['ppo_trend'] = None
        except Exception:
            result.update({
                'ppo': None, 
                'ppo_signal': None, 
                'ppo_hist': None,
                'ppo_trend': None
            })
    
    return result
