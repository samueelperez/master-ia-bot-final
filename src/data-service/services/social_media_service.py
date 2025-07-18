"""
Social media service for the External Data Service.
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
from models.schemas import SocialMediaItem, SocialMediaResponse

logger = logging.getLogger(__name__)

# Cache file path
SOCIAL_MEDIA_CACHE_FILE = "services/social_media_cache.json"


async def _fetch_social_data_from_api(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch social media data from the external API.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        List of social media items
    """
    url = settings.TWITTER_API_URL
    params = {
        "apiKey": settings.TWITTER_API_KEY,
        "apiSecret": settings.TWITTER_API_SECRET
    }
    
    if symbol:
        params["symbol"] = symbol
    
    async def _fetch():
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
    
    # Use circuit breaker
    try:
        return await with_circuit_breaker("twitter_api", _fetch)
    except Exception as e:
        logger.error(f"Error fetching social media data from API: {e}")
        # Try to get from cache file as fallback
        return await _get_from_cache_file(symbol)


async def _get_from_cache_file(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get social media data from cache file.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        List of social media items
    """
    try:
        if not os.path.exists(SOCIAL_MEDIA_CACHE_FILE):
            return []
        
        with open(SOCIAL_MEDIA_CACHE_FILE, "r") as f:
            cache = json.load(f)
        
        if symbol:
            # Filter by symbol
            return [item for item in cache if symbol in item.get("symbols", [])]
        
        return cache
    except Exception as e:
        logger.error(f"Error reading from cache file: {e}")
        return []


async def _save_to_cache_file(data: List[Dict[str, Any]]) -> None:
    """
    Save social media data to cache file.
    
    Args:
        data: List of social media items
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(SOCIAL_MEDIA_CACHE_FILE), exist_ok=True)
        
        with open(SOCIAL_MEDIA_CACHE_FILE, "w") as f:
            json.dump(data, f)
        
        logger.debug(f"Saved social media data to cache file: {SOCIAL_MEDIA_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving to cache file: {e}")


@cached("social_media")
async def get_all_social_data() -> Dict[str, Any]:
    """
    Get all social media data for the cryptocurrency market.
    
    Returns:
        Dictionary with social media data
    """
    try:
        # Fetch social media data from API
        social_data = await _fetch_social_data_from_api()
        
        # Save to cache file
        await _save_to_cache_file(social_data)
        
        # Convert to SocialMediaItem objects
        social_items = []
        for item in social_data:
            try:
                social_item = SocialMediaItem(
                    id=item.get("id", str(uuid.uuid4())),
                    platform=item.get("platform", "twitter"),
                    content=item.get("content", ""),
                    author=item.get("author", ""),
                    url=item.get("url"),
                    published_at=datetime.fromisoformat(item.get("published_at")) if item.get("published_at") else datetime.now(),
                    likes=item.get("likes"),
                    shares=item.get("shares"),
                    comments=item.get("comments"),
                    sentiment=item.get("sentiment"),
                    symbols=item.get("symbols", []),
                )
                social_items.append(social_item)
            except Exception as e:
                logger.error(f"Error creating SocialMediaItem: {e}")
        
        # Create response
        response = {
            "posts": social_items,
            "count": len(social_items),
            "timestamp": datetime.now(),
        }
        
        return response
    except Exception as e:
        logger.error(f"Error getting all social media data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting all social media data: {str(e)}")


@cached("social_media")
async def get_social_data_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Get social media data for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Dictionary with social media data
    """
    try:
        # Fetch social media data from API
        social_data = await _fetch_social_data_from_api(symbol)
        
        # Convert to SocialMediaItem objects
        social_items = []
        for item in social_data:
            try:
                social_item = SocialMediaItem(
                    id=item.get("id", str(uuid.uuid4())),
                    platform=item.get("platform", "twitter"),
                    content=item.get("content", ""),
                    author=item.get("author", ""),
                    url=item.get("url"),
                    published_at=datetime.fromisoformat(item.get("published_at")) if item.get("published_at") else datetime.now(),
                    likes=item.get("likes"),
                    shares=item.get("shares"),
                    comments=item.get("comments"),
                    sentiment=item.get("sentiment"),
                    symbols=item.get("symbols", []),
                )
                social_items.append(social_item)
            except Exception as e:
                logger.error(f"Error creating SocialMediaItem: {e}")
        
        # Create response
        response = {
            "posts": social_items,
            "count": len(social_items),
            "timestamp": datetime.now(),
        }
        
        return response
    except Exception as e:
        logger.error(f"Error getting social media data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting social media data for {symbol}: {str(e)}")


@cached("sentiment")
async def get_sentiment_analysis(symbol: str) -> Dict[str, Any]:
    """
    Get sentiment analysis for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Sentiment analysis
    """
    try:
        # Fetch social media data for the symbol
        social_data = await get_social_data_for_symbol(symbol)
        
        # Extract posts
        posts = social_data.get("posts", [])
        
        # Calculate average sentiment
        sentiments = [post.sentiment for post in posts if post.sentiment is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Count positive, negative, and neutral posts
        positive_count = sum(1 for s in sentiments if s > 0.2)
        negative_count = sum(1 for s in sentiments if s < -0.2)
        neutral_count = sum(1 for s in sentiments if -0.2 <= s <= 0.2)
        
        # Create response
        response = {
            "symbol": symbol,
            "average_sentiment": avg_sentiment,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_posts": len(posts),
            "timestamp": datetime.now(),
        }
        
        return response
    except Exception as e:
        logger.error(f"Error getting sentiment analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting sentiment analysis for {symbol}: {str(e)}")
