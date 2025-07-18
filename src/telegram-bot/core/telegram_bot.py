import os
import sys
import traceback
import json
import time
import re
import asyncio
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime

# Cargar .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv opcional en producción

# Dependencias Telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler, 
        CallbackQueryHandler, ConversationHandler, filters, 
        ContextTypes
    )
except ImportError:
    raise ImportError("Instala python-telegram-bot para usar el bot de Telegram")

# Cliente HTTP asíncrono
try:
    import httpx
except ImportError:
    httpx = None

# Imports de seguridad locales
try:
    from .security_config import (
        TelegramSecurityConfig, 
        TelegramRateLimiter, 
        TelegramInputValidator, 
        TelegramSecureLogger
    )
    from .secure_memory_manager import SecureMemoryManager
except ImportError:
    # Fallback para cuando se ejecuta directamente
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.security_config import (
        TelegramSecurityConfig, 
        TelegramRateLimiter, 
        TelegramInputValidator, 
        TelegramSecureLogger
    )
    from core.secure_memory_manager import SecureMemoryManager

# Constantes para estados de conversación
(
    SELECTING_ACTION, SELECTING_CRYPTO, SELECTING_CONDITION_TYPE,
    ENTERING_CONDITION_VALUE, SELECTING_TIMEFRAME, CONFIRMING_ALERT,
    VIEWING_ALERTS, SELECTING_ALERT_TO_DELETE,
    MAIN_MENU, SELECTING_CRYPTO_FOR_ANALYSIS, SELECTING_CRYPTO_FOR_SIGNAL,
    SELECTING_TIMEFRAME_FOR_ANALYSIS, SELECTING_TIMEFRAME_FOR_SIGNAL,
    CONFIGURING_CRYPTO_LIST
) = range(14)

# Constantes para callback data
CRYPTO_PREFIX = "crypto:"
CONDITION_PREFIX = "condition:"
TIMEFRAME_PREFIX = "timeframe:"
ALERT_PREFIX = "alert:"
ACTION_PREFIX = "action:"
MENU_PREFIX = "menu:"
ANALYSIS_PREFIX = "analysis:"
SIGNAL_PREFIX = "signal:"
CONFIG_PREFIX = "config:"

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
AI_MODULE_URL = os.getenv("AI_MODULE_URL", "http://localhost:8001")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta TELEGRAM_BOT_TOKEN o TELEGRAM_TOKEN en variables de entorno")

# Inicializar componentes de seguridad
rate_limiter = TelegramRateLimiter()
validator = TelegramInputValidator()
secure_logger = TelegramSecureLogger()
secure_memory = SecureMemoryManager(db_path=os.getenv("MEMORY_DB", "telegram_bot_memory_secure.db"))

secure_logger.safe_log("Bot de Telegram securizado inicializado", "info")
secure_logger.safe_log(f"AI Module URL: {AI_MODULE_URL}", "info")

# Decorador de autenticación
def require_auth(func):
    """Decorador para requerir autenticación de usuario."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Verificar autorización
        if not TelegramSecurityConfig.is_user_authorized(user_id):
            secure_logger.safe_log("Usuario no autorizado intentó acceder", "warning", user_id)
            await update.message.reply_text(
                "❌ No tienes autorización para usar este bot.\n"
                "Contacta al administrador si crees que esto es un error."
            )
            return
        
        return await func(update, context)
    return wrapper

# Decorador de rate limiting
def rate_limit(func):
    """Decorador para aplicar rate limiting."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Verificar rate limiting
        allowed, rate_info = rate_limiter.is_allowed(user_id)
        if not allowed:
            if rate_info.get("blocked"):
                remaining = rate_info.get("remaining_seconds", 0)
                await update.message.reply_text(
                    f"⏳ Has excedido el límite de requests.\n"
                    f"Intenta de nuevo en {remaining} segundos."
                )
            else:
                await update.message.reply_text(
                    "⚠️ Estás enviando mensajes muy rápido.\n"
                    "Por favor, espera unos segundos antes de continuar."
                )
            return
        
        # Registrar request exitosa
        rate_limiter.record_request(user_id)
        return await func(update, context)
    
    return wrapper

# Validador de entrada
def validate_input(input_type: str = "message"):
    """Decorador para validar entrada del usuario."""
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            if update.message and update.message.text:
                text = update.message.text
                
                # Sanitizar mensaje
                sanitized_text = validator.sanitize_message(text)
                
                # Validar entrada
                is_valid, error_msg = validator.validate_user_input(sanitized_text, input_type)
                if not is_valid:
                    secure_logger.safe_log(f"Entrada inválida detectada: {error_msg}", "warning", user_id)
                    await update.message.reply_text(
                        f"❌ Entrada inválida: {error_msg}\n"
                        "Por favor, intenta de nuevo con datos válidos."
                    )
                    return
                
                # Almacenar el texto sanitizado en el contexto para su uso posterior
                context.user_data['sanitized_text'] = sanitized_text
            
            return await func(update, context)
        return wrapper
    return decorator

