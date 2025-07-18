"""
Servicio de integración de datos externos para análisis de criptomonedas.
Este servicio combina datos de noticias, eventos económicos y redes sociales
para proporcionar un contexto completo para el análisis de criptomonedas.
"""
import logging
from typing import Dict, Any, Optional, List
import asyncio

# Importar servicios individuales
from .news_service import get_news_for_symbol, get_all_relevant_news
from .social_media_service import get_social_data_for_symbol, get_all_social_data
from .economic_calendar_service import get_economic_events, get_events_for_symbol

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_external_data_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Obtiene todos los datos externos relevantes para una criptomoneda específica.
    
    Args:
        symbol: Símbolo de la criptomoneda (ej: BTC, ETH)
        
    Returns:
        Diccionario con todos los datos externos relevantes
    """
    try:
        # Ejecutar todas las consultas en paralelo para mejorar el rendimiento
        news_task = asyncio.create_task(get_news_for_symbol(symbol))
        social_task = asyncio.create_task(get_social_data_for_symbol(symbol))
        events_task = asyncio.create_task(get_events_for_symbol(symbol))
        
        # Esperar a que todas las tareas se completen
        news_data = await news_task
        social_data = await social_task
        events_data = await events_task
        
        # Combinar todos los datos en un solo diccionario
        result = {
            "symbol": symbol,
            "news": news_data,
            "social": social_data,
            "events": events_data
        }
        
        logger.info(f"Datos externos obtenidos correctamente para {symbol}")
        return result
    except Exception as e:
        logger.error(f"Error al obtener datos externos para {symbol}: {e}")
        return {
            "symbol": symbol,
            "error": f"Error al obtener datos externos: {str(e)}",
            "news": {},
            "social": {},
            "events": {}
        }

async def get_all_external_data() -> Dict[str, Any]:
    """
    Obtiene todos los datos externos relevantes para el mercado de criptomonedas en general.
    
    Returns:
        Diccionario con todos los datos externos relevantes
    """
    try:
        # Ejecutar todas las consultas en paralelo para mejorar el rendimiento
        news_task = asyncio.create_task(get_all_relevant_news())
        social_task = asyncio.create_task(get_all_social_data())
        events_task = asyncio.create_task(get_economic_events())
        
        # Esperar a que todas las tareas se completen
        news_data = await news_task
        social_data = await social_task
        events_data = await events_task
        
        # Combinar todos los datos en un solo diccionario
        result = {
            "news": news_data,
            "social": social_data,
            "events": events_data
        }
        
        logger.info("Datos externos generales obtenidos correctamente")
        return result
    except Exception as e:
        logger.error(f"Error al obtener datos externos generales: {e}")
        return {
            "error": f"Error al obtener datos externos: {str(e)}",
            "news": {},
            "social": {},
            "events": {}
        }

def format_external_data_for_prompt(data: Dict[str, Any]) -> str:
    """
    Formatea los datos externos para incluirlos en un prompt de IA.
    
    Args:
        data: Diccionario con datos externos
        
    Returns:
        Texto formateado para incluir en un prompt
    """
    try:
        result = "DATOS EXTERNOS RELEVANTES:\n\n"
        
        # Formatear noticias
        if "news" in data and data["news"]:
            result += "NOTICIAS RELEVANTES:\n"
            
            # Noticias de criptomonedas
            if "crypto_news" in data["news"] and data["news"]["crypto_news"]:
                result += "- Noticias de criptomonedas:\n"
                for i, news in enumerate(data["news"]["crypto_news"][:3], 1):
                    result += f"  {i}. {news.get('title', 'Sin título')} ({news.get('source', 'Fuente desconocida')})\n"
            
            # Eventos económicos
            if "economic_events" in data["news"] and data["news"]["economic_events"]:
                result += "- Eventos económicos:\n"
                for i, event in enumerate(data["news"]["economic_events"][:2], 1):
                    result += f"  {i}. {event.get('title', 'Sin título')} ({event.get('date', 'Fecha desconocida')})\n"
            
            # Eventos políticos
            if "political_events" in data["news"] and data["news"]["political_events"]:
                result += "- Eventos políticos:\n"
                for i, event in enumerate(data["news"]["political_events"][:2], 1):
                    result += f"  {i}. {event.get('title', 'Sin título')} ({event.get('date', 'Fecha desconocida')})\n"
            
            result += "\n"
        
        # Formatear datos de redes sociales
        if "social" in data and data["social"]:
            result += "TENDENCIAS EN REDES SOCIALES:\n"
            
            # Tendencias de Twitter
            if "twitter_trends" in data["social"] and data["social"]["twitter_trends"]:
                result += "- Tendencias en Twitter:\n"
                for i, trend in enumerate(data["social"]["twitter_trends"][:3], 1):
                    result += f"  {i}. {trend.get('name', 'Sin nombre')} ({trend.get('tweet_volume', 0)} tweets)\n"
            
            # Sentimiento
            if "sentiment" in data["social"] and data["social"]["sentiment"]:
                sentiment = data["social"]["sentiment"]
                result += f"- Sentimiento general: {sentiment.get('overall', 'neutral').upper()}\n"
                result += f"  Positivo: {sentiment.get('positive', 0)*100:.1f}%, "
                result += f"Negativo: {sentiment.get('negative', 0)*100:.1f}%, "
                result += f"Neutral: {sentiment.get('neutral', 0)*100:.1f}%\n"
            
            # Monedas tendencia
            if "trending_coins" in data["social"] and data["social"]["trending_coins"]:
                result += "- Criptomonedas tendencia:\n"
                for i, coin in enumerate(data["social"]["trending_coins"][:3], 1):
                    result += f"  {i}. {coin.get('name', 'Sin nombre')} ({coin.get('symbol', 'N/A')})\n"
            
            result += "\n"
        
        # Formatear eventos económicos
        if "events" in data and data["events"]:
            result += "EVENTOS ECONÓMICOS IMPORTANTES:\n"
            
            # Eventos específicos de la criptomoneda
            if "symbol_events" in data["events"] and data["events"]["symbol_events"]:
                symbol = data.get("symbol", "esta criptomoneda")
                result += f"- Eventos específicos para {symbol}:\n"
                for i, event in enumerate(data["events"]["symbol_events"][:2], 1):
                    result += f"  {i}. {event.get('title', 'Sin título')} ({event.get('date', 'Fecha desconocida')})\n"
                    if "description" in event:
                        result += f"     {event['description']}\n"
            
            # Eventos de alto impacto
            if "high_impact_events" in data["events"] and data["events"]["high_impact_events"]:
                result += "- Eventos económicos de alto impacto:\n"
                for i, event in enumerate(data["events"]["high_impact_events"][:2], 1):
                    date_time = f"{event.get('date', '')} {event.get('time', '')}"
                    result += f"  {i}. {event.get('title', 'Sin título')} ({date_time.strip()})\n"
                    if "country" in event:
                        result += f"     País: {event['country']}\n"
            
            result += "\n"
        
        return result
    except Exception as e:
        logger.error(f"Error al formatear datos externos para prompt: {e}")
        return "No se pudieron formatear los datos externos debido a un error."

async def get_formatted_data_for_prompt(symbol: Optional[str] = None) -> str:
    """
    Obtiene y formatea todos los datos externos relevantes para incluirlos en un prompt de IA.
    
    Args:
        symbol: Símbolo de la criptomoneda (opcional)
        
    Returns:
        Texto formateado para incluir en un prompt
    """
    try:
        if symbol:
            data = await get_external_data_for_symbol(symbol)
        else:
            data = await get_all_external_data()
        
        return format_external_data_for_prompt(data)
    except Exception as e:
        logger.error(f"Error al obtener datos formateados para prompt: {e}")
        return "No se pudieron obtener datos externos debido a un error."
