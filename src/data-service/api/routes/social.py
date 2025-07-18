"""
Social media API routes for the External Data Service.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from services.social_media_service import get_social_data_for_symbol, get_all_social_data, get_sentiment_analysis
from models.schemas import SocialMediaResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/all", response_model=Dict[str, Any], summary="Get all social media data")
async def get_all_social() -> Dict[str, Any]:
    """
    Get all social media data for the cryptocurrency market.
    
    Returns:
        Dictionary with social media data
    """
    try:
        logger.info("Getting all social media data")
        social_data = await get_all_social_data()
        return social_data
    except Exception as e:
        logger.error(f"Error getting all social media data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting all social media data: {str(e)}")

@router.get("/{symbol}", response_model=Dict[str, Any], summary="Get social media data for a specific cryptocurrency")
async def get_social(
    symbol: str = Path(..., description="Cryptocurrency symbol", example="BTC")
) -> Dict[str, Any]:
    """
    Get social media data for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Dictionary with social media data
    """
    try:
        logger.info(f"Getting social media data for {symbol}")
        social_data = await get_social_data_for_symbol(symbol)
        return social_data
    except Exception as e:
        logger.error(f"Error getting social media data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting social media data for {symbol}: {str(e)}")

@router.get("/sentiment/{symbol}", response_model=Dict[str, Any], summary="Get sentiment analysis for a specific cryptocurrency")
async def get_sentiment(
    symbol: str = Path(..., description="Cryptocurrency symbol", example="BTC")
) -> Dict[str, Any]:
    """
    Get sentiment analysis for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Sentiment analysis
    """
    try:
        logger.info(f"Getting sentiment analysis for {symbol}")
        sentiment = await get_sentiment_analysis(symbol)
        return sentiment
    except Exception as e:
        logger.error(f"Error getting sentiment analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting sentiment analysis for {symbol}: {str(e)}")