# Handler /start con autenticación y rate limiting
@require_auth
@rate_limit
@validate_input()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    # Crear o actualizar usuario de forma segura
    success = secure_memory.create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    
    if not success:
        secure_logger.safe_log("Error creando/actualizando usuario", "error", user.id)
        await update.message.reply_text(
            "❌ Error interno. Por favor, intenta de nuevo más tarde."
        )
        return
    
    # Crear teclado con opciones principales
    keyboard = [
        [InlineKeyboardButton("📊 Análisis", callback_data=f"{MENU_PREFIX}analysis")],
        [InlineKeyboardButton("🎯 Señales", callback_data=f"{MENU_PREFIX}signal")],
        [InlineKeyboardButton("🔔 Alertas", callback_data=f"{ACTION_PREFIX}alerts")]
    ]
    
    # Botón de administración solo para admins
    if TelegramSecurityConfig.is_admin_user(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin", callback_data=f"{ACTION_PREFIX}admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = (
        "🚀 **Crypto AI Trading Bot** 🤖\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "¡Hola! 👋 Soy tu asistente de IA especializado en análisis de criptomonedas y trading automatizado.\n\n"
        "🎯 **¿Qué puedo hacer por ti?**\n\n"
        "📈 **Análisis Técnico Avanzado:**\n"
        "• \"Analiza Bitcoin en 4h\"\n"
        "• \"¿Cómo está ETH en 1d?\"\n"
        "• \"Análisis completo de SOL\"\n\n"
        "⚡ **Señales de Trading Inteligentes:**\n"
        "• \"Dame una señal de SOL en 1h\"\n"
        "• \"Señal para BTC en 15m\"\n"
        "• \"Estrategia de scalping para ETH\"\n\n"
        "🌍 **Análisis Fundamental & Macro:**\n"
        "• \"Análisis fundamental de Bitcoin\"\n"
        "• \"Eventos macroeconómicos importantes\"\n"
        "• \"Calendario económico de esta semana\"\n"
        "• \"Impacto de la FED en crypto\"\n\n"
        "💬 **¡Escribe tu consulta o selecciona una opción del menú!**"
    )
    
    secure_memory.add_message(user.id, "assistant", welcome)
    secure_logger.safe_log("Usuario inició sesión", "info", user.id)
    
    await update.message.reply_text(welcome, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return MAIN_MENU

# Función de comunicación segura con módulo IA
async def secure_ai_call(endpoint: str, payload: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
    """
    Llamada segura al módulo de IA con endpoints correctos.
    """
    if not httpx:
        secure_logger.safe_log("httpx no está instalado", "error")
        return None
    
    # Determinar endpoint correcto
    if endpoint == "generate":
        url = f"{AI_MODULE_URL}/analyze"
    elif endpoint == "signal":
        url = f"{AI_MODULE_URL}/signal"
    elif endpoint == "prompt":
        url = f"{AI_MODULE_URL}/prompt"
    elif endpoint == "advanced-strategy":
        url = f"{AI_MODULE_URL}/advanced-strategy"
    else:
        url = f"{AI_MODULE_URL}/analyze"
    
    max_retries = 3
    
    # Token de autenticación correcto
    auth_token = "cr1nW3IDA-CQlkm6XBIoIdZmqv9mLj6U_-1z0ttyOZ4"
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(
                timeout=TelegramSecurityConfig.AI_MODULE_TIMEOUT
            ) as client:
                # Health check
                health_resp = await client.get(
                    f"{AI_MODULE_URL}/health", 
                    timeout=TelegramSecurityConfig.HEALTH_CHECK_TIMEOUT
                )
                health_resp.raise_for_status()
                
                # Debug info como en simulate_bot.py
                secure_logger.safe_log(f"Usando token: {auth_token}", "debug", user_id)
                secure_logger.safe_log(f"Enviando solicitud a: {url}", "debug", user_id)
                secure_logger.safe_log(f"Payload: {payload}", "debug", user_id)
                
                # Llamada principal con token de autenticación
                headers = {"Authorization": f"Bearer {auth_token}"}
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                response_data = response.json()
                
                secure_logger.safe_log(f"Llamada exitosa a {endpoint}", "info", user_id)
                return response_data
                
        except httpx.TimeoutException:
            secure_logger.safe_log(f"Timeout en intento {attempt + 1} para {endpoint}", "warning", user_id)
            if attempt == max_retries - 1:
                break
        except httpx.HTTPError as e:
            secure_logger.safe_log(f"Error HTTP en {endpoint}: {str(e)}", "error", user_id)
            break
        except Exception as e:
            secure_logger.safe_log(f"Error inesperado en {endpoint}: {str(e)}", "error", user_id)
            break
    
    return None

# Función para obtener precio actual (igual que simulate_bot.py)
async def get_current_price(symbol: str) -> float:
    """
    Obtiene el precio actual de Binance para el símbolo.
    Misma lógica que simulate_bot.py
    """
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("price", 0))
    except Exception as e:
        secure_logger.safe_log(f"Error obteniendo precio de Binance: {e}", "warning")
        # Precios de fallback - mismos que simulate_bot.py
        fallback_prices = {
            "BTC": 65000.0,
            "ETH": 3500.0,
            "SOL": 150.0,
            "ADA": 0.5,
            "DOT": 7.0,
            "MATIC": 0.8,
            "AVAX": 35.0,
            "LINK": 15.0,
            "DOGE": 0.12,
            "SHIB": 0.00002,
            "XRP": 0.55
        }
        return fallback_prices.get(symbol, 100.0)

async def try_multiple_cryptos_and_timeframes(user_id: int, text: str) -> Optional[Dict[str, Any]]:
    """Analiza múltiples criptomonedas y timeframes para encontrar la mejor señal."""
    import asyncio
    from datetime import datetime
    
    # Top 3 criptomonedas por capitalización de mercado
    top_cryptos = ["BTC", "ETH", "SOL"]
    timeframes_to_try = ["5m", "15m", "1h", "30m", "4h", "1d"]
    
    secure_logger.safe_log(f"Analizando top 3 cryptos: {top_cryptos}", "info", user_id)
    
    best_signal = None
    best_confidence = 0.0
    best_score = 0.0
    
    # Mensaje de progreso
    progress_msg = "🔍 Analizando las mejores oportunidades...\n\n"
    progress_msg += "📊 Top 3 criptomonedas:\n"
    for i, crypto in enumerate(top_cryptos, 1):
        progress_msg += f"{i}. {crypto}\n"
    progress_msg += "\n⏳ Buscando señales en múltiples timeframes..."
    
    # Enviar mensaje de progreso (esto requeriría modificar la función para recibir el update)
    # Por ahora, solo loggeamos
    
    for crypto in top_cryptos:
        secure_logger.safe_log(f"Analizando {crypto}...", "info", user_id)
        
        for tf in timeframes_to_try:
            try:
                # Obtener precio actual
                current_price = await get_current_price(crypto)
                
                # Crear payload para este crypto y timeframe
                test_payload = {
                    "symbol": crypto,
                    "timeframe": tf,
                    "strategy_name": "scalping",
                    "request_id": f"signal_{user_id}_{int(datetime.now().timestamp())}",
                    "current_price": current_price,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Llamar al AI Module
                data = await secure_ai_call("advanced-strategy", test_payload, user_id)
                
                if data and "result" in data:
                    result = data.get("result", {})
                    signal = result.get("signal", "NEUTRAL")
                    confidence = result.get("confidence", 0.0)
                    entry_price = result.get("entry_price")
                    
                    # Si encontramos una señal válida, calcular score
                    if signal != "NEUTRAL" and entry_price is not None and confidence > 0:
                        # Calcular score basado en confianza y otros factores
                        score = confidence
                        
                        # Bonus por timeframe preferido (timeframes más cortos para scalping)
                        timeframe_bonus = {
                            "5m": 0.1,
                            "15m": 0.08,
                            "30m": 0.06,
                            "1h": 0.04,
                            "4h": 0.02,
                            "1d": 0.0
                        }
                        score += timeframe_bonus.get(tf, 0.0)
                        
                        # Bonus por crypto (BTC suele ser más estable)
                        crypto_bonus = {
                            "BTC": 0.05,
                            "ETH": 0.03,
                            "SOL": 0.02
                        }
                        score += crypto_bonus.get(crypto, 0.0)
                        
                        # Si es la mejor señal hasta ahora, guardarla
                        if score > best_score:
                            best_score = score
                            best_confidence = confidence
                            best_signal = data
                            best_signal["found_crypto"] = crypto
                            best_signal["found_timeframe"] = tf
                            best_signal["score"] = score
                            
                            secure_logger.safe_log(f"Nueva mejor señal: {crypto} en {tf} (score: {score:.3f})", "info", user_id)
                
                # Pequeña pausa entre llamadas
                await asyncio.sleep(0.3)
                
            except Exception as e:
                secure_logger.safe_log(f"Error analizando {crypto} en {tf}: {str(e)}", "warning", user_id)
                continue
    
    if best_signal:
        secure_logger.safe_log(f"Mejor señal encontrada: {best_signal['found_crypto']} en {best_signal['found_timeframe']} (score: {best_score:.3f})", "info", user_id)
        return best_signal
    else:
        secure_logger.safe_log("No se encontraron señales válidas en ninguna crypto", "info", user_id)
        return None

# Función de construcción segura de payload (alineada con simulate_bot.py)
async def try_multiple_timeframes(payload: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
    """Prueba múltiples timeframes hasta encontrar una señal válida."""
    import asyncio
    timeframes_to_try = ["5m", "15m", "1h", "30m", "4h", "1d"]
    symbol = payload.get("symbol", "BTC")
    
    secure_logger.safe_log(f"Probando múltiples timeframes para {symbol}: {timeframes_to_try}", "info", user_id)
    
    for tf in timeframes_to_try:
        try:
            # Crear payload para este timeframe específico
            test_payload = {
                "symbol": symbol,
                "timeframe": tf,
                "strategy_name": "scalping",
                "request_id": f"signal_{user_id}_{int(datetime.now().timestamp())}",
                "current_price": payload.get("current_price", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Llamar al AI Module
            data = await secure_ai_call("advanced-strategy", test_payload, user_id)
            
            if data and "result" in data:
                result = data.get("result", {})
                signal = result.get("signal", "NEUTRAL")
                entry_price = result.get("entry_price")
                
                # Si encontramos una señal válida, la devolvemos
                if signal != "NEUTRAL" and entry_price is not None:
                    secure_logger.safe_log(f"Señal válida encontrada en {tf} para {symbol}", "info", user_id)
                    # Agregar información del timeframe encontrado
                    data["found_timeframe"] = tf
                    return data
            
            # Pequeña pausa entre llamadas para no sobrecargar
            await asyncio.sleep(0.5)
            
        except Exception as e:
            secure_logger.safe_log(f"Error probando timeframe {tf}: {str(e)}", "warning", user_id)
            continue
    
    # Si no se encontró ninguna señal válida, devolver la última respuesta
    secure_logger.safe_log(f"No se encontraron señales válidas para {symbol} en ningún timeframe", "info", user_id)
    
    # Probar con el último timeframe como fallback
    try:
        fallback_payload = {
            "symbol": symbol,
            "timeframe": timeframes_to_try[-1],
            "strategy_name": "scalping",
            "request_id": f"signal_{user_id}_{int(datetime.now().timestamp())}",
            "current_price": payload.get("current_price", 0),
            "timestamp": datetime.now().isoformat()
        }
        return await secure_ai_call("advanced-strategy", fallback_payload, user_id)
    except:
        return None

async def build_secure_payload(user_id: int, text: str) -> dict:
    """Construye payload de forma segura usando la misma lógica que simulate_bot.py."""
    import re
    from datetime import datetime
    sanitized_text = validator.sanitize_message(text)
    sanitized_text = re.sub(r';\s*\w+', ' ', sanitized_text)
    symbol = "BTC"
    timeframes = ["1h"]  # Cambiar valor por defecto a 1h
    common_symbols = ["BTC", "ETH", "ADA", "DOT", "SOL", "MATIC", "AVAX", "LINK", "DOGE", "SHIB", "XRP", "JASMY", "PEPE", "BONK", "WIF", "FLOKI", "BOME", "MEME", "BOOK", "POPCAT"]
    
    # Detectar si se especificó una criptomoneda
    crypto_specified = False
    for s in common_symbols:
        if s.lower() in sanitized_text.lower():
            symbol = s
            crypto_specified = True
            break
    
    timeframe_patterns = {
        "15m": ["15 minutos", "15m", "quince minutos", "15 min", "15min", "15 m"],
        "30m": ["30 minutos", "30m", "treinta minutos", "30 min", "30min", "30 m", "media hora"],
        "5m": ["5 minutos", "5m", "cinco minutos", "5 min", "5min", "5 m"],
        "1m": ["1 minuto", "1m", "un minuto", "1 min", "1min", "1 m"],
        "4h": ["4 horas", "4h", "cuatro horas", "4 h", "4hr", "4 hr"],
        "1h": ["1 hora", "1h", "una hora", "1 h", "1hr", "1 hr"],
        "1d": ["1 día", "1d", "un día", "diario", "daily", "1 d", "1day", "1 day"],
        "1w": ["1 semana", "1w", "una semana", "semanal", "weekly", "1 w", "1week", "1 week"]
    }
    detected_timeframe = None
    for tf, patterns in timeframe_patterns.items():
        if any(pattern in sanitized_text.lower() for pattern in patterns):
            detected_timeframe = tf
            break
    if detected_timeframe:
        timeframes = [detected_timeframe]
    else:
        timeframes = ["1h"]  # Si no se detecta timeframe, usar 1h
    current_price = await get_current_price(symbol)
    # Detectar si es una solicitud de señal (palabra clave 'señal')
    is_signal_request = "señal" in sanitized_text.lower()
    
    # Detectar si es una consulta conversacional (preguntas personales, consultas sobre compras, etc.)
    conversational_keywords = [
        "he comprado", "compré", "tengo", "es buena", "es mala", "debería", 
        "qué opinas", "qué piensas", "me recomiendas", "ayúdame", "consejo",
        "invertir", "inversión", "portfolio", "cartera", "ganancias", "pérdidas"
    ]
    is_conversational = any(keyword in sanitized_text.lower() for keyword in conversational_keywords)
    
    if is_signal_request:
        # Siempre usar advanced-strategy para señales
        payload = {
            "symbol": symbol,
            "timeframe": timeframes[0],
            "strategy_name": "scalping",  # O "swing" si quieres lógica más avanzada
            "request_id": f"signal_{user_id}_{int(datetime.now().timestamp())}",
            "current_price": current_price,
            "timestamp": datetime.now().isoformat(),
            "crypto_specified": crypto_specified  # Agregar flag para saber si se especificó crypto
        }
        return payload, "advanced-strategy"
    elif is_conversational:
        # Usar endpoint /prompt para consultas conversacionales
        payload = {
            "prompt": sanitized_text,
            "creativity_level": 0.7,
            "expected_response_length": 800,
                            "conversation_history": secure_memory.get_conversation_history(user_id, limit=5),
            "timestamp": datetime.now().isoformat(),
            "request_id": f"conversation_{user_id}_{int(datetime.now().timestamp())}"
        }
        return payload, "prompt"
    else:
        # Si no es señal ni conversacional, flujo normal de análisis
        payload = {
            "symbol": symbol,
            "timeframes": timeframes,
            "user_prompt": sanitized_text,
            "current_price": current_price
        }
        return payload, "generate"

# Procesar mensaje con validación y seguridad
@require_auth
@rate_limit
@validate_input()
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Actualizar información del usuario
    secure_memory.create_or_update_user(
        user_id=user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name,
    )
    
    # Añadir mensaje del usuario al historial
    secure_memory.add_message(user_id, "user", text)
    
    # Construir payload seguro usando la misma lógica que simulate_bot.py
    payload, endpoint = await build_secure_payload(user_id, text)
    
    secure_logger.safe_log(f"Procesando: {text[:50]}...", "info", user_id)
    
    try:
        # Si es una solicitud de señal
        if endpoint == "advanced-strategy" and "señal" in text.lower():
            # Si no se especificó una criptomoneda, analizar top 3
            if not payload.get("crypto_specified", False):
                data = await try_multiple_cryptos_and_timeframes(user_id, text)
            else:
                # Si se especificó una criptomoneda, probar múltiples timeframes
                data = await try_multiple_timeframes(payload, user_id)
        else:
            # Usar siempre el endpoint /generate como en simulate_bot.py
            data = await secure_ai_call(endpoint, payload, user_id)
        
        if not data:
            error_msg = "❌ Error comunicándose con el servicio de IA. Intenta de nuevo más tarde."
            await update.message.reply_text(error_msg)
            secure_memory.add_message(user_id, "assistant", error_msg)
            return
        
        # Procesar respuesta usando la misma lógica que simulate_bot.py
        if "response" in data and endpoint == "prompt":
            # Respuesta conversacional del endpoint /prompt
            response_text = data.get("response", "No he podido procesar tu consulta. ¿Puedes intentarlo de nuevo?")
            secure_logger.safe_log(f"Respuesta del prompt: {response_text[:100]}...", "debug", user_id)
            secure_logger.safe_log(f"Data completo: {data}", "debug", user_id)
        elif "analysis" in data:
            # Respuesta de análisis - mismo formato que simulate_bot.py
            symbol = data.get("symbol", "Crypto")
            timeframes = data.get("timeframes", ["1d"])
            timeframe = timeframes[0] if timeframes else "1d"
            current_price = data.get("current_price", 0)  # Usar "current_price" como devuelve el módulo de IA
            analysis = data.get("analysis", "<sin análisis>")
            
            response_text = (
                f"🧠 Análisis IA para {symbol} ({timeframe}):\n\n"
                f"💰 Precio actual: ${current_price}\n\n"
                f"{analysis}\n\n"
                "⚠️ No es asesoramiento financiero."
            )
        elif "result" in data:
            # Respuesta avanzada real del backend
            result = data["result"]
            signal = result.get("signal", "-")
            
            # Si la señal es NEUTRAL o no hay oportunidad, mostrar mensaje simple
            if signal == "NEUTRAL" or signal == "neutral" or signal == "None" or signal == "-":
                # Si se analizaron múltiples cryptos, mostrar información adicional
                crypto_analysis_info = ""
                if not payload.get("crypto_specified", False):
                    crypto_analysis_info = f"\n📊 **Análisis realizado en:** BTC, ETH, SOL\n"
                    crypto_analysis_info += f"⏰ **Timeframes probados:** 5m, 15m, 30m, 1h, 4h, 1d\n\n"
                
                symbol_to_show = data.get('found_crypto', data.get('symbol', 'BTC'))
                timeframe_to_show = data.get('found_timeframe', data.get('timeframe', '1h'))
                
                response_text = (
                    f"🔍 **Análisis completado para {symbol_to_show} ({timeframe_to_show})**\n\n"
                    f"❌ **No se encontró oportunidad de trading**\n\n"
                    f"💡 **Razón:** Los indicadores técnicos no muestran confluencia suficiente para generar una señal segura.\n\n"
                    f"{crypto_analysis_info}"
                    f"⏰ **Próximo análisis:** Intenta en unos minutos o cambia el timeframe.\n\n"
                    f"⚠️ **Recuerda:** Es mejor no operar que operar sin fundamento técnico."
                )
            else:
                # Procesar señal válida con el formato profesional
                entry = result.get("entry_price", "-")
                stop = result.get("stop_loss", "-")
                take = result.get("take_profit", "-")
                confidence = result.get("confidence", "-")
                reasoning = result.get("reasoning", "-")
                
                # Procesar confianza - redondear a 2 decimales
                if isinstance(confidence, (int, float)):
                    confidence = round(confidence, 2)
                
                # Extraer niveles del razonamiento si están disponibles
                entry_match = re.search(r'Punto de entrada:\s*\$?([\d,]+\.?\d*)', reasoning)
                stop_match = re.search(r'Stop loss:\s*\$?([\d,]+\.?\d*)', reasoning)
                take_match = re.search(r'Take profit:\s*\$?([\d,]+\.?\d*)', reasoning)
                
                if entry_match:
                    entry = float(entry_match.group(1).replace(',', ''))
                if stop_match:
                    stop = float(stop_match.group(1).replace(',', ''))
                if take_match:
                    take = float(take_match.group(1).replace(',', ''))
                
                # Validar niveles coherentes
                if isinstance(entry, (int, float)) and isinstance(stop, (int, float)) and isinstance(take, (int, float)):
                    if stop >= entry:
                        stop = entry * 0.995  # 0.5% por debajo
                    if take <= entry:
                        take = entry * 1.01   # 1% por encima
                
                # Procesar señal con contexto
                signal_text = str(signal) if signal is not None else "-"
                signal_emoji = "⚡"
                
                # Convertir a string y validar antes de usar .upper()
                if isinstance(signal, str):
                    signal_upper = signal.upper()
                    if signal_upper in ["BUY", "COMPRAR", "LONG"]:
                        signal_text = "LONG"
                        signal_emoji = "📈"
                    elif signal_upper in ["SELL", "VENDER", "SHORT"]:
                        signal_text = "SHORT"
                        signal_emoji = "📉"
                
                # Formatear precios
                entry_str = f"${entry:,.2f}" if isinstance(entry, (int, float)) else str(entry)
                stop_str = f"${stop:,.2f}" if isinstance(stop, (int, float)) else str(stop)
                take_str = f"${take:,.2f}" if isinstance(take, (int, float)) else str(take)
                
                # Calcular ratios de riesgo
                risk_reward = "N/A"
                if isinstance(entry, (int, float)) and isinstance(stop, (int, float)) and isinstance(take, (int, float)):
                    risk = abs(entry - stop)
                    reward = abs(take - entry)
                    if risk > 0:
                        risk_reward = f"{reward/risk:.2f}:1"
                
                # Determinar confianza textual
                confidence_text = "Baja"
                if isinstance(confidence, (int, float)):
                    if confidence >= 0.7:
                        confidence_text = "Alta"
                    elif confidence >= 0.5:
                        confidence_text = "Media"
                    else:
                        confidence_text = "Baja"
                
                # Calcular TP2 (segundo take profit)
                tp2_str = "N/A"
                if isinstance(entry, (int, float)) and isinstance(take, (int, float)):
                    tp2 = entry + (take - entry) * 1.5  # 50% más que TP1
                    tp2_str = f"${tp2:,.2f}"
                
                # Procesar razonamiento para análisis
                analysis_text = "Análisis técnico basado en indicadores como RSI, MACD, SMA, EMA y bandas de Bollinger."
                if reasoning:
                    # Extraer líneas relevantes del razonamiento
                    reasoning_lines = reasoning.split('\n')
                    relevant_lines = []
                    
                    # Buscar indicadores específicos mencionados en el razonamiento
                    indicators_found = []
                    for line in reasoning_lines:
                        line_lower = line.lower()
                        # Buscar indicadores específicos
                        if 'rsi' in line_lower and any(str(i) in line_lower for i in [6, 14, 21]):
                            indicators_found.append('RSI')
                        if 'macd' in line_lower:
                            indicators_found.append('MACD')
                        if 'bollinger' in line_lower or 'bb' in line_lower:
                            indicators_found.append('Bandas de Bollinger')
                        if 'estocástico' in line_lower or 'stoch' in line_lower:
                            indicators_found.append('Estocástico')
                        if 'sma' in line_lower or 'ema' in line_lower:
                            indicators_found.append('Medias Móviles')
                        if 'atr' in line_lower:
                            indicators_found.append('ATR')
                        if 'volumen' in line_lower:
                            indicators_found.append('Volumen')
                        
                        # Buscar líneas con información técnica relevante
                        if any(keyword in line_lower for keyword in ['patrón', 'breakout', 'nivel', 'tendencia', 'volatilidad', 'soporte', 'resistencia', 'cruce']):
                            relevant_lines.append(line.strip())
                    
                    # Si encontramos indicadores específicos, usarlos
                    if indicators_found:
                        unique_indicators = list(set(indicators_found))  # Eliminar duplicados
                        analysis_text = f"Análisis basado en: {', '.join(unique_indicators)}"
                        
                        # Añadir información específica si está disponible
                        if relevant_lines:
                            specific_info = ' '.join(relevant_lines[:2])  # Tomar las 2 líneas más relevantes
                            if len(specific_info) > 150:
                                specific_info = specific_info[:150] + "..."
                            analysis_text += f" - {specific_info}"
                    elif relevant_lines:
                        # Si no encontramos indicadores específicos pero sí líneas relevantes
                        analysis_text = ' '.join(relevant_lines[:3])  # Tomar las 3 líneas más relevantes
                        if len(analysis_text) > 200:
                            analysis_text = analysis_text[:200] + "..."
                
                # Formato profesional y visual
                symbol_to_show = data.get('found_crypto', data.get('symbol', 'BTC'))
                timeframe_to_show = data.get('found_timeframe', data.get('timeframe', '5m'))
                
                # Si se analizaron múltiples cryptos, mostrar información adicional
                crypto_analysis_info = ""
                if data.get('found_crypto') and not payload.get("crypto_specified", False):
                    score = data.get('score', 0.0)
                    crypto_analysis_info = f"\n🏆 **MEJOR OPORTUNIDAD ENCONTRADA**\n"
                    crypto_analysis_info += f"📊 Analizadas: BTC, ETH, SOL\n"
                    crypto_analysis_info += f"⭐ Score: {score:.3f}\n"
                
                response_text = (
                    f"🚀 {symbol_to_show}/USDT - SEÑAL {timeframe_to_show}\n"
                    f"💰 {entry_str} | {signal_emoji} {signal_text} | ⚡ {risk_reward}\n\n"
                    f"🎯 NIVELES:\n"
                    f"• Entrada: {entry_str}\n"
                    f"• Stop Loss: {stop_str}\n"
                    f"• TP1: {take_str} | TP2: {tp2_str}\n\n"
                    f"💡 ANÁLISIS: {analysis_text}\n\n"
                    f"🔥 CONFIANZA: {confidence_text}"
                    f"{crypto_analysis_info}"
                )
        else:
            # Respuesta general - mismo fallback que simulate_bot.py
            response_text = data.get("response", "No he podido procesar tu mensaje. ¿Puedes intentarlo de nuevo?")
        
        # Validar y sanitizar respuesta
        if len(response_text) > TelegramSecurityConfig.MAX_MESSAGE_LENGTH:
            response_text = response_text[:TelegramSecurityConfig.MAX_MESSAGE_LENGTH] + "..."
        
        # Añadir respuesta al historial
        secure_memory.add_message(user_id, "assistant", response_text)
        
        # Enviar respuesta
        await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)
        
        secure_logger.safe_log("Mensaje procesado exitosamente", "info", user_id)
        
    except Exception as e:
        error_msg = "❌ Error inesperado procesando tu solicitud."
        secure_logger.safe_log(f"Error procesando mensaje: {str(e)}", "error", user_id)
        await update.message.reply_text(error_msg)
        secure_memory.add_message(user_id, "assistant", error_msg)

# Handler de alertas con validación
@require_auth
@rate_limit
async def alertas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Obtener alertas del usuario
    alerts = secure_memory.get_user_alerts(user_id, active_only=True)
    
    if not alerts:
        keyboard = [[InlineKeyboardButton("➕ Crear Alerta", callback_data=f"{ACTION_PREFIX}create_alert")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔔 No tienes alertas activas.\n\n"
            "Las alertas te notificarán cuando se cumplan ciertas condiciones de precio o indicadores técnicos.",
            reply_markup=reply_markup
        )
        return VIEWING_ALERTS
    
    # Mostrar alertas existentes
    alerts_text = "🔔 **Tus alertas activas:**\n\n"
    keyboard = []
    
    for i, alert in enumerate(alerts[:10]):  # Límite de 10 para UI
        condition_text = f"{alert['symbol']} {alert['condition_type'].replace('_', ' ')} {alert['condition_value']}"
        alerts_text += f"{i+1}. {condition_text} ({alert['timeframe']})\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Eliminar {alert['symbol']}", 
                callback_data=f"{ALERT_PREFIX}delete:{alert['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Nueva Alerta", callback_data=f"{ACTION_PREFIX}create_alert")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(alerts_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return VIEWING_ALERTS

# Handler de administración (solo para admins)
@require_auth
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if not TelegramSecurityConfig.is_admin_user(user_id):
        secure_logger.safe_log("Usuario no admin intentó acceder a funciones de admin", "warning", user_id)
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return
    
    # Obtener estadísticas del sistema
    stats = rate_limiter.get_user_stats(user_id)
    
    admin_text = (
        "⚙️ **Panel de Administración**\n\n"
        f"**Estadísticas de rate limiting:**\n"
        f"• Requests último minuto: {stats['minute_requests']}\n"
        f"• Requests última hora: {stats['hour_requests']}\n"
        f"• Requests últimos 10s: {stats['burst_requests']}\n\n"
        f"**Configuración de seguridad:**\n"
        f"• Rate limit/min: {TelegramSecurityConfig.RATE_LIMIT_PER_MINUTE}\n"
        f"• Rate limit/hora: {TelegramSecurityConfig.RATE_LIMIT_PER_HOUR}\n"
                 f"• Usuarios autorizados: {'Configurado' if os.getenv('AUTHORIZED_TELEGRAM_USERS') else 'Todos'}\n"
        f"• Timeout AI: {TelegramSecurityConfig.AI_MODULE_TIMEOUT}s"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Ver Logs", callback_data=f"{ACTION_PREFIX}view_logs")],
        [InlineKeyboardButton("🧹 Limpiar DB", callback_data=f"{ACTION_PREFIX}cleanup_db")],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# Manejador de callbacks para menús
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks de los botones del menú."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Asegurarse de que el callback tenga datos
    if not query.data:
        return MAIN_MENU
    
    await query.answer()  # Responder al callback para quitar el estado de "cargando"
    
    # Manejar diferentes tipos de callbacks
    if query.data.startswith(MENU_PREFIX):
        action = query.data[len(MENU_PREFIX):]
        
        if action == "main":
            # Volver al menú principal
            return await show_main_menu(update, context)
        
        elif action == "analysis":
            # Mostrar menú de criptomonedas para análisis
            return await show_crypto_menu(update, context, for_analysis=True)
        
        elif action == "signal":
            # Mostrar menú de criptomonedas para señales
            return await show_crypto_menu(update, context, for_analysis=False)
    
    elif query.data.startswith(CRYPTO_PREFIX):
        # Extraer símbolo de criptomoneda
        symbol = query.data[len(CRYPTO_PREFIX):]
        
        # Guardar símbolo seleccionado
        context.user_data['selected_crypto'] = symbol
        
        # Verificar si es para análisis o señal
        if context.user_data.get('for_analysis', True):
            return await show_timeframe_menu(update, context, for_analysis=True)
        else:
            return await show_timeframe_menu(update, context, for_analysis=False)
    
    elif query.data.startswith(TIMEFRAME_PREFIX):
        # Extraer timeframe
        timeframe = query.data[len(TIMEFRAME_PREFIX):]
        
        # Guardar timeframe seleccionado
        context.user_data['selected_timeframe'] = timeframe
        
        # Obtener símbolo seleccionado
        symbol = context.user_data.get('selected_crypto', 'BTC')
        
        # Verificar si es para análisis o señal
        if context.user_data.get('for_analysis', True):
            # Generar análisis
            return await generate_analysis(update, context, symbol, timeframe)
        else:
            # Generar señal
            return await generate_signal(update, context, symbol, timeframe)
    
    elif query.data.startswith(ACTION_PREFIX):
        action = query.data[len(ACTION_PREFIX):]
        
        if action == "alerts":
            # Mostrar alertas
            return await show_alerts(update, context)
        
        elif action == "create_alert":
            # Iniciar flujo de creación de alerta
            return await start_alert_creation(update, context)
    
    # Si llegamos aquí, volver al menú principal
    return await show_main_menu(update, context)

# Función para mostrar el menú principal
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el menú principal."""
    query = update.callback_query
    user = update.effective_user
    
    # Crear teclado con opciones principales
    keyboard = [
        [InlineKeyboardButton("📊 Análisis", callback_data=f"{MENU_PREFIX}analysis")],
        [InlineKeyboardButton("🎯 Señales", callback_data=f"{MENU_PREFIX}signal")],
        [InlineKeyboardButton("🔔 Alertas", callback_data=f"{ACTION_PREFIX}alerts")]
    ]
    
    # Botón de administración solo para admins
    if TelegramSecurityConfig.is_admin_user(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin", callback_data=f"{ACTION_PREFIX}admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = (
        "🚀 **Crypto AI Trading Bot** 🤖\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "¡Hola! 👋 Soy tu asistente de IA especializado en análisis de criptomonedas y trading automatizado.\n\n"
        "🎯 **¿Qué puedo hacer por ti?**\n\n"
        "📈 **Análisis Técnico Avanzado:**\n"
        "• \"Analiza Bitcoin en 4h\"\n"
        "• \"¿Cómo está ETH en 1d?\"\n"
        "• \"Análisis completo de SOL\"\n\n"
        "⚡ **Señales de Trading Inteligentes:**\n"
        "• \"Dame una señal de SOL en 1h\"\n"
        "• \"Señal para BTC en 15m\"\n"
        "• \"Estrategia de scalping para ETH\"\n\n"
        "🌍 **Análisis Fundamental & Macro:**\n"
        "• \"Análisis fundamental de Bitcoin\"\n"
        "• \"Eventos macroeconómicos importantes\"\n"
        "• \"Calendario económico de esta semana\"\n"
        "• \"Impacto de la FED en crypto\"\n\n"
        "💬 **¡Escribe tu consulta o selecciona una opción del menú!**"
    )
    
    if query:
        await query.edit_message_text(welcome, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(welcome, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return MAIN_MENU

# Función para mostrar el menú de criptomonedas
async def show_crypto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, for_analysis: bool = True) -> int:
    """Muestra el menú de selección de criptomonedas."""
    query = update.callback_query
    
    # Guardar si es para análisis o señal
    context.user_data['for_analysis'] = for_analysis
    
    # Lista de criptomonedas populares
    popular_cryptos = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "DOT", "AVAX", "MATIC"]
    
    # Crear teclado con criptomonedas
    keyboard = []
    row = []
    
    for i, crypto in enumerate(popular_cryptos):
        row.append(InlineKeyboardButton(crypto, callback_data=f"{CRYPTO_PREFIX}{crypto}"))
        
        # 3 criptomonedas por fila
        if (i + 1) % 3 == 0 or i == len(popular_cryptos) - 1:
            keyboard.append(row)
            row = []
    
    # Añadir botones adicionales
    keyboard.append([InlineKeyboardButton("🔄 Más criptomonedas", callback_data=f"{CONFIG_PREFIX}more_cryptos")])
    keyboard.append([InlineKeyboardButton("⚙️ Configurar lista", callback_data=f"{CONFIG_PREFIX}config_list")])
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    title = "📊 Selecciona una criptomoneda para análisis:" if for_analysis else "🎯 Selecciona una criptomoneda para señal:"
    
    await query.edit_message_text(title, reply_markup=reply_markup)
    
    return SELECTING_CRYPTO_FOR_ANALYSIS if for_analysis else SELECTING_CRYPTO_FOR_SIGNAL

# Función para mostrar el menú de timeframes
async def show_timeframe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, for_analysis: bool = True) -> int:
    """Muestra el menú de selección de timeframes."""
    query = update.callback_query
    symbol = context.user_data.get('selected_crypto', 'BTC')
    
    # Lista de timeframes
    timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    
    # Crear teclado con timeframes
    keyboard = []
    row = []
    
    for i, tf in enumerate(timeframes):
        row.append(InlineKeyboardButton(tf, callback_data=f"{TIMEFRAME_PREFIX}{tf}"))
        
        # 4 timeframes por fila
        if (i + 1) % 4 == 0 or i == len(timeframes) - 1:
            keyboard.append(row)
            row = []
    
    # Añadir botón de volver
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}{'analysis' if for_analysis else 'signal'}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    title = f"⏱️ Selecciona un timeframe para {symbol}:"
    
    await query.edit_message_text(title, reply_markup=reply_markup)
    
    return SELECTING_TIMEFRAME_FOR_ANALYSIS if for_analysis else SELECTING_TIMEFRAME_FOR_SIGNAL

# Función para generar análisis
async def generate_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str, timeframe: str) -> int:
    """Genera un análisis para la criptomoneda y timeframe seleccionados."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Mensaje de carga
    await query.edit_message_text(f"🔍 Generando análisis para {symbol} en {timeframe}...\nEsto puede tomar unos segundos.")
    
    # Construir prompt para análisis
    prompt = f"Analiza {symbol} en {timeframe}"
    
    # Añadir mensaje del usuario al historial
    secure_memory.add_message(user_id, "user", prompt)
    
    # Construir payload seguro usando la nueva función
    payload, endpoint = await build_secure_payload(user_id, prompt)
    
    try:
        # Llamar al módulo de IA usando el mismo endpoint que simulate_bot.py
        data = await secure_ai_call(endpoint, payload, user_id)
        
        if not data:
            error_msg = "❌ Error comunicándose con el servicio de IA. Intenta de nuevo más tarde."
            await query.edit_message_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}main")]])
            )
            secure_memory.add_message(user_id, "assistant", error_msg)
            return MAIN_MENU
        
        # Procesar respuesta usando la misma lógica que simulate_bot.py
        if "analysis" in data:
            symbol_resp = data.get("symbol", symbol)
            timeframes_resp = data.get("timeframes", [timeframe])
            timeframe_resp = timeframes_resp[0] if timeframes_resp else timeframe
            current_price = data.get("current_price", 0)
            analysis = data.get("analysis", "<sin análisis>")
            
            response_text = (
                f"🧠 Análisis IA para {symbol_resp} ({timeframe_resp}):\n\n"
                f"💰 Precio actual: ${current_price}\n\n"
                f"{analysis}\n\n"
                "⚠️ No es asesoramiento financiero."
            )
        else:
            response_text = data.get("response", "No he podido procesar tu mensaje. ¿Puedes intentarlo de nuevo?")
        
        # Validar y sanitizar respuesta
        if len(response_text) > TelegramSecurityConfig.MAX_MESSAGE_LENGTH:
            response_text = response_text[:TelegramSecurityConfig.MAX_MESSAGE_LENGTH] + "..."
        
        # Añadir respuesta al historial
        secure_memory.add_message(user_id, "assistant", response_text)
        
        # Enviar respuesta con botón para volver
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data=f"{MENU_PREFIX}main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        secure_logger.safe_log(f"Análisis generado para {symbol} en {timeframe}", "info", user_id)
        
    except Exception as e:
        error_msg = "❌ Error inesperado generando el análisis."
        secure_logger.safe_log(f"Error generando análisis: {str(e)}", "error", user_id)
        
        await query.edit_message_text(
            error_msg,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}main")]])
        )
        
        secure_memory.add_message(user_id, "assistant", error_msg)
    
    return MAIN_MENU

# Función para generar señal
async def generate_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str, timeframe: str) -> int:
    """Genera una señal para la criptomoneda y timeframe seleccionados."""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.edit_message_text(f"🎯 Generando señal para {symbol} en {timeframe}...\nEsto puede tomar unos segundos.")
    prompt = f"Dame una señal de trading para {symbol} en {timeframe}"
    secure_memory.add_message(user_id, "user", prompt)
    payload, endpoint = await build_secure_payload(user_id, prompt)
    try:
        data = await secure_ai_call(endpoint, payload, user_id)
        if not data:
            error_msg = "❌ Error comunicándose con el servicio de IA. Intenta de nuevo más tarde."
            await query.edit_message_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}main")]])
            )
            secure_memory.add_message(user_id, "assistant", error_msg)
            return MAIN_MENU
        # --- NUEVO: Formato profesional ---
        if "result" in data:
            result = data["result"]
            signal_dict = {
                "symbol": result.get("symbol", symbol),
                "timeframe": result.get("timeframe", timeframe),
                "direction": result.get("signal", "-"),
                "entry": result.get("entry_price", "-"),
                "stop_loss": result.get("stop_loss", "-"),
                "take_profit_1": result.get("take_profit", "-"),
                "take_profit_2": result.get("take_profit_2", "-"),
                "confidence": result.get("confidence", "-"),
                "summary": result.get("reasoning", ""),
                "indicators": result.get("indicators", "RSI, MACD, SMA, EMA, Bollinger Bands"),
                "risk_warning": "⚠️ Recuerda: ninguna señal es garantía. Usa gestión de riesgo."
            }
            mensaje = formatear_senal_profesional(signal_dict)
            keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data=f"{MENU_PREFIX}main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            secure_memory.add_message(user_id, "assistant", mensaje)
            secure_logger.safe_log(f"Señal generada para {symbol} en {timeframe}", "info", user_id)
            return MAIN_MENU
        # --- FIN NUEVO ---
        # Fallbacks
        if "analysis" in data:
            symbol_resp = data.get("symbol", symbol)
            timeframes_resp = data.get("timeframes", [timeframe])
            timeframe_resp = timeframes_resp[0] if timeframes_resp else timeframe
            current_price = data.get("current_price", 0)
            analysis = data.get("analysis", "<sin análisis>")
            response_text = (
                f"🎯 Señal de Trading para {symbol_resp} ({timeframe_resp}):\n\n"
                f"💰 Precio actual: ${current_price}\n\n"
                f"{analysis}\n\n"
                "⚠️ No es asesoramiento financiero."
            )
        elif "signal" in data:
            response_text = data.get("signal", "")
        else:
            response_text = data.get("response", "No he podido procesar tu mensaje. ¿Puedes intentarlo de nuevo?")
        if len(response_text) > TelegramSecurityConfig.MAX_MESSAGE_LENGTH:
            response_text = response_text[:TelegramSecurityConfig.MAX_MESSAGE_LENGTH] + "..."
        secure_memory.add_message(user_id, "assistant", response_text)
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data=f"{MENU_PREFIX}main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        secure_logger.safe_log(f"Señal generada para {symbol} en {timeframe}", "info", user_id)
    except Exception as e:
        error_msg = "❌ Error inesperado generando la señal."
        secure_logger.safe_log(f"Error generando señal: {str(e)}", "error", user_id)
        await query.edit_message_text(
            error_msg,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}main")]])
        )
        secure_memory.add_message(user_id, "assistant", error_msg)
    return MAIN_MENU

