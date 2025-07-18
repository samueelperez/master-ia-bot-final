"""
Data integration API routes for the External Data Service.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from services.data_integration_service import get_integrated_data, get_formatted_data
from models.schemas import ExternalDataResponse, FormattedDataResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/all", response_model=Dict[str, Any], summary="Get all integrated data")
async def get_all_integrated() -> Dict[str, Any]:
    """
    Get all integrated data for the cryptocurrency market.
    
    Returns:
        Dictionary with integrated data
    """
    try:
        logger.info("Getting all integrated data")
        data = await get_integrated_data()
        return data
    except Exception as e:
        logger.error(f"Error getting all integrated data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting all integrated data: {str(e)}")

@router.get("/{symbol}", response_model=Dict[str, Any], summary="Get integrated data for a specific cryptocurrency")
async def get_integrated(
    symbol: str = Path(..., description="Cryptocurrency symbol", example="BTC")
) -> Dict[str, Any]:
    """
    Get integrated data for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Dictionary with integrated data
    """
    try:
        logger.info(f"Getting integrated data for {symbol}")
        data = await get_integrated_data(symbol)
        return data
    except Exception as e:
        logger.error(f"Error getting integrated data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting integrated data for {symbol}: {str(e)}")

@router.get("/formatted/all", response_model=FormattedDataResponse, summary="Get formatted data for all cryptocurrencies")
async def get_all_formatted() -> Dict[str, Any]:
    """
    Get formatted data for all cryptocurrencies.
    
    Returns:
        Formatted data
    """
    try:
        logger.info("Getting formatted data for all cryptocurrencies")
        formatted = await get_formatted_data()
        return {"formatted_data": formatted}
    except Exception as e:
        logger.error(f"Error getting formatted data for all cryptocurrencies: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting formatted data for all cryptocurrencies: {str(e)}")

@router.get("/formatted/{symbol}", response_model=FormattedDataResponse, summary="Get formatted data for a specific cryptocurrency")
async def get_formatted(
    symbol: str = Path(..., description="Cryptocurrency symbol", example="BTC")
) -> Dict[str, Any]:
    """
    Get formatted data for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Formatted data
    """
    try:
        logger.info(f"Getting formatted data for {symbol}")
        formatted = await get_formatted_data(symbol)
        return {"formatted_data": formatted}
    except Exception as e:
        logger.error(f"Error getting formatted data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting formatted data for {symbol}: {str(e)}")
