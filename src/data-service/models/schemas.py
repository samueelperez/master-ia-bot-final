"""
Pydantic models for the External Data Service.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class EconomicEvent(BaseModel):
    """Economic event model."""
    title: str
    date: str
    time: str
    impact: str
    country: str
    description: str


class EconomicEventsResponse(BaseModel):
    """Response model for economic events."""
    high_impact_events: List[Dict[str, Any]] = []
    upcoming_events: List[Dict[str, Any]] = []
    symbol_events: Optional[List[Dict[str, Any]]] = None


class NewsItem(BaseModel):
    """News item model."""
    title: str
    date: str
    source: str
    url: str
    summary: str
    sentiment: Optional[str] = None


class NewsResponse(BaseModel):
    """Response model for news."""
    general_news: List[NewsItem] = []
    crypto_news: List[NewsItem] = []
    symbol_news: Optional[List[NewsItem]] = None


class SocialMediaItem(BaseModel):
    """Social media item model."""
    platform: str
    date: str
    author: str
    content: str
    url: Optional[str] = None
    sentiment: Optional[str] = None
    engagement: Optional[int] = None


class SocialMediaResponse(BaseModel):
    """Response model for social media."""
    trending_posts: List[SocialMediaItem] = []
    trending_hashtags: List[str] = []
    symbol_mentions: Optional[List[SocialMediaItem]] = None
    sentiment_analysis: Optional[Dict[str, Any]] = None


class IntegratedDataResponse(BaseModel):
    """Response model for integrated data."""
    economic_events: EconomicEventsResponse
    news: NewsResponse
    social_media: SocialMediaResponse
    timestamp: str
