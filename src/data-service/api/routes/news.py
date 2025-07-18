"""
News API routes for the External Data Service.
Incluye validaciones de seguridad robustas.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Path, Query, Request, Depends
from fastapi.responses import JSONResponse

from services.news_service import get_news_for_symbol, get_all_relevant_news
from models.schemas import NewsResponse
from core.auth import has_scope
from core.security import (
    SecureAPIRequest,
    RateLimiter,
    InputSanitizer,
    secure_external_call,
    secure_logger
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Inicializar componentes de seguridad
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()

@router.get("/all", response_model=NewsResponse, summary="Get all relevant news")
async def get_all_news(
    request: Request,
    current_user=Depends(has_scope(["read:news"]))
) -> Dict[str, Any]:
    """
    Get all relevant news for the cryptocurrency market con validaciones de seguridad.
    
    Args:
        request: Request object
        current_user: Usuario autenticado con scope news
        
    Returns:
        Dictionary with news
    """
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Verificar rate limiting para noticias generales
    news_all_key = f"news_all:{client_ip}"
    if not rate_limiter.is_allowed(news_all_key, max_requests=20, window_minutes=1):
        secure_logger.safe_log(f"Rate limit exceeded for all news from IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many requests for news. Please slow down.",
            headers={"Retry-After": "60"}
        )
    
    try:
        # Log solicitud segura
        secure_logger.safe_log(f"Getting all relevant news - User: {current_user.username} IP: {client_ip}")
        
        # Llamada segura al servicio
        news = await secure_external_call(
            get_all_relevant_news,
            timeout=15,
            description="Getting all relevant news"
        )
        
        # Validar respuesta
        if not isinstance(news, dict):
            raise ValueError("Invalid response format from news service")
        
        # Log éxito
        news_count = len(news.get('articles', []))
        secure_logger.safe_log(f"Successfully retrieved {news_count} news articles")
        
        return news
        
    except Exception as e:
        # Log error sin exponer detalles internos
        secure_logger.safe_log(f"Error getting all relevant news from IP: {client_ip}")
        logger.error(f"Error getting all relevant news: {e}")
        
        raise HTTPException(
            status_code=500, 
            detail="Error retrieving news. Please try again later."
        )

@router.get("/{symbol}", response_model=NewsResponse, summary="Get news for a specific cryptocurrency")
async def get_news(
    request: Request,
    symbol: str = Path(..., description="Cryptocurrency symbol", example="BTC"),
    limit: int = Query(10, ge=1, le=50, description="Number of articles to return"),
    current_user=Depends(has_scope(["read:news"]))
) -> Dict[str, Any]:
    """
    Get news for a specific cryptocurrency con validaciones de seguridad.
    
    Args:
        request: Request object
        symbol: Cryptocurrency symbol (validado)
        limit: Límite de artículos (1-50)
        current_user: Usuario autenticado con scope news
        
    Returns:
        Dictionary with news
    """
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Sanitizar y validar símbolo
    clean_symbol = input_sanitizer.sanitize_string(symbol.upper())
    
    # Verificar que el símbolo es válido (solo letras y números, máx 10 caracteres)
    if not clean_symbol.isalnum() or len(clean_symbol) > 10:
        secure_logger.safe_log(f"Invalid symbol format: {symbol} from IP: {client_ip}")
        raise HTTPException(
            status_code=400,
            detail="Invalid symbol format. Only alphanumeric characters allowed, max 10 chars."
        )
    
    # Verificar lista blanca de símbolos conocidos
    allowed_symbols = {
        'BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'MATIC', 'AVAX', 'LINK', 'UNI', 'AAVE',
        'ATOM', 'ALGO', 'XRP', 'LTC', 'BCH', 'ETC', 'XLM', 'VET', 'TRX', 'FIL',
        'THETA', 'XTZ', 'EOS', 'NEO', 'IOTA', 'DASH', 'ZEC', 'XMR', 'QTUM', 'ONT',
        'ICX', 'ZIL', 'BAT', 'ENJ', 'REN', 'KNC'
    }
    
    if clean_symbol not in allowed_symbols:
        secure_logger.safe_log(f"Unknown symbol requested: {clean_symbol} from IP: {client_ip}")
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{clean_symbol}' not supported. Please use a valid cryptocurrency symbol."
        )
    
    # Verificar rate limiting por símbolo
    news_symbol_key = f"news_symbol:{client_ip}:{clean_symbol}"
    if not rate_limiter.is_allowed(news_symbol_key, max_requests=30, window_minutes=1):
        secure_logger.safe_log(f"Rate limit exceeded for symbol {clean_symbol} from IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests for {clean_symbol} news. Please slow down.",
            headers={"Retry-After": "60"}
        )
    
    try:
        # Log solicitud segura con detalles
        secure_logger.safe_log(
            f"Getting news for {clean_symbol} - User: {current_user.username} "
            f"IP: {client_ip} Limit: {limit}"
        )
        
        # Llamada segura al servicio con timeout
        news = await secure_external_call(
            get_news_for_symbol,
            args=[clean_symbol],
            timeout=20,
            description=f"Getting news for {clean_symbol}"
        )
        
        # Validar respuesta
        if not isinstance(news, dict):
            raise ValueError("Invalid response format from news service")
        
        # Aplicar límite si hay artículos
        if 'articles' in news and isinstance(news['articles'], list):
            news['articles'] = news['articles'][:limit]
        
        # Log éxito con estadísticas
        article_count = len(news.get('articles', []))
        secure_logger.safe_log(
            f"Successfully retrieved {article_count} news articles for {clean_symbol}"
        )
        
        return news
        
    except Exception as e:
        # Log error sin exponer detalles internos
        secure_logger.safe_log(f"Error getting news for {clean_symbol} from IP: {client_ip}")
        logger.error(f"Error getting news for {clean_symbol}: {e}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving news for {clean_symbol}. Please try again later."
        )


@router.get("/search", summary="Search news with keywords")
async def search_news(
    request: Request,
    query: str = Query(..., min_length=3, max_length=100, description="Search query"),
    limit: int = Query(10, ge=1, le=25, description="Number of results"),
    current_user=Depends(has_scope(["read:news"]))
) -> Dict[str, Any]:
    """
    Buscar noticias con palabras clave con validaciones de seguridad.
    
    Args:
        request: Request object
        query: Consulta de búsqueda (3-100 caracteres)
        limit: Límite de resultados (1-25)
        current_user: Usuario autenticado
        
    Returns:
        Dictionary with search results
    """
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Sanitizar query de búsqueda
    clean_query = input_sanitizer.sanitize_string(query)
    
    # Verificar intentos de inyección
    if input_sanitizer.detect_injection_attempts(clean_query):
        secure_logger.safe_log(f"Injection attempt in news search from IP: {client_ip}")
        raise HTTPException(
            status_code=400,
            detail="Invalid search query format"
        )
    
    # Rate limiting para búsquedas
    search_key = f"news_search:{client_ip}"
    if not rate_limiter.is_allowed(search_key, max_requests=15, window_minutes=1):
        secure_logger.safe_log(f"Rate limit exceeded for news search from IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many search requests. Please slow down.",
            headers={"Retry-After": "60"}
        )
    
    try:
        # Log búsqueda segura
        secure_logger.safe_log(
            f"News search query: '{clean_query}' - User: {current_user.username} "
            f"IP: {client_ip} Limit: {limit}"
        )
        
        # Simular búsqueda (implementar con servicio real)
        search_results = {
            "query": clean_query,
            "total_results": 0,
            "articles": [],
            "message": "Search functionality will be implemented with actual news service integration"
        }
        
        return search_results
        
    except Exception as e:
        secure_logger.safe_log(f"Error in news search from IP: {client_ip}")
        logger.error(f"Error in news search: {e}")
        
        raise HTTPException(
            status_code=500,
            detail="Error performing news search. Please try again later."
        )
