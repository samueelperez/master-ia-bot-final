"""
News service for the External Data Service.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

import httpx
from fastapi import HTTPException

from core.config import settings
from core.cache import cached
from core.circuit_breaker import with_circuit_breaker
from models.schemas import NewsItem, NewsResponse

logger = logging.getLogger(__name__)

# Cache file path
NEWS_CACHE_FILE = "services/news_cache.json"


async def _fetch_news_from_api(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch news from the external API.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        List of news items
    """
    url = settings.NEWS_API_URL
    params = {"apiKey": settings.NEWS_API_KEY}
    
    if symbol:
        params["symbol"] = symbol
    
    async def _fetch():
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
    
    # Use circuit breaker
    try:
        result = await with_circuit_breaker("news_api", _fetch)
        return result
    except Exception as e:
        logger.error(f"Error fetching news from API: {e}")
        # Try to get from cache file as fallback
        return await _get_from_cache_file(symbol)


async def _get_from_cache_file(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get news from cache file.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        List of news items
    """
    try:
        if not os.path.exists(NEWS_CACHE_FILE):
            return []
        
        with open(NEWS_CACHE_FILE, "r") as f:
            cache = json.load(f)
        
        if symbol:
            # Filter by symbol
            return [item for item in cache if symbol in item.get("symbols", [])]
        
        return cache
    except Exception as e:
        logger.error(f"Error reading from cache file: {e}")
        return []


async def _save_to_cache_file(news: List[Dict[str, Any]]) -> None:
    """
    Save news to cache file.
    
    Args:
        news: List of news items
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(NEWS_CACHE_FILE), exist_ok=True)
        
        with open(NEWS_CACHE_FILE, "w") as f:
            json.dump(news, f)
        
        logger.debug(f"Saved news to cache file: {NEWS_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving to cache file: {e}")


@cached("news")
async def get_all_relevant_news() -> Dict[str, Any]:
    """
    Get all relevant news for the cryptocurrency market.
    
    Returns:
        Dictionary with news
    """
    try:
        # Fetch news from API
        news_data = await _fetch_news_from_api()
        
        # Save to cache file
        await _save_to_cache_file(news_data)
        
        # Convert to NewsItem objects
        news_items = []
        for item in news_data:
            try:
                # Extract date from published_at or use current date
                date_str = ""
                if item.get("published_at"):
                    try:
                        date_obj = datetime.fromisoformat(item.get("published_at"))
                        date_str = date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                # Convert sentiment to string if it's a float
                sentiment_str = None
                if item.get("sentiment") is not None:
                    if isinstance(item.get("sentiment"), float):
                        sentiment_value = item.get("sentiment")
                        if sentiment_value > 0.5:
                            sentiment_str = "positive"
                        elif sentiment_value < 0:
                            sentiment_str = "negative"
                        else:
                            sentiment_str = "neutral"
                    else:
                        sentiment_str = str(item.get("sentiment"))
                
                news_item = NewsItem(
                    title=item.get("title", ""),
                    date=date_str,
                    source=item.get("source", ""),
                    url=item.get("url", ""),
                    summary=item.get("description", ""),
                    sentiment=sentiment_str
                )
                news_items.append(news_item)
            except Exception as e:
                logger.error(f"Error creating NewsItem: {e}")
        
        # Create response
        response = {
            "news": news_items,
            "count": len(news_items),
            "timestamp": datetime.now(),
        }
        
        return response
    except Exception as e:
        logger.error(f"Error getting all relevant news: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting all relevant news: {str(e)}")


@cached("news")
async def get_news_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Get news for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Dictionary with news
    """
    try:
        # Fetch news from API
        news_data = await _fetch_news_from_api(symbol)
        
        # Convert to NewsItem objects
        news_items = []
        for item in news_data:
            try:
                # Extract date from published_at or use current date
                date_str = ""
                if item.get("published_at"):
                    try:
                        date_obj = datetime.fromisoformat(item.get("published_at"))
                        date_str = date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                # Convert sentiment to string if it's a float
                sentiment_str = None
                if item.get("sentiment") is not None:
                    if isinstance(item.get("sentiment"), float):
                        sentiment_value = item.get("sentiment")
                        if sentiment_value > 0.5:
                            sentiment_str = "positive"
                        elif sentiment_value < 0:
                            sentiment_str = "negative"
                        else:
                            sentiment_str = "neutral"
                    else:
                        sentiment_str = str(item.get("sentiment"))
                
                news_item = NewsItem(
                    title=item.get("title", ""),
                    date=date_str,
                    source=item.get("source", ""),
                    url=item.get("url", ""),
                    summary=item.get("description", ""),
                    sentiment=sentiment_str
                )
                news_items.append(news_item)
            except Exception as e:
                logger.error(f"Error creating NewsItem: {e}")
        
        # Create response
        response = {
            "news": news_items,
            "count": len(news_items),
            "timestamp": datetime.now(),
        }
        
        return response
    except Exception as e:
        logger.error(f"Error getting news for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting news for {symbol}: {str(e)}")
