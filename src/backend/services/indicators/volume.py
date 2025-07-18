"""
Indicadores de volumen para análisis técnico de criptomonedas.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Union

def compute_volume_indicators(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calcula los indicadores de volumen para el DataFrame proporcionado.
    
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
    open_price = df['open']
    
    # Si no se especifican indicadores, calcular todos
    if indicators is None:
        indicators = [
            'obv', 'cmf', 'fi', 'mfi', 'vpt', 'nvi', 'pvi', 'vwap',
            'ad', 'adosc', 'eom', 'kvo', 'pvt', 'pvr'
        ]
    
    # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
    indicators = [ind.lower() for ind in indicators]
    
    # OBV - On Balance Volume
    if 'obv' in indicators or 'all' in indicators:
        try:
            obv = ta.obv(close, volume)
            result['obv'] = float(obv.iloc[-1]) if not obv.empty else None
            
            # Añadir interpretación del OBV
            if result['obv'] is not None and len(obv) > 10:
                # Calcular tendencia del OBV (últimos 10 períodos)
                obv_trend = obv.iloc[-10:].mean()
                if obv.iloc[-1] > obv_trend:
                    result['obv_trend'] = 'rising'
                else:
                    result['obv_trend'] = 'falling'
                
                # Detectar divergencia
                if len(close) > 10:
                    price_direction = 'up' if close.iloc[-1] > close.iloc[-10] else 'down'
                    obv_direction = 'up' if obv.iloc[-1] > obv.iloc[-10] else 'down'
                    
                    if price_direction != obv_direction:
                        result['obv_divergence'] = f'{obv_direction}_divergence'
                    else:
                        result['obv_divergence'] = 'none'
                else:
                    result['obv_divergence'] = None
            else:
                result['obv_trend'] = None
                result['obv_divergence'] = None
        except Exception:
            result['obv'] = None
            result['obv_trend'] = None
            result['obv_divergence'] = None
    
    # CMF - Chaikin Money Flow
    if 'cmf' in indicators or 'all' in indicators:
        for length in [20, 50]:
            key = f'cmf_{length}'
            try:
                cmf = ta.cmf(high, low, close, volume, length=length)
                result[key] = float(cmf.iloc[-1]) if not cmf.empty else None
                
                # Añadir interpretación del CMF
                if result[key] is not None:
                    if result[key] > 0.05:
                        result[f'{key}_signal'] = 'bullish'
                    elif result[key] < -0.05:
                        result[f'{key}_signal'] = 'bearish'
                    else:
                        result[f'{key}_signal'] = 'neutral'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # FI - Force Index
    if 'fi' in indicators or 'all' in indicators:
        for length in [13, 50]:
            key = f'fi_{length}'
            try:
                fi = ta.fi(close, volume, length=length)
                result[key] = float(fi.iloc[-1]) if not fi.empty else None
                
                # Añadir interpretación del Force Index
                if result[key] is not None:
                    if result[key] > 0:
                        result[f'{key}_signal'] = 'bullish'
                    else:
                        result[f'{key}_signal'] = 'bearish'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # MFI - Money Flow Index
    if 'mfi' in indicators or 'all' in indicators:
        for length in [14, 50]:
            key = f'mfi_{length}'
            try:
                mfi = ta.mfi(high, low, close, volume, length=length)
                result[key] = float(mfi.iloc[-1]) if not mfi.empty else None
                
                # Añadir interpretación del MFI
                if result[key] is not None:
                    if result[key] > 80:
                        result[f'{key}_signal'] = 'overbought'
                    elif result[key] < 20:
                        result[f'{key}_signal'] = 'oversold'
                    else:
                        result[f'{key}_signal'] = 'neutral'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # VPT - Volume Price Trend
    if 'vpt' in indicators or 'all' in indicators:
        try:
            vpt = ta.vpt(close, volume)
            result['vpt'] = float(vpt.iloc[-1]) if not vpt.empty else None
            
            # Añadir interpretación del VPT
            if result['vpt'] is not None and len(vpt) > 10:
                # Calcular tendencia del VPT (últimos 10 períodos)
                vpt_trend = vpt.iloc[-10:].mean()
                if vpt.iloc[-1] > vpt_trend:
                    result['vpt_trend'] = 'rising'
                else:
                    result['vpt_trend'] = 'falling'
            else:
                result['vpt_trend'] = None
        except Exception:
            result['vpt'] = None
            result['vpt_trend'] = None
    
    # NVI - Negative Volume Index
    if 'nvi' in indicators or 'all' in indicators:
        try:
            # Implementación manual del NVI
            nvi = pd.Series(index=close.index)
            nvi.iloc[0] = 1000  # Valor inicial
            
            for i in range(1, len(close)):
                if volume.iloc[i] < volume.iloc[i-1]:
                    nvi.iloc[i] = nvi.iloc[i-1] * (1 + ((close.iloc[i] - close.iloc[i-1]) / close.iloc[i-1]))
                else:
                    nvi.iloc[i] = nvi.iloc[i-1]
            
            result['nvi'] = float(nvi.iloc[-1]) if not nvi.empty else None
            
            # Añadir interpretación del NVI
            if result['nvi'] is not None and len(nvi) > 10:
                # Calcular tendencia del NVI (últimos 10 períodos)
                nvi_trend = nvi.iloc[-10:].mean()
                if nvi.iloc[-1] > nvi_trend:
                    result['nvi_trend'] = 'rising'
                else:
                    result['nvi_trend'] = 'falling'
            else:
                result['nvi_trend'] = None
        except Exception:
            result['nvi'] = None
            result['nvi_trend'] = None
    
    # PVI - Positive Volume Index
    if 'pvi' in indicators or 'all' in indicators:
        try:
            # Implementación manual del PVI
            pvi = pd.Series(index=close.index)
            pvi.iloc[0] = 1000  # Valor inicial
            
            for i in range(1, len(close)):
                if volume.iloc[i] > volume.iloc[i-1]:
                    pvi.iloc[i] = pvi.iloc[i-1] * (1 + ((close.iloc[i] - close.iloc[i-1]) / close.iloc[i-1]))
                else:
                    pvi.iloc[i] = pvi.iloc[i-1]
            
            result['pvi'] = float(pvi.iloc[-1]) if not pvi.empty else None
            
            # Añadir interpretación del PVI
            if result['pvi'] is not None and len(pvi) > 10:
                # Calcular tendencia del PVI (últimos 10 períodos)
                pvi_trend = pvi.iloc[-10:].mean()
                if pvi.iloc[-1] > pvi_trend:
                    result['pvi_trend'] = 'rising'
                else:
                    result['pvi_trend'] = 'falling'
            else:
                result['pvi_trend'] = None
        except Exception:
            result['pvi'] = None
            result['pvi_trend'] = None
    
    # AD - Accumulation/Distribution Line
    if 'ad' in indicators or 'all' in indicators:
        try:
            ad = ta.ad(high, low, close, volume)
            result['ad'] = float(ad.iloc[-1]) if not ad.empty else None
            
            # Añadir interpretación del AD
            if result['ad'] is not None and len(ad) > 10:
                # Calcular tendencia del AD (últimos 10 períodos)
                ad_trend = ad.iloc[-10:].mean()
                if ad.iloc[-1] > ad_trend:
                    result['ad_trend'] = 'rising'
                else:
                    result['ad_trend'] = 'falling'
                
                # Detectar divergencia
                if len(close) > 10:
                    price_direction = 'up' if close.iloc[-1] > close.iloc[-10] else 'down'
                    ad_direction = 'up' if ad.iloc[-1] > ad.iloc[-10] else 'down'
                    
                    if price_direction != ad_direction:
                        result['ad_divergence'] = f'{ad_direction}_divergence'
                    else:
                        result['ad_divergence'] = 'none'
                else:
                    result['ad_divergence'] = None
            else:
                result['ad_trend'] = None
                result['ad_divergence'] = None
        except Exception:
            result['ad'] = None
            result['ad_trend'] = None
            result['ad_divergence'] = None
    
    # ADOSC - Accumulation/Distribution Oscillator (Chaikin Oscillator)
    if 'adosc' in indicators or 'all' in indicators:
        try:
            adosc = ta.adosc(high, low, close, volume, fast=3, slow=10)
            result['adosc'] = float(adosc.iloc[-1]) if not adosc.empty else None
            
            # Añadir interpretación del ADOSC
            if result['adosc'] is not None:
                if result['adosc'] > 0:
                    result['adosc_signal'] = 'bullish'
                else:
                    result['adosc_signal'] = 'bearish'
            else:
                result['adosc_signal'] = None
        except Exception:
            result['adosc'] = None
            result['adosc_signal'] = None
    
    # EOM - Ease of Movement
    if 'eom' in indicators or 'all' in indicators:
        for length in [14, 20]:
            key = f'eom_{length}'
            try:
                eom = ta.eom(high, low, close, volume, length=length)
                result[key] = float(eom.iloc[-1]) if not eom.empty else None
                
                # Añadir interpretación del EOM
                if result[key] is not None:
                    if result[key] > 0:
                        result[f'{key}_signal'] = 'bullish'
                    else:
                        result[f'{key}_signal'] = 'bearish'
            except Exception:
                result[key] = None
                result[f'{key}_signal'] = None
    
    # KVO - Klinger Volume Oscillator
    if 'kvo' in indicators or 'all' in indicators:
        try:
            kvo = ta.kvo(high, low, close, volume, fast=34, slow=55, signal=13)
            result['kvo'] = float(kvo['KVO_34_55'].iloc[-1]) if not kvo.empty else None
            result['kvo_signal'] = float(kvo['KVOs_34_55_13'].iloc[-1]) if not kvo.empty else None
            
            # Añadir interpretación del KVO
            if result['kvo'] is not None and result['kvo_signal'] is not None:
                if result['kvo'] > result['kvo_signal']:
                    result['kvo_trend'] = 'bullish'
                else:
                    result['kvo_trend'] = 'bearish'
            else:
                result['kvo_trend'] = None
        except Exception:
            result['kvo'] = None
            result['kvo_signal'] = None
            result['kvo_trend'] = None
    
    # PVT - Price Volume Trend
    if 'pvt' in indicators or 'all' in indicators:
        try:
            # Implementación manual del PVT
            pvt = pd.Series(index=close.index)
            pvt.iloc[0] = 0  # Valor inicial
            
            for i in range(1, len(close)):
                pvt.iloc[i] = pvt.iloc[i-1] + (volume.iloc[i] * (close.iloc[i] - close.iloc[i-1]) / close.iloc[i-1])
            
            result['pvt'] = float(pvt.iloc[-1]) if not pvt.empty else None
            
            # Añadir interpretación del PVT
            if result['pvt'] is not None and len(pvt) > 10:
                # Calcular tendencia del PVT (últimos 10 períodos)
                pvt_trend = pvt.iloc[-10:].mean()
                if pvt.iloc[-1] > pvt_trend:
                    result['pvt_trend'] = 'rising'
                else:
                    result['pvt_trend'] = 'falling'
            else:
                result['pvt_trend'] = None
        except Exception:
            result['pvt'] = None
            result['pvt_trend'] = None
    
    # PVR - Price Volume Rank
    if 'pvr' in indicators or 'all' in indicators:
        try:
            # Implementación manual del PVR
            # Calcular el rango de precios
            price_range = high - low
            # Calcular el PVR como el producto del rango de precios y el volumen
            pvr = price_range * volume
            
            result['pvr'] = float(pvr.iloc[-1]) if not pvr.empty else None
            
            # Añadir interpretación del PVR
            if result['pvr'] is not None and len(pvr) > 10:
                # Calcular tendencia del PVR (últimos 10 períodos)
                pvr_trend = pvr.iloc[-10:].mean()
                if pvr.iloc[-1] > pvr_trend:
                    result['pvr_trend'] = 'rising'
                else:
                    result['pvr_trend'] = 'falling'
            else:
                result['pvr_trend'] = None
        except Exception:
            result['pvr'] = None
            result['pvr_trend'] = None
    
    return result
