"""
Indicadores de soporte y resistencia para análisis técnico de criptomonedas.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple

def compute_support_resistance(df: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calcula los niveles de soporte y resistencia para el DataFrame proporcionado.
    
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
            'fibonacci', 'pivots', 'sr_levels', 'demand_zones', 'supply_zones'
        ]
    
    # Convertir a minúsculas para comparación insensible a mayúsculas/minúsculas
    indicators = [ind.lower() for ind in indicators]
    
    # Fibonacci Retracement
    if 'fibonacci' in indicators or 'all' in indicators:
        try:
            # Encontrar máximo y mínimo recientes
            recent_high = high.iloc[-20:].max()
            recent_low = low.iloc[-20:].min()
            current_price = close.iloc[-1]
            
            # Calcular niveles de Fibonacci (retrocesos)
            fib_levels = {
                'fib_0': recent_low,
                'fib_0.236': recent_low + 0.236 * (recent_high - recent_low),
                'fib_0.382': recent_low + 0.382 * (recent_high - recent_low),
                'fib_0.5': recent_low + 0.5 * (recent_high - recent_low),
                'fib_0.618': recent_low + 0.618 * (recent_high - recent_low),
                'fib_0.786': recent_low + 0.786 * (recent_high - recent_low),
                'fib_1': recent_high
            }
            
            # Añadir extensiones de Fibonacci
            fib_levels.update({
                'fib_1.272': recent_low + 1.272 * (recent_high - recent_low),
                'fib_1.618': recent_low + 1.618 * (recent_high - recent_low),
                'fib_2.618': recent_low + 2.618 * (recent_high - recent_low)
            })
            
            # Añadir niveles al resultado
            result.update(fib_levels)
            
            # Determinar el nivel de Fibonacci más cercano al precio actual
            closest_level = min(fib_levels.items(), key=lambda x: abs(x[1] - current_price))
            result['closest_fib_level'] = closest_level[0]
            result['closest_fib_value'] = closest_level[1]
            
            # Determinar si el precio está por encima o por debajo del nivel más cercano
            if current_price > closest_level[1]:
                result['fib_position'] = 'above'
            else:
                result['fib_position'] = 'below'
        except Exception:
            result.update({
                'fib_0': None, 'fib_0.236': None, 'fib_0.382': None, 'fib_0.5': None,
                'fib_0.618': None, 'fib_0.786': None, 'fib_1': None,
                'fib_1.272': None, 'fib_1.618': None, 'fib_2.618': None,
                'closest_fib_level': None, 'closest_fib_value': None, 'fib_position': None
            })
    
    # Pivot Points
    if 'pivots' in indicators or 'all' in indicators:
        try:
            # Obtener datos del último día/semana completo
            if len(df) >= 2:
                prev_high = high.iloc[-2]
                prev_low = low.iloc[-2]
                prev_close = close.iloc[-2]
                current_price = close.iloc[-1]
                
                # Calcular pivot points (método clásico)
                pivot = (prev_high + prev_low + prev_close) / 3
                
                # Calcular niveles de soporte y resistencia
                s1 = (2 * pivot) - prev_high
                s2 = pivot - (prev_high - prev_low)
                s3 = s2 - (prev_high - prev_low)
                
                r1 = (2 * pivot) - prev_low
                r2 = pivot + (prev_high - prev_low)
                r3 = r2 + (prev_high - prev_low)
                
                # Añadir niveles al resultado
                result.update({
                    'pivot': pivot,
                    'pivot_s1': s1,
                    'pivot_s2': s2,
                    'pivot_s3': s3,
                    'pivot_r1': r1,
                    'pivot_r2': r2,
                    'pivot_r3': r3
                })
                
                # Determinar el nivel de pivot más cercano al precio actual
                pivot_levels = {
                    'pivot': pivot,
                    'pivot_s1': s1,
                    'pivot_s2': s2,
                    'pivot_s3': s3,
                    'pivot_r1': r1,
                    'pivot_r2': r2,
                    'pivot_r3': r3
                }
                
                closest_level = min(pivot_levels.items(), key=lambda x: abs(x[1] - current_price))
                result['closest_pivot_level'] = closest_level[0]
                result['closest_pivot_value'] = closest_level[1]
                
                # Determinar si el precio está por encima o por debajo del pivot
                if current_price > pivot:
                    result['pivot_position'] = 'above'
                else:
                    result['pivot_position'] = 'below'
            else:
                result.update({
                    'pivot': None, 'pivot_s1': None, 'pivot_s2': None, 'pivot_s3': None,
                    'pivot_r1': None, 'pivot_r2': None, 'pivot_r3': None,
                    'closest_pivot_level': None, 'closest_pivot_value': None, 'pivot_position': None
                })
        except Exception:
            result.update({
                'pivot': None, 'pivot_s1': None, 'pivot_s2': None, 'pivot_s3': None,
                'pivot_r1': None, 'pivot_r2': None, 'pivot_r3': None,
                'closest_pivot_level': None, 'closest_pivot_value': None, 'pivot_position': None
            })
    
    # Niveles de Soporte y Resistencia basados en máximos y mínimos históricos
    if 'sr_levels' in indicators or 'all' in indicators:
        try:
            # Función para identificar máximos y mínimos locales
            def find_local_extrema(series, window=5):
                highs = []
                lows = []
                
                for i in range(window, len(series) - window):
                    if all(series.iloc[i] > series.iloc[i-j] for j in range(1, window+1)) and \
                       all(series.iloc[i] > series.iloc[i+j] for j in range(1, window+1)):
                        highs.append((i, series.iloc[i]))
                    
                    if all(series.iloc[i] < series.iloc[i-j] for j in range(1, window+1)) and \
                       all(series.iloc[i] < series.iloc[i+j] for j in range(1, window+1)):
                        lows.append((i, series.iloc[i]))
                
                return highs, lows
            
            # Encontrar máximos y mínimos locales
            highs, lows = find_local_extrema(high, window=5)
            
            # Filtrar niveles significativos (aquellos que se repiten o están cerca)
            def cluster_levels(levels, tolerance=0.01):
                if not levels:
                    return []
                
                # Ordenar por precio
                sorted_levels = sorted(levels, key=lambda x: x[1])
                
                # Agrupar niveles cercanos
                clusters = []
                current_cluster = [sorted_levels[0]]
                
                for i in range(1, len(sorted_levels)):
                    current_level = sorted_levels[i]
                    prev_level = sorted_levels[i-1]
                    
                    # Si el nivel actual está cerca del anterior, añadirlo al cluster actual
                    if abs(current_level[1] - prev_level[1]) / prev_level[1] < tolerance:
                        current_cluster.append(current_level)
                    else:
                        # Si no, cerrar el cluster actual y empezar uno nuevo
                        clusters.append(current_cluster)
                        current_cluster = [current_level]
                
                # Añadir el último cluster
                if current_cluster:
                    clusters.append(current_cluster)
                
                # Calcular el valor promedio de cada cluster
                return [sum(level[1] for level in cluster) / len(cluster) for cluster in clusters]
            
            # Agrupar niveles cercanos
            resistance_levels = cluster_levels(highs)
            support_levels = cluster_levels(lows)
            
            # Ordenar niveles de mayor a menor
            resistance_levels = sorted(resistance_levels, reverse=True)
            support_levels = sorted(support_levels, reverse=True)
            
            # Añadir niveles al resultado (hasta 5 de cada uno)
            for i, level in enumerate(resistance_levels[:5]):
                result[f'resistance_{i+1}'] = level
            
            for i, level in enumerate(support_levels[:5]):
                result[f'support_{i+1}'] = level
            
            # Determinar niveles de soporte y resistencia más cercanos al precio actual
            current_price = close.iloc[-1]
            
            # Encontrar resistencia más cercana por encima del precio actual
            resistances_above = [r for r in resistance_levels if r > current_price]
            if resistances_above:
                result['nearest_resistance'] = min(resistances_above)
            else:
                result['nearest_resistance'] = None
            
            # Encontrar soporte más cercano por debajo del precio actual
            supports_below = [s for s in support_levels if s < current_price]
            if supports_below:
                result['nearest_support'] = max(supports_below)
            else:
                result['nearest_support'] = None
            
            # Calcular la distancia a los niveles más cercanos (como porcentaje)
            if result['nearest_resistance'] is not None:
                result['distance_to_resistance_pct'] = ((result['nearest_resistance'] / current_price) - 1) * 100
            else:
                result['distance_to_resistance_pct'] = None
            
            if result['nearest_support'] is not None:
                result['distance_to_support_pct'] = (1 - (result['nearest_support'] / current_price)) * 100
            else:
                result['distance_to_support_pct'] = None
        except Exception:
            for i in range(5):
                result[f'resistance_{i+1}'] = None
                result[f'support_{i+1}'] = None
            
            result.update({
                'nearest_resistance': None,
                'nearest_support': None,
                'distance_to_resistance_pct': None,
                'distance_to_support_pct': None
            })
    
    # Zonas de Demanda (Soporte)
    if 'demand_zones' in indicators or 'all' in indicators:
        try:
            # Identificar zonas de demanda (áreas de soporte con alto volumen)
            def find_demand_zones(df, lookback=50, min_volume_factor=1.5):
                zones = []
                
                # Calcular el volumen promedio
                avg_volume = df['volume'].iloc[-lookback:].mean()
                
                for i in range(len(df) - 3, max(0, len(df) - lookback), -1):
                    # Buscar velas con alto volumen
                    if df['volume'].iloc[i] > avg_volume * min_volume_factor:
                        # Buscar velas alcistas (cierre > apertura)
                        if df['close'].iloc[i] > df['open'].iloc[i]:
                            # La zona de demanda está entre el mínimo y la apertura
                            zone_low = df['low'].iloc[i]
                            zone_high = df['open'].iloc[i]
                            
                            # Añadir la zona si no se solapa con zonas existentes
                            if not any(z[0] <= zone_high and zone_low <= z[1] for z in zones):
                                zones.append((zone_low, zone_high))
                
                return zones[:5]  # Devolver las 5 zonas más recientes
            
            # Encontrar zonas de demanda
            demand_zones = find_demand_zones(df)
            
            # Añadir zonas al resultado
            for i, zone in enumerate(demand_zones):
                result[f'demand_zone_{i+1}_low'] = zone[0]
                result[f'demand_zone_{i+1}_high'] = zone[1]
            
            # Rellenar con None si hay menos de 5 zonas
            for i in range(len(demand_zones), 5):
                result[f'demand_zone_{i+1}_low'] = None
                result[f'demand_zone_{i+1}_high'] = None
            
            # Determinar si el precio actual está dentro de alguna zona de demanda
            current_price = close.iloc[-1]
            in_demand_zone = any(zone[0] <= current_price <= zone[1] for zone in demand_zones)
            result['in_demand_zone'] = in_demand_zone
            
            # Encontrar la zona de demanda más cercana por debajo del precio actual
            zones_below = [zone for zone in demand_zones if zone[1] < current_price]
            if zones_below:
                nearest_zone = max(zones_below, key=lambda x: x[1])
                result['nearest_demand_zone_low'] = nearest_zone[0]
                result['nearest_demand_zone_high'] = nearest_zone[1]
                result['distance_to_demand_zone_pct'] = (1 - (nearest_zone[1] / current_price)) * 100
            else:
                result['nearest_demand_zone_low'] = None
                result['nearest_demand_zone_high'] = None
                result['distance_to_demand_zone_pct'] = None
        except Exception:
            for i in range(5):
                result[f'demand_zone_{i+1}_low'] = None
                result[f'demand_zone_{i+1}_high'] = None
            
            result.update({
                'in_demand_zone': None,
                'nearest_demand_zone_low': None,
                'nearest_demand_zone_high': None,
                'distance_to_demand_zone_pct': None
            })
    
    # Zonas de Oferta (Resistencia)
    if 'supply_zones' in indicators or 'all' in indicators:
        try:
            # Identificar zonas de oferta (áreas de resistencia con alto volumen)
            def find_supply_zones(df, lookback=50, min_volume_factor=1.5):
                zones = []
                
                # Calcular el volumen promedio
                avg_volume = df['volume'].iloc[-lookback:].mean()
                
                for i in range(len(df) - 3, max(0, len(df) - lookback), -1):
                    # Buscar velas con alto volumen
                    if df['volume'].iloc[i] > avg_volume * min_volume_factor:
                        # Buscar velas bajistas (cierre < apertura)
                        if df['close'].iloc[i] < df['open'].iloc[i]:
                            # La zona de oferta está entre la apertura y el máximo
                            zone_low = df['open'].iloc[i]
                            zone_high = df['high'].iloc[i]
                            
                            # Añadir la zona si no se solapa con zonas existentes
                            if not any(z[0] <= zone_high and zone_low <= z[1] for z in zones):
                                zones.append((zone_low, zone_high))
                
                return zones[:5]  # Devolver las 5 zonas más recientes
            
            # Encontrar zonas de oferta
            supply_zones = find_supply_zones(df)
            
            # Añadir zonas al resultado
            for i, zone in enumerate(supply_zones):
                result[f'supply_zone_{i+1}_low'] = zone[0]
                result[f'supply_zone_{i+1}_high'] = zone[1]
            
            # Rellenar con None si hay menos de 5 zonas
            for i in range(len(supply_zones), 5):
                result[f'supply_zone_{i+1}_low'] = None
                result[f'supply_zone_{i+1}_high'] = None
            
            # Determinar si el precio actual está dentro de alguna zona de oferta
            current_price = close.iloc[-1]
            in_supply_zone = any(zone[0] <= current_price <= zone[1] for zone in supply_zones)
            result['in_supply_zone'] = in_supply_zone
            
            # Encontrar la zona de oferta más cercana por encima del precio actual
            zones_above = [zone for zone in supply_zones if zone[0] > current_price]
            if zones_above:
                nearest_zone = min(zones_above, key=lambda x: x[0])
                result['nearest_supply_zone_low'] = nearest_zone[0]
                result['nearest_supply_zone_high'] = nearest_zone[1]
                result['distance_to_supply_zone_pct'] = ((nearest_zone[0] / current_price) - 1) * 100
            else:
                result['nearest_supply_zone_low'] = None
                result['nearest_supply_zone_high'] = None
                result['distance_to_supply_zone_pct'] = None
        except Exception:
            for i in range(5):
                result[f'supply_zone_{i+1}_low'] = None
                result[f'supply_zone_{i+1}_high'] = None
            
            result.update({
                'in_supply_zone': None,
                'nearest_supply_zone_low': None,
                'nearest_supply_zone_high': None,
                'distance_to_supply_zone_pct': None
            })
    
    return result
