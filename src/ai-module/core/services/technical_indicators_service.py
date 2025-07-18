"""
Servicio para obtener indicadores técnicos reales del backend.
"""
import asyncio
import aiohttp
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class TechnicalIndicatorsService:
    """Servicio para obtener indicadores técnicos del backend."""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self._session: Optional[aiohttp.ClientSession] = None
        # Token para autenticación con el backend
        self.backend_token = os.getenv("BACKEND_API_SECRET_KEY", "cr1nW3IDA-CQlkm6XBIoIdZmqv9mLj6U_-1z0ttyOZ4")
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener sesión HTTP reutilizable."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Cerrar la sesión HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Obtener el estado del servicio de indicadores técnicos.
        
        Returns:
            Diccionario con el estado del servicio
        """
        return {
            "status": "healthy",
            "backend_url": self.backend_url,
            "session_active": self._session is not None and not (self._session.closed if self._session else True),
            "service_name": "TechnicalIndicatorsService",
            "version": "1.0.0",
            "capabilities": [
                "technical_indicators",
                "trading_signals", 
                "confidence_levels",
                "comprehensive_analysis",
                "trading_levels_extraction"
            ]
        }
    
    def _normalize_backend_indicators(self, backend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizar los indicadores del backend al formato esperado.
        
        Args:
            backend_data: Datos del backend con formato original
            
        Returns:
            Diccionario con indicadores normalizados
        """
        indicators = backend_data.get("indicators", {})
        normalized = {}
        
        # Mapeo de nombres del backend a nombres esperados
        indicator_mapping = {
            # RSI
            "RSI": "rsi_14",
            "rsi": "rsi_14",
            
            # MACD
            "MACD": "macd_line",
            "macd": "macd_line",
            "MACD_Signal": "macd_signal",
            "macd_signal": "macd_signal",
            
            # Medias Móviles
            "SMA_20": "sma_20",
            "SMA_50": "sma_50",
            "SMA_200": "sma_200",
            "EMA_12": "ema_12",
            "EMA_26": "ema_26",
            "EMA_20": "ema_20",
            "EMA_50": "ema_50",
            "EMA_200": "ema_200",
            
            # Bollinger Bands
            "Bollinger_Upper": "bb_20_2.0_upper",
            "Bollinger_Lower": "bb_20_2.0_lower",
            "Bollinger_Middle": "bb_20_2.0_middle",
            
            # Estocástico
            "Stoch_K": "stoch_k",
            "Stoch_D": "stoch_d",
            
            # ATR
            "ATR": "atr_14",
            "atr": "atr_14",
            
            # ADX
            "ADX": "adx_14",
            "adx": "adx_14",
            
            # CCI
            "CCI": "cci_14",
            "cci": "cci_14",
            
            # Williams %R
            "Williams_R": "williams_14",
            "williams_r": "williams_14",
            
            # VWAP
            "VWAP": "vwap",
            "vwap": "vwap",
            
            # Parabolic SAR
            "SAR": "parabolic_sar",
            "Parabolic_SAR": "parabolic_sar",
            "sar": "parabolic_sar",
        }
        
        # Aplicar mapeo
        for backend_key, value in indicators.items():
            if backend_key in indicator_mapping:
                normalized_key = indicator_mapping[backend_key]
                normalized[normalized_key] = value
            else:
                # Mantener el nombre original si no hay mapeo
                normalized[backend_key.lower()] = value
        
        # Copiar otros campos del backend
        result = backend_data.copy()
        result["indicators"] = normalized
        
        logger.info(f"Indicadores normalizados: {len(normalized)} indicadores disponibles")
        return result

    async def get_technical_indicators(
        self,
        symbol: str,
        timeframe: str = "1h",
        indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Obtener indicadores técnicos del backend.
        
        Args:
            symbol: Símbolo de la criptomoneda (ej: BTC, ETH)
            timeframe: Timeframe para los datos (1m, 5m, 15m, 1h, 4h, 1d)
            indicators: Lista de indicadores específicos a obtener
        
        Returns:
            Diccionario con los indicadores técnicos calculados
        
        Raises:
            Exception: Si no se pueden obtener los indicadores del backend
        """
        session = await self._get_session()
        
        # Endpoint del backend para indicadores técnicos
        url = f"{self.backend_url}/indicators"
        
        params = {
            "symbol": f"{symbol}-USD",  # Formato esperado por el backend
            "tf": timeframe,
            "limit": 100,  # Obtener suficientes datos para cálculos
            "profile": "advanced"  # Usar perfil avanzado para obtener todos los indicadores
        }
        
        if indicators:
            params["indicators"] = ",".join(indicators)
        
        # Headers con autenticación
        headers = {
            "Authorization": f"Bearer {self.backend_token}"
        }
        
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                # Normalizar los indicadores al formato esperado
                normalized_data = self._normalize_backend_indicators(data)
                logger.info(f"Indicadores técnicos obtenidos para {symbol} ({timeframe})")
                return normalized_data
            else:
                error_msg = f"Error obteniendo indicadores del backend: HTTP {response.status}"
                logger.error(error_msg)
                raise Exception(error_msg)
    
    def format_indicators_for_analysis(self, indicators: Dict[str, Any]) -> str:
        """
        Formatear indicadores técnicos para incluir en el análisis.
        
        Args:
            indicators: Diccionario con indicadores técnicos
            
        Returns:
            String formateado con los indicadores técnicos
        """
        indicators_data = indicators.get("indicators", {})
        
        # Verificar si hay indicadores disponibles
        if not indicators_data:
            return "⚠️ No se pudieron obtener indicadores técnicos del backend"
        
        # Formatear todos los indicadores disponibles
        formatted_indicators = self._format_all_indicators(indicators_data)
        
        if formatted_indicators:
            # Agregar información sobre el estado de los datos
            status_info = ""
            if indicators.get("status") == "demo_mode":
                status_info = "\n⚠️ Datos de demostración - conectar servicios externos para datos reales"
            
            return "📊 INDICADORES TÉCNICOS:\n" + "\n".join(f"• {data}" for data in formatted_indicators) + status_info
        else:
            # Si no hay indicadores formateados pero sí hay datos, mostrar qué se recibió
            available_keys = list(indicators_data.keys())
            return f"⚠️ Indicadores disponibles pero no formateados: {', '.join(available_keys[:5])}"
    
    def _format_all_indicators(self, indicators_data: Dict[str, Any]) -> List[str]:
        """Formatear todos los indicadores técnicos disponibles."""
        formatted = []
        
        # 1. RSI (Relative Strength Index)
        for period in [6, 14, 21]:
            key = f"rsi_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                rsi = indicators_data[key]
                status = "sobrecompra" if rsi > 70 else "sobreventa" if rsi < 30 else "neutral"
                formatted.append(f"RSI({period}): {rsi:.1f} ({status})")
        
        # 2. MACD
        if "macd_line" in indicators_data and indicators_data["macd_line"] is not None:
            macd_line = indicators_data["macd_line"]
            macd_signal = indicators_data.get("macd_signal", 0)
            trend = "alcista" if macd_line > macd_signal else "bajista"
            formatted.append(f"MACD: {trend} ({macd_line:.3f})")
        
        # 3. Medias Móviles (SMA/EMA)
        sma_periods = [9, 20, 50, 100, 200]
        ema_periods = [9, 12, 20, 26, 50, 100, 200]
        
        for period in sma_periods:
            key = f"sma_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                formatted.append(f"SMA({period}): ${indicators_data[key]:,.2f}")
        
        for period in ema_periods:
            key = f"ema_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                formatted.append(f"EMA({period}): ${indicators_data[key]:,.2f}")
        
        # 4. Bollinger Bands
        if "bb_20_2.0_upper" in indicators_data:
            bb_upper = indicators_data["bb_20_2.0_upper"]
            bb_lower = indicators_data["bb_20_2.0_lower"]
            if bb_upper and bb_lower:
                formatted.append(f"Bollinger: ${bb_lower:,.0f} - ${bb_upper:,.0f}")
        
        # 5. Estocástico
        if "stoch_k" in indicators_data and indicators_data["stoch_k"] is not None:
            stoch_k = indicators_data["stoch_k"]
            stoch_d = indicators_data.get("stoch_d", 0)
            status = "sobrecompra" if stoch_k > 80 else "sobreventa" if stoch_k < 20 else "neutral"
            formatted.append(f"Estocástico: %K={stoch_k:.1f}, %D={stoch_d:.1f} ({status})")
        
        # 6. CCI (Commodity Channel Index)
        for period in [14, 20]:
            key = f"cci_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                cci = indicators_data[key]
                status = "sobrecompra" if cci > 100 else "sobreventa" if cci < -100 else "neutral"
                formatted.append(f"CCI({period}): {cci:.1f} ({status})")
        
        # 7. Williams %R
        for period in [14, 20]:
            key = f"williams_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                williams = indicators_data[key]
                status = "sobrecompra" if williams > -20 else "sobreventa" if williams < -80 else "neutral"
                formatted.append(f"Williams%R({period}): {williams:.1f} ({status})")
        
        # 8. ADX (Average Directional Index)
        if "adx_14" in indicators_data and indicators_data["adx_14"] is not None:
            adx = indicators_data["adx_14"]
            strength = "fuerte" if adx > 25 else "débil" if adx < 20 else "moderada"
            formatted.append(f"ADX: {adx:.1f} (tendencia {strength})")
        
        # 9. SAR Parabólico
        if "parabolic_sar" in indicators_data and indicators_data["parabolic_sar"] is not None:
            sar = indicators_data["parabolic_sar"]
            formatted.append(f"SAR Parabólico: ${sar:,.2f}")
        
        # 10. ATR (Average True Range)
        if "atr_14" in indicators_data and indicators_data["atr_14"] is not None:
            atr = indicators_data["atr_14"]
            formatted.append(f"ATR(14): ${atr:,.2f}")
        
        # 11. Ichimoku
        if "tenkan_sen" in indicators_data and indicators_data["tenkan_sen"] is not None:
            tenkan = indicators_data["tenkan_sen"]
            kijun = indicators_data.get("kijun_sen", 0)
            cloud_pos = indicators_data.get("cloud_position", "unknown")
            formatted.append(f"Ichimoku: Tenkan=${tenkan:,.2f}, posición {cloud_pos}")
        
        # 12. Keltner Channels
        if "keltner_upper" in indicators_data and indicators_data["keltner_upper"] is not None:
            k_upper = indicators_data["keltner_upper"]
            k_lower = indicators_data["keltner_lower"]
            formatted.append(f"Keltner: ${k_lower:,.2f} - ${k_upper:,.2f}")
        
        # 13. Donchian Channels
        if "dc_20_upper" in indicators_data and indicators_data["dc_20_upper"] is not None:
            dc_upper = indicators_data["dc_20_upper"]
            dc_lower = indicators_data["dc_20_lower"]
            formatted.append(f"Donchian: ${dc_lower:,.2f} - ${dc_upper:,.2f}")
        
        # 14. Ultimate Oscillator
        if "uo" in indicators_data and indicators_data["uo"] is not None:
            uo = indicators_data["uo"]
            status = "sobrecompra" if uo > 70 else "sobreventa" if uo < 30 else "neutral"
            formatted.append(f"Ultimate Oscillator: {uo:.1f} ({status})")
        
        # 15. TRIX
        for period in [9, 14, 30]:
            key = f"trix_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                trix = indicators_data[key]
                trend = "alcista" if trix > 0 else "bajista"
                formatted.append(f"TRIX({period}): {trend}")
        
        # 16. Vortex Indicator
        for period in [14, 20]:
            key = f"vortex_signal_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                vortex_signal = indicators_data[key]
                formatted.append(f"Vortex({period}): {vortex_signal}")
        
        # 17. Momentum
        for period in [10, 14]:
            key = f"mom_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                mom = indicators_data[key]
                trend = "alcista" if mom > 0 else "bajista"
                formatted.append(f"Momentum({period}): {trend}")
        
        # 18. OBV (On-Balance Volume)
        if "obv" in indicators_data and indicators_data["obv"] is not None:
            obv_trend = indicators_data.get("obv_trend", "neutral")
            formatted.append(f"OBV: tendencia {obv_trend}")
        
        # 19. Chaikin Money Flow
        for period in [20, 50]:
            key = f"cmf_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                cmf = indicators_data[key]
                flow = "compradora" if cmf > 0.05 else "vendedora" if cmf < -0.05 else "neutral"
                formatted.append(f"CMF({period}): presión {flow}")
        
        # 20. Force Index
        for period in [13, 50]:
            key = f"fi_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                fi = indicators_data[key]
                force = "alcista" if fi > 0 else "bajista"
                formatted.append(f"Force Index({period}): {force}")
        
        # 21. MFI (Money Flow Index)
        for period in [14, 50]:
            key = f"mfi_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                mfi = indicators_data[key]
                status = "sobrecompra" if mfi > 80 else "sobreventa" if mfi < 20 else "neutral"
                formatted.append(f"MFI({period}): {mfi:.1f} ({status})")
        
        # 22. VWAP
        if "vwap" in indicators_data and indicators_data["vwap"] is not None:
            vwap = indicators_data["vwap"]
            position = indicators_data.get("vwap_position", "unknown")
            formatted.append(f"VWAP: ${vwap:,.2f} (precio {position})")
        
        # 23. McGinley Dynamic
        if "mcginley_dynamic" in indicators_data and indicators_data["mcginley_dynamic"] is not None:
            mcginley = indicators_data["mcginley_dynamic"]
            formatted.append(f"McGinley Dynamic: ${mcginley:,.2f}")
        
        # 24. True Strength Index (TSI)
        if "tsi" in indicators_data and indicators_data["tsi"] is not None:
            tsi = indicators_data["tsi"]
            tsi_signal = indicators_data.get("tsi_signal", 0)
            trend = "alcista" if tsi > tsi_signal else "bajista"
            formatted.append(f"TSI: {trend} ({tsi:.2f})")
        
        # 25. Balance of Power (BOP)
        if "bop" in indicators_data and indicators_data["bop"] is not None:
            bop = indicators_data["bop"]
            power = "compradores" if bop > 0.1 else "vendedores" if bop < -0.1 else "equilibrio"
            formatted.append(f"BOP: dominio {power}")
        
        # 26. Volume Price Trend (VPT)
        if "vpt" in indicators_data and indicators_data["vpt"] is not None:
            vpt_trend = indicators_data.get("vpt_trend", "neutral")
            formatted.append(f"VPT: tendencia {vpt_trend}")
        
        # 27. Accumulation/Distribution Line
        if "ad" in indicators_data and indicators_data["ad"] is not None:
            ad_trend = indicators_data.get("ad_trend", "neutral")
            formatted.append(f"A/D Line: {ad_trend}")
        
        # 28. SuperTrend
        if "supertrend" in indicators_data and indicators_data["supertrend"] is not None:
            supertrend_signal = indicators_data.get("supertrend_signal", "neutral")
            formatted.append(f"SuperTrend: {supertrend_signal}")
        
        # 29. Hull Moving Average (HMA)
        for period in [9, 21]:
            key = f"hma_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                hma = indicators_data[key]
                formatted.append(f"HMA({period}): ${hma:,.2f}")
        
        # 30. Connors RSI
        if "connors_rsi" in indicators_data and indicators_data["connors_rsi"] is not None:
            crsi = indicators_data["connors_rsi"]
            status = "sobrecompra" if crsi > 90 else "sobreventa" if crsi < 10 else "neutral"
            formatted.append(f"Connors RSI: {crsi:.1f} ({status})")
        
        # 31. QQE (Quantitative Qualitative Estimation)
        if "qqe" in indicators_data and indicators_data["qqe"] is not None:
            qqe = indicators_data["qqe"]
            qqe_signal = indicators_data.get("qqe_signal", 0)
            trend = "alcista" if qqe > qqe_signal else "bajista"
            formatted.append(f"QQE: {trend}")
        
        # 32. Zero Lag EMA
        for period in [12, 26]:
            key = f"zlema_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                zlema = indicators_data[key]
                formatted.append(f"Zero Lag EMA({period}): ${zlema:,.2f}")
        
        # 33. FRAMA (Fractal Adaptive Moving Average)
        if "frama" in indicators_data and indicators_data["frama"] is not None:
            frama = indicators_data["frama"]
            formatted.append(f"FRAMA: ${frama:,.2f}")
        
        # 34. Triangular Moving Average (TMA)
        for period in [20, 50]:
            key = f"tma_{period}"
            if key in indicators_data and indicators_data[key] is not None:
                tma = indicators_data[key]
                formatted.append(f"TMA({period}): ${tma:,.2f}")
        
        # 35. Anchored VWAP
        if "anchored_vwap" in indicators_data and indicators_data["anchored_vwap"] is not None:
            avwap = indicators_data["anchored_vwap"]
            formatted.append(f"Anchored VWAP: ${avwap:,.2f}")
        
        # 36. Volatility Stop (VSTOP)
        if "vstop" in indicators_data and indicators_data["vstop"] is not None:
            vstop = indicators_data["vstop"]
            vstop_signal = indicators_data.get("vstop_signal", "neutral")
            formatted.append(f"VSTOP: {vstop_signal}")
        
        # 37. Negative Volume Index (NVI)
        if "nvi" in indicators_data and indicators_data["nvi"] is not None:
            nvi_trend = indicators_data.get("nvi_trend", "neutral")
            formatted.append(f"NVI: {nvi_trend}")
        
        # 38. Positive Volume Index (PVI)
        if "pvi" in indicators_data and indicators_data["pvi"] is not None:
            pvi_trend = indicators_data.get("pvi_trend", "neutral")
            formatted.append(f"PVI: {pvi_trend}")
        
        # 39. Guppy Multiple Moving Averages
        if "guppy_short_aligned" in indicators_data and "guppy_long_aligned" in indicators_data:
            guppy_short = indicators_data["guppy_short_aligned"]
            guppy_long = indicators_data["guppy_long_aligned"]
            if guppy_short and guppy_long:
                formatted.append(f"Guppy MMA: traders {guppy_short}, institucional {guppy_long}")
        
        # 40. Jurik Moving Average (JMA)
        if "jma" in indicators_data and indicators_data["jma"] is not None:
            jma = indicators_data["jma"]
            formatted.append(f"JMA: ${jma:,.2f}")
        
        # Limitar a los más relevantes para evitar saturación
        return formatted[:15] if len(formatted) > 15 else formatted
    
    def extract_trading_levels(self, indicators: Dict[str, Any], current_price: float) -> Dict[str, float]:
        """
        Extraer niveles de trading de los indicadores técnicos.
        
        Args:
            indicators: Diccionario con indicadores técnicos
            current_price: Precio actual
            
        Returns:
            Diccionario con niveles de soporte, resistencia, etc.
        """
        levels = {}
        
        indicators_data = indicators.get("indicators", {})
        
        # Bollinger Bands (soporte/resistencia dinámicos)
        if "bb_20_2.0_upper" in indicators_data and indicators_data["bb_20_2.0_upper"]:
            levels["bb_resistance"] = indicators_data["bb_20_2.0_upper"]
            levels["resistance"] = indicators_data["bb_20_2.0_upper"]
            
        if "bb_20_2.0_lower" in indicators_data and indicators_data["bb_20_2.0_lower"]:
            levels["bb_support"] = indicators_data["bb_20_2.0_lower"]
            levels["support"] = indicators_data["bb_20_2.0_lower"]
        
        # Keltner Channels
        if "keltner_upper" in indicators_data and indicators_data["keltner_upper"]:
            levels["keltner_resistance"] = indicators_data["keltner_upper"]
            if "resistance" not in levels:
                levels["resistance"] = indicators_data["keltner_upper"]
                
        if "keltner_lower" in indicators_data and indicators_data["keltner_lower"]:
            levels["keltner_support"] = indicators_data["keltner_lower"]
            if "support" not in levels:
                levels["support"] = indicators_data["keltner_lower"]
        
        # Donchian Channels
        if "dc_20_upper" in indicators_data and indicators_data["dc_20_upper"]:
            levels["donchian_resistance"] = indicators_data["dc_20_upper"]
            
        if "dc_20_lower" in indicators_data and indicators_data["dc_20_lower"]:
            levels["donchian_support"] = indicators_data["dc_20_lower"]
        
        # Medias móviles como soporte/resistencia
        key_emas = ["ema_20", "ema_50", "ema_200"]
        key_smas = ["sma_20", "sma_50", "sma_200"]
        
        for key in key_emas + key_smas:
            if key in indicators_data and indicators_data[key]:
                ma_value = indicators_data[key]
                if ma_value < current_price:
                    levels[f"{key}_support"] = ma_value
                    if "support" not in levels or ma_value > levels["support"]:
                        levels["support"] = ma_value
                else:
                    levels[f"{key}_resistance"] = ma_value
                    if "resistance" not in levels or ma_value < levels["resistance"]:
                        levels["resistance"] = ma_value
        
        # SAR Parabólico
        if "parabolic_sar" in indicators_data and indicators_data["parabolic_sar"]:
            sar_value = indicators_data["parabolic_sar"]
            if sar_value < current_price:
                levels["sar_support"] = sar_value
            else:
                levels["sar_resistance"] = sar_value
        
        # VWAP
        if "vwap" in indicators_data and indicators_data["vwap"]:
            vwap_value = indicators_data["vwap"]
            if vwap_value < current_price:
                levels["vwap_support"] = vwap_value
            else:
                levels["vwap_resistance"] = vwap_value
        
        # McGinley Dynamic
        if "mcginley_dynamic" in indicators_data and indicators_data["mcginley_dynamic"]:
            mcginley_value = indicators_data["mcginley_dynamic"]
            if mcginley_value < current_price:
                levels["mcginley_support"] = mcginley_value
            else:
                levels["mcginley_resistance"] = mcginley_value
        
        # SuperTrend
        if "supertrend" in indicators_data and indicators_data["supertrend"]:
            supertrend_value = indicators_data["supertrend"]
            supertrend_signal = indicators_data.get("supertrend_signal", "neutral")
            if supertrend_signal == "bullish":
                levels["supertrend_support"] = supertrend_value
            elif supertrend_signal == "bearish":
                levels["supertrend_resistance"] = supertrend_value
        
        # Hull Moving Average (HMA)
        for period in [9, 21]:
            key = f"hma_{period}"
            if key in indicators_data and indicators_data[key]:
                hma_value = indicators_data[key]
                if hma_value < current_price:
                    levels[f"{key}_support"] = hma_value
                else:
                    levels[f"{key}_resistance"] = hma_value
        
        # Zero Lag EMA
        for period in [12, 26]:
            key = f"zlema_{period}"
            if key in indicators_data and indicators_data[key]:
                zlema_value = indicators_data[key]
                if zlema_value < current_price:
                    levels[f"{key}_support"] = zlema_value
                else:
                    levels[f"{key}_resistance"] = zlema_value
        
        # FRAMA (Fractal Adaptive Moving Average)
        if "frama" in indicators_data and indicators_data["frama"]:
            frama_value = indicators_data["frama"]
            if frama_value < current_price:
                levels["frama_support"] = frama_value
            else:
                levels["frama_resistance"] = frama_value
        
        # Triangular Moving Average (TMA)
        for period in [20, 50]:
            key = f"tma_{period}"
            if key in indicators_data and indicators_data[key]:
                tma_value = indicators_data[key]
                if tma_value < current_price:
                    levels[f"{key}_support"] = tma_value
                else:
                    levels[f"{key}_resistance"] = tma_value
        
        # Anchored VWAP
        if "anchored_vwap" in indicators_data and indicators_data["anchored_vwap"]:
            avwap_value = indicators_data["anchored_vwap"]
            if avwap_value < current_price:
                levels["anchored_vwap_support"] = avwap_value
            else:
                levels["anchored_vwap_resistance"] = avwap_value
        
        # Volatility Stop (VSTOP)
        if "vstop" in indicators_data and indicators_data["vstop"]:
            vstop_value = indicators_data["vstop"]
            vstop_signal = indicators_data.get("vstop_signal", "neutral")
            if vstop_signal == "bullish":
                levels["vstop_support"] = vstop_value
            elif vstop_signal == "bearish":
                levels["vstop_resistance"] = vstop_value
        
        # Jurik Moving Average (JMA)
        if "jma" in indicators_data and indicators_data["jma"]:
            jma_value = indicators_data["jma"]
            if jma_value < current_price:
                levels["jma_support"] = jma_value
            else:
                levels["jma_resistance"] = jma_value
        
        # Si no hay niveles específicos, usar niveles psicológicos
        if "support" not in levels:
            levels["support"] = current_price * 0.985
        if "resistance" not in levels:
            levels["resistance"] = current_price * 1.015
            
        return levels
    
    def get_trading_signal_from_indicators(self, indicators: Dict[str, Any]) -> str:
        """
        Determinar señal de trading basada en múltiples estrategias de indicadores técnicos.
        
        Args:
            indicators: Diccionario con indicadores técnicos
            
        Returns:
            Señal de trading: "LONG", "SHORT", o "NEUTRAL"
        """
        indicators_data = indicators.get("indicators", {})
        signals = []
        
        # 1. Estrategia RSI (Relative Strength Index)
        for period in [14, 21]:
            rsi_key = f"rsi_{period}"
            if rsi_key in indicators_data and indicators_data[rsi_key] is not None:
                rsi = indicators_data[rsi_key]
                if rsi < 30:
                    signals.append("LONG")  # Sobreventa
                elif rsi > 70:
                    signals.append("SHORT")  # Sobrecompra
        
        # 2. Estrategia MACD (Cruce de líneas)
        if all(k in indicators_data for k in ["macd_line", "macd_signal"]):
            macd_line = indicators_data["macd_line"]
            macd_signal = indicators_data["macd_signal"]
            if macd_line is not None and macd_signal is not None:
                if macd_line > macd_signal:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # 3. Estrategia de Medias Móviles (Cruces)
        # Cruce EMA 12/26 (Golden Cross)
        if all(k in indicators_data for k in ["ema_12", "ema_26"]):
            ema_12 = indicators_data["ema_12"]
            ema_26 = indicators_data["ema_26"]
            if ema_12 is not None and ema_26 is not None:
                if ema_12 > ema_26:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # Cruce SMA 20/50
        if all(k in indicators_data for k in ["sma_20", "sma_50"]):
            sma_20 = indicators_data["sma_20"]
            sma_50 = indicators_data["sma_50"]
            if sma_20 is not None and sma_50 is not None:
                if sma_20 > sma_50:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # 4. Estrategia Estocástico (Cruce %K y %D)
        if all(k in indicators_data for k in ["stoch_k", "stoch_d"]):
            stoch_k = indicators_data["stoch_k"]
            stoch_d = indicators_data["stoch_d"]
            if stoch_k is not None and stoch_d is not None:
                if stoch_k > stoch_d and stoch_k < 80:  # Cruce alcista no en sobrecompra
                    signals.append("LONG")
                elif stoch_k < stoch_d and stoch_k > 20:  # Cruce bajista no en sobreventa
                    signals.append("SHORT")
        
        # 5. Estrategia CCI (Commodity Channel Index)
        for period in [14, 20]:
            cci_key = f"cci_{period}"
            if cci_key in indicators_data and indicators_data[cci_key] is not None:
                cci = indicators_data[cci_key]
                if cci < -100:  # Sobreventa
                    signals.append("LONG")
                elif cci > 100:  # Sobrecompra
                    signals.append("SHORT")
        
        # 6. Estrategia Williams %R
        for period in [14, 20]:
            williams_key = f"williams_{period}"
            if williams_key in indicators_data and indicators_data[williams_key] is not None:
                williams = indicators_data[williams_key]
                if williams < -80:  # Sobreventa
                    signals.append("LONG")
                elif williams > -20:  # Sobrecompra
                    signals.append("SHORT")
        
        # 7. Estrategia ADX (Fuerza de tendencia)
        if "adx_14" in indicators_data and indicators_data["adx_14"] is not None:
            adx = indicators_data["adx_14"]
            # ADX solo confirma fuerza, necesitamos DI+ y DI-
            if "di_plus_14" in indicators_data and "di_minus_14" in indicators_data:
                di_plus = indicators_data["di_plus_14"]
                di_minus = indicators_data["di_minus_14"]
                if adx > 25 and di_plus is not None and di_minus is not None:
                    if di_plus > di_minus:
                        signals.append("LONG")
                    else:
                        signals.append("SHORT")
        
        # 8. Estrategia Ichimoku
        if "cloud_position" in indicators_data:
            cloud_pos = indicators_data["cloud_position"]
            if cloud_pos == "above":
                signals.append("LONG")
            elif cloud_pos == "below":
                signals.append("SHORT")
        
        # 9. Estrategia Ultimate Oscillator
        if "uo" in indicators_data and indicators_data["uo"] is not None:
            uo = indicators_data["uo"]
            if uo < 30:
                signals.append("LONG")
            elif uo > 70:
                signals.append("SHORT")
        
        # 10. Estrategia TRIX
        for period in [14, 30]:
            trix_key = f"trix_{period}"
            if trix_key in indicators_data and indicators_data[trix_key] is not None:
                trix = indicators_data[trix_key]
                if trix > 0:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # 11. Estrategia Momentum
        for period in [10, 14]:
            mom_key = f"mom_{period}"
            if mom_key in indicators_data and indicators_data[mom_key] is not None:
                mom = indicators_data[mom_key]
                if mom > 0:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # 12. Estrategia Chaikin Money Flow
        for period in [20, 50]:
            cmf_key = f"cmf_{period}"
            if cmf_key in indicators_data and indicators_data[cmf_key] is not None:
                cmf = indicators_data[cmf_key]
                if cmf > 0.05:
                    signals.append("LONG")
                elif cmf < -0.05:
                    signals.append("SHORT")
        
        # 13. Estrategia Force Index
        for period in [13, 50]:
            fi_key = f"fi_{period}"
            if fi_key in indicators_data and indicators_data[fi_key] is not None:
                fi = indicators_data[fi_key]
                if fi > 0:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # 14. Estrategia MFI (Money Flow Index)  
        for period in [14, 50]:
            mfi_key = f"mfi_{period}"
            if mfi_key in indicators_data and indicators_data[mfi_key] is not None:
                mfi = indicators_data[mfi_key]
                if mfi < 20:
                    signals.append("LONG")
                elif mfi > 80:
                    signals.append("SHORT")
        
        # 15. Estrategia True Strength Index (TSI)
        if "tsi" in indicators_data and indicators_data["tsi"] is not None:
            tsi = indicators_data["tsi"]
            if tsi > 0:
                signals.append("LONG")
            else:
                signals.append("SHORT")
        
        # 16. Estrategia Balance of Power (BOP)
        if "bop" in indicators_data and indicators_data["bop"] is not None:
            bop = indicators_data["bop"]
            if bop > 0.1:
                signals.append("LONG")  # Dominio compradores
            elif bop < -0.1:
                signals.append("SHORT")  # Dominio vendedores
        
        # 17. Estrategia Volume Price Trend (VPT)
        if "vpt_trend" in indicators_data and indicators_data["vpt_trend"] is not None:
            vpt_trend = indicators_data["vpt_trend"]
            if vpt_trend == "rising":
                signals.append("LONG")
            elif vpt_trend == "falling":
                signals.append("SHORT")
        
        # 18. Estrategia Accumulation/Distribution Line
        if "ad_trend" in indicators_data and indicators_data["ad_trend"] is not None:
            ad_trend = indicators_data["ad_trend"]
            if ad_trend == "accumulation":
                signals.append("LONG")
            elif ad_trend == "distribution":
                signals.append("SHORT")
        
        # 19. Estrategia SuperTrend
        if "supertrend_signal" in indicators_data and indicators_data["supertrend_signal"] is not None:
            supertrend_signal = indicators_data["supertrend_signal"]
            if supertrend_signal == "bullish":
                signals.append("LONG")
            elif supertrend_signal == "bearish":
                signals.append("SHORT")
        
        # 20. Estrategia Connors RSI
        if "connors_rsi" in indicators_data and indicators_data["connors_rsi"] is not None:
            crsi = indicators_data["connors_rsi"]
            if crsi < 10:
                signals.append("LONG")  # Sobreventa extrema
            elif crsi > 90:
                signals.append("SHORT")  # Sobrecompra extrema
        
        # 21. Estrategia QQE (Quantitative Qualitative Estimation)
        if "qqe" in indicators_data and "qqe_signal" in indicators_data:
            qqe = indicators_data["qqe"]
            qqe_signal = indicators_data["qqe_signal"]
            if qqe is not None and qqe_signal is not None:
                if qqe > qqe_signal:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # 22. Estrategia Volatility Stop (VSTOP)
        if "vstop_signal" in indicators_data and indicators_data["vstop_signal"] is not None:
            vstop_signal = indicators_data["vstop_signal"]
            if vstop_signal == "bullish":
                signals.append("LONG")
            elif vstop_signal == "bearish":
                signals.append("SHORT")
        
        # 23. Estrategia Negative Volume Index (NVI)
        if "nvi_trend" in indicators_data and indicators_data["nvi_trend"] is not None:
            nvi_trend = indicators_data["nvi_trend"]
            if nvi_trend == "rising":
                signals.append("LONG")  # Acumulación inteligente
        
        # 24. Estrategia Positive Volume Index (PVI)
        if "pvi_trend" in indicators_data and indicators_data["pvi_trend"] is not None:
            pvi_trend = indicators_data["pvi_trend"]
            if pvi_trend == "rising":
                signals.append("LONG")  # Participación pública alcista
            elif pvi_trend == "falling":
                signals.append("SHORT")  # Participación pública bajista
        
        # 25. Estrategia Guppy Multiple Moving Averages
        if "guppy_short_aligned" in indicators_data and "guppy_long_aligned" in indicators_data:
            guppy_short = indicators_data["guppy_short_aligned"]
            guppy_long = indicators_data["guppy_long_aligned"]
            if guppy_short == "bullish" and guppy_long == "bullish":
                signals.append("LONG")  # Alineación completa alcista
            elif guppy_short == "bearish" and guppy_long == "bearish":
                signals.append("SHORT")  # Alineación completa bajista
        
        # 26. Estrategias de Medias Móviles Avanzadas
        # McGinley Dynamic vs Precio
        if "mcginley_dynamic" in indicators_data and indicators_data["mcginley_dynamic"] is not None:
            mcginley = indicators_data["mcginley_dynamic"]
            # Usar precio actual para comparación (se pasa como contexto)
            # Señal basada en cruce con la media dinámica
            # Esta lógica se puede refinar con datos históricos
            
        # Hull Moving Average (HMA) vs Precio
        for period in [9, 21]:
            hma_key = f"hma_{period}"
            if hma_key in indicators_data and indicators_data[hma_key] is not None:
                # Señal basada en posición relativa del precio vs HMA
                # Se puede implementar con datos de precio actual
                pass
        
        # Zero Lag EMA cruces
        if all(k in indicators_data for k in ["zlema_12", "zlema_26"]):
            zlema_12 = indicators_data["zlema_12"]
            zlema_26 = indicators_data["zlema_26"]
            if zlema_12 is not None and zlema_26 is not None:
                if zlema_12 > zlema_26:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # FRAMA vs Precio (adaptativa a volatilidad)
        if "frama" in indicators_data and indicators_data["frama"] is not None:
            # Señal basada en la tendencia adaptativa
            # Se puede implementar con datos de precio actual
            pass
        
        # Triangular Moving Average (TMA) cruces
        if all(k in indicators_data for k in ["tma_20", "tma_50"]):
            tma_20 = indicators_data["tma_20"]
            tma_50 = indicators_data["tma_50"]
            if tma_20 is not None and tma_50 is not None:
                if tma_20 > tma_50:
                    signals.append("LONG")
                else:
                    signals.append("SHORT")
        
        # Determinar señal final basada en consenso
        if not signals:
            return "NEUTRAL"
        
        long_signals = signals.count("LONG")
        short_signals = signals.count("SHORT")
        total_signals = len(signals)
        
        # Requerir al menos 60% de consenso para una señal fuerte
        if long_signals / total_signals >= 0.6:
            return "LONG"
        elif short_signals / total_signals >= 0.6:
            return "SHORT"
        else:
            return "NEUTRAL"
    
    def get_confidence_level(self, indicators: Dict[str, Any]) -> str:
        """
        Determinar nivel de confianza basado en la cantidad y calidad de indicadores disponibles.
        
        Args:
            indicators: Diccionario con indicadores técnicos
            
        Returns:
            Nivel de confianza: "Alto", "Medio", "Bajo"
        """
        indicators_data = indicators.get("indicators", {})
        available_indicators = len([k for k, v in indicators_data.items() if v is not None])
        
        # Clasificar por cantidad de indicadores disponibles
        if available_indicators >= 15:
            return "Alto"
        elif available_indicators >= 8:
            return "Medio"
        else:
            return "Bajo"
    
    def get_comprehensive_analysis(self, indicators: Dict[str, Any], current_price: float) -> str:
        """
        Generar análisis técnico comprensivo basado en todas las estrategias.
        
        Args:
            indicators: Diccionario con indicadores técnicos
            current_price: Precio actual
            
        Returns:
            Análisis técnico detallado
        """
        indicators_data = indicators.get("indicators", {})
        analysis_parts = []
        
        # Análisis de tendencia
        trend_signals = []
        if "sma_20" in indicators_data and "sma_50" in indicators_data:
            sma_20 = indicators_data["sma_20"]
            sma_50 = indicators_data["sma_50"]
            if sma_20 and sma_50:
                if sma_20 > sma_50:
                    trend_signals.append("alcista (SMA 20>50)")
                else:
                    trend_signals.append("bajista (SMA 20<50)")
        
        if "ema_12" in indicators_data and "ema_26" in indicators_data:
            ema_12 = indicators_data["ema_12"]
            ema_26 = indicators_data["ema_26"]
            if ema_12 and ema_26:
                if ema_12 > ema_26:
                    trend_signals.append("alcista (EMA 12>26)")
                else:
                    trend_signals.append("bajista (EMA 12<26)")
        
        if trend_signals:
            analysis_parts.append(f"Tendencia: {', '.join(trend_signals)}")
        
        # Análisis de momentum
        momentum_signals = []
        if "rsi_14" in indicators_data and indicators_data["rsi_14"]:
            rsi = indicators_data["rsi_14"]
            if rsi > 70:
                momentum_signals.append(f"RSI sobrecomprado ({rsi:.1f})")
            elif rsi < 30:
                momentum_signals.append(f"RSI sobrevendido ({rsi:.1f})")
            else:
                momentum_signals.append(f"RSI neutral ({rsi:.1f})")
        
        if "macd_line" in indicators_data and "macd_signal" in indicators_data:
            macd_line = indicators_data["macd_line"]
            macd_signal = indicators_data["macd_signal"]
            if macd_line and macd_signal:
                if macd_line > macd_signal:
                    momentum_signals.append("MACD alcista")
                else:
                    momentum_signals.append("MACD bajista")
        
        if momentum_signals:
            analysis_parts.append(f"Momentum: {', '.join(momentum_signals)}")
        
        # Análisis de volatilidad
        volatility_signals = []
        if "bb_20_2.0_upper" in indicators_data and "bb_20_2.0_lower" in indicators_data:
            bb_upper = indicators_data["bb_20_2.0_upper"]
            bb_lower = indicators_data["bb_20_2.0_lower"]
            if bb_upper and bb_lower:
                bb_width = ((bb_upper - bb_lower) / current_price) * 100
                if current_price > bb_upper:
                    volatility_signals.append("precio sobre Bollinger superior")
                elif current_price < bb_lower:
                    volatility_signals.append("precio bajo Bollinger inferior")
                else:
                    volatility_signals.append(f"precio dentro de Bollinger (ancho: {bb_width:.1f}%)")
        
        if "atr_14" in indicators_data and indicators_data["atr_14"]:
            atr = indicators_data["atr_14"]
            atr_pct = (atr / current_price) * 100
            volatility_signals.append(f"ATR {atr_pct:.1f}% del precio")
        
        if volatility_signals:
            analysis_parts.append(f"Volatilidad: {', '.join(volatility_signals)}")
        
        # Análisis de volumen
        volume_signals = []
        if "obv_trend" in indicators_data and indicators_data["obv_trend"]:
            obv_trend = indicators_data["obv_trend"]
            volume_signals.append(f"OBV {obv_trend}")
        
        if "cmf_20" in indicators_data and indicators_data["cmf_20"]:
            cmf = indicators_data["cmf_20"]
            if cmf > 0.05:
                volume_signals.append("flujo de dinero positivo")
            elif cmf < -0.05:
                volume_signals.append("flujo de dinero negativo")
            else:
                volume_signals.append("flujo de dinero neutral")
        
        if volume_signals:
            analysis_parts.append(f"Volumen: {', '.join(volume_signals)}")
        
        return ". ".join(analysis_parts) if analysis_parts else "Análisis técnico basado en múltiples indicadores" 