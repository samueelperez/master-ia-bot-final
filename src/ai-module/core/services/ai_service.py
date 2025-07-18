"""
Servicio de IA para interacciones con OpenAI.
Encapsula toda la lógica de generación de texto y manejo de prompts.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..config.security_config import SecurityConfig
from .technical_indicators_service import TechnicalIndicatorsService

logger = logging.getLogger(__name__)

# Importaciones condicionales
try:
    from openai import OpenAI, AsyncOpenAI
    from openai.types.chat import ChatCompletion
except ImportError:
    logger.error("OpenAI library no está instalada. Ejecutar: pip install openai")
    OpenAI = None
    AsyncOpenAI = None


class ModelType(Enum):
    """Tipos de modelos disponibles."""
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"


@dataclass
class AIPromptTemplate:
    """Template para prompts estructurados."""
    system_prompt: str
    context_template: str
    instruction_template: str
    
    def format(self, context: Dict[str, Any], instruction: str) -> List[Dict[str, str]]:
        """Formatear el template con datos específicos."""
        formatted_context = self.context_template.format(**context)
        formatted_instruction = self.instruction_template.format(instruction=instruction)
        
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{formatted_context}\n\n{formatted_instruction}"}
        ]


class AIService:
    """
    Servicio de IA con manejo seguro de OpenAI API.
    Implementa retry logic y rate limiting.
    """
    
    # Templates predefinidos para diferentes tipos de análisis
    ANALYSIS_TEMPLATE = AIPromptTemplate(
        system_prompt="""
        Eres un analista experto en criptomonedas con amplia experiencia en análisis técnico.
        
        DEBES SEGUIR EXACTAMENTE ESTE FORMATO DE RESPUESTA:

        📊 ANÁLISIS DE {symbol} ({timeframes})

        📈 DIRECCIÓN: [ALCISTA/BAJISTA/LATERAL]

        💡 ANÁLISIS TÉCNICO:
        [Análisis detallado de indicadores técnicos, RSI, MACD, volumen, patrones de precio, etc.]

        📰 FACTORES FUNDAMENTALES:
        [Análisis de sentimiento, noticias relevantes, eventos económicos que puedan afectar el precio]

        🔑 NIVELES IMPORTANTES:
        - Soporte: $[precio] ([justificación técnica])
        - Resistencia: $[precio] ([justificación técnica])

        🔮 ESCENARIO PROBABLE:
        [Proyección técnica a corto/medio plazo basada en el análisis]

        ⏱️ HORIZONTE TEMPORAL: [Próximos días/semanas]

        ⚠️ No es asesoramiento financiero.

        IMPORTANTE: Usa datos técnicos reales, niveles de precio coherentes con el valor actual, y mantén un análisis profesional y objetivo.
        """,
        context_template="""
        DATOS DE ANÁLISIS:
        - Símbolo: {symbol}
        - Precio actual: ${price:,.2f}
        - Timeframes analizados: {timeframes}
        - Timestamp: {timestamp}
        
        Analiza la criptomoneda con base técnica sólida.
        """,
        instruction_template="{instruction}"
    )
    
    SIGNAL_TEMPLATE = AIPromptTemplate(
        system_prompt="""
Eres un generador profesional de señales de trading para criptomonedas.

DEBES generar una señal usando EXACTAMENTE este formato, completando TODOS los campos:

🚀 **{symbol}/USDT - SEÑAL {timeframe}**
💰 **${price:,.2f}** | 📈 **{signal_direction}** | ⚡ **10x**

🎯 **NIVELES:**
• **Entrada:** ${entry_price:,.2f}
• **Stop Loss:** ${stop_loss:,.2f}
• **TP1:** ${tp1:,.2f} | **TP2:** ${tp2:,.2f}

💡 **ANÁLISIS:** {technical_analysis}

🔥 **CONFIANZA:** {confidence_level}

