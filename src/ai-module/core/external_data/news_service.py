"""
Servicio para obtener noticias relevantes sobre criptomonedas y eventos que puedan afectar al mercado.
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes
CACHE_DURATION = 3600  # 1 hora en segundos
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_cache.json")

# APIs de noticias
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

class NewsService:
    """Servicio para obtener noticias relevantes sobre criptomonedas."""
    
    def __init__(self):
        """Inicializa el servicio de noticias."""
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Carga el caché de noticias desde el archivo."""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                    # Verificar si el caché ha expirado
                    if time.time() - cache.get("timestamp", 0) < CACHE_DURATION:
                        logger.info("Caché de noticias cargado correctamente")
                        return cache
                    else:
                        logger.info("Caché de noticias expirado")
            return {"timestamp": 0, "news": {}}
        except Exception as e:
            logger.error(f"Error al cargar el caché de noticias: {e}")
            return {"timestamp": 0, "news": {}}
    
    def _save_cache(self) -> None:
        """Guarda el caché de noticias en el archivo."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
            logger.info("Caché de noticias guardado correctamente")
        except Exception as e:
            logger.error(f"Error al guardar el caché de noticias: {e}")
    
    async def get_crypto_news(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene noticias sobre criptomonedas.
        
        Args:
            symbol: Símbolo de la criptomoneda (opcional)
            
        Returns:
            Lista de noticias
        """
        cache_key = f"crypto_{symbol or 'general'}"
        
        # Verificar si hay noticias en caché y no han expirado
        if (cache_key in self.cache["news"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info(f"Usando noticias en caché para {cache_key}")
            return self.cache["news"][cache_key]
        
        news = []
        
        # Intentar obtener noticias de CryptoPanic
        if CRYPTOPANIC_API_KEY:
            try:
                url = "https://cryptopanic.com/api/v1/posts/"
                params = {
                    "auth_token": CRYPTOPANIC_API_KEY,
                    "kind": "news",
                    "filter": "important",
                    "public": "true"
                }
                
                if symbol:
                    params["currencies"] = symbol
                
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("results", []):
                        news.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "source": item.get("source", {}).get("title", "CryptoPanic"),
                            "published_at": item.get("published_at", ""),
                            "currencies": [c.get("code", "") for c in item.get("currencies", [])]
                        })
                
                logger.info(f"Obtenidas {len(news)} noticias de CryptoPanic")
            except Exception as e:
                logger.error(f"Error al obtener noticias de CryptoPanic: {e}")
        
        # Si no hay noticias de CryptoPanic o no hay API key, intentar con NewsAPI
        if not news and NEWSAPI_KEY:
            try:
                url = "https://newsapi.org/v2/everything"
                
                # Construir la consulta según el símbolo
                if symbol:
                    query = f"{symbol} OR {self._get_full_name(symbol)} cryptocurrency"
                else:
                    query = "cryptocurrency OR bitcoin OR ethereum OR crypto"
                
                params = {
                    "apiKey": NEWSAPI_KEY,
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10
                }
                
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("articles", []):
                        news.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "source": item.get("source", {}).get("name", "NewsAPI"),
                            "published_at": item.get("publishedAt", ""),
                            "currencies": [symbol] if symbol else []
                        })
                
                logger.info(f"Obtenidas {len(news)} noticias de NewsAPI")
            except Exception as e:
                logger.error(f"Error al obtener noticias de NewsAPI: {e}")
        
        # Si no se pudieron obtener noticias de ninguna fuente, devolver lista vacía
        if not news:
            logger.warning("No se pudieron obtener noticias de fuentes externas")
            news = []
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["news"][cache_key] = news
        self._save_cache()
        
        return news
    
    async def get_economic_events(self) -> List[Dict[str, Any]]:
        """
        Obtiene eventos económicos importantes.
        
        Returns:
            Lista de eventos económicos
        """
        cache_key = "economic_events"
        
        # Verificar si hay eventos en caché y no han expirado
        if (cache_key in self.cache["news"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info("Usando eventos económicos en caché")
            return self.cache["news"][cache_key]
        
        events = []
        
        # Intentar obtener eventos económicos (simulado por ahora)
        # En una implementación real, se conectaría a APIs como Investing.com o ForexFactory
        try:
            # Simulación de eventos económicos
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            
            events = [
                {
                    "title": "Reunión de la Reserva Federal",
                    "date": today.strftime("%Y-%m-%d"),
                    "time": "14:00",
                    "impact": "high",
                    "description": "Decisión sobre tasas de interés y política monetaria"
                },
                {
                    "title": "Datos de inflación de EE.UU.",
                    "date": tomorrow.strftime("%Y-%m-%d"),
                    "time": "08:30",
                    "impact": "high",
                    "description": "Publicación del Índice de Precios al Consumidor (IPC)"
                },
                {
                    "title": "Discurso del presidente de la SEC sobre regulación de criptomonedas",
                    "date": today.strftime("%Y-%m-%d"),
                    "time": "10:00",
                    "impact": "medium",
                    "description": "Posibles anuncios sobre nuevas regulaciones para el mercado cripto"
                }
            ]
            
            logger.info(f"Obtenidos {len(events)} eventos económicos")
        except Exception as e:
            logger.error(f"Error al obtener eventos económicos: {e}")
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["news"][cache_key] = events
        self._save_cache()
        
        return events
    
    async def get_political_events(self) -> List[Dict[str, Any]]:
        """
        Obtiene eventos políticos importantes que pueden afectar al mercado.
        
        Returns:
            Lista de eventos políticos
        """
        cache_key = "political_events"
        
        # Verificar si hay eventos en caché y no han expirado
        if (cache_key in self.cache["news"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info("Usando eventos políticos en caché")
            return self.cache["news"][cache_key]
        
        events = []
        
        # Intentar obtener eventos políticos (simulado por ahora)
        try:
            # Simulación de eventos políticos
            today = datetime.now()
            
            events = [
                {
                    "title": "Discurso de Trump sobre criptomonedas",
                    "date": today.strftime("%Y-%m-%d"),
                    "source": "Casa Blanca",
                    "impact": "high",
                    "description": "El expresidente hablará sobre su visión de las criptomonedas y posibles políticas"
                },
                {
                    "title": "Votación sobre regulación cripto en el Congreso de EE.UU.",
                    "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                    "source": "Congreso de EE.UU.",
                    "impact": "high",
                    "description": "Votación sobre una nueva ley que podría afectar significativamente al mercado"
                }
            ]
            
            logger.info(f"Obtenidos {len(events)} eventos políticos")
        except Exception as e:
            logger.error(f"Error al obtener eventos políticos: {e}")
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["news"][cache_key] = events
        self._save_cache()
        
        return events
    
    def _get_full_name(self, symbol: str) -> str:
        """
        Obtiene el nombre completo de una criptomoneda a partir de su símbolo.
        
        Args:
            symbol: Símbolo de la criptomoneda
            
        Returns:
            Nombre completo de la criptomoneda
        """
        crypto_names = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "SOL": "Solana",
            "XRP": "Ripple",
            "ADA": "Cardano",
            "DOGE": "Dogecoin",
            "SHIB": "Shiba Inu",
            "BNB": "Binance Coin",
            "DOT": "Polkadot",
            "AVAX": "Avalanche"
        }
        
        return crypto_names.get(symbol.upper(), symbol)
    
    # Método eliminado: _get_fallback_news

# Instancia global del servicio
news_service = NewsService()

async def get_news_for_symbol(symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene noticias y eventos relevantes para una criptomoneda.
    
    Args:
        symbol: Símbolo de la criptomoneda (opcional)
        
    Returns:
        Diccionario con noticias y eventos
    """
    try:
        # Obtener noticias específicas de la criptomoneda
        crypto_news = await news_service.get_crypto_news(symbol)
        
        # Obtener eventos económicos
        economic_events = await news_service.get_economic_events()
        
        # Obtener eventos políticos
        political_events = await news_service.get_political_events()
        
        return {
            "crypto_news": crypto_news[:5],  # Limitar a 5 noticias
            "economic_events": economic_events[:3],  # Limitar a 3 eventos
            "political_events": political_events[:2]  # Limitar a 2 eventos
        }
    except Exception as e:
        logger.error(f"Error al obtener noticias para {symbol}: {e}")
        return {
            "crypto_news": [],
            "economic_events": [],
            "political_events": []
        }

# Función principal para obtener todas las noticias relevantes
async def get_all_relevant_news() -> List[Dict[str, Any]]:
    """
    Obtiene todas las noticias y eventos relevantes para el mercado de criptomonedas.
    
    Returns:
        Lista con todas las noticias y eventos
    """
    try:
        # Obtener noticias generales
        crypto_news = await news_service.get_crypto_news()
        
        # Obtener eventos económicos
        economic_events = await news_service.get_economic_events()
        
        # Obtener eventos políticos
        political_events = await news_service.get_political_events()
        
        # Combinar todas las noticias en una sola lista
        all_news = []
        
        # Agregar noticias de crypto
        if isinstance(crypto_news, list):
            all_news.extend(crypto_news[:5])
        
        # Agregar eventos económicos como noticias
        if isinstance(economic_events, list):
            for event in economic_events[:3]:
                all_news.append({
                    "title": event.get("title", "Evento económico"),
                    "source": "Calendario Económico",
                    "published_at": event.get("date", ""),
                    "summary": event.get("description", "")
                })
        
        # Agregar eventos políticos como noticias
        if isinstance(political_events, list):
            for event in political_events[:2]:
                all_news.append({
                    "title": event.get("title", "Evento político"),
                    "source": event.get("source", "Política"),
                    "published_at": event.get("date", ""),
                    "summary": event.get("description", "")
                })
        
        return all_news
    except Exception as e:
        logger.error(f"Error al obtener todas las noticias relevantes: {e}")
        return []
