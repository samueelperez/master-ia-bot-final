"""
Aplicación principal del módulo AI con arquitectura modular.
Implementa separación de responsabilidades y mejores prácticas.
"""

import os
import sys
import logging
import asyncio
import uuid
from typing import Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    
    # Cargar primero el .env de la raíz del proyecto
    root_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(root_env_path):
        load_dotenv(root_env_path)
        print(f"✅ Variables de entorno cargadas desde .env raíz: {root_env_path}")
    
    # Luego cargar el .env local (puede sobrescribir valores)
    local_env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(local_env_path):
        load_dotenv(local_env_path, override=True)
        print(f"✅ Variables de entorno locales cargadas desde: {local_env_path}")
    
    # Fallback: cargar desde directorio actual
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️ python-dotenv no disponible, usando variables de entorno del sistema")

# Configurar logging básico primero
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar path para importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importaciones de FastAPI
try:
    from fastapi import FastAPI, HTTPException, Depends, Request, Response, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.responses import JSONResponse
    logger.info("✅ FastAPI importado correctamente")
except ImportError:
    logger.error("❌ FastAPI no disponible")
    sys.exit(1)

# Importaciones del módulo
from core.config.security_config import SecurityConfig
from core.middleware.rate_limiter import rate_limiter
from core.validation.input_validator import InputValidator, InputValidationError
from core.services.ai_service import AIService
from core.services.data_service import DataService
from core.models.request_models import (
    CryptoAnalysisRequest, TradingSignalRequest, CustomPromptRequest,
    MultiSymbolRequest, HealthCheckRequest, RequestFactory,
    AdvancedStrategyRequest, AdvancedStrategyType
)
from core.services.advanced_strategies_service import AdvancedStrategiesService, StrategyResult, test_router

# Configurar logging
log_config = SecurityConfig.get_log_config()
os.makedirs(log_config["dir"], exist_ok=True)
log_file = os.path.join(log_config["dir"], "ai_module.log")

logging.basicConfig(
    level=getattr(logging, log_config["level"]),
    format=log_config["format"],
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuración de seguridad
security = HTTPBearer()

# Servicios globales
ai_service: AIService = None
data_service: DataService = None
advanced_strategies_service: AdvancedStrategiesService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    global ai_service, data_service, advanced_strategies_service
    
    logger.info("🚀 Iniciando módulo AI...")
    
    try:
        # Inicializar servicios
        ai_service = AIService()
        data_service = DataService()
        advanced_strategies_service = AdvancedStrategiesService(ai_service, data_service)
        
        logger.info("✅ Servicios inicializados correctamente")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Error durante la inicialización: {e}")
        raise
    finally:
        logger.info("🛑 Cerrando módulo AI...")


# Crear aplicación FastAPI
app = FastAPI(
    title="Crypto AI Module",
    description="Módulo de IA para análisis de criptomonedas con arquitectura modular",
    version="2.0.0",
    lifespan=lifespan
)

# Registrar el router temporal solo en desarrollo/debug
app.include_router(test_router)

# Configurar middleware de seguridad
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=SecurityConfig.ALLOWED_HOSTS
)

app.add_middleware(
    CORSMiddleware,
    **SecurityConfig.get_cors_config()
)


# ============================================
# MIDDLEWARE Y AUTENTICACIÓN
# ============================================

def get_client_ip(request: Request) -> str:
    """Obtener IP real del cliente."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verificar token de autenticación."""
    token = credentials.credentials
    
    # Comparar directamente con el token esperado
    if token != SecurityConfig.API_SECRET_KEY:
        logger.warning(f"Intento de autenticación fallido con token: {token[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Token de autenticación inválido"
        )
    
    return token


async def rate_limit_middleware(request: Request) -> None:
    """Middleware de rate limiting."""
    client_ip = get_client_ip(request)
    
    allowed, reason = rate_limiter.is_allowed(client_ip)
    
    if not allowed:
        logger.warning(f"Rate limit excedido para {client_ip}: {reason}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit excedido: {reason}",
            headers={"Retry-After": "300"}
        )
    
    rate_limiter.record_request(client_ip)


# ============================================
# ENDPOINTS DE LA API
# ============================================

@app.get("/health")
async def health_check():
    """Health check básico sin autenticación."""
    return {
        "status": "healthy",
        "timestamp": "2025-01-20T06:39:18Z",
        "version": "2.0.0",
        "module": "ai-crypto-analysis"
    }


