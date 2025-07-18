"""
Indicadores de Correlación para análisis de pares de activos.
Implementa coeficientes de correlación, divergencias y análisis de pares correlacionados.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from scipy import stats
from scipy.stats import pearsonr, spearmanr

@dataclass
class CorrelationResult:
    """Resultado de análisis de correlación."""
    symbol1: str
    symbol2: str
    pearson_correlation: float
    spearman_correlation: float
    correlation_strength: str  # "strong", "moderate", "weak"
    correlation_direction: str  # "positive", "negative"
    confidence_interval: Tuple[float, float]
    p_value: float
    is_significant: bool

@dataclass
class DivergenceResult:
    """Resultado de análisis de divergencia."""
    symbol1: str
    symbol2: str
    divergence_type: str  # "price", "momentum", "volume"
    direction: str  # "bullish", "bearish"
    strength: float  # 0.0 to 1.0
    start_idx: int
    end_idx: int
    description: str

@dataclass
class PairAnalysis:
    """Análisis completo de un par de activos."""
    symbol1: str
    symbol2: str
    correlation: CorrelationResult
    divergences: List[DivergenceResult]
    beta_ratio: float
    volatility_ratio: float
    trading_opportunity: Optional[str] = None

class CorrelationIndicators:
    """Indicadores de correlación y análisis de pares."""
    
    def __init__(self):
        self.min_correlation_threshold = 0.7  # Correlación mínima para considerar pares
        self.min_data_points = 30  # Mínimo de puntos de datos para análisis
        self.confidence_level = 0.95  # Nivel de confianza para intervalos
    
    def calculate_correlation(
        self, 
        data1: pd.Series, 
        data2: pd.Series, 
        symbol1: str, 
        symbol2: str
    ) -> CorrelationResult:
        """
        Calcula la correlación entre dos series de datos.
        
        Args:
            data1: Serie de datos del primer activo
            data2: Serie de datos del segundo activo
            symbol1: Símbolo del primer activo
            symbol2: Símbolo del segundo activo
            
        Returns:
            CorrelationResult con los resultados
        """
        # Alinear datos
        aligned_data = pd.concat([data1, data2], axis=1).dropna()
        
        if len(aligned_data) < self.min_data_points:
            raise ValueError(f"Insuficientes datos: {len(aligned_data)} < {self.min_data_points}")
        
        series1 = aligned_data.iloc[:, 0]
        series2 = aligned_data.iloc[:, 1]
        
        # Calcular correlaciones
        pearson_corr, pearson_p = pearsonr(series1, series2)
        spearman_corr, spearman_p = spearmanr(series1, series2)
        
        # Calcular intervalo de confianza
        ci_lower, ci_upper = self._calculate_confidence_interval(
            pearson_corr, len(aligned_data)
        )
        
        # Determinar fuerza de correlación
        correlation_strength = self._get_correlation_strength(abs(pearson_corr))
        correlation_direction = "positive" if pearson_corr > 0 else "negative"
        
        return CorrelationResult(
            symbol1=symbol1,
            symbol2=symbol2,
            pearson_correlation=pearson_corr,
            spearman_correlation=spearman_corr,
            correlation_strength=correlation_strength,
            correlation_direction=correlation_direction,
            confidence_interval=(ci_lower, ci_upper),
            p_value=pearson_p,
            is_significant=pearson_p < (1 - self.confidence_level)
        )
    
    def _calculate_confidence_interval(self, correlation: float, n: int) -> Tuple[float, float]:
        """Calcula el intervalo de confianza para la correlación."""
        # Transformación de Fisher
        z = np.arctanh(correlation)
        
        # Error estándar
        se = 1 / np.sqrt(n - 3)
        
        # Intervalo de confianza
        z_score = stats.norm.ppf((1 + self.confidence_level) / 2)
        z_lower = z - z_score * se
        z_upper = z + z_score * se
        
        # Transformación inversa
        ci_lower = np.tanh(z_lower)
        ci_upper = np.tanh(z_upper)
        
        return ci_lower, ci_upper
    
    def _get_correlation_strength(self, abs_correlation: float) -> str:
        """Determina la fuerza de la correlación."""
        if abs_correlation >= 0.8:
            return "strong"
        elif abs_correlation >= 0.5:
            return "moderate"
        else:
            return "weak"
    
    def detect_divergences(
        self, 
        df1: pd.DataFrame, 
        df2: pd.DataFrame, 
        symbol1: str, 
        symbol2: str
    ) -> List[DivergenceResult]:
        """
        Detecta divergencias entre dos activos.
        
        Args:
            df1: DataFrame del primer activo
            df2: DataFrame del segundo activo
            symbol1: Símbolo del primer activo
            symbol2: Símbolo del segundo activo
            
        Returns:
            Lista de divergencias detectadas
        """
        divergences = []
        
        # Alinear datos
        aligned_data = self._align_dataframes(df1, df2)
        if aligned_data is None:
            return divergences
        
        # Detectar divergencias de precio
        price_divs = self._detect_price_divergences(
            aligned_data, symbol1, symbol2
        )
        divergences.extend(price_divs)
        
        # Detectar divergencias de momentum
        momentum_divs = self._detect_momentum_divergences(
            aligned_data, symbol1, symbol2
        )
        divergences.extend(momentum_divs)
        
        # Detectar divergencias de volumen
        volume_divs = self._detect_volume_divergences(
            aligned_data, symbol1, symbol2
        )
        divergences.extend(volume_divs)
        
        return divergences
    
    def _align_dataframes(self, df1: pd.DataFrame, df2: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Alinea dos DataFrames por timestamp."""
        try:
            # Asumiendo que ambos DataFrames tienen índice de tiempo
            df1_copy = df1.copy()
            df2_copy = df2.copy()
            
            # Renombrar columnas para evitar conflictos
            df1_copy.columns = [f"{col}_1" for col in df1_copy.columns]
            df2_copy.columns = [f"{col}_2" for col in df2_copy.columns]
            
            # Unir por índice
            aligned = df1_copy.join(df2_copy, how='inner')
            
            if len(aligned) < self.min_data_points:
                return None
            
            return aligned
        except Exception:
            return None
    
    def _detect_price_divergences(
        self, 
        aligned_data: pd.DataFrame, 
        symbol1: str, 
        symbol2: str
    ) -> List[DivergenceResult]:
        """Detecta divergencias de precio."""
        divergences = []
        
        # Buscar divergencias en los últimos 20 períodos
        lookback = min(20, len(aligned_data) // 2)
        
        for i in range(lookback, len(aligned_data)):
            # Divergencia alcista: symbol1 hace nuevo mínimo, symbol2 no
            if self._is_bullish_price_divergence(aligned_data, i, lookback):
                div = self._create_bullish_price_divergence(
                    aligned_data, i, symbol1, symbol2
                )
                if div:
                    divergences.append(div)
            
            # Divergencia bajista: symbol1 hace nuevo máximo, symbol2 no
            elif self._is_bearish_price_divergence(aligned_data, i, lookback):
                div = self._create_bearish_price_divergence(
                    aligned_data, i, symbol1, symbol2
                )
                if div:
                    divergences.append(div)
        
        return divergences
    
    def _is_bullish_price_divergence(
        self, 
        data: pd.DataFrame, 
        idx: int, 
        lookback: int
    ) -> bool:
        """Verifica si hay divergencia alcista de precio."""
        if idx < lookback:
            return False
        
        # Symbol1 hace nuevo mínimo
        symbol1_lows = data.iloc[idx-lookback:idx]['low_1']
        current_low_1 = data.iloc[idx]['low_1']
        
        if current_low_1 > symbol1_lows.min():
            return False
        
        # Symbol2 no hace nuevo mínimo
        symbol2_lows = data.iloc[idx-lookback:idx]['low_2']
        current_low_2 = data.iloc[idx]['low_2']
        
        return current_low_2 > symbol2_lows.min()
    
    def _is_bearish_price_divergence(
        self, 
        data: pd.DataFrame, 
        idx: int, 
        lookback: int
    ) -> bool:
        """Verifica si hay divergencia bajista de precio."""
        if idx < lookback:
            return False
        
        # Symbol1 hace nuevo máximo
        symbol1_highs = data.iloc[idx-lookback:idx]['high_1']
        current_high_1 = data.iloc[idx]['high_1']
        
        if current_high_1 < symbol1_highs.max():
            return False
        
        # Symbol2 no hace nuevo máximo
        symbol2_highs = data.iloc[idx-lookback:idx]['high_2']
        current_high_2 = data.iloc[idx]['high_2']
        
        return current_high_2 < symbol2_highs.max()
    
    def _create_bullish_price_divergence(
        self, 
        data: pd.DataFrame, 
        idx: int, 
        symbol1: str, 
        symbol2: str
    ) -> Optional[DivergenceResult]:
        """Crea una divergencia alcista de precio."""
        # Calcular fuerza basada en la diferencia de mínimos
        symbol1_lows = data.iloc[idx-10:idx]['low_1']
        symbol2_lows = data.iloc[idx-10:idx]['low_2']
        
        diff_ratio = (symbol2_lows.min() - symbol1_lows.min()) / symbol1_lows.min()
        strength = min(abs(diff_ratio) * 2, 1.0)
        
        return DivergenceResult(
            symbol1=symbol1,
            symbol2=symbol2,
            divergence_type="price",
            direction="bullish",
            strength=strength,
            start_idx=idx-10,
            end_idx=idx,
            description=f"{symbol1} hace nuevo mínimo mientras {symbol2} mantiene soporte"
        )
    
    def _create_bearish_price_divergence(
        self, 
        data: pd.DataFrame, 
        idx: int, 
        symbol1: str, 
        symbol2: str
    ) -> Optional[DivergenceResult]:
        """Crea una divergencia bajista de precio."""
        # Calcular fuerza basada en la diferencia de máximos
        symbol1_highs = data.iloc[idx-10:idx]['high_1']
        symbol2_highs = data.iloc[idx-10:idx]['high_2']
        
        diff_ratio = (symbol1_highs.max() - symbol2_highs.max()) / symbol2_highs.max()
        strength = min(abs(diff_ratio) * 2, 1.0)
        
        return DivergenceResult(
            symbol1=symbol1,
            symbol2=symbol2,
            divergence_type="price",
            direction="bearish",
            strength=strength,
            start_idx=idx-10,
            end_idx=idx,
            description=f"{symbol1} hace nuevo máximo mientras {symbol2} no confirma"
        )
    
    def _detect_momentum_divergences(
        self, 
        aligned_data: pd.DataFrame, 
        symbol1: str, 
        symbol2: str
    ) -> List[DivergenceResult]:
        """Detecta divergencias de momentum usando RSI."""
        divergences = []
        
        # Calcular RSI para ambos activos
        rsi1 = self._calculate_rsi(aligned_data['close_1'])
        rsi2 = self._calculate_rsi(aligned_data['close_2'])
        
        # Buscar divergencias en RSI
        lookback = min(14, len(aligned_data) // 3)
        
        for i in range(lookback, len(aligned_data)):
            # Divergencia alcista en RSI
            if self._is_bullish_rsi_divergence(rsi1, rsi2, i, lookback):
                div = self._create_bullish_rsi_divergence(
                    rsi1, rsi2, i, symbol1, symbol2
                )
                if div:
                    divergences.append(div)
            
            # Divergencia bajista en RSI
            elif self._is_bearish_rsi_divergence(rsi1, rsi2, i, lookback):
                div = self._create_bearish_rsi_divergence(
                    rsi1, rsi2, i, symbol1, symbol2
                )
                if div:
                    divergences.append(div)
        
        return divergences
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula el RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _is_bullish_rsi_divergence(
        self, 
        rsi1: pd.Series, 
        rsi2: pd.Series, 
        idx: int, 
        lookback: int
    ) -> bool:
        """Verifica divergencia alcista en RSI."""
        if idx < lookback:
            return False
        
        # RSI1 hace nuevo mínimo
        rsi1_mins = rsi1.iloc[idx-lookback:idx]
        current_rsi1 = rsi1.iloc[idx]
        
        if current_rsi1 > rsi1_mins.min():
            return False
        
        # RSI2 no hace nuevo mínimo
        rsi2_mins = rsi2.iloc[idx-lookback:idx]
        current_rsi2 = rsi2.iloc[idx]
        
        return current_rsi2 > rsi2_mins.min()
    
    def _is_bearish_rsi_divergence(
        self, 
        rsi1: pd.Series, 
        rsi2: pd.Series, 
        idx: int, 
        lookback: int
    ) -> bool:
        """Verifica divergencia bajista en RSI."""
        if idx < lookback:
            return False
        
        # RSI1 hace nuevo máximo
        rsi1_maxs = rsi1.iloc[idx-lookback:idx]
        current_rsi1 = rsi1.iloc[idx]
        
        if current_rsi1 < rsi1_maxs.max():
            return False
        
        # RSI2 no hace nuevo máximo
        rsi2_maxs = rsi2.iloc[idx-lookback:idx]
        current_rsi2 = rsi2.iloc[idx]
        
        return current_rsi2 < rsi2_maxs.max()
    
    def _create_bullish_rsi_divergence(
        self, 
        rsi1: pd.Series, 
        rsi2: pd.Series, 
        idx: int, 
        symbol1: str, 
        symbol2: str
    ) -> Optional[DivergenceResult]:
        """Crea divergencia alcista en RSI."""
        strength = min((rsi2.iloc[idx] - rsi1.iloc[idx]) / 50, 1.0)
        
        return DivergenceResult(
            symbol1=symbol1,
            symbol2=symbol2,
            divergence_type="momentum",
            direction="bullish",
            strength=strength,
            start_idx=idx-14,
            end_idx=idx,
            description=f"RSI de {symbol1} en sobreventa mientras {symbol2} mantiene momentum"
        )
    
    def _create_bearish_rsi_divergence(
        self, 
        rsi1: pd.Series, 
        rsi2: pd.Series, 
        idx: int, 
        symbol1: str, 
        symbol2: str
    ) -> Optional[DivergenceResult]:
        """Crea divergencia bajista en RSI."""
        strength = min((rsi1.iloc[idx] - rsi2.iloc[idx]) / 50, 1.0)
        
        return DivergenceResult(
            symbol1=symbol1,
            symbol2=symbol2,
            divergence_type="momentum",
            direction="bearish",
            strength=strength,
            start_idx=idx-14,
            end_idx=idx,
            description=f"RSI de {symbol1} en sobrecompra mientras {symbol2} pierde momentum"
        )
    
    def _detect_volume_divergences(
        self, 
        aligned_data: pd.DataFrame, 
        symbol1: str, 
        symbol2: str
    ) -> List[DivergenceResult]:
        """Detecta divergencias de volumen."""
        divergences = []
        
        # Buscar divergencias en los últimos 10 períodos
        lookback = min(10, len(aligned_data) // 4)
        
        for i in range(lookback, len(aligned_data)):
            # Divergencia de volumen: un activo tiene volumen alto, otro bajo
            if self._is_volume_divergence(aligned_data, i, lookback):
                div = self._create_volume_divergence(
                    aligned_data, i, symbol1, symbol2
                )
                if div:
                    divergences.append(div)
        
        return divergences
    
    def _is_volume_divergence(
        self, 
        data: pd.DataFrame, 
        idx: int, 
        lookback: int
    ) -> bool:
        """Verifica si hay divergencia de volumen."""
        if idx < lookback:
            return False
        
        # Calcular volúmenes promedio
        vol1_avg = data.iloc[idx-lookback:idx]['volume_1'].mean()
        vol2_avg = data.iloc[idx-lookback:idx]['volume_2'].mean()
        
        current_vol1 = data.iloc[idx]['volume_1']
        current_vol2 = data.iloc[idx]['volume_2']
        
        # Un activo tiene volumen alto (>2x promedio), otro bajo (<0.5x promedio)
        vol1_high = current_vol1 > vol1_avg * 2
        vol2_low = current_vol2 < vol2_avg * 0.5
        
        vol1_low = current_vol1 < vol1_avg * 0.5
        vol2_high = current_vol2 > vol2_avg * 2
        
        return (vol1_high and vol2_low) or (vol1_low and vol2_high)
    
    def _create_volume_divergence(
        self, 
        data: pd.DataFrame, 
        idx: int, 
        symbol1: str, 
        symbol2: str
    ) -> Optional[DivergenceResult]:
        """Crea divergencia de volumen."""
        vol1_avg = data.iloc[idx-10:idx]['volume_1'].mean()
        vol2_avg = data.iloc[idx-10:idx]['volume_2'].mean()
        
        current_vol1 = data.iloc[idx]['volume_1']
        current_vol2 = data.iloc[idx]['volume_2']
        
        vol1_ratio = current_vol1 / vol1_avg
        vol2_ratio = current_vol2 / vol2_avg
        
        strength = min(abs(vol1_ratio - vol2_ratio) / 2, 1.0)
        
        if vol1_ratio > vol2_ratio:
            direction = "bullish"
            description = f"{symbol1} tiene volumen alto mientras {symbol2} tiene volumen bajo"
        else:
            direction = "bearish"
            description = f"{symbol2} tiene volumen alto mientras {symbol1} tiene volumen bajo"
        
        return DivergenceResult(
            symbol1=symbol1,
            symbol2=symbol2,
            divergence_type="volume",
            direction=direction,
            strength=strength,
            start_idx=idx-10,
            end_idx=idx,
            description=description
        )
    
    def analyze_pair(
        self, 
        df1: pd.DataFrame, 
        df2: pd.DataFrame, 
        symbol1: str, 
        symbol2: str
    ) -> PairAnalysis:
        """
        Análisis completo de un par de activos.
        
        Args:
            df1: DataFrame del primer activo
            df2: DataFrame del segundo activo
            symbol1: Símbolo del primer activo
            symbol2: Símbolo del segundo activo
            
        Returns:
            PairAnalysis con resultados completos
        """
        # Calcular correlación
        correlation = self.calculate_correlation(
            df1['close'], df2['close'], symbol1, symbol2
        )
        
        # Detectar divergencias
        divergences = self.detect_divergences(df1, df2, symbol1, symbol2)
        
        # Calcular ratios
        beta_ratio = self._calculate_beta_ratio(df1, df2)
        volatility_ratio = self._calculate_volatility_ratio(df1, df2)
        
        # Determinar oportunidad de trading
        trading_opportunity = self._determine_trading_opportunity(
            correlation, divergences, beta_ratio, volatility_ratio
        )
        
        return PairAnalysis(
            symbol1=symbol1,
            symbol2=symbol2,
            correlation=correlation,
            divergences=divergences,
            beta_ratio=beta_ratio,
            volatility_ratio=volatility_ratio,
            trading_opportunity=trading_opportunity
        )
    
    def _calculate_beta_ratio(self, df1: pd.DataFrame, df2: pd.DataFrame) -> float:
        """Calcula el ratio beta entre dos activos."""
        returns1 = df1['close'].pct_change().dropna()
        returns2 = df2['close'].pct_change().dropna()
        
        # Alinear retornos
        aligned_returns = pd.concat([returns1, returns2], axis=1).dropna()
        
        if len(aligned_returns) < 30:
            return 1.0
        
        # Calcular beta
        covariance = aligned_returns.iloc[:, 0].cov(aligned_returns.iloc[:, 1])
        variance = aligned_returns.iloc[:, 1].var()
        
        if variance == 0:
            return 1.0
        
        return covariance / variance
    
    def _calculate_volatility_ratio(self, df1: pd.DataFrame, df2: pd.DataFrame) -> float:
        """Calcula el ratio de volatilidad entre dos activos."""
        returns1 = df1['close'].pct_change().dropna()
        returns2 = df2['close'].pct_change().dropna()
        
        vol1 = returns1.std()
        vol2 = returns2.std()
        
        if vol2 == 0:
            return 1.0
        
        return vol1 / vol2
    
    def _determine_trading_opportunity(
        self, 
        correlation: CorrelationResult, 
        divergences: List[DivergenceResult],
        beta_ratio: float, 
        volatility_ratio: float
    ) -> Optional[str]:
        """Determina si hay oportunidad de trading basada en el análisis."""
        # Verificar si la correlación es suficientemente fuerte
        if correlation.correlation_strength != "strong":
            return None
        
        # Buscar divergencias recientes y fuertes
        strong_divergences = [d for d in divergences if d.strength > 0.7]
        
        if not strong_divergences:
            return None
        
        # Obtener la divergencia más reciente
        latest_divergence = max(strong_divergences, key=lambda x: x.end_idx)
        
        if latest_divergence.direction == "bullish":
            return f"LONG oportunidad basada en divergencia alcista de {latest_divergence.divergence_type}"
        else:
            return f"SHORT oportunidad basada en divergencia bajista de {latest_divergence.divergence_type}"
    
    def get_correlation_summary(self, pair_analysis: PairAnalysis) -> Dict[str, Any]:
        """
        Obtiene un resumen del análisis de correlación.
        
        Args:
            pair_analysis: Análisis del par de activos
            
        Returns:
            Diccionario con resumen
        """
        return {
            "symbols": f"{pair_analysis.symbol1} vs {pair_analysis.symbol2}",
            "correlation": {
                "pearson": round(pair_analysis.correlation.pearson_correlation, 3),
                "strength": pair_analysis.correlation.correlation_strength,
                "direction": pair_analysis.correlation.correlation_direction,
                "significant": pair_analysis.correlation.is_significant
            },
            "divergences": {
                "total": len(pair_analysis.divergences),
                "price": len([d for d in pair_analysis.divergences if d.divergence_type == "price"]),
                "momentum": len([d for d in pair_analysis.divergences if d.divergence_type == "momentum"]),
                "volume": len([d for d in pair_analysis.divergences if d.divergence_type == "volume"]),
                "strong": len([d for d in pair_analysis.divergences if d.strength > 0.7])
            },
            "ratios": {
                "beta": round(pair_analysis.beta_ratio, 3),
                "volatility": round(pair_analysis.volatility_ratio, 3)
            },
            "trading_opportunity": pair_analysis.trading_opportunity
        } 