IMPORTANTE:
- Usa los valores proporcionados para precios y análisis técnico
- El análisis está basado en indicadores técnicos reales
- Los niveles están calculados basándose en datos técnicos actuales
- Mantén el formato exacto sin modificar los valores calculados
        """,
        context_template="""
DATOS TÉCNICOS:
- {symbol}/USDT | {timeframe} | ${price:,.2f}
        - Estrategia: {strategy}
- Señal calculada: {signal_direction}

{technical_indicators}

NIVELES CALCULADOS:
- Entrada: ${entry_price:,.2f}
- Stop Loss: ${stop_loss:,.2f}
- TP1: ${tp1:,.2f}
- TP2: ${tp2:,.2f}

Usa estos datos para generar la señal formateada.
        """,
        instruction_template="Genera señal con datos técnicos reales: {instruction}"
    )
    
    FUNDAMENTAL_TEMPLATE = AIPromptTemplate(
        system_prompt="""
Eres un analista fundamental experto en criptomonedas y macroeconomía.

DEBES SEGUIR EXACTAMENTE ESTE FORMATO DE RESPUESTA:

📊 **ANÁLISIS FUNDAMENTAL DE {symbol}**
💰 **Precio actual:** ${price:,.2f}

🌍 **CONTEXTO MACROECONÓMICO:**
{macro_context}

📰 **ANÁLISIS DE NOTICIAS:**
{news_analysis}

📈 **IMPACTO EN {symbol}:**
{impact_analysis}

🔮 **PERSPECTIVA FUNDAMENTAL:**
{fundamental_outlook}

⚠️ **RIESGOS Y OPORTUNIDADES:**
{risks_opportunities}

📅 **EVENTOS CLAVE A SEGUIR:**
{key_events}

⚠️ Este análisis es educativo, no asesoramiento financiero.
        """,
        context_template="""
DATOS FUNDAMENTALES:
- {symbol}/USDT | ${price:,.2f}

EVENTOS ECONÓMICOS:
{economic_events}

NOTICIAS RELEVANTES:
{news_data}

DATOS SOCIALES:
{social_data}

Usa estos datos para generar el análisis fundamental.
        """,
        instruction_template="Genera análisis fundamental completo: {instruction}"
    )

    MACRO_TEMPLATE = AIPromptTemplate(
        system_prompt="""
Eres un analista macroeconómico especializado en el impacto de eventos económicos en criptomonedas.

DEBES SEGUIR EXACTAMENTE ESTE FORMATO DE RESPUESTA:

🌍 **ANÁLISIS MACROECONÓMICO**
📅 **Período:** {days} días

🔥 **EVENTOS DE ALTO IMPACTO:**
{high_impact_events}

📊 **EVENTOS DE IMPACTO MEDIO:**
{medium_impact_events}

₿ **EVENTOS ESPECÍFICOS DE CRYPTO:**
{crypto_events}

💡 **ANÁLISIS INTEGRADO:**
{integrated_analysis}

📈 **IMPACTO ESPERADO EN CRIPTOMONEDAS:**
{crypto_impact}

⏰ **CRONOGRAMA DE EVENTOS CLAVE:**
{timeline}

🎯 **RECOMENDACIONES ESTRATÉGICAS:**
{strategic_recommendations}

⚠️ Información educativa, no asesoramiento financiero.
        """,
        context_template="""
CONSULTA: {query}
PERÍODO: {days} días

EVENTOS ECONÓMICOS:
{events_data}

NOTICIAS RELEVANTES:
{news_data}