# Función para mostrar alertas
async def show_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra las alertas del usuario."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Obtener alertas del usuario
    alerts = secure_memory.get_user_alerts(user_id, active_only=True)
    
    if not alerts:
        keyboard = [[InlineKeyboardButton("➕ Crear Alerta", callback_data=f"{ACTION_PREFIX}create_alert")]]
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔔 No tienes alertas activas.\n\n"
            "Las alertas te notificarán cuando se cumplan ciertas condiciones de precio o indicadores técnicos.",
            reply_markup=reply_markup
        )
        return VIEWING_ALERTS
    
    # Mostrar alertas existentes
    alerts_text = "🔔 **Tus alertas activas:**\n\n"
    keyboard = []
    
    for i, alert in enumerate(alerts[:10]):  # Límite de 10 para UI
        condition_text = f"{alert['symbol']} {alert['condition_type'].replace('_', ' ')} {alert['condition_value']}"
        alerts_text += f"{i+1}. {condition_text} ({alert['timeframe']})\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Eliminar {alert['symbol']}", 
                callback_data=f"{ALERT_PREFIX}delete:{alert['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Nueva Alerta", callback_data=f"{ACTION_PREFIX}create_alert")])
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(alerts_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return VIEWING_ALERTS

# Función para iniciar creación de alerta
async def start_alert_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de creación de una alerta."""
    query = update.callback_query
    
    # Mostrar menú de criptomonedas para alerta
    # Lista de criptomonedas populares
    popular_cryptos = ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "DOT", "AVAX", "MATIC"]
    
    # Crear teclado con criptomonedas
    keyboard = []
    row = []
    
    for i, crypto in enumerate(popular_cryptos):
        row.append(InlineKeyboardButton(crypto, callback_data=f"{CRYPTO_PREFIX}{crypto}"))
        
        # 3 criptomonedas por fila
        if (i + 1) % 3 == 0 or i == len(popular_cryptos) - 1:
            keyboard.append(row)
            row = []
    
    # Añadir botón de volver
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{ACTION_PREFIX}alerts")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("🔔 Selecciona una criptomoneda para la alerta:", reply_markup=reply_markup)
    
    return SELECTING_CRYPTO

# Error handler seguro
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors causados por Updates."""
    user_id = None
    if isinstance(update, Update) and update.effective_user:
        user_id = update.effective_user.id
    
    secure_logger.safe_log(f"Error en bot: {str(context.error)}", "error", user_id)
    
    # No exponer detalles del error al usuario
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text(
                "❌ Ha ocurrido un error interno.\n"
                "Por favor, intenta de nuevo más tarde."
            )
        except Exception:
            pass  # Evitar loops de error

def formatear_senal_profesional(signal_dict: dict) -> str:
    """Formatea la señal en un mensaje profesional, visual y educativo."""
    symbol = signal_dict.get('symbol', 'Activo')
    timeframe = signal_dict.get('timeframe', '-')
    direction = signal_dict.get('direction', '').upper()
    entry = signal_dict.get('entry', '-')
    stop = signal_dict.get('stop_loss', '-')
    tp1 = signal_dict.get('take_profit_1', '-')
    tp2 = signal_dict.get('take_profit_2', '-')
    confianza = signal_dict.get('confidence', '-')
    resumen = signal_dict.get('summary', '')
    indicadores = signal_dict.get('indicators', '')
    riesgo = signal_dict.get('risk_warning', '⚠️ Recuerda: ninguna señal es garantía. Usa gestión de riesgo.')
    mensaje = f"""
🚦 Señal de Trading ({symbol}, {timeframe})
-------------------------------------
📈 Dirección: {direction}
🎯 Entrada: {entry}
🛑 Stop Loss: {stop}
🏁 Take Profit 1: {tp1}
🏁 Take Profit 2: {tp2}

📊 Indicadores clave: {indicadores}

📝 Análisis técnico:
{resumen}

🔒 Confianza: {confianza}
{riesgo}
"""
    return mensaje.strip()

SUGGESTION_INPUT = 1001

async def sugerencias_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "✉️ Por favor, escribe tu sugerencia o comentario."
    )
    return SUGGESTION_INPUT

