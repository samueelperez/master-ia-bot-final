"""
Motor de Estrategias de Trading
Orquesta todas las estrategias y genera señales consolidadas
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from .indicators import TechnicalIndicators, StrategySignals, SignalResult
from enum import Enum
import logging


class StrategyType(Enum):
    """Tipos de estrategia disponibles"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME_BASED = "volume_based"
    COMPREHENSIVE = "comprehensive"


class StrategyEngine:
    """Motor principal de estrategias de trading"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.signal_generator = StrategySignals()
        self.logger = logging.getLogger(__name__)
        
        # Configuración de estrategias
        self.strategy_weights = {
            'sma_crossover': 0.15,
            'ema_strategy': 0.15,
            'rsi_strategy': 0.12,
            'macd_strategy': 0.15,
            'bollinger_strategy': 0.12,
            'stochastic_strategy': 0.10,
            'adx_confirmation': 0.08,
            'volume_confirmation': 0.08,
            'support_resistance': 0.05
        }
    
    def prepare_data(self, ohlcv_data: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """Prepara los datos para el análisis"""
        try:
            # Convertir a numpy arrays si es necesario
            prepared_data = {}
            
            for key in ['open', 'high', 'low', 'close', 'volume']:
                if key in ohlcv_data:
                    data = ohlcv_data[key]
                    if isinstance(data, list):
                        prepared_data[key] = np.array(data, dtype=float)
                    elif isinstance(data, np.ndarray):
                        prepared_data[key] = data.astype(float)
                    else:
                        # Asumir que es un valor único
                        prepared_data[key] = np.array([float(data)])
            
            # Verificar que tenemos al menos los datos mínimos
            required_keys = ['close']
            for key in required_keys:
                if key not in prepared_data:
                    raise ValueError(f"Datos requeridos faltantes: {key}")
            
            # Si no tenemos OHLV completo, creamos estimaciones
            if 'high' not in prepared_data:
                prepared_data['high'] = prepared_data['close'] * 1.02  # Estimación +2%
            if 'low' not in prepared_data:
                prepared_data['low'] = prepared_data['close'] * 0.98   # Estimación -2%
            if 'open' not in prepared_data:
                prepared_data['open'] = prepared_data['close']         # Usar close como open
            if 'volume' not in prepared_data:
                prepared_data['volume'] = np.ones_like(prepared_data['close']) * 1000  # Volumen dummy
            
            return prepared_data
            
        except Exception as e:
            self.logger.error(f"Error preparando datos: {e}")
            raise
    
    def generate_trend_following_signal(self, data: Dict[str, np.ndarray]) -> SignalResult:
        """Genera señal basada en estrategias de seguimiento de tendencia"""
        close = data['close']
        high = data['high']
        low = data['low']
        
        signals = []
        
        # SMA Crossover (10/20)
        signals.append(self.signal_generator.sma_crossover_strategy(close, 10, 20))
        
        # EMA Strategy (12/26)
        signals.append(self.signal_generator.ema_strategy(close, 12, 26))
        
        # MACD
        signals.append(self.signal_generator.macd_strategy(close))
        
        # ADX para confirmar tendencia
        adx_strength = self.signal_generator.adx_trend_strength(high, low, close)
        
        return self._consolidate_signals(signals, adx_strength, "TREND_FOLLOWING")
    
    def generate_mean_reversion_signal(self, data: Dict[str, np.ndarray]) -> SignalResult:
        """Genera señal basada en estrategias de reversión a la media"""
        close = data['close']
        high = data['high']
        low = data['low']
        
        signals = []
        
        # RSI (sobreventa/sobrecompra)
        signals.append(self.signal_generator.rsi_strategy(close, oversold=30, overbought=70))
        
        # Bandas de Bollinger
        signals.append(self.signal_generator.bollinger_strategy(close))
        
        # Estocástico
        signals.append(self.signal_generator.stochastic_strategy(high, low, close))
        
        # Williams %R
        williams_r = self.indicators.williams_r(high, low, close)
        if len(williams_r) > 0 and not np.isnan(williams_r[-1]):
            if williams_r[-1] < -80:  # Sobreventa
                signals.append(SignalResult("BUY", (-80 - williams_r[-1]) / 20, confidence=0.7))
            elif williams_r[-1] > -20:  # Sobrecompra
                signals.append(SignalResult("SELL", (williams_r[-1] + 20) / 20, confidence=0.7))
        
        return self._consolidate_signals(signals, 1.0, "MEAN_REVERSION")
    
    def generate_momentum_signal(self, data: Dict[str, np.ndarray]) -> SignalResult:
        """Genera señal basada en estrategias de momentum"""
        close = data['close']
        high = data['high']
        low = data['low']
        
        signals = []
        
        # Momentum simple
        momentum = self.indicators.momentum(close, period=10)
        if len(momentum) > 0 and not np.isnan(momentum[-1]):
            if momentum[-1] > 0:
                strength = min(momentum[-1] / close[-1] * 100, 1.0)
                signals.append(SignalResult("BUY", strength, confidence=0.6))
            else:
                strength = min(abs(momentum[-1]) / close[-1] * 100, 1.0)
                signals.append(SignalResult("SELL", strength, confidence=0.6))
        
        # CCI
        cci = self.indicators.cci(high, low, close)
        if len(cci) > 0 and not np.isnan(cci[-1]):
            if cci[-1] > 100:  # Sobrecompra fuerte
                signals.append(SignalResult("SELL", min((cci[-1] - 100) / 100, 1.0), confidence=0.7))
            elif cci[-1] < -100:  # Sobreventa fuerte
                signals.append(SignalResult("BUY", min((abs(cci[-1]) - 100) / 100, 1.0), confidence=0.7))
        
        # TRIX
        trix = self.indicators.trix(close)
        if len(trix) > 1 and not np.isnan(trix[-1]) and not np.isnan(trix[-2]):
            # Cruce con línea cero
            if trix[-1] > 0 and trix[-2] <= 0:
                signals.append(SignalResult("BUY", min(abs(trix[-1]) * 1000, 1.0), confidence=0.65))
            elif trix[-1] < 0 and trix[-2] >= 0:
                signals.append(SignalResult("SELL", min(abs(trix[-1]) * 1000, 1.0), confidence=0.65))
        
        return self._consolidate_signals(signals, 1.0, "MOMENTUM")
    
    def generate_volatility_signal(self, data: Dict[str, np.ndarray]) -> SignalResult:
        """Genera señal basada en análisis de volatilidad"""
        close = data['close']
        high = data['high']
        low = data['low']
        
        signals = []
        
        # ATR para medir volatilidad
        atr = self.indicators.atr(high, low, close)
        if len(atr) > 1:
            atr_change = (atr[-1] - atr[-2]) / atr[-2] if atr[-2] != 0 else 0
            # Volatilidad creciente puede indicar ruptura
            if atr_change > 0.1:  # 10% de incremento en ATR
                signals.append(SignalResult("HOLD", 0.3, confidence=0.5))  # Esperar dirección
        
        # Keltner Channels
        upper, middle, lower = self.indicators.keltner_channels(high, low, close)
        if len(upper) > 0 and not np.isnan(upper[-1]):
            current_price = close[-1]
            if current_price > upper[-1]:  # Ruptura alcista
                strength = (current_price - upper[-1]) / upper[-1]
                signals.append(SignalResult("BUY", min(strength * 10, 1.0), confidence=0.75))
            elif current_price < lower[-1]:  # Ruptura bajista
                strength = (lower[-1] - current_price) / lower[-1]
                signals.append(SignalResult("SELL", min(strength * 10, 1.0), confidence=0.75))
        
        # Donchian Channels
        upper_don, middle_don, lower_don = self.indicators.donchian_channels(high, low, period=20)
        if len(upper_don) > 0 and not np.isnan(upper_don[-1]):
            current_price = close[-1]
            if current_price >= upper_don[-1]:  # Breakout alcista
                signals.append(SignalResult("BUY", 0.8, confidence=0.8))
            elif current_price <= lower_don[-1]:  # Breakout bajista
                signals.append(SignalResult("SELL", 0.8, confidence=0.8))
        
        return self._consolidate_signals(signals, 1.0, "VOLATILITY")
    
    def generate_volume_signal(self, data: Dict[str, np.ndarray]) -> SignalResult:
        """Genera señal basada en análisis de volumen"""
        close = data['close']
        volume = data['volume']
        high = data['high']
        low = data['low']
        
        signals = []
        
        # OBV (On Balance Volume)
        obv = self.indicators.obv(close, volume)
        if len(obv) > 1:
            obv_change = (obv[-1] - obv[-2]) / abs(obv[-2]) if obv[-2] != 0 else 0
            price_change = (close[-1] - close[-2]) / close[-2]
            
            # Divergencia entre OBV y precio
            if obv_change > 0.02 and price_change > 0:  # Confirmación alcista
                signals.append(SignalResult("BUY", min(obv_change * 10, 1.0), confidence=0.7))
            elif obv_change < -0.02 and price_change < 0:  # Confirmación bajista
                signals.append(SignalResult("SELL", min(abs(obv_change) * 10, 1.0), confidence=0.7))
        
        # Chaikin Money Flow
        cmf = self.indicators.chaikin_money_flow(high, low, close, volume)
        if len(cmf) > 0 and not np.isnan(cmf[-1]):
            if cmf[-1] > 0.1:  # Presión compradora
                signals.append(SignalResult("BUY", min(cmf[-1] * 5, 1.0), confidence=0.65))
            elif cmf[-1] < -0.1:  # Presión vendedora
                signals.append(SignalResult("SELL", min(abs(cmf[-1]) * 5, 1.0), confidence=0.65))
        
        # Confirmación por volumen
        volume_factor = self.signal_generator.volume_confirmation(volume)
        
        return self._consolidate_signals(signals, volume_factor, "VOLUME_BASED")
    
    def generate_comprehensive_signal(self, data: Dict[str, np.ndarray], timeframe: str = "1h") -> SignalResult:
        """Genera una señal comprensiva usando todas las estrategias"""
        try:
            # Generar señales de cada categoría
            trend_signal = self.generate_trend_following_signal(data)
            mean_reversion_signal = self.generate_mean_reversion_signal(data)
            momentum_signal = self.generate_momentum_signal(data)
            volatility_signal = self.generate_volatility_signal(data)
            volume_signal = self.generate_volume_signal(data)
            
            # Pesos según el timeframe
            if timeframe in ['1m', '5m', '15m']:
                # Timeframes cortos - más peso a momentum y volatilidad
                weights = {
                    'trend': 0.15,
                    'mean_reversion': 0.25,
                    'momentum': 0.30,
                    'volatility': 0.20,
                    'volume': 0.10
                }
            elif timeframe in ['1h', '4h']:
                # Timeframes medios - balance
                weights = {
                    'trend': 0.25,
                    'mean_reversion': 0.20,
                    'momentum': 0.25,
                    'volatility': 0.15,
                    'volume': 0.15
                }
            else:
                # Timeframes largos - más peso a tendencia
                weights = {
                    'trend': 0.35,
                    'mean_reversion': 0.15,
                    'momentum': 0.20,
                    'volatility': 0.15,
                    'volume': 0.15
                }
            
            # Calcular puntuaciones ponderadas
            signals_data = [
                (trend_signal, weights['trend']),
                (mean_reversion_signal, weights['mean_reversion']),
                (momentum_signal, weights['momentum']),
                (volatility_signal, weights['volatility']),
                (volume_signal, weights['volume'])
            ]
            
            buy_score = 0.0
            sell_score = 0.0
            total_confidence = 0.0
            total_weight = 0.0
            
            details = {
                'trend_signal': trend_signal.signal,
                'mean_reversion_signal': mean_reversion_signal.signal,
                'momentum_signal': momentum_signal.signal,
                'volatility_signal': volatility_signal.signal,
                'volume_signal': volume_signal.signal,
                'timeframe': timeframe,
                'weights_used': weights
            }
            
            for signal, weight in signals_data:
                if signal.signal == "BUY":
                    buy_score += signal.strength * signal.confidence * weight
                elif signal.signal == "SELL":
                    sell_score += signal.strength * signal.confidence * weight
                
                total_confidence += signal.confidence * weight
                total_weight += weight
            
            # Normalizar
            if total_weight > 0:
                avg_confidence = total_confidence / total_weight
            else:
                avg_confidence = 0.5
            
            # Determinar señal final
            score_diff = abs(buy_score - sell_score)
            min_threshold = 0.15  # Umbral mínimo para generar señal
            
            if buy_score > sell_score and score_diff > min_threshold:
                final_strength = min(buy_score, 1.0)
                return SignalResult("BUY", final_strength, confidence=avg_confidence, 
                                  details=details)
            elif sell_score > buy_score and score_diff > min_threshold:
                final_strength = min(sell_score, 1.0)
                return SignalResult("SELL", final_strength, confidence=avg_confidence,
                                  details=details)
            else:
                return SignalResult("HOLD", score_diff, confidence=avg_confidence,
                                  details=details)
                
        except Exception as e:
            self.logger.error(f"Error generando señal comprensiva: {e}")
            return SignalResult("HOLD", 0.0, confidence=0.0, 
                              details={"error": str(e)})
    
    def _consolidate_signals(self, signals: List[SignalResult], multiplier: float, strategy_type: str) -> SignalResult:
        """Consolida múltiples señales en una sola"""
        if not signals:
            return SignalResult("HOLD", 0.0)
        
        buy_signals = [s for s in signals if s.signal == "BUY"]
        sell_signals = [s for s in signals if s.signal == "SELL"]
        
        if len(buy_signals) > len(sell_signals) and buy_signals:
            avg_strength = np.mean([s.strength for s in buy_signals])
            avg_confidence = np.mean([s.confidence for s in buy_signals])
            final_strength = min(avg_strength * multiplier, 1.0)
            
            return SignalResult("BUY", final_strength, confidence=avg_confidence,
                              details={
                                  "strategy_type": strategy_type,
                                  "buy_count": len(buy_signals),
                                  "sell_count": len(sell_signals),
                                  "multiplier": multiplier
                              })
        
        elif len(sell_signals) > len(buy_signals) and sell_signals:
            avg_strength = np.mean([s.strength for s in sell_signals])
            avg_confidence = np.mean([s.confidence for s in sell_signals])
            final_strength = min(avg_strength * multiplier, 1.0)
            
            return SignalResult("SELL", final_strength, confidence=avg_confidence,
                              details={
                                  "strategy_type": strategy_type,
                                  "buy_count": len(buy_signals),
                                  "sell_count": len(sell_signals),
                                  "multiplier": multiplier
                              })
        
        return SignalResult("HOLD", 0.0, confidence=0.5,
                          details={
                              "strategy_type": strategy_type,
                              "buy_count": len(buy_signals),
                              "sell_count": len(sell_signals),
                              "multiplier": multiplier
                          })
    
    def get_strategy_explanation(self, signal_result: SignalResult) -> str:
        """Genera explicación detallada de la señal"""
        if not signal_result.details:
            return "Señal básica sin detalles adicionales."
        
        explanation = f"📊 **Señal {signal_result.signal}** (Fuerza: {signal_result.strength:.2f}, Confianza: {signal_result.confidence:.2f})\n\n"
        
        if 'strategy_type' in signal_result.details:
            strategy_type = signal_result.details['strategy_type']
            explanation += f"🎯 **Estrategia**: {strategy_type}\n"
            explanation += f"📈 Señales de compra: {signal_result.details.get('buy_count', 0)}\n"
            explanation += f"📉 Señales de venta: {signal_result.details.get('sell_count', 0)}\n\n"
        
        if 'timeframe' in signal_result.details:
            explanation += f"⏰ **Timeframe**: {signal_result.details['timeframe']}\n"
            
            if 'weights_used' in signal_result.details:
                weights = signal_result.details['weights_used']
                explanation += "⚖️ **Pesos de estrategias**:\n"
                for strategy, weight in weights.items():
                    explanation += f"  • {strategy}: {weight:.0%}\n"
                explanation += "\n"
            
            # Detalles de señales individuales
            individual_signals = [
                ('trend_signal', 'Tendencia'),
                ('mean_reversion_signal', 'Reversión'),
                ('momentum_signal', 'Momentum'),
                ('volatility_signal', 'Volatilidad'),
                ('volume_signal', 'Volumen')
            ]
            
            explanation += "🔍 **Señales individuales**:\n"
            for signal_key, signal_name in individual_signals:
                if signal_key in signal_result.details:
                    signal_value = signal_result.details[signal_key]
                    emoji = "🟢" if signal_value == "BUY" else "🔴" if signal_value == "SELL" else "⚪"
                    explanation += f"  {emoji} {signal_name}: {signal_value}\n"
        
        return explanation 