Analiza el impacto macroeconómico en criptomonedas.
        """,
        instruction_template="Analiza el impacto macroeconómico: {instruction}"
    )
    
    def __init__(self):
        self.default_model = ModelType.GPT_3_5_TURBO
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Inicializar servicio de indicadores técnicos
        self.technical_service = TechnicalIndicatorsService()
        
        if not OpenAI:
            logger.error("OpenAI library no está disponible")
            raise ImportError("OpenAI library requerida no está disponible")
        
        if not SecurityConfig.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY no configurada")
            raise ValueError("OPENAI_API_KEY es requerida")
        
        # Cliente síncrono
        self.client = OpenAI(
            api_key=SecurityConfig.OPENAI_API_KEY,
            timeout=SecurityConfig.OPENAI_TIMEOUT
        )
        
        # Cliente asíncrono
        self.async_client = AsyncOpenAI(
            api_key=SecurityConfig.OPENAI_API_KEY,
            timeout=SecurityConfig.OPENAI_TIMEOUT
        )
        
        logger.info("AI Service inicializado correctamente")
    
    def _validate_completion_params(self, **kwargs) -> Dict[str, Any]:
        """Validar y sanitizar parámetros de completion."""
        safe_params = {}
        
        # Modelo
        model = kwargs.get('model', self.default_model.value)
        if isinstance(model, ModelType):
            safe_params['model'] = model.value
        else:
            # Validar que el modelo esté permitido
            allowed_models = [m.value for m in ModelType]
            if model not in allowed_models:
                logger.warning(f"Modelo no permitido: {model}. Usando {self.default_model.value}")
                safe_params['model'] = self.default_model.value
            else:
                safe_params['model'] = model
        
        # Temperatura (0.0 - 1.0)
        temperature = kwargs.get('temperature', 0.6)
        safe_params['temperature'] = max(0.0, min(1.0, float(temperature)))
        
        # Max tokens (limitar para evitar costos excesivos)
        max_tokens = kwargs.get('max_tokens', 500)
        safe_params['max_tokens'] = max(50, min(2000, int(max_tokens)))
        
        # Top P
        top_p = kwargs.get('top_p', 1.0)
        safe_params['top_p'] = max(0.1, min(1.0, float(top_p)))
        
        # Presence penalty
        presence_penalty = kwargs.get('presence_penalty', 0.0)
        safe_params['presence_penalty'] = max(-2.0, min(2.0, float(presence_penalty)))
        
        # Frequency penalty
        frequency_penalty = kwargs.get('frequency_penalty', 0.0)
        safe_params['frequency_penalty'] = max(-2.0, min(2.0, float(frequency_penalty)))
        
        return safe_params
    
    async def _generate_completion_with_retry(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> str:
        """Generar completion con retry logic."""
        if not self.async_client:
            raise RuntimeError("Cliente OpenAI no disponible")
        
        safe_params = self._validate_completion_params(**kwargs)
        safe_params['messages'] = messages
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Intento {attempt + 1} de completion con modelo {safe_params['model']}")
                
                response: ChatCompletion = await self.async_client.chat.completions.create(**safe_params)
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content and content.strip():
                        logger.debug(f"Completion exitoso en intento {attempt + 1}")
                        return content.strip()
                
                raise ValueError("Respuesta vacía de OpenAI")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Error en intento {attempt + 1}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # Si todos los intentos fallaron
        logger.error(f"Todos los intentos de completion fallaron. Último error: {last_error}")
        raise RuntimeError(f"No se pudo generar completion después de {self.max_retries} intentos: {last_error}")
    
    async def generate_crypto_analysis(
        self, 
        symbol: str, 
        price: float,
        timeframes: List[str],
        user_prompt: str = "",
        **kwargs
    ) -> str:
        """
        Generar análisis de criptomoneda.
        
        Args:
            symbol: Símbolo de la criptomoneda
            price: Precio actual
            timeframes: Lista de timeframes
            user_prompt: Prompt adicional del usuario
            **kwargs: Parámetros adicionales para el modelo
        
        Returns:
            Análisis generado
        """
        from datetime import datetime
        
        context = {
            "symbol": symbol,
            "price": price,
            "timeframes": ", ".join(timeframes),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        instruction = user_prompt if user_prompt else "Proporciona un análisis técnico completo"
        messages = self.ANALYSIS_TEMPLATE.format(context, instruction)
        
        return await self._generate_completion_with_retry(messages, **kwargs)
    
    async def generate_trading_signal(
        self,
        symbol: str,
        price: float,
        timeframe: str,
        strategy: str = "technical_analysis",
        context: str = "",
        **kwargs
    ) -> str:
        """
        Generar señal de trading con indicadores técnicos reales.
        
        Args:
            symbol: Símbolo de la criptomoneda
            price: Precio actual
            timeframe: Timeframe para la señal
            strategy: Estrategia de trading
            context: Contexto adicional
            **kwargs: Parámetros adicionales para el modelo
        
        Returns:
            Señal de trading generada con datos técnicos reales
        """
        # Obtener indicadores técnicos reales del backend usando perfil avanzado
        indicators = await self.technical_service.get_technical_indicators(
            symbol=symbol,
            timeframe=timeframe,
            indicators=None  # Obtener todos los indicadores disponibles
        )
        
        # Determinar dirección de la señal basada en múltiples estrategias
        signal_direction = self.technical_service.get_trading_signal_from_indicators(indicators)
        
        # Extraer niveles de trading usando múltiples fuentes
        levels = self.technical_service.extract_trading_levels(indicators, price)
        
        # Obtener nivel de confianza basado en cantidad de indicadores
        confidence = self.technical_service.get_confidence_level(indicators)
        
        # Calcular niveles de entrada, stop loss y take profit
        if signal_direction == "LONG":
            entry_price = price * 1.001  # Entrada ligeramente por encima del precio actual
            
            # Usar múltiples niveles de soporte para stop loss
            support_candidates = [
                levels.get("bb_support"),
                levels.get("keltner_support"), 
                levels.get("ema_20_support"),
                levels.get("sma_20_support"),
                levels.get("vwap_support"),
                levels.get("sar_support")
            ]
            valid_supports = [s for s in support_candidates if s and s < price]
            stop_loss = max(valid_supports) if valid_supports else price * 0.97
            
            # Asegurar que el stop loss no esté más del 5% del precio actual
            max_stop_distance = price * 0.95
            stop_loss = max(stop_loss, max_stop_distance)
            
            # Usar múltiples niveles de resistencia para take profit
            resistance_candidates = [
                levels.get("bb_resistance"),
                levels.get("keltner_resistance"),
                levels.get("donchian_resistance"),
                levels.get("ema_50_resistance"),
                levels.get("sma_50_resistance")
            ]
            valid_resistances = [r for r in resistance_candidates if r and r > price]
            tp1 = min(valid_resistances) if valid_resistances else price * 1.025
            tp2 = price * 1.05
            
            # Asegurar que TP1 esté al menos 2% arriba
            min_tp1 = price * 1.02
            tp1 = max(tp1, min_tp1)
            
        elif signal_direction == "SHORT":
            entry_price = price * 0.999  # Entrada ligeramente por debajo del precio actual
            
            # Usar múltiples niveles de resistencia para stop loss
            resistance_candidates = [
                levels.get("bb_resistance"),
                levels.get("keltner_resistance"),
                levels.get("ema_20_resistance"),
                levels.get("sma_20_resistance"),
                levels.get("vwap_resistance"),
                levels.get("sar_resistance")
            ]
            valid_resistances = [r for r in resistance_candidates if r and r > price]
            stop_loss = min(valid_resistances) if valid_resistances else price * 1.03
            
            # Asegurar que el stop loss no esté más del 5% del precio actual
            max_stop_distance = price * 1.05
            stop_loss = min(stop_loss, max_stop_distance)
            
            # Usar múltiples niveles de soporte para take profit
            support_candidates = [
                levels.get("bb_support"),
                levels.get("keltner_support"),
                levels.get("donchian_support"),
                levels.get("ema_50_support"),
                levels.get("sma_50_support")
            ]
            valid_supports = [s for s in support_candidates if s and s < price]
            tp1 = max(valid_supports) if valid_supports else price * 0.975
            tp2 = price * 0.95
            
            # Asegurar que TP1 esté al menos 2% abajo
            max_tp1 = price * 0.98
            tp1 = min(tp1, max_tp1)
            
        else:  # NEUTRAL
            # Señal neutral - usar niveles conservadores
            entry_price = price
            stop_loss = price * 0.98
            tp1 = price * 1.02
            tp2 = price * 1.04
            signal_direction = "LONG"  # Por defecto LONG en neutral
            confidence = "Bajo"
        
        # Generar análisis técnico comprensivo
        technical_analysis = self.technical_service.get_comprehensive_analysis(indicators, price)
        
        # Preparar contexto para el template
        signal_context = {
            "symbol": symbol,
            "price": price,
            "timeframe": timeframe,
            "strategy": strategy,
            "signal_direction": signal_direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "technical_analysis": technical_analysis,
            "confidence_level": confidence,
            "technical_indicators": self.technical_service.format_indicators_for_analysis(indicators)
        }
        
        instruction = "Generar señal de trading con análisis técnico comprensivo basado en múltiples estrategias"
        messages = self.SIGNAL_TEMPLATE.format(signal_context, instruction)
        
        return await self._generate_completion_with_retry(messages, **kwargs)
    
    async def generate_custom_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generar completion personalizado.
        
        Args:
            messages: Lista de mensajes para el chat
            **kwargs: Parámetros adicionales para el modelo
        
        Returns:
            Respuesta generada
        """
        # Validar estructura de mensajes
        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                raise ValueError("Formato de mensaje inválido")
        
        return await self._generate_completion_with_retry(messages, **kwargs)
    
    async def generate_fundamental_analysis(
        self,
        symbol: str,
        price: float,
        external_data: Dict[str, Any],
        timeframes: List[str] = None,
        **kwargs
    ) -> str:
        """
        Generar análisis fundamental de una criptomoneda.
        
        Args:
            symbol: Símbolo de la criptomoneda
            price: Precio actual
            external_data: Datos externos (noticias, eventos, etc.)
            timeframes: Lista de timeframes
            **kwargs: Parámetros adicionales para el modelo
        
        Returns:
            Análisis fundamental generado
        """
        # Formatear eventos económicos
        economic_events = external_data.get("economic_events", [])
        events_text = ""
        if economic_events:
            for event in economic_events[:5]:  # Limitar a 5 eventos
                events_text += f"• {event.get('title', 'N/A')} ({event.get('date', 'N/A')} {event.get('time', '')})\n"
                events_text += f"  País: {event.get('country', 'N/A')} | Impacto: {event.get('impact', 'N/A')}\n"
                if event.get('forecast'):
                    events_text += f"  Pronóstico: {event.get('forecast')} | Anterior: {event.get('previous', 'N/A')}\n"
                events_text += "\n"
        else:
            events_text = "No hay eventos económicos importantes programados."

        # Formatear noticias
        news_data = external_data.get("news", [])
        news_text = ""
        if news_data:
            for news in news_data[:3]:  # Limitar a 3 noticias
                news_text += f"• {news.get('title', 'N/A')}\n"
                news_text += f"  Fuente: {news.get('source', 'N/A')} | {news.get('published_at', 'N/A')}\n"
                if news.get('summary'):
                    news_text += f"  Resumen: {news.get('summary')}\n"
                news_text += "\n"
        else:
            news_text = "No hay noticias relevantes recientes."

        # Formatear datos sociales
        social_data = external_data.get("social_data", {})
        social_text = f"Sentimiento: {social_data.get('sentiment', 'neutral').title()}"
        if social_data.get('trending_score'):
            social_text += f" | Tendencia: {social_data.get('trending_score')}/100"

        context = {
            "symbol": symbol,
            "price": price,
            "economic_events": events_text,
            "news_data": news_text,
            "social_data": social_text
        }
        
        instruction = "Proporciona un análisis fundamental completo considerando eventos macroeconómicos, noticias y sentimiento social"
        messages = self.FUNDAMENTAL_TEMPLATE.format(context, instruction)
        
        return await self._generate_completion_with_retry(messages, **kwargs)

    async def generate_macro_analysis(
        self,
        query: str,
        events: Dict[str, Any],
        news: List[Dict[str, Any]],
        days: int = 7,
        **kwargs
    ) -> str:
        """
        Generar análisis macroeconómico personalizado.
        
        Args:
            query: Consulta específica del usuario
            events: Eventos económicos
            news: Noticias relevantes
            days: Período de análisis
            **kwargs: Parámetros adicionales para el modelo
        
        Returns:
            Análisis macroeconómico generado
        """
        # Formatear eventos de alto impacto
        high_impact = events.get("high_impact_events", [])
        high_impact_text = ""
        if high_impact:
            for event in high_impact:
                high_impact_text += f"• {event.get('title', 'N/A')} - {event.get('date', 'N/A')} {event.get('time', '')}\n"
                high_impact_text += f"  {event.get('country', 'N/A')} | Pronóstico: {event.get('forecast', 'N/A')}\n\n"
        else:
            high_impact_text = "No hay eventos de alto impacto programados."

        # Formatear eventos de impacto medio
        medium_impact = events.get("medium_impact_events", [])
        medium_impact_text = ""
        if medium_impact:
            for event in medium_impact:
                medium_impact_text += f"• {event.get('title', 'N/A')} - {event.get('date', 'N/A')}\n"
        else:
            medium_impact_text = "No hay eventos de impacto medio relevantes."

        # Formatear eventos de crypto
        crypto_events = events.get("crypto_events", [])
        crypto_events_text = ""
        if crypto_events:
            for event in crypto_events:
                crypto_events_text += f"• {event.get('title', 'N/A')} - {event.get('date', 'N/A')}\n"
                crypto_events_text += f"  {event.get('description', 'N/A')}\n\n"
        else:
            crypto_events_text = "No hay eventos específicos de criptomonedas programados."

        # Formatear noticias
        news_text = ""
        if news:
            for article in news[:5]:  # Limitar a 5 noticias
                news_text += f"• {article.get('title', 'N/A')}\n"
                news_text += f"  {article.get('source', 'N/A')} | {article.get('published_at', 'N/A')}\n\n"
        else:
            news_text = "No hay noticias relevantes recientes."

        context = {
            "query": query,
            "days": days,
            "events_data": f"ALTO IMPACTO:\n{high_impact_text}\nIMPACTO MEDIO:\n{medium_impact_text}\nCRIPTO EVENTOS:\n{crypto_events_text}",
            "news_data": news_text
        }
        
        instruction = f"Analiza el impacto macroeconómico según la consulta: {query}"
        messages = self.MACRO_TEMPLATE.format(context, instruction)
        
        return await self._generate_completion_with_retry(messages, **kwargs)
    
    async def close(self):
        """Cerrar conexiones y limpiar recursos."""
        if self.technical_service:
            await self.technical_service.close()
    
    def get_service_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio de IA."""
        if not self.client:
            return {
                "status": "unavailable",
                "reason": "OpenAI client no inicializado",
                "model": self.default_model.value,
                "max_retries": self.max_retries,
                "timeout": SecurityConfig.OPENAI_TIMEOUT
            }
        
        try:
            # Test simple para verificar conectividad
            test_messages = [{"role": "user", "content": "test"}]
            # No usar async aquí para simplificar
            response = self.client.chat.completions.create(
                model=self.default_model.value,
                messages=test_messages,
                max_tokens=5
            )
            is_healthy = bool(response.choices)
        except Exception as e:
            logger.warning(f"Health check falló: {e}")
            is_healthy = False
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "model": self.default_model.value,
            "max_retries": self.max_retries,
            "timeout": SecurityConfig.OPENAI_TIMEOUT,
            "backend_integration": "enabled"
        } 