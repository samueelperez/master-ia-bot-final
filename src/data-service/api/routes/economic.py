"""
Economic calendar API routes for the External Data Service.
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from services.economic_calendar_service import get_economic_events_for_symbol, get_all_economic_events, get_high_impact_events
from models.schemas import EconomicEventsResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/all", response_model=Dict[str, Any], summary="Get all economic events")
async def get_all_events() -> Dict[str, Any]:
    """
    Get all economic events.
    
    Returns:
        Dictionary with economic events
    """
    try:
        logger.info("Getting all economic events")
        events = await get_all_economic_events()
        return events
    except Exception as e:
        logger.error(f"Error getting all economic events: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting all economic events: {str(e)}")

@router.get("/{symbol}", response_model=Dict[str, Any], summary="Get economic events for a specific cryptocurrency")
async def get_events(
    symbol: str = Path(..., description="Cryptocurrency symbol", example="BTC")
) -> Dict[str, Any]:
    """
    Get economic events for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Dictionary with economic events
    """
    try:
        logger.info(f"Getting economic events for {symbol}")
        events = await get_economic_events_for_symbol(symbol)
        return events
    except Exception as e:
        logger.error(f"Error getting economic events for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting economic events for {symbol}: {str(e)}")

@router.get("/high-impact", response_model=List[Dict[str, Any]], summary="Get high impact economic events")
async def get_high_impact() -> List[Dict[str, Any]]:
    """
    Get high impact economic events.
    
    Returns:
        List of high impact economic events
    """
    try:
        logger.info("Getting high impact economic events")
        events = await get_high_impact_events()
        return events
    except Exception as e:
        logger.error(f"Error getting high impact economic events: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting high impact economic events: {str(e)}")