async def recibir_sugerencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    suggestion = update.message.text
    user_info = {
        "telegram_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "http://localhost:8000/sugerencias",
                json={"suggestion": suggestion, "user_info": user_info}
            )
        if response.status_code == 200:
            await update.message.reply_text("✅ ¡Gracias! Tu sugerencia ha sido recibida.")
        else:
            await update.message.reply_text("❌ Hubo un error al enviar tu sugerencia. Intenta más tarde.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error de conexión: {e}")
    return ConversationHandler.END

async def cancelar_sugerencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Sugerencia cancelada.")
    return ConversationHandler.END

def main() -> None:
    """Función principal del bot securizado."""
    secure_logger.safe_log("Iniciando bot de Telegram securizado", "info")
    
    # Crear aplicación
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Añadir handlers con autenticación
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alertas", alertas_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("sugerencias", sugerencias_command))

    # Handler de conversaciones
    suggestion_conv = ConversationHandler(
        entry_points=[CommandHandler("sugerencias", sugerencias_command)],
        states={
            SUGGESTION_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_sugerencia)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_sugerencia)],
    )
    app.add_handler(suggestion_conv)
    
    # Handler de callbacks para botones
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Handler de mensajes generales
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Configurar logging
    import logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    secure_logger.safe_log("Bot de Telegram securizado iniciado exitosamente", "info")
    
    # Ejecutar bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