@app.get("/health/detailed")
async def detailed_health_check(token: str = Depends(verify_token)):
    """Health check detallado con estado de servicios."""
    try:
        # Verificar estado de servicios
        ai_status = ai_service.get_service_status() if ai_service else {"status": "not_initialized"}
        data_status = data_service.get_service_status() if data_service else {"status": "not_initialized"}
        rate_limiter_status = rate_limiter.get_global_stats()
        
        return {
            "status": "healthy",
            "timestamp": "2025-01-20T06:39:18Z",
            "version": "2.0.0",
            "services": {
                "ai_service": ai_status,
                "data_service": data_status,
                "rate_limiter": rate_limiter_status
            },
            "configuration": {
                "environment": "development" if not SecurityConfig.is_production() else "production",
                "cors_origins": SecurityConfig.ALLOWED_ORIGINS,
                "rate_limits": {
                    "per_minute": SecurityConfig.RATE_LIMIT_PER_MINUTE,
                    "per_hour": SecurityConfig.RATE_LIMIT_PER_HOUR
                }
            }
        }
    except Exception as e:
        logger.error(f"Error en health check detallado: {e}")
        raise HTTPException(status_code=503, detail="Error verificando estado de servicios")


@app.post("/analyze")
async def analyze_crypto(
    request: Request,
    req: CryptoAnalysisRequest,
    token: str = Depends(verify_token)
):
    """Analizar criptomoneda con IA."""
    # Rate limiting
    await rate_limit_middleware(request)
    
    request_id = req.request_id or str(uuid.uuid4())
    client_ip = get_client_ip(request)
    
    logger.info(f"Análisis solicitado - ID: {request_id}, IP: {client_ip}, Símbolo: {req.symbol}")
    
    try:
        # Obtener precio actual
        current_price = await data_service.get_current_price(req.symbol)
        
        if current_price <= 0:
            raise HTTPException(
                status_code=503, 
                detail=f"No se pudo obtener precio para {req.symbol}"
            )
        
        # Generar análisis con IA
        analysis = await ai_service.generate_crypto_analysis(
            symbol=req.symbol,
            price=current_price,
            timeframes=req.timeframes,
            user_prompt=req.user_prompt or "",
            max_tokens=800 if req.include_risk_analysis else 500
        )
        
        response = {
            "request_id": request_id,
            "symbol": req.symbol,
            "current_price": current_price,
            "timeframes": req.timeframes,
            "analysis_type": req.analysis_type,
            "analysis": analysis,
            "metadata": {
                "generated_at": req.timestamp.isoformat(),
                "include_risk_analysis": req.include_risk_analysis,
                "include_price_targets": req.include_price_targets
            }
        }
        
        logger.info(f"Análisis completado - ID: {request_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando análisis - ID: {request_id}, Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno generando análisis"
        )


