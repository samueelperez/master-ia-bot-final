"""
Indicadores de Smart Money Concepts (SMC) para análisis técnico institucional.
Implementa Order Blocks, Fair Value Gaps, Break of Structure y otros conceptos avanzados.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass

@dataclass
class OrderBlock:
    """Representa un Order Block (OB)."""
    start_idx: int
    end_idx: int
    high: float
    low: float
    direction: str  # "bullish" or "bearish"
    strength: float  # 0.0 to 1.0
    volume_confirmation: bool

@dataclass
class FairValueGap:
    """Representa un Fair Value Gap (FVG)."""
    start_idx: int
    end_idx: int
    gap_high: float
    gap_low: float
    direction: str  # "bullish" or "bearish"
    filled: bool
    strength: float

@dataclass
class BreakOfStructure:
    """Representa un Break of Structure (BOS)."""
    idx: int
    price: float
    direction: str  # "bullish" or "bearish"
    strength: float
    volume_confirmation: bool

@dataclass
class ChangeOfCharacter:
    """Representa un Change of Character (CHoCH)."""
    idx: int
    price: float
    direction: str  # "bullish" or "bearish"
    strength: float

class SmartMoneyIndicators:
    """Indicadores de Smart Money Concepts."""
    
    def __init__(self):
        self.min_ob_size = 0.5  # Tamaño mínimo del Order Block (% del precio)
        self.min_fvg_size = 0.3  # Tamaño mínimo del FVG (% del precio)
    
    def detect_order_blocks(self, df: pd.DataFrame, lookback: int = 20) -> List[OrderBlock]:
        """
        Detecta Order Blocks en el DataFrame.
        
        Args:
            df: DataFrame con OHLCV
            lookback: Períodos hacia atrás para buscar
            
        Returns:
            Lista de OrderBlocks detectados
        """
        order_blocks = []
        
        for i in range(3, len(df) - 1):
            # Buscar Order Block alcista (última vela alcista antes de movimiento bajista)
            if self._is_bullish_ob(df, i):
                ob = self._create_bullish_ob(df, i)
                if ob:
                    order_blocks.append(ob)
            
            # Buscar Order Block bajista (última vela bajista antes de movimiento alcista)
            elif self._is_bearish_ob(df, i):
                ob = self._create_bearish_ob(df, i)
                if ob:
                    order_blocks.append(ob)
        
        return order_blocks
    
    def _is_bullish_ob(self, df: pd.DataFrame, idx: int) -> bool:
        """Verifica si hay un Order Block alcista en el índice."""
        if idx < 3 or idx >= len(df) - 1:
            return False
        
        # Vela actual debe ser alcista
        current_candle = df.iloc[idx]
        if current_candle['close'] <= current_candle['open']:
            return False
        
        # Siguiente vela debe ser bajista
        next_candle = df.iloc[idx + 1]
        if next_candle['close'] >= next_candle['open']:
            return False
        
        # Verificar que hay movimiento bajista significativo después
        return self._has_significant_move(df, idx + 1, "down")
    
    def _is_bearish_ob(self, df: pd.DataFrame, idx: int) -> bool:
        """Verifica si hay un Order Block bajista en el índice."""
        if idx < 3 or idx >= len(df) - 1:
            return False
        
        # Vela actual debe ser bajista
        current_candle = df.iloc[idx]
        if current_candle['close'] >= current_candle['open']:
            return False
        
        # Siguiente vela debe ser alcista
        next_candle = df.iloc[idx + 1]
        if next_candle['close'] <= next_candle['open']:
            return False
        
        # Verificar que hay movimiento alcista significativo después
        return self._has_significant_move(df, idx + 1, "up")
    
    def _has_significant_move(self, df: pd.DataFrame, start_idx: int, direction: str) -> bool:
        """Verifica si hay un movimiento significativo en la dirección especificada."""
        if start_idx >= len(df) - 5:
            return False
        
        start_price = df.iloc[start_idx]['close']
        
        for i in range(start_idx + 1, min(start_idx + 10, len(df))):
            current_price = df.iloc[i]['close']
            
            if direction == "up" and current_price > start_price * 1.02:  # 2% arriba
                return True
            elif direction == "down" and current_price < start_price * 0.98:  # 2% abajo
                return True
        
        return False
    
    def _create_bullish_ob(self, df: pd.DataFrame, idx: int) -> Optional[OrderBlock]:
        """Crea un Order Block alcista."""
        candle = df.iloc[idx]
        ob_size = (candle['high'] - candle['low']) / candle['close']
        
        if ob_size < self.min_ob_size:
            return None
        
        volume_confirmation = candle['volume'] > df.iloc[idx-3:idx]['volume'].mean()
        strength = min(ob_size / self.min_ob_size, 1.0)
        
        return OrderBlock(
            start_idx=idx,
            end_idx=idx,
            high=candle['high'],
            low=candle['low'],
            direction="bullish",
            strength=strength,
            volume_confirmation=volume_confirmation
        )
    
    def _create_bearish_ob(self, df: pd.DataFrame, idx: int) -> Optional[OrderBlock]:
        """Crea un Order Block bajista."""
        candle = df.iloc[idx]
        ob_size = (candle['high'] - candle['low']) / candle['close']
        
        if ob_size < self.min_ob_size:
            return None
        
        volume_confirmation = candle['volume'] > df.iloc[idx-3:idx]['volume'].mean()
        strength = min(ob_size / self.min_ob_size, 1.0)
        
        return OrderBlock(
            start_idx=idx,
            end_idx=idx,
            high=candle['high'],
            low=candle['low'],
            direction="bearish",
            strength=strength,
            volume_confirmation=volume_confirmation
        )
    
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        Detecta Fair Value Gaps en el DataFrame.
        
        Args:
            df: DataFrame con OHLCV
            
        Returns:
            Lista de FairValueGaps detectados
        """
        fvgs = []
        
        for i in range(1, len(df) - 2):
            # FVG alcista: vela 3 low > vela 1 high
            if self._is_bullish_fvg(df, i):
                fvg = self._create_bullish_fvg(df, i)
                if fvg:
                    fvgs.append(fvg)
            
            # FVG bajista: vela 3 high < vela 1 low
            elif self._is_bearish_fvg(df, i):
                fvg = self._create_bearish_fvg(df, i)
                if fvg:
                    fvgs.append(fvg)
        
        return fvgs
    
    def _is_bullish_fvg(self, df: pd.DataFrame, idx: int) -> bool:
        """Verifica si hay un FVG alcista."""
        if idx >= len(df) - 2:
            return False
        
        vela1 = df.iloc[idx]
        vela3 = df.iloc[idx + 2]
        
        return vela3['low'] > vela1['high']
    
    def _is_bearish_fvg(self, df: pd.DataFrame, idx: int) -> bool:
        """Verifica si hay un FVG bajista."""
        if idx >= len(df) - 2:
            return False
        
        vela1 = df.iloc[idx]
        vela3 = df.iloc[idx + 2]
        
        return vela3['high'] < vela1['low']
    
    def _create_bullish_fvg(self, df: pd.DataFrame, idx: int) -> Optional[FairValueGap]:
        """Crea un FVG alcista."""
        vela1 = df.iloc[idx]
        vela3 = df.iloc[idx + 2]
        
        gap_size = (vela3['low'] - vela1['high']) / vela1['close']
        
        if gap_size < self.min_fvg_size:
            return None
        
        # Verificar si está lleno
        filled = self._is_fvg_filled(df, idx, "bullish")
        strength = min(gap_size / self.min_fvg_size, 1.0)
        
        return FairValueGap(
            start_idx=idx,
            end_idx=idx + 2,
            gap_high=vela3['low'],
            gap_low=vela1['high'],
            direction="bullish",
            filled=filled,
            strength=strength
        )
    
    def _create_bearish_fvg(self, df: pd.DataFrame, idx: int) -> Optional[FairValueGap]:
        """Crea un FVG bajista."""
        vela1 = df.iloc[idx]
        vela3 = df.iloc[idx + 2]
        
        gap_size = (vela1['low'] - vela3['high']) / vela1['close']
        
        if gap_size < self.min_fvg_size:
            return None
        
        # Verificar si está lleno
        filled = self._is_fvg_filled(df, idx, "bearish")
        strength = min(gap_size / self.min_fvg_size, 1.0)
        
        return FairValueGap(
            start_idx=idx,
            end_idx=idx + 2,
            gap_high=vela1['low'],
            gap_low=vela3['high'],
            direction="bearish",
            filled=filled,
            strength=strength
        )
    
    def _is_fvg_filled(self, df: pd.DataFrame, fvg_idx: int, direction: str) -> bool:
        """Verifica si un FVG ha sido lleno."""
        if fvg_idx >= len(df) - 2:
            return False
        
        vela1 = df.iloc[fvg_idx]
        vela3 = df.iloc[fvg_idx + 2]
        
        for i in range(fvg_idx + 3, len(df)):
            candle = df.iloc[i]
            
            if direction == "bullish":
                if candle['low'] <= vela1['high']:
                    return True
            else:  # bearish
                if candle['high'] >= vela1['low']:
                    return True
        
        return False
    
    def detect_break_of_structure(self, df: pd.DataFrame, lookback: int = 10) -> List[BreakOfStructure]:
        """
        Detecta Break of Structure (BOS).
        
        Args:
            df: DataFrame con OHLCV
            lookback: Períodos para calcular estructura
            
        Returns:
            Lista de BreakOfStructure detectados
        """
        bos_list = []
        
        for i in range(lookback, len(df)):
            # BOS alcista: rompe máximo anterior
            if self._is_bullish_bos(df, i, lookback):
                bos = self._create_bullish_bos(df, i)
                if bos:
                    bos_list.append(bos)
            
            # BOS bajista: rompe mínimo anterior
            elif self._is_bearish_bos(df, i, lookback):
                bos = self._create_bearish_bos(df, i)
                if bos:
                    bos_list.append(bos)
        
        return bos_list
    
    def _is_bullish_bos(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """Verifica si hay un BOS alcista."""
        if idx < lookback:
            return False
        
        current_high = df.iloc[idx]['high']
        previous_highs = df.iloc[idx-lookback:idx]['high']
        
        return current_high > previous_highs.max()
    
    def _is_bearish_bos(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """Verifica si hay un BOS bajista."""
        if idx < lookback:
            return False
        
        current_low = df.iloc[idx]['low']
        previous_lows = df.iloc[idx-lookback:idx]['low']
        
        return current_low < previous_lows.min()
    
    def _create_bullish_bos(self, df: pd.DataFrame, idx: int) -> Optional[BreakOfStructure]:
        """Crea un BOS alcista."""
        candle = df.iloc[idx]
        volume_confirmation = candle['volume'] > df.iloc[idx-5:idx]['volume'].mean()
        
        # Calcular fuerza basada en el tamaño del break
        previous_highs = df.iloc[idx-10:idx]['high']
        break_size = (candle['high'] - previous_highs.max()) / previous_highs.max()
        strength = min(break_size * 10, 1.0)  # Normalizar
        
        return BreakOfStructure(
            idx=idx,
            price=candle['high'],
            direction="bullish",
            strength=strength,
            volume_confirmation=volume_confirmation
        )
    
    def _create_bearish_bos(self, df: pd.DataFrame, idx: int) -> Optional[BreakOfStructure]:
        """Crea un BOS bajista."""
        candle = df.iloc[idx]
        volume_confirmation = candle['volume'] > df.iloc[idx-5:idx]['volume'].mean()
        
        # Calcular fuerza basada en el tamaño del break
        previous_lows = df.iloc[idx-10:idx]['low']
        break_size = (previous_lows.min() - candle['low']) / previous_lows.min()
        strength = min(break_size * 10, 1.0)  # Normalizar
        
        return BreakOfStructure(
            idx=idx,
            price=candle['low'],
            direction="bearish",
            strength=strength,
            volume_confirmation=volume_confirmation
        )
    
    def detect_change_of_character(self, df: pd.DataFrame, lookback: int = 10) -> List[ChangeOfCharacter]:
        """
        Detecta Change of Character (CHoCH).
        
        Args:
            df: DataFrame con OHLCV
            lookback: Períodos para calcular estructura
            
        Returns:
            Lista de ChangeOfCharacter detectados
        """
        choch_list = []
        
        for i in range(lookback, len(df)):
            # CHoCH alcista: después de un BOS bajista, rompe estructura alcista
            if self._is_bullish_choch(df, i, lookback):
                choch = self._create_bullish_choch(df, i)
                if choch:
                    choch_list.append(choch)
            
            # CHoCH bajista: después de un BOS alcista, rompe estructura bajista
            elif self._is_bearish_choch(df, i, lookback):
                choch = self._create_bearish_choch(df, i)
                if choch:
                    choch_list.append(choch)
        
        return choch_list
    
    def _is_bullish_choch(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """Verifica si hay un CHoCH alcista."""
        if idx < lookback * 2:
            return False
        
        # Buscar BOS bajista previo
        bos_found = False
        for i in range(idx - lookback, idx):
            if self._is_bearish_bos(df, i, lookback):
                bos_found = True
                break
        
        if not bos_found:
            return False
        
        # Verificar si ahora rompe estructura alcista
        return self._is_bullish_bos(df, idx, lookback)
    
    def _is_bearish_choch(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """Verifica si hay un CHoCH bajista."""
        if idx < lookback * 2:
            return False
        
        # Buscar BOS alcista previo
        bos_found = False
        for i in range(idx - lookback, idx):
            if self._is_bullish_bos(df, i, lookback):
                bos_found = True
                break
        
        if not bos_found:
            return False
        
        # Verificar si ahora rompe estructura bajista
        return self._is_bearish_bos(df, idx, lookback)
    
    def _create_bullish_choch(self, df: pd.DataFrame, idx: int) -> Optional[ChangeOfCharacter]:
        """Crea un CHoCH alcista."""
        candle = df.iloc[idx]
        
        # Calcular fuerza basada en el tamaño del cambio
        previous_lows = df.iloc[idx-10:idx]['low']
        change_size = (candle['high'] - previous_lows.min()) / previous_lows.min()
        strength = min(change_size * 5, 1.0)  # Normalizar
        
        return ChangeOfCharacter(
            idx=idx,
            price=candle['high'],
            direction="bullish",
            strength=strength
        )
    
    def _create_bearish_choch(self, df: pd.DataFrame, idx: int) -> Optional[ChangeOfCharacter]:
        """Crea un CHoCH bajista."""
        candle = df.iloc[idx]
        
        # Calcular fuerza basada en el tamaño del cambio
        previous_highs = df.iloc[idx-10:idx]['high']
        change_size = (previous_highs.max() - candle['low']) / previous_highs.max()
        strength = min(change_size * 5, 1.0)  # Normalizar
        
        return ChangeOfCharacter(
            idx=idx,
            price=candle['low'],
            direction="bearish",
            strength=strength
        )
    
    def get_smart_money_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Obtiene un resumen completo de Smart Money Concepts.
        
        Args:
            df: DataFrame con OHLCV
            
        Returns:
            Diccionario con resumen de SMC
        """
        order_blocks = self.detect_order_blocks(df)
        fvgs = self.detect_fair_value_gaps(df)
        bos_list = self.detect_break_of_structure(df)
        choch_list = self.detect_change_of_character(df)
        
        return {
            "order_blocks": {
                "count": len(order_blocks),
                "bullish": len([ob for ob in order_blocks if ob.direction == "bullish"]),
                "bearish": len([ob for ob in order_blocks if ob.direction == "bearish"]),
                "strong": len([ob for ob in order_blocks if ob.strength > 0.7])
            },
            "fair_value_gaps": {
                "count": len(fvgs),
                "bullish": len([fvg for fvg in fvgs if fvg.direction == "bullish"]),
                "bearish": len([fvg for fvg in fvgs if fvg.direction == "bearish"]),
                "filled": len([fvg for fvg in fvgs if fvg.filled]),
                "unfilled": len([fvg for fvg in fvgs if not fvg.filled])
            },
            "break_of_structure": {
                "count": len(bos_list),
                "bullish": len([bos for bos in bos_list if bos.direction == "bullish"]),
                "bearish": len([bos for bos in bos_list if bos.direction == "bearish"]),
                "with_volume": len([bos for bos in bos_list if bos.volume_confirmation])
            },
            "change_of_character": {
                "count": len(choch_list),
                "bullish": len([choch for choch in choch_list if choch.direction == "bullish"]),
                "bearish": len([choch for choch in choch_list if choch.direction == "bearish"])
            }
        } 