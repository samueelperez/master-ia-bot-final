"""
Data integration service for the External Data Service.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from core.cache import cache
from core.circuit_breaker import circuit_breaker
from core.config import settings
from services.news_service import get_news_for_symbol, get_all_relevant_news
from services.social_media_service import get_social_data_for_symbol, get_all_social_data
from services.economic_calendar_service import get_economic_events_for_symbol, get_all_economic_events

logger = logging.getLogger(__name__)

async def get_integrated_data(symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Get integrated external data.
    
    Args:
        symbol: Cryptocurrency symbol (optional)
        
    Returns:
        Integrated external data
    """
    cache_key = f"integrated_{symbol}" if symbol else "integrated_all"
    
    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Using cached integrated data for {symbol or 'all cryptocurrencies'}")
        return cached_data
    
    try:
        # Fetch data
        if symbol:
            logger.info(f"Getting integrated data for {symbol}")
            news = await get_news_for_symbol(symbol)
            social = await get_social_data_for_symbol(symbol)
            events = await get_economic_events_for_symbol(symbol)
        else:
            logger.info("Getting integrated data for all cryptocurrencies")
            news = await get_all_relevant_news()
            social = await get_all_social_data()
            events = await get_all_economic_events()
        
        # Prepare response
        result = {
            "symbol": symbol,
            "news": news,
            "social": social,
            "events": events,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Cache the result
        await cache.set(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"Error getting integrated data: {e}")
        return {
            "symbol": symbol,
            "news": {},
            "social": {},
            "events": {},
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

async def get_formatted_data(symbol: Optional[str] = None) -> str:
    """
    Get formatted external data for use in prompts.
    
    Args:
        symbol: Cryptocurrency symbol (optional)
        
    Returns:
        Formatted external data
    """
    cache_key = f"formatted_{symbol}" if symbol else "formatted_all"
    
    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Using cached formatted data for {symbol or 'all cryptocurrencies'}")
        return cached_data
    
    try:
        # Get integrated data
        data = await get_integrated_data(symbol)
        
        # Format data
        formatted = format_data_for_prompt(data)
        
        # Cache the result
        await cache.set(cache_key, formatted)
        
        return formatted
    except Exception as e:
        logger.error(f"Error getting formatted data: {e}")
        return f"Error getting formatted data: {str(e)}"

def format_data_for_prompt(data: Dict[str, Any]) -> str:
    """
    Format data for use in prompts.
    
    Args:
        data: Integrated data
        
    Returns:
        Formatted data
    """
    try:
        symbol = data.get("symbol")
        timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Format news
        news_data = data.get("news", {})
        crypto_news = news_data.get("crypto_news", [])
        economic_events_news = news_data.get("economic_events", [])
        political_events_news = news_data.get("political_events", [])
        
        # Format social
        social_data = data.get("social", {})
        twitter_trends = social_data.get("twitter_trends", [])
        sentiment = social_data.get("sentiment", {})
        trending_coins = social_data.get("trending_coins", [])
        
        # Format events
        events_data = data.get("events", {})
        high_impact_events = events_data.get("high_impact_events", [])
        upcoming_events = events_data.get("upcoming_events", [])
        symbol_events = events_data.get("symbol_events", [])
        
        # Build formatted text
        lines = []
        
        # Header
        if symbol:
            lines.append(f"# External Data for {symbol}")
        else:
            lines.append("# External Data for Cryptocurrency Market")
        
        lines.append(f"Timestamp: {timestamp}")
        lines.append("")
        
        # Sentiment
        if sentiment:
            overall = sentiment.get("overall", "neutral")
            positive = sentiment.get("positive", 0)
            negative = sentiment.get("negative", 0)
            neutral = sentiment.get("neutral", 0)
            
            lines.append("## Market Sentiment")
            lines.append(f"Overall: {overall.upper()}")
            lines.append(f"Positive: {positive:.2f}, Negative: {negative:.2f}, Neutral: {neutral:.2f}")
            lines.append("")
        
        # Crypto News
        if crypto_news:
            lines.append("## Cryptocurrency News")
            for i, news in enumerate(crypto_news[:3]):  # Limit to 3 news items
                lines.append(f"- {news.get('title')} ({news.get('source')}, {news.get('date')})")
            lines.append("")
        
        # Economic Events News
        if economic_events_news:
            lines.append("## Economic News")
            for i, news in enumerate(economic_events_news[:2]):  # Limit to 2 news items
                lines.append(f"- {news.get('title')} ({news.get('source')}, {news.get('date')})")
            lines.append("")
        
        # Political Events News
        if political_events_news:
            lines.append("## Political News")
            for i, news in enumerate(political_events_news[:2]):  # Limit to 2 news items
                lines.append(f"- {news.get('title')} ({news.get('source')}, {news.get('date')})")
            lines.append("")
        
        # Twitter Trends
        if twitter_trends:
            lines.append("## Twitter Trends")
            for i, trend in enumerate(twitter_trends[:5]):  # Limit to 5 trends
                lines.append(f"- {trend.get('name')} (Volume: {trend.get('tweet_volume')}, Sentiment: {trend.get('sentiment')})")
            lines.append("")
        
        # Trending Coins
        if trending_coins:
            lines.append("## Trending Cryptocurrencies")
            for i, coin in enumerate(trending_coins):
                lines.append(f"- {coin.get('name')} ({coin.get('symbol')}) - Mentions: {coin.get('mentions')}, Sentiment: {coin.get('sentiment')}")
            lines.append("")
        
        # High Impact Events
        if high_impact_events:
            lines.append("## High Impact Economic Events")
            for i, event in enumerate(high_impact_events[:3]):  # Limit to 3 events
                lines.append(f"- {event.get('date')} {event.get('time')}: {event.get('title')} ({event.get('country')})")
            lines.append("")
        
        # Symbol-specific Events
        if symbol_events:
            lines.append(f"## {symbol} Specific Events")
            for i, event in enumerate(symbol_events):
                lines.append(f"- {event.get('date')} {event.get('time')}: {event.get('title')} (Impact: {event.get('impact')})")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error formatting data: {e}")
        return f"Error formatting data: {str(e)}"