@app.post("/prompt")
async def custom_prompt(
    request: Request,
    req: CustomPromptRequest,
    token: str = Depends(verify_token)
):
    """Procesar prompt personalizado."""
    await rate_limit_middleware(request)
    
    request_id = req.request_id or str(uuid.uuid4())
    client_ip = get_client_ip(request)
    
    logger.info(f"Prompt personalizado - ID: {request_id}, IP: {client_ip}")
    
    try:
        # Extraer símbolo de la consulta si es una pregunta sobre inversión
        import re
        symbol_match = re.search(r'\b(BTC|ETH|SOL|ADA|DOT|LINK|UNI|AVAX|MATIC|JASMY|DOGE|SHIB|PEPE|WIF|BONK)\b', req.prompt.upper())
        symbol = symbol_match.group(1) if symbol_match else None
        
        # Obtener precio actual y datos técnicos si se menciona un símbolo
        current_price = None
        technical_data = ""
        if symbol:
            try:
                # Obtener precio actual del símbolo
                current_price = await data_service.get_current_price(symbol)
                
                import httpx
                async with httpx.AsyncClient() as client:
                    # Obtener indicadores técnicos del backend
                    backend_url = "http://localhost:8000"
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    # Obtener RSI, MACD, y otros indicadores
                    ta_response = await client.get(
                        f"{backend_url}/indicators?symbol={symbol}-USD&tf=1h&limit=100&profile=basic",
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if ta_response.status_code == 200:
                        ta_data = ta_response.json()
                        indicators = ta_data.get('indicators', {})
                        technical_data = f"""
                        PRECIO ACTUAL DE {symbol}: ${current_price:,.2f}
                        
                        DATOS TÉCNICOS ACTUALES DE {symbol} (TIMEFRAME 1H):
                        - RSI: {indicators.get('RSI', 'N/A')}
                        - MACD: {indicators.get('MACD', 'N/A')}
                        - Media Móvil 20: {indicators.get('SMA_20', 'N/A')}
                        - Media Móvil 50: {indicators.get('SMA_50', 'N/A')}
                        - EMA 12: {indicators.get('EMA_12', 'N/A')}
                        - Bollinger Superior: {indicators.get('Bollinger_Upper', 'N/A')}
                        - Bollinger Inferior: {indicators.get('Bollinger_Lower', 'N/A')}
                        """
                    else:
                        technical_data = f"""
                        PRECIO ACTUAL DE {symbol}: ${current_price:,.2f}
                        ⚠️ No se pudieron obtener datos técnicos para {symbol}
                        """
                        
            except Exception as e:
                logger.warning(f"Error obteniendo datos para {symbol}: {e}")
                technical_data = f"⚠️ Error obteniendo datos para {symbol}: {str(e)}"
        
        # Preparar mensajes para el modelo
        messages = []
        
        # Agregar historial de conversación si existe
        if req.conversation_history:
            messages.extend(req.conversation_history)
        
        # Crear prompt optimizado con datos técnicos
        enhanced_prompt = f"""
        Eres un experto analista de criptomonedas. Responde de manera DETALLADA y ESTRUCTURADA:

        CONSULTA: {req.prompt}

        {technical_data}

        REGLAS:
        1. Máximo 350 palabras
        2. INCLUYE SOLO las secciones esenciales
        3. Usa emojis clave (⚠️ 📊 💰 🔄 📈 💡)
        4. Estructura SIMPLIFICADA:
           - 💰 Precio actual de la cripto (línea inicial)
           - ⚠️ Advertencia legal
           - 📊 Análisis de Rentabilidad (con cálculos específicos)
           - 💰 Cálculo de ROI y Ganancias
           - 🔄 Evaluación de la Estrategia
           - 📈 Contexto Técnico Actual (interpretación relevante para tu situación)
           - 💡 Recomendaciones Accionables
        5. Para ROI: Muestra solo los resultados finales sin fórmulas
        6. Para múltiples compras: Calcula ROI individual por cada compra y luego promedio ponderado
        7. Para indicadores técnicos, explica qué significan para la situación específica del usuario (no solo definiciones)
        8. Incluye cálculos específicos y números exactos
        9. Mantén un tono profesional pero accesible
        10. Para cada compra: Muestra solo el resultado final
        11. NO incluir: Gestión de Riesgo, Comandos útiles, ni texto de cierre
        12. SIEMPRE incluir el precio actual de la cripto en la primera línea
        13. USA SALTOS DE LÍNEA para separar cada sección (\\n\\n)
        14. En Contexto Técnico: Explica qué significan los indicadores para tu inversión específica, no solo definiciones generales

        Formato con saltos de línea:
        💰 Precio actual: $XXX.XX

        ⚠️ Advertencia legal

        📊 Análisis de Rentabilidad

        💰 Cálculo de ROI

        🔄 Evaluación de la Estrategia

        📈 Contexto Técnico

        💡 Recomendaciones Accionables
        """
        
        # Agregar prompt mejorado
        messages.append({"role": "user", "content": enhanced_prompt})
        
        # Parámetros del modelo
        model_params = req.model_parameters or {}
        model_params.update({
            "temperature": req.creativity_level,
            "max_tokens": req.expected_response_length
        })
        
        # Generar respuesta
        response_text = await ai_service.generate_custom_completion(
            messages=messages,
            **model_params
        )
        
        response = {
            "request_id": request_id,
            "prompt": req.prompt,
            "response": response_text,
            "parameters": {
                "creativity_level": req.creativity_level,
                "expected_length": req.expected_response_length,
                "conversation_length": len(req.conversation_history)
            },
            "metadata": {
                "generated_at": req.timestamp.isoformat()
            }
        }
        
        logger.info(f"Prompt personalizado completado - ID: {request_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando prompt - ID: {request_id}, Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno procesando prompt"
        )


@app.post("/multi-analysis")
async def multi_symbol_analysis(
    request: Request,
    req: MultiSymbolRequest,
    token: str = Depends(verify_token)
):
    """Análisis de múltiples símbolos."""
    await rate_limit_middleware(request)
    
    request_id = req.request_id or str(uuid.uuid4())
    client_ip = get_client_ip(request)
    
    logger.info(f"Análisis múltiple - ID: {request_id}, IP: {client_ip}, Símbolos: {req.symbols}")
    
    try:
        # Obtener precios de todos los símbolos en paralelo
        prices = await data_service.get_multiple_prices(req.symbols)
        
        # Generar análisis individual para cada símbolo
        analyses = {}
        for symbol in req.symbols:
            price = prices.get(symbol, 0)
            if price > 0:
                analysis = await ai_service.generate_crypto_analysis(
                    symbol=symbol,
                    price=price,
                    timeframes=[req.timeframe],
                    user_prompt=f"Análisis para comparación múltiple. Timeframe: {req.timeframe}",
                    max_tokens=400
                )
                analyses[symbol] = {
                    "price": price,
                    "analysis": analysis
                }
        
        # Generar análisis comparativo si se solicita
        comparative_analysis = None
        if req.compare_symbols and len(analyses) > 1:
            symbols_data = ", ".join([
                f"{symbol}: ${data['price']:,.2f}" 
                for symbol, data in analyses.items()
            ])
            
            comparative_prompt = f"""
            Compara los siguientes activos: {symbols_data}
            Timeframe: {req.timeframe}
            Proporciona un análisis comparativo conciso destacando fortalezas y debilidades relativas.
            """
            
            comparative_analysis = await ai_service.generate_custom_completion([
                {"role": "user", "content": comparative_prompt}
            ], max_tokens=500)
        
        response = {
            "request_id": request_id,
            "symbols": req.symbols,
            "timeframe": req.timeframe,
            "analysis_type": req.analysis_type,
            "individual_analyses": analyses,
            "comparative_analysis": comparative_analysis,
            "metadata": {
                "generated_at": req.timestamp.isoformat(),
                "symbols_analyzed": len(analyses),
                "include_comparison": req.compare_symbols
            }
        }
        
        logger.info(f"Análisis múltiple completado - ID: {request_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en análisis múltiple - ID: {request_id}, Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno en análisis múltiple"
        )


@app.post("/fundamental_analysis")
async def fundamental_analysis(req: CryptoAnalysisRequest):
    """Generar análisis fundamental de una criptomoneda."""
    try:
        # Validar entrada (usando el validador del request model)
        # La validación se hace automáticamente por Pydantic
        
        # Obtener precio actual
        current_price = await data_service.get_current_price(req.symbol)
        
        # Obtener datos externos (noticias, eventos económicos, etc.)
        from core.external_data.data_integration_service import get_external_data_for_symbol
        external_data = await get_external_data_for_symbol(req.symbol)
        
        # Generar análisis fundamental
        analysis = await ai_service.generate_fundamental_analysis(
            symbol=req.symbol,
            price=current_price,
            external_data=external_data,
            timeframes=req.timeframes or ["1d"]
        )
        
        return {
            "symbol": req.symbol,
            "price": current_price,
            "analysis": analysis,
            "external_data_summary": {
                "news_count": len(external_data.get("news", [])),
                "economic_events_count": len(external_data.get("economic_events", [])),
                "social_sentiment": external_data.get("social_data", {}).get("sentiment", "neutral")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error en análisis fundamental: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/economic_calendar")
async def get_economic_calendar(days: int = 7):
    """Obtener calendario de eventos económicos."""
    try:
        from core.external_data.economic_calendar_service import get_economic_events
        
        # Obtener eventos económicos
        events = await get_economic_events(days)
        
        return {
            "period_days": days,
            "events": events,
            "total_events": sum(len(events[key]) for key in events),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo calendario económico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/macro_analysis")
async def macro_analysis(req: dict):
    """Generar análisis macroeconómico personalizado."""
    try:
        query = req.get("query", "")
        days = req.get("days", 7)
        
        if not query:
            raise ValueError("Query is required")
        
        # Obtener eventos económicos
        from core.external_data.economic_calendar_service import get_economic_events
        events = await get_economic_events(days)
        
        # Obtener noticias relevantes
        from core.external_data.news_service import get_all_relevant_news
        news = await get_all_relevant_news()
        
        # Generar análisis macroeconómico
        analysis = await ai_service.generate_macro_analysis(
            query=query,
            events=events,
            news=news,
            days=days
        )
        
        return {
            "query": query,
            "analysis": analysis,
            "data_summary": {
                "high_impact_events": len(events.get("high_impact_events", [])),
                "medium_impact_events": len(events.get("medium_impact_events", [])),
                "crypto_events": len(events.get("crypto_events", [])),
                "news_articles": len(news)
            },
            "period_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error en análisis macroeconómico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/advanced-strategy")
async def advanced_strategy(
    request: Request,
    req: dict = Body(...),
    token: str = Depends(verify_token)
):
    """Ejecutar una estrategia avanzada de trading o señal simple."""
    await rate_limit_middleware(request)
    request_id = req.get("request_id") or str(uuid.uuid4())
    client_ip = get_client_ip(request)

    # Detectar tipo de request y convertir si es necesario
    if "strategy_type" in req:
        # Es AdvancedStrategyRequest
        advanced_req = AdvancedStrategyRequest(**req)
    else:
        # Es TradingSignalRequest, convertir a AdvancedStrategyRequest
        strategy_type = "scalping"
        if req.get("strategy_name"):
            strategy_mapping = {
                "technical_analysis": "scalping",
                "scalping": "scalping",
                "stochastic": "estocastico",
                "rsi": "rsi",
                "smart_money": "smart_money",
                "volatility": "volatilidad",
                "intraday": "intradia",
                "fair_value_gap": "fair_value_gap",
                "divergence": "divergencia_correlacionada"
            }
            strategy_type = strategy_mapping.get(req["strategy_name"].lower(), "scalping")
        try:
            strategy_enum = AdvancedStrategyType(strategy_type)
        except ValueError:
            strategy_enum = AdvancedStrategyType.SCALPING
        # Usar timestamp actual si no se proporciona
        timestamp = req.get("timestamp")
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        advanced_req = AdvancedStrategyRequest(
            strategy_type=strategy_enum,
            symbol=req["symbol"],
            timeframe=req["timeframe"],
            user_prompt=f"Generar señal de trading con {strategy_type} para {req['symbol']}",
            include_risk_analysis=True,
            include_price_targets=True,
            timestamp=timestamp
        )
    logger.info(f"Estrategia avanzada - ID: {request_id}, IP: {client_ip}, Estrategia: {advanced_req.strategy_type}")
    try:
        result: StrategyResult = await advanced_strategies_service.execute_strategy(
            strategy_type=advanced_req.strategy_type,
            symbol=advanced_req.symbol,
            timeframe=advanced_req.timeframe,
            correlated_symbol=advanced_req.secondary_symbol
        )
        strategy_type_value = advanced_req.strategy_type.value if hasattr(advanced_req.strategy_type, 'value') else str(advanced_req.strategy_type)
        response = {
            "request_id": request_id,
            "strategy_type": strategy_type_value,
            "symbol": advanced_req.symbol,
            "secondary_symbol": advanced_req.secondary_symbol,
            "timeframe": advanced_req.timeframe,
            "result": result.__dict__,
            "metadata": {
                "generated_at": advanced_req.timestamp.isoformat() if advanced_req.timestamp else None
            }
        }
        logger.info(f"Estrategia avanzada completada - ID: {request_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ejecutando estrategia avanzada - ID: {request_id}, Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno ejecutando estrategia avanzada"
        )


# ============================================
# MANEJO DE ERRORES
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejar excepciones HTTP."""
    client_ip = get_client_ip(request)
    logger.warning(f"HTTP Exception - IP: {client_ip}, Status: {exc.status_code}, Detail: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": "2025-01-20T06:39:18Z"
        }
    )


@app.exception_handler(InputValidationError)
async def validation_exception_handler(request: Request, exc: InputValidationError):
    """Manejar errores de validación."""
    client_ip = get_client_ip(request)
    logger.warning(f"Validation Error - IP: {client_ip}, Field: {exc.field}, Reason: {exc.reason}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "status_code": 422,
            "message": "Error de validación",
            "details": {
                "field": exc.field,
                "reason": exc.reason,
                "value": exc.value
            },
            "timestamp": "2025-01-20T06:39:18Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejar excepciones generales."""
    client_ip = get_client_ip(request)
    logger.error(f"Unhandled Exception - IP: {client_ip}, Error: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Error interno del servidor",
            "timestamp": "2025-01-20T06:39:18Z"
        }
    )


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """Función principal para ejecutar la aplicación."""
    try:
        import uvicorn
        
        logger.info("🚀 Iniciando servidor AI Module...")
        
        print(f"[DEBUG] API_SECRET_KEY en backend: {SecurityConfig.API_SECRET_KEY}")

        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8001,
            log_level="info",
            reload=not SecurityConfig.is_production()
        )
        
    except ImportError:
        logger.error("uvicorn no está instalado. Ejecutar: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 