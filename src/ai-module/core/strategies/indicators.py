"""
Módulo de Indicadores Técnicos Completo
Implementa todos los indicadores necesarios para las estrategias de trading
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import talib
from dataclasses import dataclass


@dataclass
class SignalResult:
    """Resultado de una señal de trading"""
    signal: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0.0 - 1.0
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence: float = 0.0
    details: Dict[str, Any] = None


class TechnicalIndicators:
    """Clase que implementa todos los indicadores técnicos"""
    
    @staticmethod
    def sma(data: np.ndarray, period: int) -> np.ndarray:
        """Media Móvil Simple"""
        return talib.SMA(data, timeperiod=period)
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """Media Móvil Exponencial"""
        return talib.EMA(data, timeperiod=period)
    
    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index"""
        return talib.RSI(data, timeperiod=period)
    
    @staticmethod
    def macd(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD - Moving Average Convergence Divergence"""
        macd_line, signal_line, histogram = talib.MACD(data)
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bandas de Bollinger"""
        upper, middle, lower = talib.BBANDS(data, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return upper, middle, lower
    
    @staticmethod
    def stochastic(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                   k_period: int = 14, d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """Oscilador Estocástico"""
        k_percent = talib.STOCH(high, low, close, 
                               fastk_period=k_period, 
                               slowk_period=d_period, 
                               slowd_period=d_period)[0]
        d_percent = talib.STOCH(high, low, close, 
                               fastk_period=k_period, 
                               slowk_period=d_period, 
                               slowd_period=d_period)[1]
        return k_percent, d_percent
    
    @staticmethod
    def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Average Directional Index"""
        return talib.ADX(high, low, close, timeperiod=period)
    
    @staticmethod
    def sar(high: np.ndarray, low: np.ndarray, acceleration: float = 0.02, maximum: float = 0.2) -> np.ndarray:
        """Parabolic SAR"""
        return talib.SAR(high, low, acceleration=acceleration, maximum=maximum)
    
    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range"""
        return talib.ATR(high, low, close, timeperiod=period)
    
    @staticmethod
    def cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Commodity Channel Index"""
        return talib.CCI(high, low, close, timeperiod=period)
    
    @staticmethod
    def momentum(data: np.ndarray, period: int = 10) -> np.ndarray:
        """Momentum"""
        return talib.MOM(data, timeperiod=period)
    
    @staticmethod
    def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """On Balance Volume"""
        return talib.OBV(close, volume)
    
    @staticmethod
    def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Williams %R"""
        return talib.WILLR(high, low, close, timeperiod=period)
    
    @staticmethod
    def trix(data: np.ndarray, period: int = 14) -> np.ndarray:
        """TRIX"""
        return talib.TRIX(data, timeperiod=period)
    
    @staticmethod
    def dmi(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> Tuple[np.ndarray, np.ndarray]:
        """Directional Movement Index"""
        di_plus = talib.PLUS_DI(high, low, close, timeperiod=period)
        di_minus = talib.MINUS_DI(high, low, close, timeperiod=period)
        return di_plus, di_minus
    
    @staticmethod
    def ultimate_oscillator(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """Ultimate Oscillator"""
        return talib.ULTOSC(high, low, close)
    
    @staticmethod
    def keltner_channels(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                        period: int = 20, multiplier: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Keltner Channels"""
        ema_line = talib.EMA(close, timeperiod=period)
        atr_line = talib.ATR(high, low, close, timeperiod=period)
        upper = ema_line + (multiplier * atr_line)
        lower = ema_line - (multiplier * atr_line)
        return upper, ema_line, lower
    
    @staticmethod
    def donchian_channels(high: np.ndarray, low: np.ndarray, period: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Donchian Channels"""
        upper = talib.MAX(high, timeperiod=period)
        lower = talib.MIN(low, timeperiod=period)
        middle = (upper + lower) / 2
        return upper, middle, lower
    
    @staticmethod
    def chaikin_money_flow(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                          volume: np.ndarray, period: int = 20) -> np.ndarray:
        """Chaikin Money Flow"""
        return talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
    
    @staticmethod
    def vortex_indicator(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                        period: int = 14) -> Tuple[np.ndarray, np.ndarray]:
        """Vortex Indicator"""
        # Implementación manual ya que no está en talib
        tr = np.maximum(high - low, 
                       np.maximum(np.abs(high - np.roll(close, 1)), 
                                 np.abs(low - np.roll(close, 1))))
        
        vm_plus = np.abs(high - np.roll(low, 1))
        vm_minus = np.abs(low - np.roll(high, 1))
        
        vi_plus = pd.Series(vm_plus).rolling(period).sum() / pd.Series(tr).rolling(period).sum()
        vi_minus = pd.Series(vm_minus).rolling(period).sum() / pd.Series(tr).rolling(period).sum()
        
        return vi_plus.values, vi_minus.values
    
    @staticmethod
    def elder_ray_index(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                       period: int = 13) -> Tuple[np.ndarray, np.ndarray]:
        """Elder Ray Index"""
        ema_line = talib.EMA(close, timeperiod=period)
        bull_power = high - ema_line
        bear_power = low - ema_line
        return bull_power, bear_power
    
    @staticmethod
    def detrended_price_oscillator(close: np.ndarray, period: int = 20) -> np.ndarray:
        """Detrended Price Oscillator"""
        sma_line = talib.SMA(close, timeperiod=period)
        shift = period // 2 + 1
        dpo = close - np.roll(sma_line, shift)
        return dpo
    
    @staticmethod
    def price_oscillator(close: np.ndarray, fast_period: int = 12, slow_period: int = 26) -> np.ndarray:
        """Price Oscillator (PPO)"""
        return talib.PPO(close, fastperiod=fast_period, slowperiod=slow_period)
    
    @staticmethod
    def chande_momentum_oscillator(close: np.ndarray, period: int = 14) -> np.ndarray:
        """Chande Momentum Oscillator"""
        return talib.CMO(close, timeperiod=period)
    
    @staticmethod
    def ease_of_movement(high: np.ndarray, low: np.ndarray, volume: np.ndarray, period: int = 14) -> np.ndarray:
        """Ease of Movement"""
        distance_moved = ((high + low) / 2) - ((np.roll(high, 1) + np.roll(low, 1)) / 2)
        box_height = volume / (high - low)
        eom = distance_moved / box_height
        return pd.Series(eom).rolling(period).mean().values
    
    @staticmethod
    def force_index(close: np.ndarray, volume: np.ndarray, period: int = 13) -> np.ndarray:
        """Force Index"""
        fi = (close - np.roll(close, 1)) * volume
        return talib.EMA(fi, timeperiod=period)
    
    @staticmethod
    def relative_vigor_index(open_price: np.ndarray, high: np.ndarray, low: np.ndarray, 
                           close: np.ndarray, period: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """Relative Vigor Index"""
        numerator = (close - open_price) + 2 * (np.roll(close, 1) - np.roll(open_price, 1)) + \
                   2 * (np.roll(close, 2) - np.roll(open_price, 2)) + (np.roll(close, 3) - np.roll(open_price, 3))
        
        denominator = (high - low) + 2 * (np.roll(high, 1) - np.roll(low, 1)) + \
                     2 * (np.roll(high, 2) - np.roll(low, 2)) + (np.roll(high, 3) - np.roll(low, 3))
        
        rvi = pd.Series(numerator).rolling(period).mean() / pd.Series(denominator).rolling(period).mean()
        rvi_signal = pd.Series(rvi).rolling(4).mean()
        
        return rvi.values, rvi_signal.values
    
    @staticmethod
    def mass_index(high: np.ndarray, low: np.ndarray, period: int = 25) -> np.ndarray:
        """Mass Index"""
        range_hl = high - low
        ema9 = talib.EMA(range_hl, timeperiod=9)
        ema9_ema9 = talib.EMA(ema9, timeperiod=9)
        mass_index = pd.Series(ema9 / ema9_ema9).rolling(period).sum()
        return mass_index.values
    
    @staticmethod
    def know_sure_thing(close: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Know Sure Thing (KST)"""
        roc1 = talib.ROC(close, timeperiod=10)
        roc2 = talib.ROC(close, timeperiod=15)
        roc3 = talib.ROC(close, timeperiod=20)
        roc4 = talib.ROC(close, timeperiod=30)
        
        kst = (talib.SMA(roc1, timeperiod=10) * 1) + \
              (talib.SMA(roc2, timeperiod=10) * 2) + \
              (talib.SMA(roc3, timeperiod=10) * 3) + \
              (talib.SMA(roc4, timeperiod=15) * 4)
        
        kst_signal = talib.SMA(kst, timeperiod=9)
        return kst, kst_signal
    
    @staticmethod
    def schaff_trend_cycle(close: np.ndarray, period: int = 23) -> np.ndarray:
        """Schaff Trend Cycle"""
        # Implementación simplificada
        ema1 = talib.EMA(close, timeperiod=23)
        ema2 = talib.EMA(close, timeperiod=50)
        macd_line = ema1 - ema2
        
        # Calcular el STC usando el concepto de estocástico doble
        stc = pd.Series(macd_line).rolling(period).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else 50
        )
        
        return stc.values


class StrategySignals:
    """Generador de señales basado en estrategias específicas"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def sma_crossover_strategy(self, close: np.ndarray, fast_period: int = 10, slow_period: int = 20) -> SignalResult:
        """Estrategia de cruce de medias móviles simples"""
        sma_fast = self.indicators.sma(close, fast_period)
        sma_slow = self.indicators.sma(close, slow_period)
        
        if len(sma_fast) < 2 or len(sma_slow) < 2:
            return SignalResult("HOLD", 0.0)
        
        # Cruce alcista
        if sma_fast[-1] > sma_slow[-1] and sma_fast[-2] <= sma_slow[-2]:
            strength = min(abs(sma_fast[-1] - sma_slow[-1]) / sma_slow[-1] * 100, 1.0)
            return SignalResult("BUY", strength, confidence=0.7)
        
        # Cruce bajista
        elif sma_fast[-1] < sma_slow[-1] and sma_fast[-2] >= sma_slow[-2]:
            strength = min(abs(sma_fast[-1] - sma_slow[-1]) / sma_slow[-1] * 100, 1.0)
            return SignalResult("SELL", strength, confidence=0.7)
        
        return SignalResult("HOLD", 0.0)
    
    def ema_strategy(self, close: np.ndarray, short_period: int = 12, long_period: int = 26) -> SignalResult:
        """Estrategia EMA con cruce de precio"""
        ema_short = self.indicators.ema(close, short_period)
        ema_long = self.indicators.ema(close, long_period)
        
        if len(ema_short) < 2 or len(ema_long) < 2:
            return SignalResult("HOLD", 0.0)
        
        # Precio por encima de EMA corta y EMA corta por encima de EMA larga
        if close[-1] > ema_short[-1] and ema_short[-1] > ema_long[-1]:
            strength = min((close[-1] - ema_long[-1]) / ema_long[-1] * 5, 1.0)
            return SignalResult("BUY", strength, confidence=0.75)
        
        # Precio por debajo de EMA corta y EMA corta por debajo de EMA larga
        elif close[-1] < ema_short[-1] and ema_short[-1] < ema_long[-1]:
            strength = min((ema_long[-1] - close[-1]) / ema_long[-1] * 5, 1.0)
            return SignalResult("SELL", strength, confidence=0.75)
        
        return SignalResult("HOLD", 0.0)
    
    def rsi_strategy(self, close: np.ndarray, period: int = 14, oversold: float = 30, overbought: float = 70) -> SignalResult:
        """Estrategia RSI - Sobrecompra/Sobreventa"""
        rsi = self.indicators.rsi(close, period)
        
        if len(rsi) < 1 or np.isnan(rsi[-1]):
            return SignalResult("HOLD", 0.0)
        
        current_rsi = rsi[-1]
        
        # Sobreventa - señal de compra
        if current_rsi < oversold:
            strength = (oversold - current_rsi) / oversold
            return SignalResult("BUY", strength, confidence=0.8)
        
        # Sobrecompra - señal de venta
        elif current_rsi > overbought:
            strength = (current_rsi - overbought) / (100 - overbought)
            return SignalResult("SELL", strength, confidence=0.8)
        
        return SignalResult("HOLD", 0.0)
    
    def macd_strategy(self, close: np.ndarray) -> SignalResult:
        """Estrategia MACD - Cruce de líneas"""
        macd_line, signal_line, histogram = self.indicators.macd(close)
        
        if len(macd_line) < 2 or len(signal_line) < 2:
            return SignalResult("HOLD", 0.0)
        
        # Filtrar NaN
        if np.isnan(macd_line[-1]) or np.isnan(signal_line[-1]):
            return SignalResult("HOLD", 0.0)
        
        # Cruce alcista
        if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
            strength = min(abs(macd_line[-1] - signal_line[-1]) * 0.1, 1.0)
            return SignalResult("BUY", strength, confidence=0.75)
        
        # Cruce bajista
        elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
            strength = min(abs(macd_line[-1] - signal_line[-1]) * 0.1, 1.0)
            return SignalResult("SELL", strength, confidence=0.75)
        
        return SignalResult("HOLD", 0.0)
    
    def bollinger_strategy(self, close: np.ndarray, period: int = 20, std_dev: float = 2.0) -> SignalResult:
        """Estrategia Bandas de Bollinger"""
        upper, middle, lower = self.indicators.bollinger_bands(close, period, std_dev)
        
        if len(upper) < 1 or np.isnan(upper[-1]):
            return SignalResult("HOLD", 0.0)
        
        current_price = close[-1]
        
        # Precio toca banda inferior - señal de compra
        if current_price <= lower[-1]:
            strength = (lower[-1] - current_price) / lower[-1]
            return SignalResult("BUY", min(strength * 10, 1.0), confidence=0.7)
        
        # Precio toca banda superior - señal de venta
        elif current_price >= upper[-1]:
            strength = (current_price - upper[-1]) / upper[-1]
            return SignalResult("SELL", min(strength * 10, 1.0), confidence=0.7)
        
        return SignalResult("HOLD", 0.0)
    
    def volume_confirmation(self, volume: np.ndarray, period: int = 20) -> float:
        """Confirmación por volumen"""
        if len(volume) < period:
            return 0.5
        
        avg_volume = np.mean(volume[-period:])
        current_volume = volume[-1]
        
        # Factor de confirmación basado en volumen
        volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
        return volume_factor
    
    def stochastic_strategy(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> SignalResult:
        """Estrategia Estocástico"""
        k_percent, d_percent = self.indicators.stochastic(high, low, close)
        
        if len(k_percent) < 2 or len(d_percent) < 2:
            return SignalResult("HOLD", 0.0)
        
        # Filtrar NaN
        if np.isnan(k_percent[-1]) or np.isnan(d_percent[-1]):
            return SignalResult("HOLD", 0.0)
        
        # Cruce alcista en zona de sobreventa
        if (k_percent[-1] > d_percent[-1] and k_percent[-2] <= d_percent[-2] and 
            k_percent[-1] < 30):
            strength = (30 - k_percent[-1]) / 30
            return SignalResult("BUY", strength, confidence=0.75)
        
        # Cruce bajista en zona de sobrecompra
        elif (k_percent[-1] < d_percent[-1] and k_percent[-2] >= d_percent[-2] and 
              k_percent[-1] > 70):
            strength = (k_percent[-1] - 70) / 30
            return SignalResult("SELL", strength, confidence=0.75)
        
        return SignalResult("HOLD", 0.0)
    
    def adx_trend_strength(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
        """Confirmación de fuerza de tendencia con ADX"""
        adx = self.indicators.adx(high, low, close)
        
        if len(adx) < 1 or np.isnan(adx[-1]):
            return 0.5
        
        # ADX > 25 indica tendencia fuerte
        if adx[-1] > 25:
            return min(adx[-1] / 50, 1.0)
        else:
            return adx[-1] / 50
    
    def comprehensive_signal(self, ohlcv_data: Dict[str, np.ndarray]) -> SignalResult:
        """Señal comprensiva combinando múltiples estrategias"""
        close = ohlcv_data['close']
        high = ohlcv_data['high']
        low = ohlcv_data['low']
        volume = ohlcv_data.get('volume', np.ones_like(close))
        
        # Generar señales individuales
        signals = []
        
        # Estrategias principales
        signals.append(self.sma_crossover_strategy(close))
        signals.append(self.ema_strategy(close))
        signals.append(self.rsi_strategy(close))
        signals.append(self.macd_strategy(close))
        signals.append(self.bollinger_strategy(close))
        signals.append(self.stochastic_strategy(high, low, close))
        
        # Factores de confirmación
        volume_factor = self.volume_confirmation(volume)
        trend_strength = self.adx_trend_strength(high, low, close)
        
        # Análisis de consenso
        buy_signals = [s for s in signals if s.signal == "BUY"]
        sell_signals = [s for s in signals if s.signal == "SELL"]
        
        if len(buy_signals) > len(sell_signals) and len(buy_signals) >= 3:
            avg_strength = np.mean([s.strength for s in buy_signals])
            avg_confidence = np.mean([s.confidence for s in buy_signals])
            
            # Aplicar factores de confirmación
            final_strength = avg_strength * volume_factor * trend_strength
            final_confidence = avg_confidence * 0.8 + 0.2 * (len(buy_signals) / len(signals))
            
            return SignalResult("BUY", final_strength, confidence=final_confidence,
                              details={
                                  "buy_signals": len(buy_signals),
                                  "sell_signals": len(sell_signals),
                                  "volume_factor": volume_factor,
                                  "trend_strength": trend_strength
                              })
        
        elif len(sell_signals) > len(buy_signals) and len(sell_signals) >= 3:
            avg_strength = np.mean([s.strength for s in sell_signals])
            avg_confidence = np.mean([s.confidence for s in sell_signals])
            
            # Aplicar factores de confirmación
            final_strength = avg_strength * volume_factor * trend_strength
            final_confidence = avg_confidence * 0.8 + 0.2 * (len(sell_signals) / len(signals))
            
            return SignalResult("SELL", final_strength, confidence=final_confidence,
                              details={
                                  "buy_signals": len(buy_signals),
                                  "sell_signals": len(sell_signals),
                                  "volume_factor": volume_factor,
                                  "trend_strength": trend_strength
                              })
        
        return SignalResult("HOLD", 0.0, confidence=0.5,
                          details={
                              "buy_signals": len(buy_signals),
                              "sell_signals": len(sell_signals),
                              "volume_factor": volume_factor,
                              "trend_strength": trend_strength
                          }) 