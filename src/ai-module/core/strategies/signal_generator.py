"""
Generador de Señales de Trading
Integra el motor de estrategias con el sistema principal
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from .strategy_engine import StrategyEngine, StrategyType
from .indicators import SignalResult
import logging


class SignalGenerator:
    """Generador principal de señales de trading"""
    
    def __init__(self):
        self.strategy_engine = StrategyEngine()
        self.logger = logging.getLogger(__name__)
    
    def generate_signal(self, symbol: str, ohlcv_data: Dict[str, Any], 
                       timeframe: str = "1h", strategy_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Genera una señal de trading completa
        
        Args:
            symbol: Símbolo de la criptomoneda (ej: BTC, ETH)
            ohlcv_data: Datos OHLCV (open, high, low, close, volume)
            timeframe: Marco temporal (1m, 5m, 15m, 1h, 4h, 1d)
            strategy_type: Tipo de estrategia a usar
        
        Returns:
            Dict con la señal generada y detalles
        """
        try:
            # Preparar los datos
            prepared_data = self.strategy_engine.prepare_data(ohlcv_data)
            
            # Generar la señal según el tipo de estrategia
            if strategy_type == "comprehensive":
                signal_result = self.strategy_engine.generate_comprehensive_signal(prepared_data, timeframe)
            elif strategy_type == "trend_following":
                signal_result = self.strategy_engine.generate_trend_following_signal(prepared_data)
            elif strategy_type == "mean_reversion":
                signal_result = self.strategy_engine.generate_mean_reversion_signal(prepared_data)
            elif strategy_type == "momentum":
                signal_result = self.strategy_engine.generate_momentum_signal(prepared_data)
            elif strategy_type == "volatility":
                signal_result = self.strategy_engine.generate_volatility_signal(prepared_data)
            elif strategy_type == "volume_based":
                signal_result = self.strategy_engine.generate_volume_signal(prepared_data)
            else:
                # Por defecto usar comprensiva
                signal_result = self.strategy_engine.generate_comprehensive_signal(prepared_data, timeframe)
            
            # Calcular niveles técnicos
            current_price = float(prepared_data['close'][-1])
            technical_levels = self._calculate_technical_levels(prepared_data, signal_result, current_price)
            
            # Formatear la respuesta
            response = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal_result.signal,
                "strength": round(signal_result.strength, 3),
                "confidence": round(signal_result.confidence, 3),
                "current_price": current_price,
                "technical_levels": technical_levels,
                "strategy_type": strategy_type,
                "explanation": self.strategy_engine.get_strategy_explanation(signal_result),
                "recommendation": self._generate_recommendation(signal_result, current_price, technical_levels),
                "risk_assessment": self._assess_risk(signal_result, prepared_data),
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            # Añadir detalles específicos si están disponibles
            if signal_result.details:
                response["details"] = signal_result.details
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generando señal para {symbol}: {e}")
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": "HOLD",
                "strength": 0.0,
                "confidence": 0.0,
                "error": str(e),
                "timestamp": pd.Timestamp.now().isoformat()
            }
    
    def _calculate_technical_levels(self, data: Dict[str, np.ndarray], 
                                   signal_result: SignalResult, current_price: float) -> Dict[str, float]:
        """Calcula niveles técnicos para la señal"""
        try:
            close = data['close']
            high = data['high']
            low = data['low']
            
            # ATR para stops dinámicos
            atr = self.strategy_engine.indicators.atr(high, low, close, period=14)
            atr_value = atr[-1] if len(atr) > 0 and not np.isnan(atr[-1]) else current_price * 0.02
            
            # Niveles base
            if signal_result.signal == "BUY":
                # Para señal de compra
                stop_loss = current_price - (2.0 * atr_value)
                take_profit_1 = current_price + (1.5 * atr_value)
                take_profit_2 = current_price + (3.0 * atr_value)
                
                # Ajustar según la fuerza de la señal
                multiplier = 0.5 + (signal_result.strength * 0.5)  # 0.5 - 1.0
                take_profit_1 *= multiplier
                take_profit_2 *= multiplier
                
            elif signal_result.signal == "SELL":
                # Para señal de venta
                stop_loss = current_price + (2.0 * atr_value)
                take_profit_1 = current_price - (1.5 * atr_value)
                take_profit_2 = current_price - (3.0 * atr_value)
                
                # Ajustar según la fuerza de la señal
                multiplier = 0.5 + (signal_result.strength * 0.5)
                take_profit_1 = current_price - (abs(current_price - take_profit_1) * multiplier)
                take_profit_2 = current_price - (abs(current_price - take_profit_2) * multiplier)
                
            else:  # HOLD
                # Niveles de observación
                stop_loss = current_price - (1.5 * atr_value)
                take_profit_1 = current_price + (1.0 * atr_value)
                take_profit_2 = current_price + (2.0 * atr_value)
            
            # Calcular soportes y resistencias
            support, resistance = self._calculate_support_resistance(close, high, low)
            
            # Calcular invalidación
            if signal_result.signal == "BUY":
                invalidation = min(stop_loss * 0.95, support * 0.98) if support else stop_loss * 0.95
            elif signal_result.signal == "SELL":
                invalidation = max(stop_loss * 1.05, resistance * 1.02) if resistance else stop_loss * 1.05
            else:
                invalidation = current_price * 0.9  # 10% de invalidación por defecto
            
            return {
                "stop_loss": round(stop_loss, 2),
                "take_profit_1": round(take_profit_1, 2),
                "take_profit_2": round(take_profit_2, 2),
                "support": round(support, 2) if support else None,
                "resistance": round(resistance, 2) if resistance else None,
                "invalidation": round(invalidation, 2),
                "atr": round(atr_value, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando niveles técnicos: {e}")
            # Niveles de fallback
            return {
                "stop_loss": round(current_price * 0.95, 2),
                "take_profit_1": round(current_price * 1.05, 2),
                "take_profit_2": round(current_price * 1.10, 2),
                "invalidation": round(current_price * 0.90, 2),
                "atr": round(current_price * 0.02, 2)
            }
    
    def _calculate_support_resistance(self, close: np.ndarray, high: np.ndarray, 
                                    low: np.ndarray, period: int = 20) -> Tuple[Optional[float], Optional[float]]:
        """Calcula niveles de soporte y resistencia"""
        try:
            if len(close) < period:
                return None, None
            
            # Usar los últimos N períodos
            recent_high = high[-period:]
            recent_low = low[-period:]
            recent_close = close[-period:]
            
            # Soporte: nivel de mínimos significativos
            support_level = np.percentile(recent_low, 25)  # 25% percentil de mínimos
            
            # Resistencia: nivel de máximos significativos
            resistance_level = np.percentile(recent_high, 75)  # 75% percentil de máximos
            
            # Validar que los niveles son razonables
            current_price = close[-1]
            if support_level > current_price * 0.8:  # No más del 20% abajo
                support_level = current_price * 0.9
            if resistance_level < current_price * 1.2:  # No más del 20% arriba
                resistance_level = current_price * 1.1
            
            return support_level, resistance_level
            
        except Exception:
            return None, None
    
    def _generate_recommendation(self, signal_result: SignalResult, current_price: float, 
                               technical_levels: Dict[str, float]) -> str:
        """Genera recomendación textual detallada"""
        try:
            signal = signal_result.signal
            strength = signal_result.strength
            confidence = signal_result.confidence
            
            if signal == "BUY":
                recommendation = f"🟢 **SEÑAL DE COMPRA** - Fuerza: {strength:.1%}, Confianza: {confidence:.1%}\n\n"
                recommendation += f"📈 **Recomendación**: Considerar apertura de posición larga en ${current_price:.2f}\n"
                recommendation += f"🛑 **Stop Loss**: ${technical_levels['stop_loss']:.2f} ({((technical_levels['stop_loss'] - current_price) / current_price * 100):+.1f}%)\n"
                recommendation += f"🎯 **Take Profit 1**: ${technical_levels['take_profit_1']:.2f} ({((technical_levels['take_profit_1'] - current_price) / current_price * 100):+.1f}%)\n"
                recommendation += f"🎯 **Take Profit 2**: ${technical_levels['take_profit_2']:.2f} ({((technical_levels['take_profit_2'] - current_price) / current_price * 100):+.1f}%)\n"
                
                if strength > 0.7:
                    recommendation += "\n💪 **Señal Fuerte**: Multiple indicadores confirman la oportunidad de compra."
                elif strength > 0.4:
                    recommendation += "\n⚖️ **Señal Moderada**: Algunos indicadores sugieren compra, monitorear evolución."
                else:
                    recommendation += "\n⚠️ **Señal Débil**: Considerar esperar mayor confirmación antes de abrir posición."
                    
            elif signal == "SELL":
                recommendation = f"🔴 **SEÑAL DE VENTA** - Fuerza: {strength:.1%}, Confianza: {confidence:.1%}\n\n"
                recommendation += f"📉 **Recomendación**: Considerar apertura de posición corta en ${current_price:.2f}\n"
                recommendation += f"🛑 **Stop Loss**: ${technical_levels['stop_loss']:.2f} ({((technical_levels['stop_loss'] - current_price) / current_price * 100):+.1f}%)\n"
                recommendation += f"🎯 **Take Profit 1**: ${technical_levels['take_profit_1']:.2f} ({((technical_levels['take_profit_1'] - current_price) / current_price * 100):+.1f}%)\n"
                recommendation += f"🎯 **Take Profit 2**: ${technical_levels['take_profit_2']:.2f} ({((technical_levels['take_profit_2'] - current_price) / current_price * 100):+.1f}%)\n"
                
                if strength > 0.7:
                    recommendation += "\n💪 **Señal Fuerte**: Multiple indicadores confirman la oportunidad de venta."
                elif strength > 0.4:
                    recommendation += "\n⚖️ **Señal Moderada**: Algunos indicadores sugieren venta, monitorear evolución."
                else:
                    recommendation += "\n⚠️ **Señal Débil**: Considerar esperar mayor confirmación antes de abrir posición."
                    
            else:  # HOLD
                recommendation = f"⚪ **MANTENER POSICIÓN** - Fuerza: {strength:.1%}, Confianza: {confidence:.1%}\n\n"
                recommendation += f"⏳ **Recomendación**: No hay señal clara de entrada. Mantener observación en ${current_price:.2f}\n"
                recommendation += f"📊 **Niveles a vigilar**:\n"
                if technical_levels.get('support'):
                    recommendation += f"  • Soporte: ${technical_levels['support']:.2f}\n"
                if technical_levels.get('resistance'):
                    recommendation += f"  • Resistencia: ${technical_levels['resistance']:.2f}\n"
                recommendation += f"  • Invalidación: ${technical_levels['invalidation']:.2f}\n"
                recommendation += "\n🔍 **Monitoreo**: Esperar ruptura de niveles clave o confirmación de tendencia."
            
            return recommendation
            
        except Exception as e:
            return f"Error generando recomendación: {e}"
    
    def _assess_risk(self, signal_result: SignalResult, data: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Evalúa el riesgo de la señal"""
        try:
            close = data['close']
            high = data['high']
            low = data['low']
            
            # Calcular volatilidad (ATR normalizado)
            atr = self.strategy_engine.indicators.atr(high, low, close, period=14)
            volatility = (atr[-1] / close[-1] * 100) if len(atr) > 0 and not np.isnan(atr[-1]) else 2.0
            
            # Evaluar tendencia
            ema_short = self.strategy_engine.indicators.ema(close, 12)
            ema_long = self.strategy_engine.indicators.ema(close, 26)
            trend_strength = 0.5
            if len(ema_short) > 0 and len(ema_long) > 0:
                trend_strength = abs(ema_short[-1] - ema_long[-1]) / ema_long[-1]
            
            # Clasificar el riesgo
            risk_score = 0.0
            
            # Factor volatilidad (0-0.4)
            if volatility > 5.0:
                risk_score += 0.4
            elif volatility > 3.0:
                risk_score += 0.25
            elif volatility > 1.5:
                risk_score += 0.15
            else:
                risk_score += 0.05
            
            # Factor confianza de señal (0-0.3)
            confidence_factor = (1.0 - signal_result.confidence) * 0.3
            risk_score += confidence_factor
            
            # Factor fuerza de tendencia (0-0.3)
            trend_factor = (1.0 - min(trend_strength * 5, 1.0)) * 0.3
            risk_score += trend_factor
            
            # Clasificación final
            if risk_score <= 0.3:
                risk_level = "BAJO"
                risk_description = "Condiciones favorables para la operación"
            elif risk_score <= 0.6:
                risk_level = "MEDIO"
                risk_description = "Condiciones moderadas, gestionar posición cuidadosamente"
            else:
                risk_level = "ALTO"
                risk_description = "Condiciones de alto riesgo, considerar reducir exposición"
            
            return {
                "risk_level": risk_level,
                "risk_score": round(risk_score, 2),
                "volatility": round(volatility, 2),
                "trend_strength": round(trend_strength, 3),
                "description": risk_description
            }
            
        except Exception as e:
            return {
                "risk_level": "DESCONOCIDO",
                "risk_score": 0.5,
                "description": f"Error evaluando riesgo: {e}"
            }
    
    def get_available_strategies(self) -> List[str]:
        """Retorna lista de estrategias disponibles"""
        return [
            "comprehensive",
            "trend_following", 
            "mean_reversion",
            "momentum",
            "volatility",
            "volume_based"
        ]
    
    def get_supported_timeframes(self) -> List[str]:
        """Retorna lista de timeframes soportados"""
        return ["1m", "5m", "15m", "1h", "4h", "1d", "1w"] 