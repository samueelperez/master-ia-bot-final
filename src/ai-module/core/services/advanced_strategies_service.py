"""
Servicio de Estrategias Avanzadas de Trading
Implementa estrategias especializadas con prompts específicos.
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from fastapi import APIRouter

from ..models.request_models import AdvancedStrategyType
from .ai_service import AIService
from .data_service import DataService

logger = logging.getLogger(__name__)

@dataclass
class StrategyResult:
    """Resultado de una estrategia avanzada."""
    strategy_type: str
    signal: str  # "LONG", "SHORT", "NEUTRAL"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    reasoning: str = ""
    metadata: Dict[str, Any] = None

class AdvancedStrategiesService:
    """Servicio para estrategias avanzadas de trading."""
    def __init__(self, ai_service: AIService, data_service: DataService):
        self.ai_service = ai_service
        self.data_service = data_service
        self._strategy_prompts = {
            AdvancedStrategyType.DIVERGENCIA_CORRELACIONADA: self._get_divergencia_prompt,
            AdvancedStrategyType.ESTOCASTICO: self._get_estocastico_prompt,
            AdvancedStrategyType.SCALPING_ESTOCASTICO: self._get_estocastico_prompt,
            AdvancedStrategyType.FAIR_VALUE_GAP: self._get_fvg_prompt,
            AdvancedStrategyType.INTRADIA: self._get_intradia_prompt,
            AdvancedStrategyType.RSI: self._get_rsi_prompt,
            AdvancedStrategyType.SCALPING: self._get_scalping_prompt,
            AdvancedStrategyType.SMART_MONEY: self._get_smart_money_prompt,
            AdvancedStrategyType.VOLATILIDAD: self._get_volatilidad_prompt
        }

    async def execute_strategy(
        self,
        strategy_type: AdvancedStrategyType,
        symbol: str,
        timeframe: str,
        **kwargs
    ) -> StrategyResult:
        try:
            strategy_type_str = strategy_type.value if hasattr(strategy_type, "value") else str(strategy_type)
            logger.info(f"Ejecutando estrategia {strategy_type_str} para {symbol} en {timeframe}")
            
            # Convertir string a enum si es necesario
            if isinstance(strategy_type, str):
                try:
                    strategy_type = AdvancedStrategyType(strategy_type)
                except ValueError:
                    raise ValueError(f"Estrategia no válida: {strategy_type}")
            
            technical_data, indicators = await self._get_technical_data(symbol, timeframe, strategy_type, **kwargs)
            prompt_generator = self._strategy_prompts.get(strategy_type)
            if not prompt_generator:
                raise ValueError(f"Estrategia no soportada: {strategy_type}")
            
            prompt = prompt_generator()
            formatted_prompt = self._format_prompt(prompt, symbol, timeframe, technical_data, **kwargs)

            # LOG: Imprimir los datos técnicos enviados a la IA
            logger.info(f"[TRACE] DATOS TÉCNICOS ENVIADOS A LA IA:\n{technical_data}")

            ai_response = await self.ai_service.generate_custom_completion([{"role": "user", "content": formatted_prompt}])
            
            # LOG: Registrar la respuesta cruda de la IA para debugging
            logger.info(f"[TRACE] RESPUESTA CRUDA DE LA IA:\n{ai_response}")
            
            result = self._parse_strategy_response(ai_response, strategy_type, indicators)
            
            logger.info(f"Estrategia {strategy_type_str} completada: {result.signal}")
            return result
        except Exception as e:
            strategy_type_str = strategy_type.value if hasattr(strategy_type, "value") else str(strategy_type)
            logger.error(f"Error ejecutando estrategia {strategy_type_str}: {str(e)}")
            return StrategyResult(
                strategy_type=strategy_type_str,
                signal="NEUTRAL",
                reasoning=f"Error en análisis: {str(e)}"
            )

    async def _get_technical_data(self, symbol: str, timeframe: str, strategy_type: AdvancedStrategyType, **kwargs) -> tuple[str, Dict[str, Any]]:
        """Obtiene y formatea datos técnicos para la estrategia."""
        try:
            # Obtener datos básicos
            data = await self.data_service.get_market_data(symbol, timeframe)
            
            if not data:
                return "No se pudieron obtener datos del mercado."
            
            # Obtener datos adicionales según la estrategia
            if strategy_type == AdvancedStrategyType.DIVERGENCIA_CORRELACIONADA:
                correlated_symbol = kwargs.get('correlated_symbol', 'ETH')
                correlated_data = await self.data_service.get_market_data(correlated_symbol, timeframe)
                return self._format_correlation_data(data, correlated_symbol, correlated_data), {}
            
            # Obtener indicadores técnicos adicionales
            technical_indicators = await self._get_enhanced_technical_indicators(symbol, timeframe)
            
            return self._format_standard_data(data, technical_indicators), technical_indicators
            
        except Exception as e:
            logger.error(f"Error obteniendo datos técnicos: {str(e)}")
            return f"Error obteniendo datos: {str(e)}", {}

    async def _get_enhanced_technical_indicators(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Obtiene indicadores técnicos mejorados."""
        try:
            # Obtener datos OHLCV
            ohlcv_data = await self.data_service.get_ohlcv_data(symbol, timeframe, limit=100)
            
            if not ohlcv_data or len(ohlcv_data) < 50:
                return {}
            
            # Convertir a DataFrame para cálculos
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            indicators = {}
            
            # RSI múltiples períodos
            for period in [6, 14, 21]:
                indicators[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
            
            # MACD
            macd_data = self._calculate_macd(df['close'])
            indicators['macd'] = macd_data['macd']
            indicators['macd_signal'] = macd_data['signal']
            indicators['macd_histogram'] = macd_data['histogram']
            # Determinar dirección del MACD
            indicators['macd_direction'] = "ALCISTA" if macd_data['macd'] > macd_data['signal'] else "BAJISTA"
            
            # Medias móviles
            for period in [9, 20, 50, 200]:
                indicators[f'sma_{period}'] = df['close'].rolling(window=period).mean().iloc[-1]
                indicators[f'ema_{period}'] = df['close'].ewm(span=period).mean().iloc[-1]
            
            # Bandas de Bollinger
            bb_data = self._calculate_bollinger_bands(df['close'])
            indicators['bb_upper'] = bb_data['upper']
            indicators['bb_middle'] = bb_data['middle']
            indicators['bb_lower'] = bb_data['lower']
            indicators['bb_width'] = bb_data['width']
            
            # Determinar posición del precio en las Bandas de Bollinger
            current_price = df['close'].iloc[-1]
            bb_range = bb_data['upper'] - bb_data['lower']
            if bb_range > 0:
                bb_position_ratio = (current_price - bb_data['lower']) / bb_range
                if bb_position_ratio < 0.2:
                    indicators['bb_position'] = "INFERIOR"
                elif bb_position_ratio > 0.8:
                    indicators['bb_position'] = "SUPERIOR"
                else:
                    indicators['bb_position'] = "MEDIA"
            else:
                indicators['bb_position'] = "MEDIA"
            
            # Estocástico
            stoch_data = self._calculate_stochastic(df)
            indicators['stoch_k'] = stoch_data['k']
            indicators['stoch_d'] = stoch_data['d']
            
            # Volumen y volatilidad
            indicators['volume_sma'] = df['volume'].rolling(window=20).mean().iloc[-1]
            indicators['current_volume'] = df['volume'].iloc[-1]
            indicators['volume_ratio'] = indicators['current_volume'] / indicators['volume_sma'] if indicators['volume_sma'] > 0 else 1
            
            # ATR (Average True Range)
            indicators['atr'] = self._calculate_atr(df)
            
            # VWAP (Volume Weighted Average Price)
            vwap_data = self._calculate_vwap(df)
            indicators['vwap'] = vwap_data['vwap']
            indicators['vwap_upper_1'] = vwap_data['vwap_upper_1']
            indicators['vwap_upper_2'] = vwap_data['vwap_upper_2']
            indicators['vwap_lower_1'] = vwap_data['vwap_lower_1']
            indicators['vwap_lower_2'] = vwap_data['vwap_lower_2']
            indicators['vwap_position'] = vwap_data['vwap_position']
            indicators['vwap_distance'] = vwap_data['vwap_distance']
            
            # Niveles de soporte y resistencia
            support_resistance = self._calculate_support_resistance(df)
            indicators['support_levels'] = support_resistance['support']
            indicators['resistance_levels'] = support_resistance['resistance']
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {str(e)}")
            return {}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calcula RSI."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        except:
            return 50.0

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """Calcula MACD."""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            histogram = macd - signal_line
            
            return {
                'macd': macd.iloc[-1],
                'signal': signal_line.iloc[-1],
                'histogram': histogram.iloc[-1]
            }
        except:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calcula Bandas de Bollinger."""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            width = (upper - lower) / sma
            
            return {
                'upper': upper.iloc[-1],
                'middle': sma.iloc[-1],
                'lower': lower.iloc[-1],
                'width': width.iloc[-1]
            }
        except:
            return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0, 'width': 0.0}

    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """Calcula Estocástico."""
        try:
            low_min = df['low'].rolling(window=k_period).min()
            high_max = df['high'].rolling(window=k_period).max()
            k = 100 * ((df['close'] - low_min) / (high_max - low_min))
            d = k.rolling(window=d_period).mean()
            
            return {
                'k': k.iloc[-1],
                'd': d.iloc[-1]
            }
        except:
            return {'k': 50.0, 'd': 50.0}

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula ATR."""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()
            return atr.iloc[-1]
        except:
            return 0.0

    def _calculate_vwap(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula VWAP (Volume Weighted Average Price)."""
        try:
            # Calcular precio típico
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Calcular VWAP
            vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
            
            # Calcular desviaciones estándar para bandas
            vwap_std = ((typical_price - vwap) ** 2 * df['volume']).cumsum() / df['volume'].cumsum()
            vwap_std = np.sqrt(vwap_std)
            
            # Bandas VWAP (+1, +2, -1, -2 desviaciones estándar)
            vwap_upper_1 = vwap + vwap_std
            vwap_upper_2 = vwap + (2 * vwap_std)
            vwap_lower_1 = vwap - vwap_std
            vwap_lower_2 = vwap - (2 * vwap_std)
            
            # Determinar posición del precio actual respecto al VWAP
            current_price = df['close'].iloc[-1]
            current_vwap = vwap.iloc[-1]
            
            if current_price > current_vwap:
                vwap_position = "SOBRE_VWAP"
            elif current_price < current_vwap:
                vwap_position = "BAJO_VWAP"
            else:
                vwap_position = "EN_VWAP"
            
            return {
                'vwap': current_vwap,
                'vwap_upper_1': vwap_upper_1.iloc[-1],
                'vwap_upper_2': vwap_upper_2.iloc[-1],
                'vwap_lower_1': vwap_lower_1.iloc[-1],
                'vwap_lower_2': vwap_lower_2.iloc[-1],
                'vwap_position': vwap_position,
                'vwap_distance': abs(current_price - current_vwap) / current_vwap * 100  # Distancia en %
            }
        except Exception as e:
            logger.error(f"Error calculando VWAP: {str(e)}")
            return {
                'vwap': 0.0,
                'vwap_upper_1': 0.0,
                'vwap_upper_2': 0.0,
                'vwap_lower_1': 0.0,
                'vwap_lower_2': 0.0,
                'vwap_position': "ERROR",
                'vwap_distance': 0.0
            }

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calcula niveles de soporte y resistencia."""
        try:
            # Método simple basado en pivots
            highs = df['high'].rolling(window=5, center=True).max()
            lows = df['low'].rolling(window=5, center=True).min()
            
            # Encontrar pivots
            resistance_levels = []
            support_levels = []
            
            for i in range(2, len(df) - 2):
                if df['high'].iloc[i] == highs.iloc[i]:
                    resistance_levels.append(df['high'].iloc[i])
                if df['low'].iloc[i] == lows.iloc[i]:
                    support_levels.append(df['low'].iloc[i])
            
            # Tomar los 3 niveles más cercanos al precio actual
            current_price = df['close'].iloc[-1]
            
            resistance_levels = sorted([r for r in resistance_levels if r > current_price])[:3]
            support_levels = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]
            
            return {
                'resistance': resistance_levels,
                'support': support_levels
            }
        except:
            return {'resistance': [], 'support': []}

    def _format_correlation_data(self, data: Dict, correlated_symbol: str, correlated_data: Dict) -> str:
        if not correlated_symbol:
            return "Símbolo correlacionado no especificado"
        return f"Datos de {data.get('symbol', 'N/A')} y {correlated_symbol}\n\nDatos de {correlated_symbol}:\n{self._format_standard_data(correlated_data)}"

    def _format_standard_data(self, data: Dict, indicators: Dict[str, Any] = None) -> str:
        """Formatea datos estándar con indicadores técnicos y contexto de tendencia/volatilidad."""
        try:
            current_price = data.get('current_price', 0)
            price_change_24h = data.get('price_change_24h', 0)
            volume_24h = data.get('volume_24h', 0)
            timeframe = data.get('timeframe', '-')
            
            # Últimas velas
            candles = data.get('candles', [])
            if candles:
                recent_candles = candles[-3:] if len(candles) >= 3 else candles
                candles_text = "\n".join([
                    f"Vela {i+1}: O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']:.2f}"
                    for i, candle in enumerate(recent_candles)
                ])
            else:
                candles_text = "No hay datos de velas disponibles"
            
            # Indicadores técnicos
            indicators_text = ""
            if indicators:
                indicators_text = "\n\n📊 INDICADORES TÉCNICOS:\n"
                # RSI
                rsi_values = []
                for period in [6, 14, 21]:
                    rsi_key = f'rsi_{period}'
                    if rsi_key in indicators and indicators[rsi_key] is not None:
                        rsi_values.append(f"RSI({period}): {indicators[rsi_key]:.1f}")
                if rsi_values:
                    indicators_text += f"• {' | '.join(rsi_values)}\n"
                # MACD
                if 'macd' in indicators and indicators['macd'] is not None:
                    macd_trend = "ALCISTA" if indicators['macd'] > indicators.get('macd_signal', 0) else "BAJISTA"
                    indicators_text += f"• MACD: {indicators['macd']:.4f} | Señal: {indicators.get('macd_signal', 0):.4f} | {macd_trend}\n"
                # Medias móviles
                ma_values = []
                for period in [9, 20, 50, 200]:
                    sma_key = f'sma_{period}'
                    ema_key = f'ema_{period}'
                    if sma_key in indicators and indicators[sma_key] is not None:
                        ma_values.append(f"SMA({period}): {indicators[sma_key]:.2f}")
                    if ema_key in indicators and indicators[ema_key] is not None:
                        ma_values.append(f"EMA({period}): {indicators[ema_key]:.2f}")
                if ma_values:
                    indicators_text += f"• {' | '.join(ma_values[:6])}\n"
                # Bandas de Bollinger
                if 'bb_upper' in indicators and indicators['bb_upper'] is not None:
                    bb_position = "SUPERIOR" if current_price > indicators['bb_upper'] else "INFERIOR" if current_price < indicators['bb_lower'] else "MEDIA"
                    indicators_text += f"• BB: Superior: {indicators['bb_upper']:.2f} | Media: {indicators['bb_middle']:.2f} | Inferior: {indicators['bb_lower']:.2f} | Posición: {bb_position}\n"
                # Estocástico
                if 'stoch_k' in indicators and indicators['stoch_k'] is not None:
                    stoch_zone = "SOBRECOMPRA" if indicators['stoch_k'] > 80 else "SOBREVENTA" if indicators['stoch_k'] < 20 else "NEUTRAL"
                    indicators_text += f"• Estocástico: %K: {indicators['stoch_k']:.1f} | %D: {indicators.get('stoch_d', 0):.1f} | Zona: {stoch_zone}\n"
                # Volumen
                if 'volume_ratio' in indicators and indicators['volume_ratio'] is not None:
                    volume_status = "ALTO" if indicators['volume_ratio'] > 1.5 else "BAJO" if indicators['volume_ratio'] < 0.5 else "NORMAL"
                    indicators_text += f"• Volumen: {volume_status} (Ratio: {indicators['volume_ratio']:.2f})\n"
                # ATR
                if 'atr' in indicators and indicators['atr'] is not None:
                    indicators_text += f"• ATR: {indicators['atr']:.2f}\n"
                # VWAP
                if 'vwap' in indicators and indicators['vwap'] is not None:
                    vwap_status = indicators.get('vwap_position', 'NEUTRAL')
                    vwap_distance = indicators.get('vwap_distance', 0)
                    indicators_text += f"• VWAP: {indicators['vwap']:.2f} | Posición: {vwap_status} | Distancia: {vwap_distance:.2f}%\n"
                # Soporte y Resistencia
                if 'support_levels' in indicators and indicators['support_levels']:
                    support_text = ", ".join([f"${level:.2f}" for level in indicators['support_levels'][:2]])
                    indicators_text += f"• Soporte: {support_text}\n"
                if 'resistance_levels' in indicators and indicators['resistance_levels']:
                    resistance_text = ", ".join([f"${level:.2f}" for level in indicators['resistance_levels'][:2]])
                    indicators_text += f"• Resistencia: {resistance_text}\n"
            # Contexto de tendencia y volatilidad
            tendencia = "ALCISTA" if price_change_24h > 0.5 else "BAJISTA" if price_change_24h < -0.5 else "LATERAL"
            volatilidad = "ALTA" if indicators and indicators.get('atr', 0) > 0.01 * current_price else "BAJA"
            contexto = f"\nTendencia: {tendencia} | Volatilidad: {volatilidad} | Timeframe: {timeframe}"
            return (
                f"💰 Precio actual: ${current_price:,.2f}\n"
                f"📈 Cambio 24h: {price_change_24h:+.2f}%\n"
                f"📊 Volumen 24h: ${volume_24h:,.0f}\n\n"
                f"🕯️ ÚLTIMAS VELAS:\n{candles_text}"
                f"{indicators_text}"
                f"{contexto}"
            )
        except Exception as e:
            logger.error(f"Error formateando datos: {str(e)}")
            return f"Error formateando datos: {str(e)}"

    def _format_prompt(self, prompt: str, symbol: str, timeframe: str, data: str, **kwargs) -> str:
        return prompt.format(
            activo=symbol,
            timeframe=timeframe,
            datos_tecnicos=data,
            **kwargs
        )

    def _parse_strategy_response(self, response: str, strategy_type: AdvancedStrategyType, technical_data: Dict[str, Any] = None) -> StrategyResult:
        try:
            signal = self._extract_signal(response)
            entry_price = self._extract_price(response, "entrada")
            stop_loss = self._extract_price(response, "stop")
            take_profit = self._extract_price(response, "profit")
            confidence = self._calculate_confidence(response)
            
            # Validar coherencia de la señal antes de devolverla
            is_valid, error_message = self._validate_signal_coherence(
                signal, entry_price, stop_loss, take_profit, confidence
            )
            
            # Si la señal es válida, validar confluencia de indicadores
            if is_valid and signal in ["LONG", "SHORT"] and technical_data:
                confluence_valid, confluence_error = self._validate_indicator_confluence(signal, technical_data)
                if not confluence_valid:
                    is_valid = False
                    error_message = confluence_error
            
            # Obtener el valor del enum como string
            strategy_type_value = strategy_type.value if hasattr(strategy_type, "value") else str(strategy_type)
            
            if not is_valid:
                logger.warning(f"Señal inválida detectada: {error_message}")
                return StrategyResult(
                    strategy_type=strategy_type_value,
                    signal="NEUTRAL",
                    confidence=0.0,
                    reasoning=f"No hay oportunidad real de trading en este momento. {error_message}"
                )
            
            return StrategyResult(
                strategy_type=strategy_type_value,
                signal=signal,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                reasoning=response[:500]
            )
        except Exception as e:
            logger.error(f"Error parseando respuesta: {str(e)}")
            
            # Obtener el valor del enum como string
            strategy_type_value = strategy_type.value if hasattr(strategy_type, "value") else str(strategy_type)
            
            return StrategyResult(
                strategy_type=strategy_type_value,
                signal="NEUTRAL",
                reasoning=f"Error parseando respuesta: {str(e)}"
            )

    def _extract_signal(self, response: str) -> str:
        response_lower = response.lower()
        if "long" in response_lower:
            return "LONG"
        elif "short" in response_lower:
            return "SHORT"
        else:
            return "NEUTRAL"

    def _extract_price(self, response: str, price_type: str) -> Optional[float]:
        # Mapear los tipos a los campos exactos del formato de la IA
        field_map = {
            "entrada": [r"ENTRY_PRICE[:\s\$]*([\d,]+\.?\d*)", r"ENTRADA[:\s\$]*([\d,]+\.?\d*)"],
            "stop": [r"STOP_LOSS[:\s\$]*([\d,]+\.?\d*)", r"STOP[:\s\$]*([\d,]+\.?\d*)"],
            "profit": [r"TAKE_PROFIT[:\s\$]*([\d,]+\.?\d*)", r"PROFIT[:\s\$]*([\d,]+\.?\d*)"],
        }
        patterns = field_map.get(price_type.lower(), [])
        # Buscar primero por el campo exacto
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    return float(price_str)
                except ValueError:
                    continue
        # Fallback: buscar el primer número después de la palabra clave
        fallback_patterns = [
            rf'{price_type}.*?([\d,]+\.?\d*)',
            r'\$([\d,]+\.?\d*)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'(\d+\.\d+)',
            r'(\d+)'
        ]
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    return float(price_str)
                except ValueError:
                    continue
        return None

    def _calculate_confidence(self, response: str) -> float:
        # Primero intentar extraer el valor de CONFIDENCE directamente de la respuesta
        confidence_patterns = [
            r'CONFIDENCE[:\s]*([\d.]+)',
            r'confianza[:\s]*([\d.]+)',
            r'CONFIANZA[:\s]*([\d.]+)'
        ]
        
        for pattern in confidence_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    confidence = float(match.group(1))
                    # Asegurar que esté en el rango 0-1
                    return max(0.0, min(1.0, confidence))
                except ValueError:
                    continue
        
        # Fallback: calcular confianza basada en palabras clave
        confidence_indicators = [
            "señal clara",
            "oportunidad válida", 
            "configuración operativa",
            "punto de entrada",
            "stop loss",
            "take profit"
        ]
        confidence = 0.0
        response_lower = response.lower()
        for indicator in confidence_indicators:
            if indicator in response_lower:
                confidence += 0.15
        if "no hay" in response_lower or "no se detecta" in response_lower:
            confidence = 0.0
        return min(confidence, 1.0)

    def _validate_indicator_confluence(self, signal: str, technical_data: Dict[str, Any]) -> (bool, str):
        """Valida que los indicadores técnicos confirmen la dirección de la señal."""
        try:
            rsi_14 = technical_data.get('rsi_14', 50)
            macd_direction = technical_data.get('macd_direction', 'NEUTRAL')
            bb_position = technical_data.get('bb_position', 'MEDIA')
            vwap_position = technical_data.get('vwap_position', 'EN_VWAP')
            volume_ratio = technical_data.get('volume_ratio', 1.0)
            atr = technical_data.get('atr', 0)
            
            if signal == "LONG":
                # Para LONG: RSI en sobreventa REAL Y MACD alcista Y (precio cerca de banda inferior O bajo VWAP)
                rsi_ok = rsi_14 < 30  # Más estricto: sobreventa real
                macd_ok = macd_direction == "ALCISTA"
                bb_ok = bb_position in ["INFERIOR", "MEDIA"]
                vwap_ok = vwap_position == "BAJO_VWAP"
                volume_ok = volume_ratio > 1.2  # Volumen superior al promedio
                atr_ok = atr > 0  # ATR válido
                
                # Mínimo 3 de los 6 indicadores deben confirmar (más estricto)
                confluence_count = sum([rsi_ok, macd_ok, bb_ok, vwap_ok, volume_ok, atr_ok])
                if confluence_count >= 3:
                    return True, f"Confluencia válida: {confluence_count}/6 indicadores confirmando LONG"
                else:
                    return False, f"Confluencia insuficiente: {confluence_count}/6 indicadores confirmando LONG (mínimo 3 requeridos)"
                    
            elif signal == "SHORT":
                # Para SHORT: RSI en sobrecompra REAL Y MACD bajista Y (precio cerca de banda superior O sobre VWAP)
                rsi_ok = rsi_14 > 70  # Más estricto: sobrecompra real
                macd_ok = macd_direction == "BAJISTA"
                bb_ok = bb_position in ["SUPERIOR", "MEDIA"]
                vwap_ok = vwap_position == "SOBRE_VWAP"
                volume_ok = volume_ratio > 1.2  # Volumen superior al promedio
                atr_ok = atr > 0  # ATR válido
                
                # Mínimo 3 de los 6 indicadores deben confirmar (más estricto)
                confluence_count = sum([rsi_ok, macd_ok, bb_ok, vwap_ok, volume_ok, atr_ok])
                if confluence_count >= 3:
                    return True, f"Confluencia válida: {confluence_count}/6 indicadores confirmando SHORT"
                else:
                    return False, f"Confluencia insuficiente: {confluence_count}/6 indicadores confirmando SHORT (mínimo 3 requeridos)"
            else:
                return True, "Señal NEUTRAL - no requiere validación de confluencia"
                
        except Exception as e:
            return False, f"Error validando confluencia: {str(e)}"

    def _validate_signal_coherence(self, signal: str, entry_price: Optional[float], 
                                  stop_loss: Optional[float], take_profit: Optional[float], 
                                  confidence: float) -> (bool, str):
        """Valida coherencia de la señal antes de devolverla. Devuelve (valido, mensaje_error)."""
        try:
            # Verificar que todos los precios estén presentes
            if entry_price is None or stop_loss is None or take_profit is None:
                return False, "Faltan niveles de precio en la señal"
            
            # Verificar que no sean todos iguales (caso más común de señal inválida)
            if entry_price == stop_loss == take_profit:
                return False, "Los niveles de entrada, stop loss y take profit son idénticos"
            
            # Verificar que la señal sea válida
            if signal not in ["LONG", "SHORT"]:
                return False, "Señal no válida (debe ser LONG o SHORT)"
            
            # Verificar coherencia según la dirección
            if signal == "LONG":
                if not (stop_loss < entry_price < take_profit):
                    return False, "Niveles incoherentes para LONG (SL < Entrada < TP)"
            elif signal == "SHORT":
                if not (take_profit < entry_price < stop_loss):
                    return False, "Niveles incoherentes para SHORT (TP < Entrada < SL)"
            
            # Verificar ratio riesgo/beneficio mínimo
            if signal == "LONG":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # SHORT
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk <= 0 or reward <= 0:
                return False, "Riesgo o beneficio no válido"
            
            rr = reward / risk
            if rr < 1.5:  # Ratio mínimo más estricto para scalping
                return False, f"Ratio riesgo/beneficio insuficiente: {rr:.2f} (mínimo 1.5 requerido)"
            
            # Verificar que el stop loss no sea muy cercano (mínimo 2% del precio)
            min_stop_distance = entry_price * 0.02  # 2%
            if signal == "LONG" and (entry_price - stop_loss) < min_stop_distance:
                return False, f"Stop loss muy cercano: {(entry_price - stop_loss):.2f} (mínimo {min_stop_distance:.2f} requerido)"
            elif signal == "SHORT" and (stop_loss - entry_price) < min_stop_distance:
                return False, f"Stop loss muy cercano: {(stop_loss - entry_price):.2f} (mínimo {min_stop_distance:.2f} requerido)"
            
            # Verificar que el take profit sea suficientemente lejano (mínimo 3% del precio)
            min_tp_distance = entry_price * 0.03  # 3%
            if signal == "LONG" and (take_profit - entry_price) < min_tp_distance:
                return False, f"Take profit muy cercano: {(take_profit - entry_price):.2f} (mínimo {min_tp_distance:.2f} requerido)"
            elif signal == "SHORT" and (entry_price - take_profit) < min_tp_distance:
                return False, f"Take profit muy cercano: {(entry_price - take_profit):.2f} (mínimo {min_tp_distance:.2f} requerido)"
            
            # Verificar confianza mínima
            if confidence < 0.05:
                return False, "Confianza muy baja en la señal"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validando coherencia: {str(e)}"

    def _validate_signal(self, signal: dict) -> (bool, str):
        """Valida coherencia de niveles y ratio riesgo/beneficio. Devuelve (valido, mensaje_error)."""
        try:
            entry = float(signal.get('entry', 0))
            stop = float(signal.get('stop_loss', 0))
            tp1 = float(signal.get('take_profit_1', 0))
            tp2 = float(signal.get('take_profit_2', tp1))
            direction = signal.get('direction', '').lower()
            # Validación de niveles
            if direction == 'long':
                if not (stop < entry < tp1 <= tp2):
                    return False, 'Niveles incoherentes para LONG (SL < Entrada < TP1 <= TP2)'
                risk = entry - stop
                reward = tp1 - entry
            elif direction == 'short':
                if not (tp2 <= tp1 < entry < stop):
                    return False, 'Niveles incoherentes para SHORT (TP2 <= TP1 < Entrada < SL)'
                risk = stop - entry
                reward = entry - tp1
            else:
                return False, 'Dirección de señal no reconocida'
            # Ratio riesgo/beneficio
            if risk <= 0 or reward <= 0:
                return False, 'Riesgo o beneficio no válido'
            rr = reward / risk
            if rr < 1.5:
                return False, f'Ratio riesgo/beneficio bajo: {rr:.2f} (<1.5)'
            return True, ''
        except Exception as e:
            return False, f'Error validando señal: {e}'

    def _log_signal_trace(self, datos_tecnicos: str, respuesta_ia: str):
        """Registra en logs los datos técnicos enviados y la respuesta de la IA."""
        import logging
        logger = logging.getLogger("core.services.advanced_strategies_service")
        logger.info(f"[TRACE] Datos técnicos enviados a IA:\n{datos_tecnicos}")
        logger.info(f"[TRACE] Respuesta IA:\n{respuesta_ia}")

    # Prompts corregidos usando comillas simples triples
    def _get_divergencia_prompt(self) -> str:
        return '''Actúa como un analista técnico especializado en estrategias de divergencias correlacionadas. Analiza el activo principal {activo_1} y un activo secundario correlacionado {activo_2} en el timeframe {timeframe}. A continuación se te entregan los datos técnicos recientes de ambos activos, incluyendo precio, volumen e indicadores técnicos como RSI, MACD o Estocástico:

Activo 1 ({activo_1}): {datos_tecnicos_1}
Activo 2 ({activo_2}): {datos_tecnicos_2}

1. Detecta si hay una divergencia relevante entre los dos activos:
   - ¿Uno de los activos hace un nuevo máximo o mínimo, pero el otro no?
   - ¿Hay divergencias en los indicadores técnicos (por ejemplo, RSI bajando mientras el otro sube)?
   - ¿Hay una diferencia en momentum o volumen que no está sincronizada?

2. Si detectas una divergencia correlacionada:
   - Señala cuál de los dos activos podría estar adelantando el movimiento.
   - Indica si la oportunidad es LONG o SHORT en {activo_1}.
   - Estima un punto de entrada lógico para anticipar el movimiento de alineación.
   - Fija un stop loss técnico (basado en estructura o invalidación de la divergencia).
   - Establece un take profit razonable con una relación riesgo/beneficio de al menos 1.5:1.

3. Devuelve tu análisis en el siguiente formato:
   - Tipo de divergencia: [en precio / en indicador / en momentum]
   - Activo rezagado: [{activo_1} o {activo_2}]
   - Dirección esperada: LONG / SHORT en {activo_1}
   - Punto de entrada: $[precio]
   - Stop loss: $[precio]
   - Take profit: $[precio]

Si no se detecta una divergencia correlacionada clara, responde: "No hay divergencia relevante entre {activo_1} y {activo_2} en estos datos."'''

    def _get_estocastico_prompt(self) -> str:
        return '''Actúa como un analista técnico experto en scalping con el indicador Estocástico. Analiza el activo {activo} en el timeframe {timeframe}. 

IMPORTANTE: Usa ÚNICAMENTE los datos técnicos que se te proporcionan a continuación. NO inventes precios, niveles o datos que no estén en la información dada.

Datos técnicos actuales:
{datos_tecnicos}

INSTRUCCIONES ESPECÍFICAS:
1. Analiza los datos proporcionados para detectar señales del Estocástico.
2. Si NO hay una señal clara (no hay cruces, no está en zonas extremas, no hay divergencias), responde SOLO:
   "No hay señal de entrada clara según el Estocástico en estos datos."

3. Si SÍ hay una señal clara, responde en este formato exacto:
   - Dirección: LONG / SHORT
   - Señal técnica: [descripción de la señal]
   - Punto de entrada: $[precio basado en datos reales]
   - Stop loss: $[precio basado en datos reales]
   - Take profit: $[precio basado en datos reales]

CRITERIOS PARA SEÑAL VÁLIDA:
- %K cruza %D desde zona de sobreventa (<20) = señal LONG
- %K cruza %D desde zona de sobrecompra (>80) = señal SHORT
- Divergencia entre precio y Estocástico
- Confirmación con volumen

NO generes señales si no hay evidencia clara en los datos proporcionados.
NO inventes precios que no estén en los datos reales.'''

    def _get_fvg_prompt(self) -> str:
        return '''Actúa como un analista técnico experto en scalping institucional utilizando Fair Value Gaps (FVG). Analiza el activo {activo} en el timeframe {timeframe}. A continuación se te proporcionan los datos técnicos recientes de velas: {datos_tecnicos}

1. Analiza si hay presencia de un Fair Value Gap válido. Para ello, detecta si en una secuencia de 3 velas consecutivas se cumple:
   - Para un FVG alcista: El mínimo de la vela 3 está por encima del máximo de la vela 1 (dejando un "gap" entre ambas).
   - Para un FVG bajista: El máximo de la vela 3 está por debajo del mínimo de la vela 1.

2. Si detectas una FVG válida:
   - Señala si es una oportunidad LONG o SHORT.
   - Indica la zona del FVG (entre el máximo de la vela 1 y el mínimo de la vela 3, o viceversa).
   - Estima un punto de entrada óptimo (por ejemplo, en el 50% del FVG o cuando el precio vuelve a testearlo).
   - Define un stop loss razonable (por fuera del gap o del extremo relevante).
   - Calcula un take profit con una relación riesgo/beneficio mínima de 1.5:1, basado en la dirección de entrada.

3. Devuelve el análisis en el siguiente formato:
   - Dirección: LONG / SHORT
   - Zona del FVG: [rango de precios]
   - Punto de entrada: $[precio]
   - Stop loss: $[precio]
   - Take profit: $[precio]

Si no detectas un FVG válido, responde: "No hay Fair Value Gap válido en estos datos."'''

    def _get_intradia_prompt(self) -> str:
        return '''Actúa como un analista técnico experto en trading intradía. Tu objetivo es identificar oportunidades de entrada de alta probabilidad en el activo {activo}, utilizando datos técnicos recientes del timeframe {timeframe}. Se te proporciona a continuación la información de las últimas velas, volumen e indicadores clave: {datos_tecnicos}

1. Evalúa las siguientes condiciones:
   - ¿La tendencia general es alcista o bajista? (usa estructura de mercado, EMAs, o máximos/mínimos relevantes).
   - ¿Hay alguna señal de reversión o continuación clara? (ruptura de estructura, pullback a zona de soporte/resistencia, confluencias).
   - ¿Se observan patrones técnicos relevantes? (doble suelo/techo, triángulos, breakout, etc.)

2. Si detectas una oportunidad operativa válida:
   - Define si la operación es LONG o SHORT.
   - Establece el punto óptimo de entrada.
   - Coloca un stop loss técnico (por debajo de soporte, último mínimo o máximo relevante).
   - Calcula un take profit con un mínimo de 2:1 en relación riesgo/beneficio, o en base a la próxima zona de liquidez/reversión.

3. Tu análisis debe seguir este formato:
   - Dirección: LONG / SHORT
   - Tendencia actual: [alcista / bajista / lateral]
   - Patrón técnico: [nombre del patrón o ruptura de estructura]
   - Punto de entrada: $[precio]
   - Stop loss: $[precio]
   - Take profit: $[precio]

Si no se detecta una oportunidad clara, responde: "No hay configuración operativa clara en estos datos."'''

    def _get_rsi_prompt(self) -> str:
        return '''Actúa como un analista técnico especializado en estrategias con el RSI (Índice de Fuerza Relativa). Analiza el activo {activo} en el timeframe {timeframe}. A continuación se te entregan los datos técnicos recientes, incluyendo precio, volumen y valores del RSI: {datos_tecnicos}

1. Evalúa si el RSI indica alguna de las siguientes condiciones:
   - RSI > 70 = posible sobrecompra
   - RSI < 30 = posible sobreventa
   - RSI cruza desde abajo de 30 hacia arriba = señal LONG
   - RSI cruza desde arriba de 70 hacia abajo = señal SHORT
   - Divergencias: el precio hace un nuevo máximo/mínimo pero el RSI no lo confirma

2. Si detectas una señal clara:
   - Indica si la oportunidad es LONG o SHORT.
   - Estima un punto de entrada basado en el comportamiento reciente del precio.
   - Coloca un stop loss justo por fuera del último mínimo/máximo relevante.
   - Calcula un take profit con una relación riesgo/beneficio de al menos 1.5:1, o hacia una zona técnica importante.

3. Devuelve tu análisis en este formato:
   - Dirección: LONG / SHORT
   - Señal técnica: [ej. cruce RSI desde sobreventa, divergencia bajista, etc.]
   - Punto de entrada: $[precio]
   - Stop loss: $[precio]
   - Take profit: $[precio]

Si no se detecta una señal operativa clara con RSI, responde: "No hay señal válida según RSI en estos datos."'''

    def _get_scalping_prompt(self) -> str:
        return '''Actúa como un analista experto en scalping con múltiples indicadores técnicos. Tu tarea es analizar activos financieros en marcos temporales reducidos (1min, 3min o 5min) para detectar oportunidades de entrada de alta probabilidad. Analiza los siguientes datos técnicos recientes del activo {activo} en el timeframe {timeframe}: {datos_tecnicos}

INSTRUCCIONES ESPECÍFICAS:
1. Analiza los indicadores técnicos para detectar señales de scalping:
   - RSI: Sobreventa (<30) = oportunidad LONG, Sobrecompra (>70) = oportunidad SHORT
   - MACD: Cruce alcista/bajista de la línea MACD con la señal
   - Estocástico: Cruce de %K y %D desde zonas extremas
   - Bandas de Bollinger: Precio tocando bandas superior/inferior
   - VWAP: Precio sobre/bajo VWAP para confirmar tendencia
   - Medias móviles: Cruces de EMA/SMA
   - Volumen: Confirmación con volumen alto
   - ATR: Volatilidad adecuada para scalping

2. CRITERIOS DE SEÑAL (MUY ESTRICTOS Y CONFLUENTES):
   - LONG: RSI(14) < 30 (sobreventa real) Y MACD alcista Y (precio cerca de banda inferior de Bollinger O precio bajo VWAP) Y ratio R/R >= 1.5 Y stop loss mínimo 2% del precio de entrada
   - SHORT: RSI(14) > 70 (sobrecompra real) Y MACD bajista Y (precio cerca de banda superior de Bollinger O precio sobre VWAP) Y ratio R/R >= 1.5 Y stop loss mínimo 2% del precio de entrada
   - NEUTRAL: Si no hay confluencia de al menos 3 indicadores principales O ratio R/R < 1.5 O stop loss < 2%

3. ANÁLISIS DE CONFLUENCIA (REQUERIDO):
   - RSI + MACD + VWAP = Señal fuerte (mínimo requerido)
   - Estocástico + Bandas Bollinger = Confirmación adicional
   - Medias móviles + Volumen = Confirmación final
   - ATR = Validación de volatilidad

4. GESTIÓN DE RIESGO (OBLIGATORIA):
   - Ratio riesgo/beneficio MÍNIMO 1:1.5 (preferible 1:2)
   - Stop loss basado en ATR (2x ATR) o niveles de soporte/resistencia
   - Take profit calculado para lograr ratio R/R mínimo
   - Stop loss MÍNIMO 2% del precio de entrada (para evitar stops muy ajustados)
   - Take profit MÍNIMO 3% del precio de entrada (para R/R 1.5)

5. VALIDACIÓN DE SEÑAL:
   - RSI debe estar en zonas extremas reales (<30 o >70)
   - MACD debe confirmar dirección (alcista para LONG, bajista para SHORT)
   - VWAP debe estar en posición correcta
   - Volumen debe ser superior al promedio
   - ATR debe indicar volatilidad adecuada

RESPONDE ÚNICAMENTE EN ESTE FORMATO:
SIGNAL: [LONG/SHORT/NEUTRAL]
CONFIDENCE: [0.0-1.0]
ENTRY_PRICE: [precio de entrada basado en datos reales]
STOP_LOSS: [precio de stop loss basado en datos reales]
TAKE_PROFIT: [precio de take profit basado en datos reales]
REASONING: [Análisis detallado. DEBES mencionar: RSI exacto + dirección MACD + posición VWAP + posición Bollinger + ratio R/R + volumen + contexto de mercado. IMPORTANTE: Solo usa "sobreventa" si RSI < 30, "sobrecompra" si RSI > 70. Si RSI está entre 30-70, describe como "zona neutral" o "momentum alcista/bajista". Incluye niveles de soporte/resistencia cercanos y tendencia general. Ejemplo: "RSI(14) en sobreventa extrema (28.5) + MACD cruce alcista + precio bajo VWAP ($118,311) + precio tocando banda inferior de Bollinger + ratio R/R 1.8 + volumen 1.5x promedio + soporte en $115,000. Confluencia de 4 indicadores."]

IMPORTANTE: 
- SIEMPRE genera precios reales basados en los datos proporcionados. NUNCA uses "null" para los precios.
- PARA LONG: RSI(14) debe estar en sobreventa REAL (< 30) Y MACD debe ser alcista Y ratio R/R >= 1.5 Y stop loss >= 2%
- PARA SHORT: RSI(14) debe estar en sobrecompra REAL (> 70) Y MACD debe ser bajista Y ratio R/R >= 1.5 Y stop loss >= 2%
- NUNCA generes LONG si MACD es bajista, ni SHORT si MACD es alcista
- SOLO usa NEUTRAL si no hay confluencia de al menos 3 indicadores principales O ratio R/R < 1.5 O stop loss < 2%
- En el REASONING, SIEMPRE menciona el ratio R/R calculado y la distancia del stop loss
- NUNCA uses NEUTRAL si hay indicadores claros y ratio R/R adecuado.
- SIEMPRE incluye contexto de mercado (soportes/resistencias, tendencia)

Si no hay señal clara, responde:
SIGNAL: NEUTRAL
CONFIDENCE: 0.0
ENTRY_PRICE: [precio actual]
STOP_LOSS: [precio actual - 50]
TAKE_PROFIT: [precio actual + 50]
REASONING: No hay confluencia suficiente de indicadores o ratio R/R insuficiente para generar señal de scalping.'''

    def _get_smart_money_prompt(self) -> str:
        return '''Actúa como un analista técnico institucional experto en Smart Money Concepts (SMC). Analiza el activo {activo} en el timeframe {timeframe}. A continuación se te entregan los datos técnicos más recientes, incluyendo estructura de mercado, velas, zonas clave y volumen: {datos_tecnicos}

Tu tarea es detectar una posible oportunidad operativa basada en principios de SMC. Evalúa lo siguiente:

1. ¿Hay un cambio de carácter (CHoCH) o ruptura de estructura (BOS)?
   - Identifica si se rompió un máximo o mínimo estructural relevante.

2. ¿Se ha generado una zona institucional clave?
   - Order Block (última vela alcista antes de un movimiento bajista, o viceversa).
   - Fair Value Gap (desequilibrio entre vela 1 y 3).
   - Zona de liquidez tomada (ej. sweep de mínimos/máximos antes del movimiento real).

3. Si detectas una oportunidad:
   - Indica si se trata de una operación LONG o SHORT.
   - Señala el Order Block o zona de FVG relevante donde esperar la entrada.
   - Estima un punto de entrada óptimo (idealmente en la mitigación del OB o en el 50% del FVG).
   - Coloca un stop loss técnico justo fuera de la zona institucional.
   - Establece un take profit basado en la siguiente zona de liquidez o una relación riesgo/beneficio de al menos 2:1.

Devuelve tu análisis en el siguiente formato:
   - Dirección: LONG / SHORT
   - Motivo técnico: [BOS, CHoCH, OB, FVG, Liquidez tomada]
   - Zona de entrada: [rango de precios]
   - Punto de entrada: $[precio estimado]
   - Stop loss: $[precio]
   - Take profit: $[precio]

Si no se detecta ninguna estructura válida, responde: "No hay configuración institucional clara según Smart Money Concepts en estos datos."'''

    def _get_volatilidad_prompt(self) -> str:
        return '''Actúa como un analista técnico especializado en estrategias de volatilidad. Analiza el activo {activo} en el timeframe {timeframe}. A continuación se te entregan los datos técnicos recientes, incluyendo rangos de vela, indicadores de volatilidad (como ATR o Bollinger Bands), y volumen: {datos_tecnicos}

1. Evalúa si el activo está atravesando un periodo de baja volatilidad:
   - ¿El ATR está disminuyendo progresivamente?
   - ¿Las Bandas de Bollinger se están estrechando?
   - ¿El rango de las velas (High - Low) es significativamente menor en las últimas 5 velas?

2. Si se detecta compresión de volatilidad:
   - Señala una posible dirección del breakout (basado en tendencia previa, volumen o velas con intención).
   - Estima un punto de entrada óptimo en caso de ruptura.
   - Establece un stop loss justo fuera del rango de consolidación.
   - Calcula un take profit basado en una expansión proyectada de la volatilidad (por ejemplo, 1.5x o 2x el rango previo).

3. Devuelve tu análisis en el siguiente formato:
   - Estado de volatilidad: [alta / baja / en compresión]
   - Señal esperada: BREAKOUT / FAKEOUT
   - Dirección probable: LONG / SHORT
   - Punto de entrada: $[precio]
   - Stop loss: $[precio]
   - Take profit: $[precio]

Si no se detecta una compresión de volatilidad significativa, responde: "No hay señal clara basada en volatilidad en estos datos."''' 

test_router = APIRouter()

def get_advanced_strategies_service():
    # Importar la variable global solo cuando se llama la función, para evitar importaciones circulares
    import sys
    main_module = sys.modules.get("main")
    if main_module and hasattr(main_module, "advanced_strategies_service"):
        return getattr(main_module, "advanced_strategies_service")
    return None

@test_router.get("/test-signals")
async def test_signals():
    print("🔍 Iniciando test de señales...")
    try:
        # Monedas más volátiles y populares (reducido de 20 a 8)
        monedas = [
            "BTC", "ETH", "SOL", "DOGE", "PEPE", "SHIB", "WIF", "BONK"
        ]
        timeframes = ["1m", "3m", "5m", "15m", "1h", "4h"]
        resultados = []
        
        # Usar las variables globales de servicios desde main.py
        import sys
        main_module = sys.modules.get("main")
        if main_module and hasattr(main_module, "advanced_strategies_service"):
            service = getattr(main_module, "advanced_strategies_service")
        else:
            return {"error": "Servicios no inicializados"}
        
        total_tests = len(monedas) * len(timeframes)
        test_count = 0
        
        for symbol in monedas:
            for tf in timeframes:
                test_count += 1
                print(f"📊 [{test_count}/{total_tests}] Probando {symbol} en {tf}...")
                try:
                    res = await service.execute_strategy(
                        strategy_type="scalping",
                        symbol=symbol,
                        timeframe=tf,
                        user_id="test-bot",
                        timestamp=None
                    )
                    
                    # Usar los atributos correctos de StrategyResult
                    resultado = {
                        "symbol": symbol,
                        "timeframe": tf,
                        "signal": res.signal,
                        "confidence": res.confidence,
                        "entry_price": res.entry_price,
                        "stop_loss": res.stop_loss,
                        "take_profit": res.take_profit
                    }
                    
                    resultados.append(resultado)
                    
                    if res.signal in ["LONG", "SHORT"]:
                        print(f"✅ ¡SEÑAL ENCONTRADA! {symbol} {tf}: {res.signal}")
                    else:
                        print(f"✅ Resultado {symbol} {tf}: {res.signal}")
                        
                except Exception as e:
                    print(f"❌ Error en {symbol} {tf}: {str(e)}")
                    resultados.append({
                        "symbol": symbol,
                        "timeframe": tf,
                        "signal": "ERROR",
                        "error": str(e)
                    })
        
        # Filtrar solo señales válidas
        señales_válidas = [r for r in resultados if r.get("signal") in ["LONG", "SHORT"]]
        
        print(f"🎯 Test finalizado. Total resultados: {len(resultados)}")
        print(f"🎯 Señales válidas encontradas: {len(señales_válidas)}")
        
        return {
            "total_tests": len(resultados),
            "señales_válidas": len(señales_válidas),
            "todas_las_señales": resultados,
            "solo_válidas": señales_válidas
        }
        
    except Exception as e:
        print(f"💥 Error general en test_signals: {str(e)}")
        return {"error": str(e)} 