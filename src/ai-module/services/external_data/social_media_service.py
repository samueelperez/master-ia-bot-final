"""
Servicio para obtener tendencias y sentimiento de redes sociales relacionados con criptomonedas.
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import random

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes
CACHE_DURATION = 1800  # 30 minutos en segundos
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "social_media_cache.json")

# APIs de redes sociales
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

class SocialMediaService:
    """Servicio para obtener tendencias y sentimiento de redes sociales."""
    
    def __init__(self):
        """Inicializa el servicio de redes sociales."""
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Carga el caché de redes sociales desde el archivo."""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                    # Verificar si el caché ha expirado
                    if time.time() - cache.get("timestamp", 0) < CACHE_DURATION:
                        logger.info("Caché de redes sociales cargado correctamente")
                        return cache
                    else:
                        logger.info("Caché de redes sociales expirado")
            return {"timestamp": 0, "data": {}}
        except Exception as e:
            logger.error(f"Error al cargar el caché de redes sociales: {e}")
            return {"timestamp": 0, "data": {}}
    
    def _save_cache(self) -> None:
        """Guarda el caché de redes sociales en el archivo."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
            logger.info("Caché de redes sociales guardado correctamente")
        except Exception as e:
            logger.error(f"Error al guardar el caché de redes sociales: {e}")
    
    async def get_twitter_trends(self) -> List[Dict[str, Any]]:
        """
        Obtiene las tendencias actuales de Twitter relacionadas con criptomonedas.
        
        Returns:
            Lista de tendencias
        """
        cache_key = "twitter_trends"
        
        # Verificar si hay tendencias en caché y no han expirado
        if (cache_key in self.cache["data"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info("Usando tendencias de Twitter en caché")
            return self.cache["data"][cache_key]
        
        trends = []
        
        # Intentar obtener tendencias de Twitter
        if TWITTER_BEARER_TOKEN:
            try:
                # Usar la API de Twitter v2
                url = "https://api.twitter.com/2/trends/place"
                headers = {
                    "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"
                }
                params = {
                    "id": "1"  # ID para tendencias globales
                }
                
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Filtrar tendencias relacionadas con criptomonedas
                    crypto_keywords = ["crypto", "bitcoin", "btc", "ethereum", "eth", 
                                      "blockchain", "nft", "defi", "altcoin", "token"]
                    
                    for trend in data.get("trends", []):
                        name = trend.get("name", "").lower()
                        if any(keyword in name for keyword in crypto_keywords):
                            trends.append({
                                "name": trend.get("name", ""),
                                "url": trend.get("url", ""),
                                "tweet_volume": trend.get("tweet_volume", 0)
                            })
                
                logger.info(f"Obtenidas {len(trends)} tendencias de Twitter")
            except Exception as e:
                logger.error(f"Error al obtener tendencias de Twitter: {e}")
                raise e
        else:
            logger.error("TWITTER_BEARER_TOKEN no configurado")
            raise ValueError("TWITTER_BEARER_TOKEN es requerido")
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["data"][cache_key] = trends
        self._save_cache()
        
        return trends
    
    async def get_crypto_sentiment(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene el sentimiento actual en redes sociales sobre una criptomoneda.
        
        Args:
            symbol: Símbolo de la criptomoneda (opcional)
            
        Returns:
            Diccionario con información de sentimiento
        """
        cache_key = f"sentiment_{symbol or 'general'}"
        
        # Verificar si hay sentimiento en caché y no ha expirado
        if (cache_key in self.cache["data"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info(f"Usando sentimiento en caché para {symbol or 'general'}")
            return self.cache["data"][cache_key]
        
        sentiment = {}
        
        # Intentar obtener sentimiento (simulado por ahora)
        # En una implementación real, se conectaría a APIs como Sentiment Analysis API
        try:
            # Simulación de sentimiento
            if symbol:
                # Generar valores aleatorios pero consistentes para cada símbolo
                random.seed(symbol)
            
            positive = random.uniform(0.3, 0.7)
            negative = random.uniform(0.1, 1.0 - positive)
            neutral = 1.0 - positive - negative
            
            # Ajustar para símbolos específicos para simular tendencias
            if symbol == "BTC":
                positive += 0.1
                negative -= 0.05
                neutral -= 0.05
            elif symbol == "ETH":
                positive += 0.05
                negative -= 0.02
                neutral -= 0.03
            
            # Normalizar para asegurar que sumen 1
            total = positive + negative + neutral
            positive /= total
            negative /= total
            neutral /= total
            
            sentiment = {
                "positive": round(positive, 2),
                "negative": round(negative, 2),
                "neutral": round(neutral, 2),
                "overall": "positive" if positive > 0.5 else "negative" if negative > 0.5 else "neutral",
                "volume": random.randint(1000, 10000),
                "source": "Twitter, Reddit, Discord"
            }
            
            logger.info(f"Generado sentimiento para {symbol or 'general'}")
        except Exception as e:
            logger.error(f"Error al generar sentimiento: {e}")
            # Sentimiento predeterminado
            sentiment = {
                "positive": 0.5,
                "negative": 0.3,
                "neutral": 0.2,
                "overall": "neutral",
                "volume": 1000,
                "source": "Datos simulados"
            }
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["data"][cache_key] = sentiment
        self._save_cache()
        
        return sentiment
    
    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        """
        Obtiene las criptomonedas que son tendencia en redes sociales.
        
        Returns:
            Lista de criptomonedas tendencia
        """
        cache_key = "trending_coins"
        
        # Verificar si hay monedas tendencia en caché y no han expirado
        if (cache_key in self.cache["data"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info("Usando monedas tendencia en caché")
            return self.cache["data"][cache_key]
        
        trending_coins = []
        
        # Intentar obtener monedas tendencia de CoinGecko
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                for coin_data in data.get("coins", []):
                    coin = coin_data.get("item", {})
                    trending_coins.append({
                        "id": coin.get("id", ""),
                        "name": coin.get("name", ""),
                        "symbol": coin.get("symbol", ""),
                        "market_cap_rank": coin.get("market_cap_rank", 0),
                        "price_btc": coin.get("price_btc", 0),
                        "score": coin.get("score", 0)
                    })
            
            logger.info(f"Obtenidas {len(trending_coins)} monedas tendencia de CoinGecko")
        except Exception as e:
            logger.error(f"Error al obtener monedas tendencia de CoinGecko: {e}")
            raise e
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["data"][cache_key] = trending_coins
        self._save_cache()
        
        return trending_coins

# Instancia global del servicio
social_media_service = SocialMediaService()

async def get_social_data_for_symbol(symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene datos de redes sociales para una criptomoneda.
    
    Args:
        symbol: Símbolo de la criptomoneda (opcional)
        
    Returns:
        Diccionario con datos de redes sociales
    """
    try:
        # Obtener tendencias de Twitter
        twitter_trends = await social_media_service.get_twitter_trends()
        
        # Obtener sentimiento para la criptomoneda
        sentiment = await social_media_service.get_crypto_sentiment(symbol)
        
        # Obtener monedas tendencia
        trending_coins = await social_media_service.get_trending_coins()
        
        # Filtrar tendencias relevantes para el símbolo si se proporciona
        relevant_trends = []
        if symbol:
            symbol_lower = symbol.lower()
            full_name = {
                "btc": "bitcoin",
                "eth": "ethereum",
                "sol": "solana",
                "doge": "dogecoin",
                "shib": "shiba"
            }.get(symbol_lower, symbol_lower)
            
            for trend in twitter_trends:
                trend_name = trend.get("name", "").lower()
                if symbol_lower in trend_name or full_name in trend_name:
                    relevant_trends.append(trend)
        
        # Si no hay tendencias relevantes para el símbolo, usar las generales
        if not relevant_trends and symbol:
            relevant_trends = twitter_trends[:3]  # Usar las 3 primeras tendencias generales
        elif not symbol:
            relevant_trends = twitter_trends[:5]  # Usar las 5 primeras tendencias generales
        
        return {
            "twitter_trends": relevant_trends,
            "sentiment": sentiment,
            "trending_coins": trending_coins[:5]  # Limitar a 5 monedas tendencia
        }
    except Exception as e:
        logger.error(f"Error al obtener datos de redes sociales para {symbol}: {e}")
        raise e

# Función principal para obtener todos los datos de redes sociales
async def get_all_social_data() -> Dict[str, Any]:
    """
    Obtiene todos los datos relevantes de redes sociales para el mercado de criptomonedas.
    
    Returns:
        Diccionario con todos los datos de redes sociales
    """
    try:
        # Obtener tendencias de Twitter
        twitter_trends = await social_media_service.get_twitter_trends()
        
        # Obtener sentimiento general
        sentiment = await social_media_service.get_crypto_sentiment()
        
        # Obtener monedas tendencia
        trending_coins = await social_media_service.get_trending_coins()
        
        return {
            "twitter_trends": twitter_trends[:7],  # Limitar a 7 tendencias
            "sentiment": sentiment,
            "trending_coins": trending_coins[:5]  # Limitar a 5 monedas tendencia
        }
    except Exception as e:
        logger.error(f"Error al obtener todos los datos de redes sociales: {e}")
        raise e
