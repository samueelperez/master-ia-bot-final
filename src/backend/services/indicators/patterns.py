"""
Detección de patrones chartistas y de velas para análisis técnico de criptomonedas.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple

def detect_patterns(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Detecta patrones chartistas y de velas en el DataFrame proporcionado.
    
    Args:
        df: DataFrame con datos OHLCV
        indicators: Lista de indicadores específicos a calcular. Si es None, calcula todos.
    
    Returns:
        Diccionario con los patrones detectados
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
            'candlestick', 'chart_patterns', 'harmonic_patterns', 'divergences'
        ]
    
    # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
    indicators = [ind.lower() for ind in indicators]
    
    # Patrones de velas japonesas
    if 'candlestick' in indicators or 'all' in indicators:
        try:
            # Función para calcular el tamaño del cuerpo y las sombras
            def candle_stats(df, i):
                body = abs(df['close'].iloc[i] - df['open'].iloc[i])
                upper_shadow = df['high'].iloc[i] - max(df['close'].iloc[i], df['open'].iloc[i])
                lower_shadow = min(df['close'].iloc[i], df['open'].iloc[i]) - df['low'].iloc[i]
                return body, upper_shadow, lower_shadow
            
            # Función para determinar si una vela es alcista o bajista
            def candle_direction(df, i):
                return 'bullish' if df['close'].iloc[i] > df['open'].iloc[i] else 'bearish'
            
            # Detectar patrones de velas individuales
            
            # Doji
            def is_doji(df, i, tolerance=0.05):
                body, upper_shadow, lower_shadow = candle_stats(df, i)
                price_range = df['high'].iloc[i] - df['low'].iloc[i]
                return body <= price_range * tolerance and price_range > 0
            
            # Martillo
            def is_hammer(df, i):
                body, upper_shadow, lower_shadow = candle_stats(df, i)
                return (lower_shadow > 2 * body and 
                        upper_shadow < 0.2 * body and 
                        body > 0)
            
            # Estrella fugaz
            def is_shooting_star(df, i):
                body, upper_shadow, lower_shadow = candle_stats(df, i)
                return (upper_shadow > 2 * body and 
                        lower_shadow < 0.2 * body and 
                        body > 0)
            
            # Vela envolvente
            def is_engulfing(df, i):
                if i == 0:
                    return False
                
                curr_body = abs(df['close'].iloc[i] - df['open'].iloc[i])
                prev_body = abs(df['close'].iloc[i-1] - df['open'].iloc[i-1])
                
                curr_direction = candle_direction(df, i)
                prev_direction = candle_direction(df, i-1)
                
                if curr_direction == prev_direction:
                    return False
                
                if curr_direction == 'bullish':
                    return (df['open'].iloc[i] <= df['close'].iloc[i-1] and 
                            df['close'].iloc[i] >= df['open'].iloc[i-1] and 
                            curr_body > prev_body)
                else:
                    return (df['open'].iloc[i] >= df['close'].iloc[i-1] and 
                            df['close'].iloc[i] <= df['open'].iloc[i-1] and 
                            curr_body > prev_body)
            
            # Patrón de estrella
            def is_star(df, i):
                if i < 2:
                    return False
                
                first_direction = candle_direction(df, i-2)
                middle_body, _, _ = candle_stats(df, i-1)
                first_body, _, _ = candle_stats(df, i-2)
                last_body, _, _ = candle_stats(df, i)
                
                # La vela del medio debe ser pequeña (tipo doji)
                if middle_body > 0.3 * first_body:
                    return False
                
                # Debe haber un gap entre la primera vela y la del medio
                if first_direction == 'bullish':
                    if df['close'].iloc[i-2] <= max(df['open'].iloc[i-1], df['close'].iloc[i-1]):
                        return False
                else:
                    if df['close'].iloc[i-2] >= min(df['open'].iloc[i-1], df['close'].iloc[i-1]):
                        return False
                
                # La tercera vela debe moverse en dirección opuesta a la primera
                last_direction = candle_direction(df, i)
                return last_direction != first_direction and last_body > 0.7 * first_body
            
            # Patrón de harami
            def is_harami(df, i):
                if i == 0:
                    return False
                
                curr_body = abs(df['close'].iloc[i] - df['open'].iloc[i])
                prev_body = abs(df['close'].iloc[i-1] - df['open'].iloc[i-1])
                
                curr_direction = candle_direction(df, i)
                prev_direction = candle_direction(df, i-1)
                
                if curr_direction == prev_direction:
                    return False
                
                if prev_direction == 'bullish':
                    return (df['open'].iloc[i] <= df['close'].iloc[i-1] and 
                            df['close'].iloc[i] >= df['open'].iloc[i-1] and 
                            curr_body < prev_body)
                else:
                    return (df['open'].iloc[i] >= df['close'].iloc[i-1] and 
                            df['close'].iloc[i] <= df['open'].iloc[i-1] and 
                            curr_body < prev_body)
            
            # Detectar patrones en las últimas velas
            last_idx = len(df) - 1
            
            # Patrones de velas individuales
            result['doji'] = is_doji(df, last_idx)
            result['hammer'] = is_hammer(df, last_idx)
            result['shooting_star'] = is_shooting_star(df, last_idx)
            
            # Patrones de velas múltiples
            result['engulfing'] = is_engulfing(df, last_idx)
            result['star'] = is_star(df, last_idx)
            result['harami'] = is_harami(df, last_idx)
            
            # Determinar la señal general de los patrones de velas
            bullish_patterns = ['hammer', 'engulfing', 'star', 'harami']
            bearish_patterns = ['shooting_star', 'engulfing', 'star', 'harami']
            
            bullish_count = sum(1 for pattern in bullish_patterns if result.get(pattern, False))
            bearish_count = sum(1 for pattern in bearish_patterns if result.get(pattern, False))
            
            if bullish_count > bearish_count:
                result['candlestick_signal'] = 'bullish'
            elif bearish_count > bullish_count:
                result['candlestick_signal'] = 'bearish'
            else:
                result['candlestick_signal'] = 'neutral'
        except Exception:
            result.update({
                'doji': None,
                'hammer': None,
                'shooting_star': None,
                'engulfing': None,
                'star': None,
                'harami': None,
                'candlestick_signal': None
            })
    
    # Patrones chartistas
    if 'chart_patterns' in indicators or 'all' in indicators:
        try:
            # Función para detectar tendencias
            def detect_trend(series, window=20):
                if len(series) < window:
                    return 'undefined'
                
                # Calcular la pendiente de la regresión lineal
                x = np.arange(window)
                y = series[-window:].values
                slope, _ = np.polyfit(x, y, 1)
                
                if slope > 0:
                    return 'uptrend'
                elif slope < 0:
                    return 'downtrend'
                else:
                    return 'sideways'
            
            # Función para detectar soportes y resistencias
            def find_support_resistance(df, window=20):
                if len(df) < window * 2:
                    return [], []
                
                # Encontrar máximos y mínimos locales
                highs = []
                lows = []
                
                for i in range(window, len(df) - window):
                    if all(df['high'].iloc[i] >= df['high'].iloc[i-j] for j in range(1, window)) and \
                       all(df['high'].iloc[i] >= df['high'].iloc[i+j] for j in range(1, window)):
                        highs.append((i, df['high'].iloc[i]))
                    
                    if all(df['low'].iloc[i] <= df['low'].iloc[i-j] for j in range(1, window)) and \
                       all(df['low'].iloc[i] <= df['low'].iloc[i+j] for j in range(1, window)):
                        lows.append((i, df['low'].iloc[i]))
                
                return highs, lows
            
            # Detectar tendencia actual
            current_trend = detect_trend(close)
            result['current_trend'] = current_trend
            
            # Encontrar soportes y resistencias
            highs, lows = find_support_resistance(df)
            
            # Detectar patrones chartistas
            
            # Doble techo
            def detect_double_top(df, highs):
                if len(highs) < 2:
                    return False
                
                # Buscar dos máximos similares
                for i in range(len(highs) - 1):
                    for j in range(i + 1, len(highs)):
                        idx1, price1 = highs[i]
                        idx2, price2 = highs[j]
                        
                        # Los máximos deben estar separados
                        if abs(idx2 - idx1) < 10:
                            continue
                        
                        # Los precios deben ser similares
                        if abs(price2 - price1) / price1 > 0.03:
                            continue
                        
                        # Debe haber un valle entre los dos máximos
                        min_between = df['low'].iloc[idx1:idx2].min()
                        
                        # El precio actual debe estar por debajo del valle
                        if df['close'].iloc[-1] < min_between:
                            return True
                
                return False
            
            # Doble suelo
            def detect_double_bottom(df, lows):
                if len(lows) < 2:
                    return False
                
                # Buscar dos mínimos similares
                for i in range(len(lows) - 1):
                    for j in range(i + 1, len(lows)):
                        idx1, price1 = lows[i]
                        idx2, price2 = lows[j]
                        
                        # Los mínimos deben estar separados
                        if abs(idx2 - idx1) < 10:
                            continue
                        
                        # Los precios deben ser similares
                        if abs(price2 - price1) / price1 > 0.03:
                            continue
                        
                        # Debe haber un pico entre los dos mínimos
                        max_between = df['high'].iloc[idx1:idx2].max()
                        
                        # El precio actual debe estar por encima del pico
                        if df['close'].iloc[-1] > max_between:
                            return True
                
                return False
            
            # Cabeza y hombros
            def detect_head_and_shoulders(df, highs):
                if len(highs) < 3:
                    return False
                
                # Buscar tres máximos donde el del medio es más alto
                for i in range(len(highs) - 2):
                    idx1, price1 = highs[i]
                    idx2, price2 = highs[i+1]
                    idx3, price3 = highs[i+2]
                    
                    # Los máximos deben estar separados
                    if abs(idx2 - idx1) < 5 or abs(idx3 - idx2) < 5:
                        continue
                    
                    # El máximo del medio debe ser más alto
                    if price2 <= price1 or price2 <= price3:
                        continue
                    
                    # Los hombros deben tener alturas similares
                    if abs(price3 - price1) / price1 > 0.1:
                        continue
                    
                    # Debe haber una línea de cuello (neckline)
                    min_between1 = df['low'].iloc[idx1:idx2].min()
                    min_between2 = df['low'].iloc[idx2:idx3].min()
                    
                    # La línea de cuello debe ser aproximadamente horizontal
                    if abs(min_between2 - min_between1) / min_between1 > 0.05:
                        continue
                    
                    # El precio actual debe estar por debajo de la línea de cuello
                    neckline = (min_between1 + min_between2) / 2
                    if df['close'].iloc[-1] < neckline:
                        return True
                
                return False
            
            # Cabeza y hombros invertido
            def detect_inverse_head_and_shoulders(df, lows):
                if len(lows) < 3:
                    return False
                
                # Buscar tres mínimos donde el del medio es más bajo
                for i in range(len(lows) - 2):
                    idx1, price1 = lows[i]
                    idx2, price2 = lows[i+1]
                    idx3, price3 = lows[i+2]
                    
                    # Los mínimos deben estar separados
                    if abs(idx2 - idx1) < 5 or abs(idx3 - idx2) < 5:
                        continue
                    
                    # El mínimo del medio debe ser más bajo
                    if price2 >= price1 or price2 >= price3:
                        continue
                    
                    # Los hombros deben tener alturas similares
                    if abs(price3 - price1) / price1 > 0.1:
                        continue
                    
                    # Debe haber una línea de cuello (neckline)
                    max_between1 = df['high'].iloc[idx1:idx2].max()
                    max_between2 = df['high'].iloc[idx2:idx3].max()
                    
                    # La línea de cuello debe ser aproximadamente horizontal
                    if abs(max_between2 - max_between1) / max_between1 > 0.05:
                        continue
                    
                    # El precio actual debe estar por encima de la línea de cuello
                    neckline = (max_between1 + max_between2) / 2
                    if df['close'].iloc[-1] > neckline:
                        return True
                
                return False
            
            # Triángulo ascendente
            def detect_ascending_triangle(df, highs, lows):
                if len(highs) < 2 or len(lows) < 2:
                    return False
                
                # Buscar una resistencia horizontal
                resistance_prices = [price for _, price in highs[-5:]]
                resistance_std = np.std(resistance_prices) / np.mean(resistance_prices)
                
                # La resistencia debe ser aproximadamente horizontal
                if resistance_std > 0.02:
                    return False
                
                # Buscar soportes ascendentes
                support_indices = [idx for idx, _ in lows[-5:]]
                support_prices = [price for _, price in lows[-5:]]
                
                if len(support_indices) < 2:
                    return False
                
                # Calcular la pendiente de los soportes
                x = np.array(support_indices)
                y = np.array(support_prices)
                slope, _ = np.polyfit(x, y, 1)
                
                # La pendiente debe ser positiva
                return slope > 0
            
            # Triángulo descendente
            def detect_descending_triangle(df, highs, lows):
                if len(highs) < 2 or len(lows) < 2:
                    return False
                
                # Buscar un soporte horizontal
                support_prices = [price for _, price in lows[-5:]]
                support_std = np.std(support_prices) / np.mean(support_prices)
                
                # El soporte debe ser aproximadamente horizontal
                if support_std > 0.02:
                    return False
                
                # Buscar resistencias descendentes
                resistance_indices = [idx for idx, _ in highs[-5:]]
                resistance_prices = [price for _, price in highs[-5:]]
                
                if len(resistance_indices) < 2:
                    return False
                
                # Calcular la pendiente de las resistencias
                x = np.array(resistance_indices)
                y = np.array(resistance_prices)
                slope, _ = np.polyfit(x, y, 1)
                
                # La pendiente debe ser negativa
                return slope < 0
            
            # Triángulo simétrico
            def detect_symmetric_triangle(df, highs, lows):
                if len(highs) < 2 or len(lows) < 2:
                    return False
                
                # Buscar resistencias descendentes
                resistance_indices = [idx for idx, _ in highs[-5:]]
                resistance_prices = [price for _, price in highs[-5:]]
                
                # Buscar soportes ascendentes
                support_indices = [idx for idx, _ in lows[-5:]]
                support_prices = [price for _, price in lows[-5:]]
                
                if len(resistance_indices) < 2 or len(support_indices) < 2:
                    return False
                
                # Calcular las pendientes
                x_res = np.array(resistance_indices)
                y_res = np.array(resistance_prices)
                slope_res, _ = np.polyfit(x_res, y_res, 1)
                
                x_sup = np.array(support_indices)
                y_sup = np.array(support_prices)
                slope_sup, _ = np.polyfit(x_sup, y_sup, 1)
                
                # La pendiente de resistencia debe ser negativa y la de soporte positiva
                return slope_res < 0 and slope_sup > 0
            
            # Detectar patrones
            result['double_top'] = detect_double_top(df, highs)
            result['double_bottom'] = detect_double_bottom(df, lows)
            result['head_and_shoulders'] = detect_head_and_shoulders(df, highs)
            result['inverse_head_and_shoulders'] = detect_inverse_head_and_shoulders(df, lows)
            result['ascending_triangle'] = detect_ascending_triangle(df, highs, lows)
            result['descending_triangle'] = detect_descending_triangle(df, highs, lows)
            result['symmetric_triangle'] = detect_symmetric_triangle(df, highs, lows)
            
            # Determinar la señal general de los patrones chartistas
            bullish_patterns = ['double_bottom', 'inverse_head_and_shoulders', 'ascending_triangle']
            bearish_patterns = ['double_top', 'head_and_shoulders', 'descending_triangle']
            
            bullish_count = sum(1 for pattern in bullish_patterns if result.get(pattern, False))
            bearish_count = sum(1 for pattern in bearish_patterns if result.get(pattern, False))
            
            if bullish_count > bearish_count:
                result['chart_pattern_signal'] = 'bullish'
            elif bearish_count > bullish_count:
                result['chart_pattern_signal'] = 'bearish'
            else:
                result['chart_pattern_signal'] = 'neutral'
        except Exception:
            result.update({
                'current_trend': None,
                'double_top': None,
                'double_bottom': None,
                'head_and_shoulders': None,
                'inverse_head_and_shoulders': None,
                'ascending_triangle': None,
                'descending_triangle': None,
                'symmetric_triangle': None,
                'chart_pattern_signal': None
            })
    
    # Patrones armónicos
    if 'harmonic_patterns' in indicators or 'all' in indicators:
        try:
            # Función para encontrar puntos de giro (swing highs/lows)
            def find_swings(df, window=5):
                swing_highs = []
                swing_lows = []
                
                for i in range(window, len(df) - window):
                    if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
                       all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                        swing_highs.append((i, df['high'].iloc[i]))
                    
                    if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
                       all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                        swing_lows.append((i, df['low'].iloc[i]))
                
                return swing_highs, swing_lows
            
            # Función para calcular ratios de Fibonacci
            def calculate_fib_ratio(move1, move2):
                if move1 == 0:
                    return float('inf')
                return abs(move2 / move1)
            
            # Detectar patrón Gartley
            def detect_gartley(swings, bullish=True):
                if len(swings) < 4:
                    return False
                
                # Tomar los últimos 4 puntos de giro
                points = swings[-4:]
                
                # Extraer precios
                x_idx, x_price = points[0]
                a_idx, a_price = points[1]
                b_idx, b_price = points[2]
                c_idx, c_price = points[3]
                
                # Verificar la secuencia de índices
                if not (x_idx < a_idx < b_idx < c_idx):
                    return False
                
                # Calcular movimientos
                xa = a_price - x_price
                ab = b_price - a_price
                bc = c_price - b_price
                
                # Calcular ratios
                ab_xa = calculate_fib_ratio(xa, ab)
                bc_ab = calculate_fib_ratio(ab, bc)
                
                # Verificar ratios para patrón Gartley
                if bullish:
                    return (0.618 * 0.9 <= ab_xa <= 0.618 * 1.1 and 
                            0.382 * 0.9 <= bc_ab <= 0.886 * 1.1 and 
                            x_price < a_price and a_price > b_price and b_price < c_price)
                else:
                    return (0.618 * 0.9 <= ab_xa <= 0.618 * 1.1 and 
                            0.382 * 0.9 <= bc_ab <= 0.886 * 1.1 and 
                            x_price > a_price and a_price < b_price and b_price > c_price)
            
            # Detectar patrón Butterfly
            def detect_butterfly(swings, bullish=True):
                if len(swings) < 4:
                    return False
                
                # Tomar los últimos 4 puntos de giro
                points = swings[-4:]
                
                # Extraer precios
                x_idx, x_price = points[0]
                a_idx, a_price = points[1]
                b_idx, b_price = points[2]
                c_idx, c_price = points[3]
                
                # Verificar la secuencia de índices
                if not (x_idx < a_idx < b_idx < c_idx):
                    return False
                
                # Calcular movimientos
                xa = a_price - x_price
                ab = b_price - a_price
                bc = c_price - b_price
                
                # Calcular ratios
                ab_xa = calculate_fib_ratio(xa, ab)
                bc_ab = calculate_fib_ratio(ab, bc)
                
                # Verificar ratios para patrón Butterfly
                if bullish:
                    return (0.786 * 0.9 <= ab_xa <= 0.786 * 1.1 and 
                            1.618 * 0.9 <= bc_ab <= 2.618 * 1.1 and 
                            x_price < a_price and a_price > b_price and b_price < c_price)
                else:
                    return (0.786 * 0.9 <= ab_xa <= 0.786 * 1.1 and 
                            1.618 * 0.9 <= bc_ab <= 2.618 * 1.1 and 
                            x_price > a_price and a_price < b_price and b_price > c_price)
            
            # Detectar patrón Bat
            def detect_bat(swings, bullish=True):
                if len(swings) < 4:
                    return False
                
                # Tomar los últimos 4 puntos de giro
                points = swings[-4:]
                
                # Extraer precios
                x_idx, x_price = points[0]
                a_idx, a_price = points[1]
                b_idx, b_price = points[2]
                c_idx, c_price = points[3]
                
                # Verificar la secuencia de índices
                if not (x_idx < a_idx < b_idx < c_idx):
                    return False
                
                # Calcular movimientos
                xa = a_price - x_price
                ab = b_price - a_price
                bc = c_price - b_price
                
                # Calcular ratios
                ab_xa = calculate_fib_ratio(xa, ab)
                bc_ab = calculate_fib_ratio(ab, bc)
                
                # Verificar ratios para patrón Bat
                if bullish:
                    return (0.382 * 0.9 <= ab_xa <= 0.5 * 1.1 and 
                            1.618 * 0.9 <= bc_ab <= 2.618 * 1.1 and 
                            x_price < a_price and a_price > b_price and b_price < c_price)
                else:
                    return (0.382 * 0.9 <= ab_xa <= 0.5 * 1.1 and 
                            1.618 * 0.9 <= bc_ab <= 2.618 * 1.1 and 
                            x_price > a_price and a_price < b_price and b_price > c_price)
            
            # Detectar patrón Crab
            def detect_crab(swings, bullish=True):
                if len(swings) < 4:
                    return False
                
                # Tomar los últimos 4 puntos de giro
                points = swings[-4:]
                
                # Extraer precios
                x_idx, x_price = points[0]
                a_idx, a_price = points[1]
                b_idx, b_price = points[2]
                c_idx, c_price = points[3]
                
                # Verificar la secuencia de índices
                if not (x_idx < a_idx < b_idx < c_idx):
                    return False
                
                # Calcular movimientos
                xa = a_price - x_price
                ab = b_price - a_price
                bc = c_price - b_price
                
                # Calcular ratios
                ab_xa = calculate_fib_ratio(xa, ab)
                bc_ab = calculate_fib_ratio(ab, bc)
                
                # Verificar ratios para patrón Crab
                if bullish:
                    return (0.382 * 0.9 <= ab_xa <= 0.618 * 1.1 and 
                            2.618 * 0.9 <= bc_ab <= 3.618 * 1.1 and 
                            x_price < a_price and a_price > b_price and b_price < c_price)
                else:
                    return (0.382 * 0.9 <= ab_xa <= 0.618 * 1.1 and 
                            2.618 * 0.9 <= bc_ab <= 3.618 * 1.1 and 
                            x_price > a_price and a_price < b_price and b_price > c_price)
            
            # Encontrar puntos de giro
            swing_highs, swing_lows = find_swings(df)
            
            # Detectar patrones armónicos
            result['bullish_gartley'] = detect_gartley(swing_lows, bullish=True)
            result['bearish_gartley'] = detect_gartley(swing_highs, bullish=False)
            
            result['bullish_butterfly'] = detect_butterfly(swing_lows, bullish=True)
            result['bearish_butterfly'] = detect_butterfly(swing_highs, bullish=False)
            
            result['bullish_bat'] = detect_bat(swing_lows, bullish=True)
            result['bearish_bat'] = detect_bat(swing_highs, bullish=False)
            
            result['bullish_crab'] = detect_crab(swing_lows, bullish=True)
            result['bearish_crab'] = detect_crab(swing_highs, bullish=False)
            
            # Determinar la señal general de los patrones armónicos
            bullish_patterns = ['bullish_gartley', 'bullish_butterfly', 'bullish_bat', 'bullish_crab']
            bearish_patterns = ['bearish_gartley', 'bearish_butterfly', 'bearish_bat', 'bearish_crab']
            
            bullish_count = sum(1 for pattern in bullish_patterns if result.get(pattern, False))
            bearish_count = sum(1 for pattern in bearish_patterns if result.get(pattern, False))
            
            if bullish_count > bearish_count:
                result['harmonic_pattern_signal'] = 'bullish'
            elif bearish_count > bullish_count:
                result['harmonic_pattern_signal'] = 'bearish'
            else:
                result['harmonic_pattern_signal'] = 'neutral'
        except Exception:
            result.update({
                'bullish_gartley': None, 'bearish_gartley': None,
                'bullish_butterfly': None, 'bearish_butterfly': None,
                'bullish_bat': None, 'bearish_bat': None,
                'bullish_crab': None, 'bearish_crab': None,
                'harmonic_pattern_signal': None
            })
    
    # Divergencias
    if 'divergences' in indicators or 'all' in indicators:
        try:
            # Función para detectar divergencias entre precio e indicadores
            def detect_divergence(price_series, indicator_series, window=20):
                if len(price_series) < window or len(indicator_series) < window:
                    return 'none'
                
                # Obtener los últimos N períodos
                price = price_series[-window:]
                indicator = indicator_series[-window:]
                
                # Calcular tendencias
                price_trend = 'up' if price.iloc[-1] > price.iloc[0] else 'down'
                indicator_trend = 'up' if indicator.iloc[-1] > indicator.iloc[0] else 'down'
                
                # Detectar divergencia
                if price_trend != indicator_trend:
                    if price_trend == 'up' and indicator_trend == 'down':
                        return 'bearish'  # Divergencia bajista (precio sube, indicador baja)
                    else:
                        return 'bullish'  # Divergencia alcista (precio baja, indicador sube)
                
                return 'none'
            
            # Calcular RSI para detectar divergencias
            if len(close) >= 14:
                rsi = ta.rsi(close, length=14)
                
                # Detectar divergencia RSI
                result['rsi_divergence'] = detect_divergence(close, rsi)
                
                # Calcular MACD para detectar divergencias
                macd = ta.macd(close, fast=12, slow=26, signal=9)
                if not macd.empty:
                    macd_line = macd['MACD_12_26_9']
                    result['macd_divergence'] = detect_divergence(close, macd_line)
                else:
                    result['macd_divergence'] = 'none'
                
                # Determinar la señal general de divergencias
                if result['rsi_divergence'] == 'bullish' or result['macd_divergence'] == 'bullish':
                    result['divergence_signal'] = 'bullish'
                elif result['rsi_divergence'] == 'bearish' or result['macd_divergence'] == 'bearish':
                    result['divergence_signal'] = 'bearish'
                else:
                    result['divergence_signal'] = 'neutral'
            else:
                result['rsi_divergence'] = 'none'
                result['macd_divergence'] = 'none'
                result['divergence_signal'] = 'neutral'
        except Exception:
            result.update({
                'rsi_divergence': None,
                'macd_divergence': None,
                'divergence_signal': None
            })
    
    # Señal general combinando todos los patrones
    try:
        signals = []
        
        if 'candlestick_signal' in result and result['candlestick_signal'] is not None:
            signals.append(result['candlestick_signal'])
        
        if 'chart_pattern_signal' in result and result['chart_pattern_signal'] is not None:
            signals.append(result['chart_pattern_signal'])
        
        if 'harmonic_pattern_signal' in result and result['harmonic_pattern_signal'] is not None:
            signals.append(result['harmonic_pattern_signal'])
        
        if 'divergence_signal' in result and result['divergence_signal'] is not None:
            signals.append(result['divergence_signal'])
        
        if signals:
            bullish_count = signals.count('bullish')
            bearish_count = signals.count('bearish')
            
            if bullish_count > bearish_count:
                result['overall_pattern_signal'] = 'bullish'
            elif bearish_count > bullish_count:
                result['overall_pattern_signal'] = 'bearish'
            else:
                result['overall_pattern_signal'] = 'neutral'
        else:
            result['overall_pattern_signal'] = 'neutral'
    except Exception:
        result['overall_pattern_signal'] = None
    
    return result
