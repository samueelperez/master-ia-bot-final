import os
import sys
import traceback
import json
import time
import logging
import httpx
import re
import asyncio
import nest_asyncio
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta

# Aplicar parche para event loops anidados
nest_asyncio.apply()

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
from .referral_verification import referral_verifier
from .user_verification import user_verification
except ImportError:
    # Fallback para ejecución directa
    from security_config import (
        TelegramSecurityConfig, 
        TelegramRateLimiter, 
        TelegramInputValidator, 
        TelegramSecureLogger
    )
    from secure_memory_manager import SecureMemoryManager
    from referral_verification import referral_verifier
    from user_verification import user_verification

# Constantes para estados de conversación
(
    SELECTING_ACTION, SELECTING_CRYPTO, SELECTING_CONDITION_TYPE,
    ENTERING_CONDITION_VALUE, SELECTING_TIMEFRAME, CONFIRMING_ALERT,
    VIEWING_ALERTS, SELECTING_ALERT_TO_DELETE,
    MAIN_MENU, SELECTING_CRYPTO_FOR_ANALYSIS, SELECTING_CRYPTO_FOR_SIGNAL,
    SELECTING_TIMEFRAME_FOR_ANALYSIS, SELECTING_TIMEFRAME_FOR_SIGNAL,
    CONFIGURING_CRYPTO_LIST, SELECTING_CRYPTO_FOR_STRATEGY, SELECTING_STRATEGY,
    SELECTING_TIMEFRAME_FOR_STRATEGY
) = range(17)

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
STRATEGY_PREFIX = "strategy:"

# Configuración de criptomonedas disponibles
DEFAULT_CRYPTOS = {
    "BTC": {"name": "Bitcoin", "emoji": "₿"},
    "ETH": {"name": "Ethereum", "emoji": "🔹"},
    "SOL": {"name": "Solana", "emoji": "🟣"},
    "ADA": {"name": "Cardano", "emoji": "🔵"},
    "DOT": {"name": "Polkadot", "emoji": "🟡"},
    "MATIC": {"name": "Polygon", "emoji": "🟪"},
    "AVAX": {"name": "Avalanche", "emoji": "🔺"},
    "LINK": {"name": "Chainlink", "emoji": "🔗"},
    "DOGE": {"name": "Dogecoin", "emoji": "🐕"},
    "SHIB": {"name": "Shiba Inu", "emoji": "🐕‍🦺"},
    "XRP": {"name": "XRP", "emoji": "💧"},
    "ATOM": {"name": "Cosmos", "emoji": "⚛️"},
    "ALGO": {"name": "Algorand", "emoji": "◇"},
    "FTM": {"name": "Fantom", "emoji": "👻"},
    "NEAR": {"name": "NEAR Protocol", "emoji": "🌐"}
}

# Configuración de timeframes disponibles
AVAILABLE_TIMEFRAMES = {
    "1m": {"name": "1 Minuto", "emoji": "⚡"},
    "5m": {"name": "5 Minutos", "emoji": "🔥"},
    "15m": {"name": "15 Minutos", "emoji": "⏰"},
    "30m": {"name": "30 Minutos", "emoji": "🕒"},
    "1h": {"name": "1 Hora", "emoji": "📅"},
    "4h": {"name": "4 Horas", "emoji": "📈"},
    "1d": {"name": "1 Día", "emoji": "🌅"},
    "1w": {"name": "1 Semana", "emoji": "📊"}
}

# Configuración de estrategias disponibles
AVAILABLE_STRATEGIES = {
    "scalping": {"name": "Scalping", "emoji": "⚡", "description": "Operaciones rápidas en timeframes cortos"},
    "rsi": {"name": "RSI", "emoji": "📊", "description": "Análisis de sobrecompra/sobreventa"},
    "estocastico": {"name": "Estocástico", "emoji": "🎯", "description": "Oscilador de momentum"},
    "smart_money": {"name": "Smart Money", "emoji": "🧠", "description": "Conceptos de dinero inteligente"},
    "volatilidad": {"name": "Volatilidad", "emoji": "📈", "description": "Análisis de contracción de volatilidad"},
    "intradia": {"name": "Intradía", "emoji": "🌅", "description": "Operaciones dentro del día"},
    "fair_value_gap": {"name": "Fair Value Gap", "emoji": "⚖️", "description": "Gaps de valor justo"},
    "divergencia_correlacionada": {"name": "Divergencia", "emoji": "🔄", "description": "Divergencias correlacionadas"}
}

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
AI_MODULE_URL = os.getenv("AI_MODULE_URL", "http://localhost:8001")  # Puerto del AI Module actual

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en variables de entorno")

# Inicializar componentes de seguridad
rate_limiter = TelegramRateLimiter()
validator = TelegramInputValidator()
secure_logger = TelegramSecureLogger()
secure_memory = SecureMemoryManager(db_path=os.getenv("MEMORY_DB", "telegram_bot_memory_secure.db"))

secure_logger.safe_log("Bot de Telegram securizado inicializado", "info")
secure_logger.safe_log(f"AI Module URL: {AI_MODULE_URL}", "info")

# Decorador de autenticación con verificación de referidos
def require_auth(func):
    """Decorador para requerir autenticación de usuario y verificación de referidos."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Verificar autorización básica
        if not TelegramSecurityConfig.is_user_authorized(user_id):
            secure_logger.safe_log("Usuario no autorizado intentó acceder", "warning", user_id)
            
                        # Manejar tanto mensajes como callback queries
            if update.message:
                await update.message.reply_text(
                    "❌ No tienes autorización para usar este bot.\n"
                    "Contacta al administrador si crees que esto es un error."
                )
            elif update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    "❌ No tienes autorización para usar este bot.\n"
                    "Contacta al administrador si crees que esto es un error."
                )
            return
        
        # Verificar si se requiere verificación de referidos
        if user_verification.is_verification_required():
            status = user_verification.get_verification_status(user_id)
            
            # Si no está verificado, redirigir al proceso de verificación
            if not status.is_verified:
                await handle_unverified_user(update, context, status)
                return  # Solo retornar si no está verificado
        
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
                message = f"⏳ Has excedido el límite de requests.\nIntenta de nuevo en {remaining} segundos."
            else:
                message = "⚠️ Estás enviando mensajes muy rápido.\nPor favor, espera unos segundos antes de continuar."
            
            # Manejar tanto mensajes como callback queries
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(message)
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
                
                # Crear un contexto con el texto sanitizado
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
    
    # Botones principales del menú de inicio
    keyboard = [
        [
            InlineKeyboardButton("📈 Análisis", callback_data=f"{MENU_PREFIX}analysis"),
            InlineKeyboardButton("📊 Señales", callback_data=f"{MENU_PREFIX}signal"),
            InlineKeyboardButton("🧠 Estrategias", callback_data=f"{MENU_PREFIX}strategy")
        ],
        [
            InlineKeyboardButton("🔔 Alertas", callback_data=f"{ACTION_PREFIX}alerts")
        ]
    ]
    # Botón de administración solo para admins
    if TelegramSecurityConfig.is_admin_user(user.id):
        keyboard.append([InlineKeyboardButton("🛠️ Admin", callback_data=f"{ACTION_PREFIX}admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = (
        "🚀 **Crypto AI Trading Bot** 🤖\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "¡Hola! 👋 Soy tu **asistente de IA especializado** en análisis de criptomonedas y trading automatizado.\n\n"
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
    Llamada segura al módulo de IA con timeouts y retry logic.
    """
    if not httpx:
        secure_logger.safe_log("httpx no está instalado", "error")
        return None
    
    url = f"{AI_MODULE_URL}/{endpoint}"
    max_retries = 3
    
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
                
                # Llamada principal con headers de autorización
                api_secret = "cr1nW3IDA-CQlkm6XBIoIdZmqv9mLj6U_-1z0ttyOZ4"
                headers = {
                    "Authorization": f"Bearer {api_secret}",
                    "Content-Type": "application/json"
                }
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                secure_logger.safe_log(f"Llamada exitosa a {endpoint}", "info", user_id)
                return response.json()
                
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

def is_crypto_related_query(text: str) -> bool:
    """
    Filtro SIMPLE: Solo permite consultas explícitamente de criptomonedas.
    """
    if not text or len(text.strip()) == 0:
        return False
        
    text_lower = text.lower().strip()
    
    # Lista corta y específica de términos permitidos
    allowed_terms = [
        # Cryptos principales
        "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "ada", "doge", "shib", 
        "matic", "avax", "link", "xrp", "bnb", "atom", "dot",
        
        # Términos crypto únicos
        "crypto", "criptomoneda", "cryptocurrency", "blockchain", "defi", "staking",
        "halving", "fork", "wallet", "exchange", "mining", "airdrop",
        
        # Trading crypto específico
        "trading crypto", "señal crypto", "análisis crypto", "precio crypto",
        "mercado crypto", "chart crypto", "gráfico crypto",
        
        # Eventos económicos crypto-específicos
        "fomc", "decisión de la fed", "etf bitcoin", "regulación crypto",
        "calendario económico", "eventos económicos", "datos económicos"
    ]
    
    # REGLA SIMPLE: Debe contener AL MENOS un término permitido
    for term in allowed_terms:
        if term in text_lower:
            return True
    
    # Casos especiales: análisis/trading/precio + contexto crypto
    analysis_words = ["analiza", "análisis", "precio", "trading", "señal", "mercado"]
    crypto_context = ["bitcoin", "btc", "eth", "crypto", "coin", "token"]
    
    has_analysis = any(word in text_lower for word in analysis_words)
    has_crypto_context = any(word in text_lower for word in crypto_context)
    
    if has_analysis and has_crypto_context:
        return True
    
    # Rechazar todo lo demás
    return False

# Función de construcción segura de payload
def build_secure_payload(user_id: int, text: str) -> Dict[str, Any]:
    """Construye payload de forma segura."""
    # Sanitizar texto
    sanitized_text = validator.sanitize_message(text)
    
    # Extraer símbolo y timeframe del prompt
    symbol = "BTC"  # Valor por defecto
    timeframes = ["1d"]  # Valor por defecto

    # Detectar símbolo con mapeo de nombres completos
    symbol_mapping = {
        "bitcoin": "BTC", "btc": "BTC",
        "ethereum": "ETH", "eth": "ETH",
        "cardano": "ADA", "ada": "ADA",
        "polkadot": "DOT", "dot": "DOT",
        "solana": "SOL", "sol": "SOL",
        "polygon": "MATIC", "matic": "MATIC",
        "avalanche": "AVAX", "avax": "AVAX",
        "chainlink": "LINK", "link": "LINK",
        "dogecoin": "DOGE", "doge": "DOGE",
        "shiba": "SHIB", "shib": "SHIB",
        "ripple": "XRP", "xrp": "XRP",
        "jasmy": "JASMY", "jasmy": "JASMY",
        "pepe": "PEPE", "pepe": "PEPE",
        "bonk": "BONK", "bonk": "BONK",
        "wif": "WIF", "wif": "WIF",
        "floki": "FLOKI", "floki": "FLOKI",
        "bome": "BOME", "bome": "BOME",
        "meme": "MEME", "meme": "MEME",
        "book": "BOOK", "book": "BOOK",
        "popcat": "POPCAT", "popcat": "POPCAT"
    }
    
    # Buscar coincidencias exactas primero
    for name, sym in symbol_mapping.items():
        if name in sanitized_text.lower():
            symbol = sym
            break
    else:
        # Fallback: buscar símbolos de 3-4 letras
    common_symbols = ["BTC", "ETH", "ADA", "DOT", "SOL", "MATIC", "AVAX", "LINK", "DOGE", "SHIB", "XRP"]
    for s in common_symbols:
        if s.lower() in sanitized_text.lower():
            symbol = s
            break

    # Detectar timeframe
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

    # Detectar si es una solicitud de señal específica
    signal_keywords = ["dame una señal", "señal de trading", "señal para", "dame señal", 
                      "generar señal", "necesito una señal", "quiero una señal"]
    is_signal_request = any(keyword in sanitized_text.lower() for keyword in signal_keywords)
    
    # Si es solicitud de señal, usar endpoint /signal
    if is_signal_request:
        signal_payload = {
            "symbol": symbol,
            "timeframe": detected_timeframe if detected_timeframe else "1d"
        }
        return signal_payload, "signal"
    
    # Detectar si es una solicitud de scalping específica (sin ser señal)
    scalping_keywords = ["scalping", "recomendación", "compra", "vende", "entrada", "stop loss", "take profit"]
    is_scalping_request = any(keyword in sanitized_text.lower() for keyword in scalping_keywords)
    
    # Si es solicitud de scalping, usar endpoint /generate con prompt específico
    if is_scalping_request and detected_timeframe in ["1m", "5m", "15m", "30m"]:
        timeframe_str = detected_timeframe if detected_timeframe else "5m"
        
        # Crear prompt específico para scalping
        scalping_prompt = f"""Eres un trader experto en scalping de criptomonedas. Necesito una recomendación específica para {symbol} en timeframe {timeframe_str}.

RESPONDE EXACTAMENTE EN ESTE FORMATO:

🎯 RECOMENDACIÓN SCALPING {symbol}/{timeframe_str}
💰 Precio actual: $[precio]

📊 DECISIÓN: [COMPRAR/VENDER/ESPERAR]

🎯 NIVELES:
• Entrada: $[precio]
• Stop Loss: $[precio] 
• Take Profit: $[precio]

⏱️ Duración estimada: [tiempo]

💡 Razón: [explicación técnica breve]

⚠️ Riesgo: [alto/medio/bajo]

NO des análisis general, solo la recomendación específica."""

        # Payload para endpoint /generate
        payload = {
            "symbol": symbol,
            "timeframes": [timeframe_str],
            "user_prompt": scalping_prompt
        }
        
        return payload, "generate"  # Retornar también el tipo de endpoint
    
    # Construir payload básico para análisis general
    payload = {
        "prompt": sanitized_text,
        "user_context": f"user_{user_id}",  # No exponer ID real
        "conversation_history": []
    }
    
    # Obtener historial de conversación de forma segura
    try:
        history = secure_memory.get_conversation_history(user_id, limit=5)
        # Filtrar solo contenido, no metadata
        payload["conversation_history"] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]
    except Exception as e:
        secure_logger.safe_log(f"Error obteniendo historial: {str(e)}", "warning", user_id)
    
    return payload, "generate"  # Retornar también el tipo de endpoint

# Funciones auxiliares para gestión de configuración de usuario
def get_user_cryptos(user_id: int) -> List[str]:
    """Obtiene la lista personalizada de criptomonedas del usuario."""
    try:
        user_config = secure_memory.get_user_config(user_id)
        if user_config and user_config.get('favorite_cryptos'):
            return user_config['favorite_cryptos']
    except:
        pass
    # Retornar top 8 por defecto
    return list(DEFAULT_CRYPTOS.keys())[:8]

def set_user_cryptos(user_id: int, crypto_list: List[str]) -> bool:
    """Establece la lista personalizada de criptomonedas del usuario."""
    try:
        # Validar que todas las criptos existen
        valid_cryptos = [crypto for crypto in crypto_list if crypto in DEFAULT_CRYPTOS]
        if len(valid_cryptos) < len(crypto_list):
            return False
        
        user_config = secure_memory.get_user_config(user_id) or {}
        user_config['favorite_cryptos'] = valid_cryptos[:15]  # Límite de 15
        secure_memory.set_user_config(user_id, user_config)
        return True
    except:
        return False

def get_user_timeframes(user_id: int) -> List[str]:
    """Obtiene la lista de timeframes preferidos del usuario."""
    try:
        user_config = secure_memory.get_user_config(user_id)
        if user_config and user_config.get('favorite_timeframes'):
            return user_config['favorite_timeframes']
    except:
        pass
    # Retornar timeframes comunes por defecto
    return ["5m", "15m", "1h", "4h", "1d"]

def create_crypto_keyboard(user_id: int, prefix: str, page: int = 0) -> List[List[InlineKeyboardButton]]:
    """Crea teclado con criptomonedas del usuario."""
    user_cryptos = get_user_cryptos(user_id)
    
    # Paginación: 6 por página
    items_per_page = 6
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_cryptos = user_cryptos[start_idx:end_idx]
    
    keyboard = []
    # Crear filas de 2 botones
    for i in range(0, len(page_cryptos), 2):
        row = []
        for j in range(2):
            if i + j < len(page_cryptos):
                crypto = page_cryptos[i + j]
                crypto_info = DEFAULT_CRYPTOS[crypto]
                button = InlineKeyboardButton(
                    f"{crypto_info['emoji']} {crypto}",
                    callback_data=f"{prefix}{crypto}"
                )
                row.append(button)
        keyboard.append(row)
    
    # Botones de navegación si hay más páginas
    nav_row = []
    total_pages = (len(user_cryptos) + items_per_page - 1) // items_per_page
    
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{prefix}page_{page-1}"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"{prefix}page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Botones de configuración y volver
    config_row = [
        InlineKeyboardButton("✏️ Personalizar", callback_data=f"{CONFIG_PREFIX}cryptos"),
        InlineKeyboardButton("🔙 Menú", callback_data=f"{MENU_PREFIX}main")
    ]
    keyboard.append(config_row)
    
    return keyboard

def create_timeframe_keyboard(selected_crypto: str, action_type: str = "analysis") -> List[List[InlineKeyboardButton]]:
    """Crea teclado de selección de timeframes."""
    keyboard = []
    
    # Crear filas de 2 timeframes
    timeframes = list(AVAILABLE_TIMEFRAMES.keys())
    for i in range(0, len(timeframes), 2):
        row = []
        for j in range(2):
            if i + j < len(timeframes):
                tf = timeframes[i + j]
                tf_info = AVAILABLE_TIMEFRAMES[tf]
                button = InlineKeyboardButton(
                    f"{tf_info['emoji']} {tf_info['name']}",
                    callback_data=f"{TIMEFRAME_PREFIX}{action_type}_{selected_crypto}_{tf}"
                )
                row.append(button)
        keyboard.append(row)
    
    # Botón de volver basado en el tipo de acción
    back_menu = "analysis" if action_type == "analysis" else "signal"
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}{back_menu}")])
    
    return keyboard

def create_strategy_keyboard(selected_crypto: str) -> List[List[InlineKeyboardButton]]:
    """Crear teclado para selección de estrategias."""
    keyboard = []
    row = []
    
    for i, (strategy_key, strategy_info) in enumerate(AVAILABLE_STRATEGIES.items()):
        emoji = strategy_info["emoji"]
        name = strategy_info["name"]
        
        button = InlineKeyboardButton(
            f"{emoji} {name}",
            callback_data=f"{STRATEGY_PREFIX}{strategy_key}:{selected_crypto}"
        )
        
        row.append(button)
        
        # Crear nueva fila cada 2 botones
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Agregar fila incompleta si existe
    if row:
        keyboard.append(row)
    
    # Botón de volver
    keyboard.append([
        InlineKeyboardButton("🔙 Volver", callback_data=f"{CRYPTO_PREFIX}back_to_crypto")
    ])
    
    return keyboard

def create_timeframe_for_strategy_keyboard(selected_crypto: str, selected_strategy: str) -> List[List[InlineKeyboardButton]]:
    """Crear teclado para selección de timeframe para estrategia."""
    keyboard = []
    row = []
    
    for i, (tf_key, tf_info) in enumerate(AVAILABLE_TIMEFRAMES.items()):
        emoji = tf_info["emoji"]
        name = tf_info["name"]
        
        # Asegurar que el callback tenga el formato correcto: timeframe:strategy:5m:ETH:rsi
        callback_data = f"{TIMEFRAME_PREFIX}strategy:{tf_key}:{selected_crypto}:{selected_strategy}"
        
        button = InlineKeyboardButton(
            f"{emoji} {name}",
            callback_data=callback_data
        )
        
        row.append(button)
        
        # Crear nueva fila cada 2 botones
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Agregar fila incompleta si existe
    if row:
        keyboard.append(row)
    
    # Botón de volver
    keyboard.append([
        InlineKeyboardButton("🔙 Volver", callback_data=f"{STRATEGY_PREFIX}back_to_strategy:{selected_crypto}")
    ])
    
    return keyboard

def format_trading_signal(symbol, signal, entry_price, stop_loss, take_profit, confidence, reasoning, timeframe, found_timeframe=None, multi_timeframe=False):
    """Formatea la señal de trading en formato profesional y uniforme."""
    emoji = "🚀" if signal == "LONG" else "📉" if signal == "SHORT" else "⚖️"
    direction_emoji = "📈" if signal == "LONG" else "📉" if signal == "SHORT" else "⚖️"
    
    # Calcular porcentajes de riesgo y ratio R/R
    if signal == "LONG":
        risk_amount = entry_price - stop_loss
        reward_amount = take_profit - entry_price
        risk_percent = (risk_amount / entry_price) * 100
    else:  # SHORT
        risk_amount = stop_loss - entry_price
        reward_amount = entry_price - take_profit
        risk_percent = (risk_amount / entry_price) * 100
    
    rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
    
    # Calcular calidad de la señal
    quality_score = 0
    if confidence > 0.7:
        quality_score += 2
    elif confidence > 0.4:
        quality_score += 1
    
    if rr_ratio >= 2.0:
        quality_score += 2
    elif rr_ratio >= 1.5:
        quality_score += 1
    
    if risk_percent >= 2.0:
        quality_score += 1
    
    quality_text = "✅ EXCELENTE" if quality_score >= 4 else "✅ BUENA" if quality_score >= 2 else "⚠️ REGULAR"
    
    # Extraer análisis técnico relevante y limpiarlo
    analysis_text = "Análisis técnico basado en indicadores como RSI, MACD, SMA, EMA y bandas de Bollinger."
    if reasoning:
        # Limpiar el texto de análisis
        clean_reasoning = reasoning.replace('\n', ' ').replace('  ', ' ').strip()
        # Extraer solo la parte relevante (primeras 200 caracteres)
        if len(clean_reasoning) > 200:
            clean_reasoning = clean_reasoning[:200] + "..."
        analysis_text = clean_reasoning
    
    # Agregar información sobre el timeframe encontrado si se probaron múltiples
    timeframe_info = ""
    if found_timeframe and multi_timeframe and found_timeframe != timeframe:
        timeframe_info = f"\n🔍 Mejor oportunidad encontrada: {symbol} en {found_timeframe}"
    
    # Determinar el timeframe a mostrar
    display_timeframe = found_timeframe if found_timeframe and isinstance(found_timeframe, str) else timeframe
    
    return (
        f"{emoji} **{symbol}/USDT - SEÑAL {display_timeframe.upper()}**\n\n"
        f"📊 **DIRECCIÓN:** {direction_emoji} {signal}\n"
        f"💰 **ENTRADA:** ${entry_price:,.2f}\n"
        f"🛑 **STOP LOSS:** ${stop_loss:,.2f} ({risk_percent:.1f}% riesgo)\n"
        f"🎯 **TAKE PROFIT:** ${take_profit:,.2f}\n"
        f"⚡ **R/R:** {rr_ratio:.2f}\n\n"
        f"💡 **ANÁLISIS:**\n{analysis_text}\n\n"
        f"📈 **CALIDAD:** {quality_text}\n"
        f"🔥 **CONFIANZA:** {confidence:.2f}{timeframe_info}\n\n"
        f"⚠️ No es asesoramiento financiero"
    )

# Procesar mensaje con validación y seguridad
async def try_multiple_timeframes(payload: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
    """Prueba múltiples timeframes hasta encontrar una señal válida."""
    timeframes_to_try = payload.get("timeframes_to_try", ["5m", "15m", "1h", "30m", "4h", "1d"])
    symbol = payload.get("symbol", "BTC")
    
    secure_logger.safe_log(f"Probando múltiples timeframes para {symbol}: {timeframes_to_try}", "info", user_id)
    
    for tf in timeframes_to_try:
        try:
            # Crear payload para este timeframe específico
            test_payload = {
                "strategy_type": payload.get("strategy_type", "scalping"),
                "symbol": symbol,
                "timeframe": tf,
                "user_id": payload.get("user_id", str(user_id))
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
            "strategy_type": payload.get("strategy_type", "scalping"),
            "symbol": symbol,
            "timeframe": timeframes_to_try[-1],
            "user_id": payload.get("user_id", str(user_id))
        }
        return await secure_ai_call("advanced-strategy", fallback_payload, user_id)
    except:
        return None

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

    # --- Clasificación automática mejorada ---
    # Detectar directamente si el usuario quiere una señal
    text_lower = text.lower()
    
    # Palabras clave para detectar solicitud de señal específica
    signal_keywords = ["señal", "signal", "dame", "quiero", "necesito", "busco"]
    crypto_keywords = ["btc", "bitcoin", "eth", "ethereum", "sol", "solana", "ada", "cardano"]
    timeframe_keywords = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    
    # Detectar si es una solicitud de señal específica
    is_signal_request = any(keyword in text_lower for keyword in signal_keywords)
    
    # Detectar si menciona indicadores técnicos específicos
    technical_indicators = ["rsi", "macd", "bollinger", "sma", "ema", "estocástico", "stochastic", "fibonacci"]
    has_technical_indicators = any(indicator in text_lower for indicator in technical_indicators)
    
    # Si menciona indicadores técnicos, es muy probable que quiera una señal
    if has_technical_indicators:
        is_signal_request = True
    
    # Detectar si es una solicitud de análisis general
    # "analiza bitcoin" = análisis general, NO señal específica
    is_analysis_request = "analiza" in text_lower or "analyze" in text_lower
    
    # Si es análisis general, NO es señal específica
    if is_analysis_request:
        is_signal_request = False
    
    # Extraer símbolo con mapeo correcto
    symbol = "BTC"  # Default
    
    # Mapeo de nombres completos a símbolos
    symbol_mapping = {
        "bitcoin": "BTC", "btc": "BTC",
        "ethereum": "ETH", "eth": "ETH",
        "cardano": "ADA", "ada": "ADA",
        "polkadot": "DOT", "dot": "DOT",
        "solana": "SOL", "sol": "SOL",
        "polygon": "MATIC", "matic": "MATIC",
        "avalanche": "AVAX", "avax": "AVAX",
        "chainlink": "LINK", "link": "LINK",
        "dogecoin": "DOGE", "doge": "DOGE",
        "shiba": "SHIB", "shib": "SHIB",
        "ripple": "XRP", "xrp": "XRP",
        "jasmy": "JASMY", "jasmy": "JASMY",
        "pepe": "PEPE", "pepe": "PEPE",
        "bonk": "BONK", "bonk": "BONK",
        "wif": "WIF", "wif": "WIF",
        "floki": "FLOKI", "floki": "FLOKI",
        "bome": "BOME", "bome": "BOME",
        "meme": "MEME", "meme": "MEME",
        "book": "BOOK", "book": "BOOK",
        "popcat": "POPCAT", "popcat": "POPCAT"
    }
    
    # Buscar coincidencias exactas primero
    for name, sym in symbol_mapping.items():
        if name in text_lower:
            symbol = sym
            break
    else:
        # Fallback: buscar símbolos de 3-4 letras
        common_symbols = ["BTC", "ETH", "ADA", "DOT", "SOL", "MATIC", "AVAX", "LINK", "DOGE", "SHIB", "XRP"]
        for s in common_symbols:
            if s.lower() in text_lower:
                symbol = s
            break
    
    # Extraer timeframe - buscar el más específico (más corto primero)
    timeframe = "1h"  # Default
    detected_timeframes = []
    
    # Primero buscar timeframes exactos
    for tf in timeframe_keywords:
        if tf in text_lower:
            detected_timeframes.append(tf)
    
    # Si no se encontraron timeframes exactos, buscar palabras descriptivas
    if not detected_timeframes:
        if "minuto" in text_lower or "minutos" in text_lower:
            # Detectar número específico de minutos
            if "5" in text_lower and ("5 minuto" in text_lower or "5 minutos" in text_lower):
                detected_timeframes.append("5m")
            elif "15" in text_lower and ("15 minuto" in text_lower or "15 minutos" in text_lower):
                detected_timeframes.append("15m")
            elif "30" in text_lower and ("30 minuto" in text_lower or "30 minutos" in text_lower):
                detected_timeframes.append("30m")
            else:
                detected_timeframes.append("5m")  # Default para minutos
        elif "hora" in text_lower or "horas" in text_lower:
            if "4" in text_lower and ("4 hora" in text_lower or "4 horas" in text_lower):
                detected_timeframes.append("4h")
            else:
                detected_timeframes.append("1h")  # Default para horas
        elif "día" in text_lower or "dias" in text_lower or "diario" in text_lower:
            detected_timeframes.append("1d")
        elif "semana" in text_lower or "semanas" in text_lower:
            detected_timeframes.append("1w")
    
    # Si se detectaron múltiples timeframes, elegir el más específico (más corto)
    if detected_timeframes:
        # Ordenar por especificidad: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
        timeframe_order = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
        timeframe = min(detected_timeframes, key=lambda x: timeframe_order.index(x))
    
    # Detectar si se especificó una criptomoneda
    crypto_specified = symbol != "BTC"  # Si se detectó un símbolo específico
    
    # Construir payload seguro
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy_name": "scalping",
        "request_id": f"signal_{user_id}_{int(datetime.now().timestamp())}",
        "current_price": 0,  # Se obtendrá del AI Module
        "timestamp": datetime.now().isoformat(),
        "crypto_specified": crypto_specified
    }
    
    # Determinar endpoint según el tipo de solicitud
    if is_signal_request:
        endpoint = "advanced-strategy"
    else:
        # Para análisis general, usar el endpoint /generate
        endpoint = "generate"
        # Actualizar payload para análisis general
        payload = {
            "prompt": text,
            "symbol": symbol,
            "timeframes": [timeframe],
            "user_id": str(user_id)
        }
    
    secure_logger.safe_log(f"Procesando (IA): {text[:50]}... (endpoint: {endpoint})", "info", user_id)

    try:
        # Si es una solicitud de señal
        if endpoint == "advanced-strategy" and is_signal_request:
            # Enviar mensaje de "buscando señal"
            searching_message = await update.message.reply_text("Buscando la mejor señal...🧠")
            
            try:
                # Si no se especificó una criptomoneda, analizar top 3
                if not crypto_specified:
                    data = await try_multiple_cryptos_and_timeframes(user_id, text)
                else:
                    # Si se especificó una criptomoneda, probar múltiples timeframes
                    data = await try_multiple_timeframes(payload, user_id)
                
                # Eliminar mensaje de "buscando señal"
                await searching_message.delete()
            except Exception as search_error:
                # Eliminar mensaje de "buscando señal" en caso de error
                try:
                    await searching_message.delete()
                except:
                    pass
                raise search_error
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
        elif "analysis" in data:
            # Respuesta de análisis - mismo formato que simulate_bot.py
            symbol = data.get("symbol", "Crypto")
            timeframes = data.get("timeframes", ["1d"])
            timeframe = timeframes[0] if timeframes else "1d"
            current_price = data.get("current_price", 0)
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
            
            # Validar tipo de signal antes de usar .upper()
            if not isinstance(signal, str):
                signal = str(signal) if signal is not None else "-"
            
            # Si la señal es NEUTRAL o no hay oportunidad, mostrar mensaje simple
            if signal.upper() in ["NEUTRAL", "NONE", "-"]:
                # Si se analizaron múltiples cryptos, mostrar información adicional
                crypto_analysis_info = ""
                if not crypto_specified:
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
                
                # Formatear precios
                entry_str = f"${entry:,.2f}" if isinstance(entry, (int, float)) else str(entry)
                stop_str = f"${stop:,.2f}" if isinstance(stop, (int, float)) else str(stop)
                take_str = f"${take:,.2f}" if isinstance(take, (int, float)) else str(take)
                
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
                
                # Validar y ajustar stop loss mínimo según timeframe
                timeframe_to_show = data.get('found_timeframe', data.get('timeframe', '5m'))
                min_stop_percentage = 0.5  # 0.5% para timeframes cortos
                
                if timeframe_to_show in ['15m', '30m', '1h', '4h', '1d']:
                    min_stop_percentage = 1.0  # 1% para timeframes mayores
                elif timeframe_to_show in ['4h', '1d']:
                    min_stop_percentage = 1.5  # 1.5% para timeframes largos
                
                # Ajustar stop loss si es muy cercano
                try:
                    if isinstance(entry, (int, float)) and isinstance(stop, (int, float)):
                        current_stop_percentage = abs((entry - stop) / entry * 100)
                        if current_stop_percentage < min_stop_percentage:
                            # Ajustar stop loss
                            if signal.upper() == "LONG":
                                stop = entry * (1 - min_stop_percentage / 100)
                            elif signal.upper() == "SHORT":
                                stop = entry * (1 + min_stop_percentage / 100)
                            
                            # Recalcular take profit para mantener ratio R/R mínimo
                            if isinstance(take, (int, float)):
                                if signal.upper() == "LONG":
                                    new_risk = entry - stop
                                    take = entry + (new_risk * 1.5)  # Ratio mínimo 1.5
                                elif signal.upper() == "SHORT":
                                    new_risk = stop - entry
                                    take = entry - (new_risk * 1.5)  # Ratio mínimo 1.5
                except:
                    pass
                
                # Calcular ratio riesgo/beneficio
                try:
                    if isinstance(entry, (int, float)) and isinstance(stop, (int, float)) and isinstance(take, (int, float)):
                        risk = abs(entry - stop)
                        reward = abs(entry - take)
                        risk_reward = f"{reward/risk:.2f}" if risk > 0 else "0.00"
        else:
                        risk_reward = "0.80"
                except:
                    risk_reward = "0.80"
                
                # Formatear análisis - limpiar y simplificar
                if reasoning and reasoning != "-":
                    # Extraer solo la parte útil del análisis
                    if "REASONING:" in reasoning:
                        analysis_parts = reasoning.split("REASONING:")
                        if len(analysis_parts) > 1:
                            analysis_text = analysis_parts[1].strip()
                        else:
                            analysis_text = reasoning
                    else:
                        analysis_text = reasoning
                    
                    # Limitar longitud y limpiar
                    if len(analysis_text) > 200:
                        analysis_text = analysis_text[:200] + "..."
                else:
                    analysis_text = "Análisis técnico basado en múltiples indicadores."
                
                # Formatear confianza
                confidence_text = "Alta" if isinstance(confidence, (int, float)) and confidence > 0.7 else "Media"
                
                # Formato profesional y visual
                symbol_to_show = data.get('found_crypto', data.get('symbol', 'BTC'))
                timeframe_to_show = data.get('found_timeframe', data.get('timeframe', '5m'))
                
                # Si se analizaron múltiples cryptos, mostrar información adicional
                multi_crypto_info = ""
                if not crypto_specified and data.get('found_crypto'):
                    multi_crypto_info = f"\n🔍 **Mejor oportunidad encontrada:** {data.get('found_crypto')} en {data.get('found_timeframe', '5m')}\n"
                    if data.get('score'):
                        multi_crypto_info += f"📊 **Score:** {data.get('score'):.2f}\n"
                
                # Calcular porcentaje de riesgo
                try:
                    if isinstance(entry, (int, float)) and isinstance(stop, (int, float)):
                        risk_percentage = abs((entry - stop) / entry * 100)
                        risk_percentage_str = f"{risk_percentage:.1f}%"
                    else:
                        risk_percentage_str = "N/A"
                except:
                    risk_percentage_str = "N/A"
                
                # Evaluar calidad de la señal basada en ratio R/R
                signal_quality = ""
                if isinstance(risk_reward, str) and risk_reward != "0.00":
                    try:
                        rr_value = float(risk_reward)
                        if rr_value >= 2.0:
                            signal_quality = "🔥 EXCELENTE"
                        elif rr_value >= 1.5:
                            signal_quality = "✅ BUENA"
                        else:
                            signal_quality = "⚠️ RIESGOSA"
                    except:
                        signal_quality = "✅ BUENA"
                else:
                    signal_quality = "⚠️ RIESGOSA"
                
                # Formatear precios actualizados
                entry_str = f"${entry:,.2f}" if isinstance(entry, (int, float)) else str(entry)
                stop_str = f"${stop:,.2f}" if isinstance(stop, (int, float)) else str(stop)
                take_str = f"${take:,.2f}" if isinstance(take, (int, float)) else str(take)
                
                # Calcular porcentaje de riesgo actualizado
                try:
                    if isinstance(entry, (int, float)) and isinstance(stop, (int, float)):
                        risk_percentage = abs((entry - stop) / entry * 100)
                        risk_percentage_str = f"{risk_percentage:.1f}%"
                    else:
                        risk_percentage_str = "N/A"
                except:
                    risk_percentage_str = "N/A"
                
                response_text = (
                    f"🚀 **{symbol_to_show}/USDT - SEÑAL {timeframe_to_show}**\n\n"
                    f"📊 **DIRECCIÓN:** {signal_emoji} {signal_text}\n"
                    f"💰 **ENTRADA:** {entry_str}\n"
                    f"🛑 **STOP LOSS:** {stop_str} ({risk_percentage_str} riesgo)\n"
                    f"🎯 **TAKE PROFIT:** {take_str}\n"
                    f"⚡ **R/R:** {risk_reward}\n\n"
                    f"💡 **ANÁLISIS:**\n{analysis_text}\n\n"
                    f"📈 **CALIDAD:** {signal_quality}\n"
                    f"🔥 **CONFIANZA:** {confidence_text}\n"
                    f"{multi_crypto_info}\n"
                    f"⚠️ *No es asesoramiento financiero*"
                )
        else:
            # Respuesta genérica
            response_text = data.get("message", "No he podido procesar tu solicitud. ¿Puedes intentarlo de nuevo?")

        # Enviar respuesta
        try:
        await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as parse_error:
            # Si falla el parsing de Markdown, enviar sin formato
            secure_logger.safe_log(f"Error parsing Markdown, sending without format: {str(parse_error)}", "warning", user_id)
            await update.message.reply_text(response_text)
        
        secure_memory.add_message(user_id, "assistant", response_text)
        secure_logger.safe_log("Mensaje procesado exitosamente", "info", user_id)

    except Exception as e:
        error_msg = f"❌ Error inesperado procesando tu solicitud."
        await update.message.reply_text(error_msg)
        secure_logger.safe_log(f"Error procesando mensaje: {str(e)}", "error", user_id)
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
    
    # Obtener estadísticas de verificación si está habilitada
    verification_stats = ""
    if user_verification.is_verification_required():
        v_stats = user_verification.get_verification_stats()
        verification_stats = (
            f"\n**Estadísticas de Verificación:**\n"
            f"• Total usuarios: {v_stats['total_users']}\n"
            f"• Usuarios verificados: {v_stats['verified_users']}\n"
            f"• Usuarios pendientes: {v_stats['pending_users']}\n"
            f"• Tasa de verificación: {v_stats['verification_rate']:.1f}%\n"
            f"• Intentos fallidos 24h: {v_stats['failed_attempts_24h']}\n"
        )
        
        if v_stats['exchange_stats']:
            verification_stats += f"• Exchanges usados: {', '.join(v_stats['exchange_stats'].keys())}\n"
    else:
        verification_stats = f"\n**Verificación de referidos:** Deshabilitada\n"
    
    admin_text = (
        "⚙️ **Panel de Administración**\n\n"
        f"**Estadísticas de rate limiting:**\n"
        f"• Requests último minuto: {stats['minute_requests']}\n"
        f"• Requests última hora: {stats['hour_requests']}\n"
        f"• Requests últimos 10s: {stats['burst_requests']}\n"
        f"{verification_stats}\n"
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

# Handler de callbacks de botones
@require_auth
@rate_limit
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los callbacks de los botones del menú."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Confirmar el callback inmediatamente y capturar errores de queries viejas
    try:
        await query.answer()
    except Exception as e:
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            # Ignorar callbacks viejos
            secure_logger.safe_log(f"Callback viejo ignorado: {str(e)[:100]}", "debug", user_id)
            return
        else:
            # Otros errores sí son importantes
            secure_logger.safe_log(f"Error en callback answer: {str(e)}", "error", user_id)
            return
    
    callback_data = query.data
    secure_logger.safe_log(f"Callback recibido: {callback_data}", "info", user_id)
    
    try:
        # Verificar autorización básica primero
        if not TelegramSecurityConfig.is_user_authorized(user_id):
            secure_logger.safe_log("Usuario no autorizado intentó usar callback", "warning", user_id)
            try:
                await query.edit_message_text(
                    "❌ No tienes autorización para usar este bot.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass  # Ignorar errores de edición de mensajes viejos
            return
        

            
        # Verificar si el usuario está verificado para otros comandos
        if user_verification.is_verification_required():
            status = user_verification.get_verification_status(user_id)
            if not status.is_verified:
                try:
                    await query.edit_message_text(
                        "🔒 **Acceso Restringido**\n\n"
                        "Necesitas verificar tu cuenta antes de usar el bot.\n"
                        "Usa /start para iniciar el proceso de verificación.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass  # Ignorar errores de edición
                return
        
        # Verificar rate limiting
        allowed, rate_info = rate_limiter.is_allowed(user_id)
        if not allowed:
            try:
                if rate_info.get("blocked"):
                    remaining = rate_info.get("remaining_seconds", 0)
                    await query.edit_message_text(
                        f"⏳ Has excedido el límite de requests.\n"
                        f"Intenta de nuevo en {remaining} segundos."
                    )
                else:
                    await query.edit_message_text(
                        "⚠️ Estás enviando mensajes muy rápido.\n"
                        "Por favor, espera unos segundos antes de continuar."
                    )
            except:
                pass  # Ignorar errores de edición
            return
        
        # Manejo de verificación de referidos
        if callback_data.startswith(f"{MENU_PREFIX}analysis"):
            # Menú de análisis con criptomonedas personalizadas
            keyboard = create_crypto_keyboard(user_id, f"{ANALYSIS_PREFIX}", 0)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📊 **Selecciona la criptomoneda para analizar:**\n\n"
                "💡 Tip: Personaliza tu lista con el botón \"✏️ Personalizar\"\n"
                "📝 O escribe: \"Analiza [moneda] en [tiempo]\"",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif callback_data.startswith(f"{MENU_PREFIX}signal"):
            # Menú de señales con criptomonedas personalizadas
            keyboard = create_crypto_keyboard(user_id, f"{SIGNAL_PREFIX}", 0)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🎯 **Selecciona una criptomoneda para señal:**\n\n"
                "💡 Tip: Personaliza tu lista con el botón \"✏️ Personalizar\"\n"
                "📝 O escribe: \"Dame una señal de [moneda]\"",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif callback_data.startswith(f"{MENU_PREFIX}config"):
            # Menú de configuración
            keyboard = [
                [InlineKeyboardButton("💰 Mis Criptomonedas", callback_data=f"{CONFIG_PREFIX}cryptos")],
                [InlineKeyboardButton("⏰ Mis Timeframes", callback_data=f"{CONFIG_PREFIX}timeframes")],
                [InlineKeyboardButton("📋 Ver Configuración", callback_data=f"{CONFIG_PREFIX}view")],
                [InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚙️ **Configuración del Bot**\n\n"
                "Personaliza tu experiencia:\n"
                "• Selecciona tus criptomonedas favoritas\n"
                "• Configura timeframes preferidos\n"
                "• Ve tu configuración actual",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif callback_data.startswith(f"{MENU_PREFIX}main"):
            # Volver al menú principal
            keyboard = [
                [InlineKeyboardButton("📊 Análisis", callback_data=f"{MENU_PREFIX}analysis")],
                [InlineKeyboardButton("🎯 Señales", callback_data=f"{MENU_PREFIX}signal")],
                [InlineKeyboardButton("🧠 Estrategias", callback_data=f"{MENU_PREFIX}strategy")],
                [InlineKeyboardButton("🔔 Alertas", callback_data=f"{ACTION_PREFIX}alerts")],
                [InlineKeyboardButton("⚙️ Configurar", callback_data=f"{MENU_PREFIX}config")]
            ]
            
            if TelegramSecurityConfig.is_admin_user(user_id):
                keyboard.append([InlineKeyboardButton("🛠️ Admin", callback_data=f"{ACTION_PREFIX}admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🔒 **Bot de Crypto AI Securizado** 🔒\n\n"
                "Selecciona una opción o escribe directamente tu consulta:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        # Nuevos handlers para análisis y señales con timeframes
        elif callback_data.startswith(f"{ANALYSIS_PREFIX}"):
            # Análisis: mostrar opciones de timeframe
            if "page_" in callback_data:
                # Paginación de criptomonedas
                page = int(callback_data.split("page_")[1])
                keyboard = create_crypto_keyboard(user_id, f"{ANALYSIS_PREFIX}", page)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📊 **Selecciona la criptomoneda para analizar:**\n\n"
                    "💡 Tip: Personaliza tu lista con el botón \"✏️ Personalizar\"\n"
                    "📝 O escribe: \"Analiza [moneda] en [tiempo]\"",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Selección de crypto: mostrar timeframes
                symbol = callback_data.replace(f"{ANALYSIS_PREFIX}", "")
                keyboard = create_timeframe_keyboard(symbol, "analysis")
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                crypto_info = DEFAULT_CRYPTOS.get(symbol, {"name": symbol, "emoji": "💰"})
                await query.edit_message_text(
                    f"📊 **Análisis de {crypto_info['emoji']} {crypto_info['name']}**\n\n"
                    f"⏰ Selecciona el timeframe para el análisis:",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        elif callback_data.startswith(f"{SIGNAL_PREFIX}"):
            # Señales: mostrar opciones de timeframe  
            if "page_" in callback_data:
                # Paginación de criptomonedas
                page = int(callback_data.split("page_")[1])
                keyboard = create_crypto_keyboard(user_id, f"{SIGNAL_PREFIX}", page)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "🎯 **Selecciona una criptomoneda para señal:**\n\n"
                    "💡 Tip: Personaliza tu lista con el botón \"✏️ Personalizar\"\n"
                    "📝 O escribe: \"Dame una señal de [moneda]\"",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Selección de crypto: mostrar timeframes
                symbol = callback_data.replace(f"{SIGNAL_PREFIX}", "")
                keyboard = create_timeframe_keyboard(symbol, "signal")
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                crypto_info = DEFAULT_CRYPTOS.get(symbol, {"name": symbol, "emoji": "💰"})
                await query.edit_message_text(
                    f"🎯 **Señal para {crypto_info['emoji']} {crypto_info['name']}**\n\n"
                    f"⏰ Selecciona el timeframe para la señal:",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        elif callback_data.startswith(f"{TIMEFRAME_PREFIX}"):
            # Ejecutar análisis/señal con timeframe seleccionado
            parts = callback_data.replace(f"{TIMEFRAME_PREFIX}", "").split("_")
            action_type = parts[0]  # "analysis" o "signal"
            symbol = parts[1]
            timeframe = parts[2]
            
            crypto_info = DEFAULT_CRYPTOS.get(symbol, {"name": symbol, "emoji": "💰"})
            tf_info = AVAILABLE_TIMEFRAMES.get(timeframe, {"name": timeframe, "emoji": "⏰"})
            
            # Mostrar mensaje diferente según el tipo
            action_emoji = "📊" if action_type == "analysis" else "🎯"
            action_text = "análisis" if action_type == "analysis" else "señal"
            
            await query.edit_message_text(
                f"🔄 Procesando {action_emoji} {action_text} de {crypto_info['emoji']} {symbol} en {tf_info['emoji']} {tf_info['name']}..."
            )
            
            # Construir payload apropiado según el tipo de acción
            if action_type == "signal":
                # Usar endpoint de estrategias avanzadas
                payload = {
                    "strategy_type": "scalping",
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "user_id": str(user_id)
                }
                
                data = await secure_ai_call("advanced-strategy", payload, user_id)
                if data and "result" in data:
                    result = data.get("result", {})
                    signal = result.get("signal", "NEUTRAL")
                    entry_price = result.get("entry_price")
                    stop_loss = result.get("stop_loss")
                    take_profit = result.get("take_profit")
                    confidence = result.get("confidence", 0)
                    reasoning = result.get("reasoning", "")
                    
                    # Verificar si hay una señal válida
                    if signal == "NEUTRAL" or entry_price is None:
                        response_text = (
                            f"📊 **Análisis de {symbol} ({timeframe})**\n\n"
                            f"🔍 **Estado actual:** No se encontró oportunidad de trading clara\n\n"
                            f"💡 **Recomendación:** Espera a que se formen mejores condiciones o prueba con otro timeframe\n\n"
                            f"⚠️ **Advertencia:** Este análisis no es asesoramiento financiero"
                        )
                    else:
                        # Formatear señal de trading profesional
                        response_text = format_trading_signal(
                            symbol, signal, entry_price, stop_loss, take_profit, confidence, reasoning,
                            timeframe, False
                        )
                else:
                    response_text = f"❌ Error obteniendo {action_text} para {symbol} en {timeframe}"
            else:
                # Usar endpoint de análisis
                payload = {
                    "symbol": symbol,
                    "timeframes": [timeframe],
                    "user_prompt": f"Análisis técnico de {symbol} en timeframe {timeframe}",
                    "analysis_type": "technical",
                    "include_risk_analysis": True,
                    "include_price_targets": True
                }
                
                data = await secure_ai_call("analyze", payload, user_id)
                if data and "analysis" in data:
                    response_text = data.get("analysis", f"Sin {action_text} disponible")
                else:
                    response_text = f"❌ Error obteniendo {action_text} para {symbol} en {timeframe}"
            
            await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN)
            
        elif callback_data.startswith(f"{CONFIG_PREFIX}"):
            # Configuración de usuario
            config_action = callback_data.replace(f"{CONFIG_PREFIX}", "")
            
            if config_action == "cryptos":
                # Mostrar lista de todas las criptomonedas disponibles para personalizar
                user_cryptos = get_user_cryptos(user_id)
                keyboard = []
                
                # Crear grid de criptomonedas (3 por fila)
                all_cryptos = list(DEFAULT_CRYPTOS.keys())
                for i in range(0, len(all_cryptos), 3):
                    row = []
                    for j in range(3):
                        if i + j < len(all_cryptos):
                            crypto = all_cryptos[i + j]
                            crypto_info = DEFAULT_CRYPTOS[crypto]
                            # Marcar con ✅ si está en favoritos
                            check = "✅" if crypto in user_cryptos else ""
                            button = InlineKeyboardButton(
                                f"{check}{crypto_info['emoji']} {crypto}",
                                callback_data=f"{CONFIG_PREFIX}toggle_{crypto}"
                            )
                            row.append(button)
                    keyboard.append(row)
                
                # Botones de acción
                keyboard.append([
                    InlineKeyboardButton("💾 Guardar", callback_data=f"{CONFIG_PREFIX}save_cryptos"),
                    InlineKeyboardButton("🔄 Restablecer", callback_data=f"{CONFIG_PREFIX}reset_cryptos")
                ])
                keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}config")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"💰 **Personalizar Criptomonedas**\n\n"
                    f"Selecciona/deselecciona tus favoritas:\n"
                    f"📊 Actualmente tienes: {len(user_cryptos)} seleccionadas\n"
                    f"🎯 Máximo permitido: 15 criptomonedas",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            elif config_action == "view":
                # Mostrar configuración actual
                user_cryptos = get_user_cryptos(user_id)
                user_timeframes = get_user_timeframes(user_id)
                
                crypto_names = ", ".join([DEFAULT_CRYPTOS[c]["name"] for c in user_cryptos[:5]])
                if len(user_cryptos) > 5:
                    crypto_names += f" y {len(user_cryptos) - 5} más"
                
                tf_names = ", ".join([AVAILABLE_TIMEFRAMES[tf]["name"] for tf in user_timeframes])
                
                config_text = (
                    f"📋 **Tu Configuración Actual**\n\n"
                    f"💰 **Criptomonedas favoritas:** ({len(user_cryptos)})\n"
                    f"{crypto_names}\n\n"
                    f"⏰ **Timeframes preferidos:** ({len(user_timeframes)})\n"
                    f"{tf_names}"
                )
                
                keyboard = [
                    [InlineKeyboardButton("✏️ Editar Criptos", callback_data=f"{CONFIG_PREFIX}cryptos")],
                    [InlineKeyboardButton("⏰ Editar Timeframes", callback_data=f"{CONFIG_PREFIX}timeframes")],
                    [InlineKeyboardButton("🔙 Volver", callback_data=f"{MENU_PREFIX}config")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    config_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            elif config_action.startswith("toggle_"):
                # Toggle de criptomoneda
                crypto = config_action.replace("toggle_", "")
                user_cryptos = get_user_cryptos(user_id)
                
                if crypto in user_cryptos:
                    user_cryptos.remove(crypto)
                else:
                    if len(user_cryptos) < 15:  # Límite máximo
                        user_cryptos.append(crypto)
                
                # Guardar temporalmente (se podría mejorar esto)
                set_user_cryptos(user_id, user_cryptos)
                
                # Actualizar mensaje (re-mostrar la lista)
                await button_callback(update, context)
                return
                
        elif callback_data.startswith(f"{ACTION_PREFIX}"):
            # Acciones del sistema
            action = callback_data.replace(f"{ACTION_PREFIX}", "")
            
            if action == "alerts":
                # Mostrar menú de alertas
                alerts = secure_memory.get_user_alerts(user_id, active_only=True)
                
                if not alerts:
                    keyboard = [
                        [InlineKeyboardButton("➕ Crear Alerta", callback_data=f"{ACTION_PREFIX}create_alert")],
                        [InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        "🔔 **Sistema de Alertas**\n\n"
                        "No tienes alertas activas.\n\n"
                        "Las alertas te notificarán cuando:\n"
                        "• El precio suba/baje a un nivel específico\n"
                        "• Los indicadores técnicos cambien\n"
                        "• Se detecten patrones importantes",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                else:
                    # Mostrar alertas existentes
                    alerts_text = "🔔 **Tus alertas activas:**\n\n"
                    keyboard = []
                    
                    for i, alert in enumerate(alerts[:10]):  # Límite de 10 para UI
                        symbol = alert['symbol']
                        condition_type = alert['condition_type'].replace('_', ' ').title()
                        condition_value = alert['condition_value']
                        timeframe = alert['timeframe']
                        
                        crypto_info = DEFAULT_CRYPTOS.get(symbol, {"emoji": "💰"})
                        tf_info = AVAILABLE_TIMEFRAMES.get(timeframe, {"emoji": "⏰"})
                        
                        alerts_text += (
                            f"{i+1}. {crypto_info['emoji']} **{symbol}** "
                            f"{condition_type} **${condition_value}** "
                            f"({tf_info['emoji']} {timeframe})\n"
                        )
                        
                        keyboard.append([
                            InlineKeyboardButton(
                                f"❌ Eliminar {symbol}", 
                                callback_data=f"{ALERT_PREFIX}delete_{alert['id']}"
                            )
                        ])
                    
                    keyboard.append([InlineKeyboardButton("➕ Nueva Alerta", callback_data=f"{ACTION_PREFIX}create_alert")])
                    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        alerts_text, 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
            elif action == "create_alert":
                # Mostrar menú para crear nueva alerta
                keyboard = create_crypto_keyboard(user_id, f"{ALERT_PREFIX}crypto_", 0)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "🔔 **Crear Nueva Alerta**\n\n"
                    "**Paso 1 de 4:** Selecciona la criptomoneda\n\n"
                    "💡 Elige la crypto que quieres monitorear:",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        elif callback_data.startswith(f"{ALERT_PREFIX}"):
            # Manejo de alertas
            alert_action = callback_data.replace(f"{ALERT_PREFIX}", "")
            
            if alert_action.startswith("delete_"):
                # Eliminar alerta
                alert_id = int(alert_action.replace("delete_", ""))
                
                success = secure_memory.delete_alert(alert_id, user_id)
                
                if success:
                    await query.edit_message_text(
                        "✅ **Alerta eliminada exitosamente**\n\n"
                        "La alerta ha sido removida de tu lista.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Volver al menú de alertas después de 2 segundos
                    import asyncio
                    await asyncio.sleep(2)
                    
                    # Simular click en menú de alertas
                    mock_query = query
                    mock_query.data = f"{ACTION_PREFIX}alerts"
                    await button_callback(update, context)
                    
                else:
                    await query.edit_message_text(
                        "❌ **Error eliminando alerta**\n\n"
                        "No se pudo eliminar la alerta. Intenta de nuevo.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
            elif alert_action.startswith("crypto_"):
                # Selección de crypto para alerta - mostrar tipos de condición
                if "page_" in alert_action:
                    # Paginación de criptomonedas
                    page = int(alert_action.split("page_")[1])
                    keyboard = create_crypto_keyboard(user_id, f"{ALERT_PREFIX}crypto_", page)
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        "🔔 **Crear Nueva Alerta**\n\n"
                        "**Paso 1 de 4:** Selecciona la criptomoneda\n\n"
                        "💡 Elige la crypto que quieres monitorear:",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    # Crypto seleccionada - mostrar tipos de condición
                    symbol = alert_action.replace("crypto_", "")
                    context.user_data['alert_symbol'] = symbol
                    
                    crypto_info = DEFAULT_CRYPTOS.get(symbol, {"name": symbol, "emoji": "💰"})
                    
                    keyboard = [
                        [InlineKeyboardButton("📈 Precio mayor a", callback_data=f"{ALERT_PREFIX}condition_price_above")],
                        [InlineKeyboardButton("📉 Precio menor a", callback_data=f"{ALERT_PREFIX}condition_price_below")],
                        [InlineKeyboardButton("🚀 RSI sobreventa (<30)", callback_data=f"{ALERT_PREFIX}condition_rsi_oversold")],
                        [InlineKeyboardButton("📊 RSI sobrecompra (>70)", callback_data=f"{ALERT_PREFIX}condition_rsi_overbought")],
                        [InlineKeyboardButton("📈 Volumen alto (+50%)", callback_data=f"{ALERT_PREFIX}condition_volume_high")],
                        [InlineKeyboardButton("🔙 Cambiar Crypto", callback_data=f"{ACTION_PREFIX}create_alert")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"🔔 **Crear Alerta para {crypto_info['emoji']} {crypto_info['name']}**\n\n"
                        f"**Paso 2 de 4:** Selecciona el tipo de condición\n\n"
                        f"💡 ¿Qué evento quieres monitorear?",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
            elif alert_action.startswith("condition_"):
                # Tipo de condición seleccionado
                condition = alert_action.replace("condition_", "")
                context.user_data['alert_condition'] = condition
                
                symbol = context.user_data.get('alert_symbol', 'BTC')
                crypto_info = DEFAULT_CRYPTOS.get(symbol, {"name": symbol, "emoji": "💰"})
                
                if condition in ["price_above", "price_below"]:
                    # Pedir valor de precio
                    keyboard = [
                        [InlineKeyboardButton("🔙 Cambiar Condición", callback_data=f"{ALERT_PREFIX}crypto_{symbol}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    direction = "mayor" if condition == "price_above" else "menor"
                    
                    await query.edit_message_text(
                        f"🔔 **Alerta de Precio para {crypto_info['emoji']} {symbol}**\n\n"
                        f"**Paso 3 de 3:** Ingresa el precio objetivo\n\n"
                        f"💰 ¿A qué precio (USD) quieres recibir la alerta?\n\n"
                        f"📝 Escribe el precio {direction} al que {symbol} debe llegar.\n"
                        f"Ejemplo: 45000\n\n"
                        f"💡 *El precio es igual en todas las temporalidades*",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    context.user_data['waiting_for_price'] = True
                    
                else:
                    # Condiciones automáticas (RSI, volumen) - ir directo a timeframe
                    context.user_data['alert_value'] = "auto"
                    
                    keyboard = []
                    for tf_key, tf_info in AVAILABLE_TIMEFRAMES.items():
                        keyboard.append([
                            InlineKeyboardButton(
                                f"{tf_info['emoji']} {tf_info['name']}", 
                                callback_data=f"{ALERT_PREFIX}timeframe_{tf_key}"
                            )
                        ])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Cambiar Condición", callback_data=f"{ALERT_PREFIX}crypto_{symbol}")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    condition_text = {
                        "rsi_oversold": "RSI en sobreventa (<30)",
                        "rsi_overbought": "RSI en sobrecompra (>70)", 
                        "volume_high": "Volumen alto (+50%)"
                    }.get(condition, condition)
                    
                    await query.edit_message_text(
                        f"🔔 **Alerta de {condition_text} para {crypto_info['emoji']} {symbol}**\n\n"
                        f"**Paso 3 de 3:** Selecciona el timeframe\n\n"
                        f"⏰ ¿En qué temporalidad monitorear?",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
            elif alert_action.startswith("timeframe_"):
                # Timeframe seleccionado - crear alerta
                timeframe = alert_action.replace("timeframe_", "")
                
                symbol = context.user_data.get('alert_symbol', 'BTC')
                condition = context.user_data.get('alert_condition', 'price_above')
                value = context.user_data.get('alert_value', '0')
                
                # Crear la alerta
                alert_id = secure_memory.create_alert(
                    user_id=user_id,
                    symbol=symbol,
                    condition_type=condition,
                    condition_value=value,
                    timeframe=timeframe
                )
                
                if alert_id:
                    crypto_info = DEFAULT_CRYPTOS.get(symbol, {"name": symbol, "emoji": "💰"})
                    tf_info = AVAILABLE_TIMEFRAMES.get(timeframe, {"name": timeframe, "emoji": "⏰"})
                    
                    condition_text = {
                        "price_above": f"precio mayor a ${value}",
                        "price_below": f"precio menor a ${value}",
                        "rsi_oversold": "RSI en sobreventa (<30)",
                        "rsi_overbought": "RSI en sobrecompra (>70)",
                        "volume_high": "volumen alto (+50%)"
                    }.get(condition, condition)
                    
                    keyboard = [
                        [InlineKeyboardButton("🔔 Ver Mis Alertas", callback_data=f"{ACTION_PREFIX}alerts")],
                        [InlineKeyboardButton("➕ Crear Otra", callback_data=f"{ACTION_PREFIX}create_alert")],
                        [InlineKeyboardButton("🔙 Menú Principal", callback_data=f"{MENU_PREFIX}main")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"✅ **¡Alerta creada exitosamente!**\n\n"
                        f"📋 **Detalles:**\n"
                        f"• Criptomoneda: {crypto_info['emoji']} {symbol}\n"
                        f"• Condición: {condition_text}\n"
                        f"• Timeframe: {tf_info['emoji']} {tf_info['name']}\n\n"
                        f"📱 Recibirás una notificación cuando se cumpla la condición.",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Limpiar datos temporales
                    context.user_data.clear()
                    
                else:
                    await query.edit_message_text(
                        "❌ **Error creando alerta**\n\n"
                        "No se pudo crear la alerta. Intenta de nuevo.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
        elif callback_data.startswith(f"{STRATEGY_PREFIX}"):
            # Menú de estrategias
            # El formato es: strategy:selectBTC o strategy:scalping:BTC
            strategy_part = callback_data.replace(f"{STRATEGY_PREFIX}", "")
            
            if strategy_part.startswith("select"):
                # Selección de criptomoneda para estrategia
                # El formato es: selectBTC
                selected_crypto = strategy_part.replace("select", "")
                keyboard = create_strategy_keyboard(selected_crypto)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🎯 **Selecciona una estrategia para {selected_crypto}**\n\n"
                    "💡 Cada estrategia tiene un enfoque específico:\n"
                    "• **Scalping**: Operaciones rápidas\n"
                    "• **RSI**: Análisis de momentum\n"
                    "• **Estocástico**: Oscilador de momentum\n"
                    "• **Smart Money**: Conceptos avanzados\n"
                    "• **Volatilidad**: Análisis de contracción\n"
                    "• **Intradía**: Operaciones diarias\n"
                    "• **Fair Value Gap**: Gaps de valor\n"
                    "• **Divergencia**: Patrones correlacionados",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif strategy_part.startswith("back_to_strategy:"):
                # Volver a selección de estrategia
                selected_crypto = strategy_part.split(":")[1]
                keyboard = create_strategy_keyboard(selected_crypto)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🎯 **Selecciona una estrategia para {selected_crypto}**\n\n"
                    "💡 Cada estrategia tiene un enfoque específico:\n"
                    "• **Scalping**: Operaciones rápidas\n"
                    "• **RSI**: Análisis de momentum\n"
                    "• **Estocástico**: Oscilador de momentum\n"
                    "• **Smart Money**: Conceptos avanzados\n"
                    "• **Volatilidad**: Análisis de contracción\n"
                    "• **Intradía**: Operaciones diarias\n"
                    "• **Fair Value Gap**: Gaps de valor\n"
                    "• **Divergencia**: Patrones correlacionados",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Estrategia seleccionada - mostrar timeframes
                # El formato es: scalping:BTC
                parts = strategy_part.split(":")
                secure_logger.safe_log(f"Strategy callback parts: {parts}", "debug", user_id)
                
                # Manejar el caso donde el callback tiene formato strategy:rsi::ETH
                if len(parts) >= 3:
                    # Caso: strategy:rsi::ETH (con dos puntos vacíos)
                    selected_strategy = parts[1].strip() if len(parts) > 1 else ""
                    selected_crypto = parts[2].strip() if len(parts) > 2 else ""
                elif len(parts) >= 2:
                    # Caso normal: strategy:rsi:ETH
                    selected_strategy = parts[0].strip()
                    selected_crypto = parts[1].strip()
                else:
                    selected_strategy = ""
                    selected_crypto = ""
                
                # Si el callback tiene formato strategy:rsi::ETH, extraer correctamente
                if not selected_strategy and len(parts) >= 2:
                    # El callback es strategy:rsi::ETH, donde rsi está en la posición 1
                    selected_strategy = parts[1].strip() if len(parts) > 1 else ""
                    selected_crypto = parts[2].strip() if len(parts) > 2 else ""
                
                # Debug: mostrar el callback completo y las partes
                secure_logger.safe_log(f"Callback completo: {strategy_part}", "debug", user_id)
                secure_logger.safe_log(f"Partes del callback: {parts}", "debug", user_id)
                secure_logger.safe_log(f"Estrategia extraída: '{selected_strategy}', Crypto extraída: '{selected_crypto}'", "debug", user_id)
                
                # Verificar que los campos no estén vacíos
                if not selected_strategy or not selected_crypto:
                    secure_logger.safe_log(f"Campos vacíos en callback - strategy: '{selected_strategy}', crypto: '{selected_crypto}'", "error", user_id)
                    await query.edit_message_text(
                        "❌ Error en la selección (campos vacíos). Intenta de nuevo.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                # Si los campos están válidos, continuar con la lógica
                strategy_info = AVAILABLE_STRATEGIES.get(selected_strategy, {"name": selected_strategy, "emoji": "🎯"})
                
                keyboard = create_timeframe_for_strategy_keyboard(selected_crypto, selected_strategy)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"⏰ **Selecciona el timeframe para {strategy_info['emoji']} {strategy_info['name']} de {selected_crypto}**\n\n"
                    f"📊 **Estrategia:** {strategy_info['name']}\n"
                    f"💡 **Descripción:** {strategy_info['description']}\n\n"
                    "⏰ **Timeframes recomendados:**\n"
                    "• **1m-5m**: Scalping, operaciones rápidas\n"
                    "• **15m-1h**: Swing trading, análisis medio plazo\n"
                    "• **4h-1d**: Posiciones largas, análisis fundamental\n"
                    "• **1w**: Análisis macro, tendencias largas",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        elif callback_data.startswith(f"{TIMEFRAME_PREFIX}strategy:"):
            # Timeframe seleccionado para estrategia - ejecutar estrategia
            # Formato esperado: timeframe:strategy:30m:BTC:estocastico
            try:
                parts = callback_data.split(":")
                secure_logger.safe_log(f"Strategy callback parts: {parts}", "debug", user_id)
                
                # Validar que tenemos suficientes partes y que no estén vacías
                if len(parts) >= 5:
                    timeframe = parts[2].strip() if len(parts) > 2 else ""
                    selected_crypto = parts[3].strip() if len(parts) > 3 else ""
                    selected_strategy = parts[4].strip() if len(parts) > 4 else ""
                    
                    # Verificar que todos los campos necesarios estén presentes
                    if timeframe and selected_crypto and selected_strategy:
                        crypto_info = DEFAULT_CRYPTOS.get(selected_crypto, {"name": selected_crypto, "emoji": "💰"})
                        strategy_info = AVAILABLE_STRATEGIES.get(selected_strategy, {"name": selected_strategy, "emoji": "🎯"})
                        tf_info = AVAILABLE_TIMEFRAMES.get(timeframe, {"name": timeframe, "emoji": "⏰"})
                        
                        await query.edit_message_text(
                            f"🔄 Procesando estrategia {strategy_info['emoji']} {strategy_info['name']} "
                            f"para {crypto_info['emoji']} {selected_crypto} en {tf_info['emoji']} {tf_info['name']}..."
                        )
                        
                        # Construir payload para estrategia avanzada
                        payload = {
                            "symbol": selected_crypto,
                            "timeframe": timeframe,
                            "strategy": selected_strategy,
                            "user_prompt": f"Estrategia {selected_strategy} para {selected_crypto} en {timeframe}"
                        }
                        
                        data = await secure_ai_call("advanced-strategy", payload, user_id)
                        
                        if data and "signal" in data:
                            signal_data = data.get("signal", {})
                            if isinstance(signal_data, dict):
                                # Extraer datos de la señal
                                signal_type = signal_data.get("signal", "NEUTRAL")
                                confidence = signal_data.get("confidence", 0.0)
                                entry_price = signal_data.get("entry_price", 0.0)
                                stop_loss = signal_data.get("stop_loss", 0.0)
                                take_profit = signal_data.get("take_profit", 0.0)
                                reasoning = signal_data.get("reasoning", "")
                                
                                # Determinar emoji y texto según el tipo de señal
                                if signal_type == "LONG":
                                    emoji = "🟢"
                                    signal_text = "COMPRA"
                                elif signal_type == "SHORT":
                                    emoji = "🔴"
                                    signal_text = "VENTA"
                                else:
                                    emoji = "🟡"
                                    signal_text = "NEUTRAL"
                                
                                confidence_text = "Alta" if confidence > 0.7 else "Media" if confidence > 0.4 else "Baja"
                                
                                # Extraer análisis técnico del razonamiento
                                analysis_text = "Análisis técnico basado en indicadores como RSI, MACD, SMA, EMA y bandas de Bollinger."
                                if reasoning:
                                    reasoning_lines = reasoning.split('\n')
                                    relevant_lines = []
                                    for line in reasoning_lines:
                                        line_lower = line.lower()
                                        if any(indicator in line_lower for indicator in ['rsi', 'macd', 'bollinger', 'sma', 'ema', 'estocástico']):
                                            relevant_lines.append(line)
                                    if relevant_lines:
                                        analysis_text = " | ".join(relevant_lines[:3])  # Máximo 3 líneas
                                
                                response_text = (
                                    f"{emoji} **{selected_crypto}/USDT - SEÑAL {timeframe.upper()}**\n"
                                    f"💰 ${entry_price:,.2f} | 📈 {signal_text} | ⚡ {confidence:.2f}\n\n"
                                    f"🎯 **NIVELES:**\n"
                                    f"• Entrada: ${entry_price:,.2f}\n"
                                    f"• Stop Loss: ${stop_loss:,.2f}\n"
                                    f"• Take Profit: ${take_profit:,.2f}\n\n"
                                    f"💡 **ANÁLISIS:** {analysis_text}\n\n"
                                    f"🔥 **CONFIANZA:** {confidence_text}\n\n"
                                    f"⚠️ **Advertencia:** Este análisis no es asesoramiento financiero"
                                )
                            else:
                                response_text = str(signal_data)
                        else:
                            response_text = f"❌ No se pudo generar señal para {selected_crypto} con estrategia {selected_strategy} en {timeframe}"
                        
                        await query.edit_message_text(response_text, parse_mode=ParseMode.MARKDOWN)
                    else:
                        # Log del error para debugging
                        secure_logger.safe_log(f"Callback mal formado - timeframe: '{timeframe}', crypto: '{selected_crypto}', strategy: '{selected_strategy}'", "error", user_id)
                        await query.edit_message_text(
                            "❌ Error en la selección de timeframe (campos vacíos). Intenta de nuevo.",
                            parse_mode=ParseMode.MARKDOWN
                        )
                else:
                    secure_logger.safe_log(f"Callback con formato incorrecto - partes insuficientes: {len(parts)}", "error", user_id)
                    await query.edit_message_text(
                        "❌ Error en la selección de timeframe (formato incorrecto). Intenta de nuevo.",
                        parse_mode=ParseMode.MARKDOWN
                    )
            except Exception as e:
                secure_logger.safe_log(f"Error parsing timeframe strategy callback: {str(e)}", "error", user_id)
                await query.edit_message_text(
                    "❌ Error procesando la selección. Intenta de nuevo.",
                    parse_mode=ParseMode.MARKDOWN
                )
        elif callback_data.startswith(f"{MENU_PREFIX}strategies"):
            # Menú de estrategias - mostrar criptomonedas
            keyboard = create_crypto_keyboard(user_id, f"{STRATEGY_PREFIX}select", page=0)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🧠 **Estrategias Avanzadas**\n\n"
                "Selecciona una criptomoneda para aplicar estrategias especializadas:\n\n"
                "📊 **Estrategias disponibles:**\n"
                "• ⚡ **Scalping**: Operaciones rápidas en timeframes cortos\n"
                "• 📊 **RSI**: Análisis de sobrecompra/sobreventa\n"
                "• 🎯 **Estocástico**: Oscilador de momentum\n"
                "• 🧠 **Smart Money**: Conceptos de dinero inteligente\n"
                "• 📈 **Volatilidad**: Análisis de contracción de volatilidad\n"
                "• 🌅 **Intradía**: Operaciones dentro del día\n"
                "• ⚖️ **Fair Value Gap**: Gaps de valor justo\n"
                "• 🔄 **Divergencia**: Divergencias correlacionadas\n\n"
                "💡 **Tip:** También puedes escribir directamente:\n"
                "• \"Estrategia scalping para BTC en 5m\"\n"
                "• \"RSI de ETH en 1h\"\n"
                "• \"Smart money de SOL en 4h\"",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Callback no reconocido
            await query.edit_message_text(
                "❌ Opción no reconocida. Regresando al menú principal...",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        secure_logger.safe_log(f"Error en callback: {str(e)}", "error", user_id)
        await query.edit_message_text(
            "❌ Error procesando la solicitud. Intenta de nuevo.",
            parse_mode=ParseMode.MARKDOWN
        )

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

async def handle_unverified_user(update: Update, context: ContextTypes.DEFAULT_TYPE, status):
    """Maneja usuarios no verificados pidiéndoles directamente el UID."""
    user_id = update.effective_user.id
    
    can_attempt, error_msg = user_verification.can_attempt_verification(user_id)
    
    if not can_attempt:
        message = (
            f"🔒 **Verificación Requerida**\n\n"
            f"❌ {error_msg}\n\n"
            f"Para más información, contacta al administrador."
        )
        
        # Manejar tanto mensajes como callback queries
        if update.message:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Obtener exchanges disponibles
    available_exchanges = referral_verifier.get_enabled_exchanges()
    
    if not available_exchanges:
        message = (
            "🔒 **Verificación Requerida**\n\n"
            "❌ No hay exchanges configurados para verificación.\n"
            "Contacta al administrador."
        )
        
        # Manejar tanto mensajes como callback queries
        if update.message:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
        return
    
    exchanges_text = ", ".join([ex.title() for ex in available_exchanges])
    
    verification_message = (
        "🔒 **Verificación de Referido Requerida**\n\n"
        "Para usar este bot, debes verificarte como referido en uno de estos exchanges:\n"
        f"📊 **Exchanges soportados:** {exchanges_text}\n\n"
        f"📝 **Intentos disponibles:** {user_verification.max_attempts - status.attempts}/{user_verification.max_attempts}\n\n"
        "💡 **¿Cómo funciona?**\n"
        "1. Debes ser referido de nuestro programa\n"
        "2. Proporciona tu UID del exchange\n"
        "3. Verificamos automáticamente tu estado\n\n"
        "📝 **Formato:** Simplemente escribe tu UID (solo números)\n"
        "📋 **Ejemplo:** `1234567890`\n\n"
        "⚠️ **Importante:**\n"
        "• Solo envía el UID, sin texto adicional\n"
        "• Debe ser exactamente como aparece en tu exchange\n"
        "• Tienes un límite de intentos por hora\n\n"
        "💬 **Escribe tu UID ahora:**"
    )
    
    # Marcar al usuario como esperando UID
    USERS_AWAITING_VERIFICATION.add(user_id)
    context.user_data['awaiting_uid'] = True
    
    # Manejar tanto mensajes como callback queries
    if update.message:
        await update.message.reply_text(
            verification_message,
            parse_mode=ParseMode.MARKDOWN
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            verification_message,
            parse_mode=ParseMode.MARKDOWN
        )

# Variable global para rastrear usuarios en proceso de verificación
USERS_AWAITING_VERIFICATION = set()



async def process_uid_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el UID para verificación."""
    user_id = update.effective_user.id
    uid = update.message.text.strip()
    
    # Validar formato UID
    if not uid.isdigit() or len(uid) < 5 or len(uid) > 15:
        await update.message.reply_text(
            "❌ **UID Inválido**\n\n"
            "El UID debe contener solo números y tener entre 5-15 dígitos.\n"
            "📋 **Ejemplo correcto:** `1234567890`\n\n"
            "Por favor, intenta de nuevo:",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Verificar si puede intentar
    can_attempt, error_msg = user_verification.can_attempt_verification(user_id)
    if not can_attempt:
        await update.message.reply_text(f"❌ {error_msg}")
        context.user_data.pop('awaiting_uid', None)
        return
    
    # Mostrar mensaje de verificación en progreso
    verification_msg = await update.message.reply_text(
        "🔍 **Verificando...**\n\n"
        f"📊 Buscando UID `{uid}` en exchanges configurados...\n"
        "⏳ Esto puede tomar unos segundos.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Verificar en exchanges
        is_verified, message, exchange_found = await referral_verifier.verify_referral(uid)
        
        if is_verified:
            # Marcar como verificado
            user_verification.record_verification_attempt(
                user_id, uid, True, exchange_found
            )
            
            await verification_msg.edit_text(
                "✅ **Verificación Exitosa!**\n\n"
                f"🎉 Tu UID `{uid}` ha sido verificado en **{exchange_found}**\n"
                f"📅 Verificado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                "🚀 Ya puedes usar todas las funciones del bot!\n"
                "📱 Usa /start para comenzar.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            secure_logger.safe_log(f"Usuario verificado exitosamente en {exchange_found} con UID {uid}", "info", user_id)
            
        else:
            # Registrar intento fallido
            user_verification.record_verification_attempt(
                user_id, uid, False, error_msg=message
            )
            
            status = user_verification.get_verification_status(user_id)
            remaining_attempts = user_verification.max_attempts - status.attempts
            
            await verification_msg.edit_text(
                "❌ **Verificación Fallida**\n\n"
                f"📋 Mensaje: {message}\n\n"
                f"🔄 **Intentos restantes:** {remaining_attempts}/{user_verification.max_attempts}\n\n"
                "💡 **Posibles soluciones:**\n"
                "• Verifica que el UID sea correcto\n"
                "• Asegúrate de estar registrado como referido\n"
                "• Contacta al administrador si persiste el error\n\n"
                f"{'⏳ Puedes intentar de nuevo en 1 hora' if remaining_attempts == 0 else '📱 Puedes intentar con otro UID'}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            secure_logger.safe_log(f"Verificación fallida para UID {uid}: {message}", "warning", user_id)
    
    except Exception as e:
        # Error en verificación
        user_verification.record_verification_attempt(
            user_id, uid, False, error_msg=f"Error técnico: {str(e)[:100]}"
        )
        
        await verification_msg.edit_text(
            "⚠️ **Error en Verificación**\n\n"
            "Ocurrió un error técnico durante la verificación.\n"
            "Por favor, intenta de nuevo más tarde o contacta al administrador.\n\n"
            f"🔍 ID de error para soporte: `{user_id}_{int(time.time())}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        secure_logger.safe_log(f"Error en verificación: {str(e)}", "error", user_id)
    
    finally:
        context.user_data.pop('awaiting_uid', None)
        # Limpiar del estado global también
        USERS_AWAITING_VERIFICATION.discard(user_id)

@require_auth
async def verify_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para que administradores verifiquen usuarios manualmente."""
    user_id = update.effective_user.id
    
    if not TelegramSecurityConfig.is_admin_user(user_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return
    
    # Verificar que hay argumentos
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "📝 **Uso del comando:**\n\n"
            "`/verify_user <user_id> [exchange] [uid]`\n\n"
            "**Ejemplos:**\n"
            "• `/verify_user 123456789` - Verificar manualmente\n"
            "• `/verify_user 123456789 bitget 1234567890` - Con detalles\n\n"
            "Para obtener user_id, pide al usuario que envíe un mensaje y revisa los logs.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        exchange = context.args[1] if len(context.args) > 1 else None
        uid = context.args[2] if len(context.args) > 2 else None
        
        # Verificar si la verificación está habilitada
        if not user_verification.is_verification_required():
            await update.message.reply_text(
                "⚠️ **Verificación Deshabilitada**\n\n"
                "La verificación de referidos está deshabilitada en la configuración.\n"
                "No es necesario verificar usuarios manualmente."
            )
            return
        
        # Obtener estado actual del usuario
        status = user_verification.get_verification_status(target_user_id)
        
        if status.is_verified:
            await update.message.reply_text(
                f"✅ **Usuario Ya Verificado**\n\n"
                f"👤 User ID: `{target_user_id}`\n"
                f"📊 Exchange: {status.exchange_used or 'N/A'}\n"
                f"🆔 UID: {status.uid_verified or 'N/A'}\n"
                f"📅 Verificado: {status.verified_at.strftime('%d/%m/%Y %H:%M') if status.verified_at else 'N/A'}\n"
                f"🔧 Método: {status.verification_method or 'N/A'}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Verificar manualmente
        user_verification.mark_verified(
            target_user_id, 
            method="manual_admin", 
            exchange=exchange, 
            uid=uid
        )
        
        # Confirmar verificación exitosa
        await update.message.reply_text(
            f"✅ **Usuario Verificado Manualmente**\n\n"
            f"👤 User ID: `{target_user_id}`\n"
            f"📊 Exchange: {exchange or 'Manual'}\n"
            f"🆔 UID: {uid or 'No especificado'}\n"
            f"👨‍💼 Verificado por: Admin (ID: {user_id})\n"
            f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"🎉 El usuario ya puede usar todas las funciones del bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        secure_logger.safe_log(f"Admin {user_id} verificó manualmente al usuario {target_user_id}", "info", user_id)
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Error de Formato**\n\n"
            "El User ID debe ser un número entero.\n"
            "Ejemplo: `/verify_user 123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ **Error**\n\n"
            f"No se pudo verificar el usuario: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )
        secure_logger.safe_log(f"Error verificando usuario manualmente: {str(e)}", "error", user_id)

async def process_uid_verification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler específico para verificación de UID."""
    user_id = update.effective_user.id
    
    # Verificar si el usuario está esperando ingresar UID (usando variable global y contexto)
    if user_id in USERS_AWAITING_VERIFICATION or context.user_data.get('awaiting_uid'):
        await process_uid_verification(update, context)
        return  # No continuar al handler general
    
    # Si no está esperando UID, continuar al handler general
    await process_message(update, context)

def main() -> None:
    """Función principal del bot securizado."""
    secure_logger.safe_log("Iniciando bot de Telegram securizado", "info")
    
    # Crear aplicación
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Añadir handlers con autenticación
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alertas", alertas_command))
    app.add_handler(CommandHandler("estrategias", estrategias_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("verify_user", verify_user_command))  # Solo para admins
    
    # Handler de callbacks de botones
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Handler específico para UID en verificación (debe ir antes que process_message)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        process_uid_verification_handler
    ))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Configurar logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    secure_logger.safe_log("Bot de Telegram securizado iniciado exitosamente", "info")
    
    # Ejecutar bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

@require_auth
@rate_limit
async def estrategias_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando para acceder a estrategias avanzadas con menús interactivos."""
    user_id = update.effective_user.id
    
    # Obtener criptomonedas del usuario
    user_cryptos = get_user_cryptos(user_id)
    if not user_cryptos:
        user_cryptos = list(DEFAULT_CRYPTOS.keys())[:8]  # Primeras 8 por defecto
    
    # Crear teclado de criptomonedas
    keyboard = create_crypto_keyboard(user_id, f"{STRATEGY_PREFIX}select:", page=0)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "🎯 **Estrategias Avanzadas**\n\n"
        "Selecciona una criptomoneda para aplicar estrategias especializadas:\n\n"
        "📊 **Estrategias disponibles:**\n"
    )
    
    # Agregar lista de estrategias
    for strategy_key, strategy_info in AVAILABLE_STRATEGIES.items():
        emoji = strategy_info["emoji"]
        name = strategy_info["name"]
        description = strategy_info["description"]
        message += f"• {emoji} **{name}**: {description}\n"
    
    message += "\n💡 **Tip:** También puedes escribir directamente:\n"
    message += "• \"Estrategia scalping para BTC en 5m\"\n"
    message += "• \"RSI de ETH en 1h\"\n"
    message += "• \"Smart money de SOL en 4h\"\n\n"
    message += "🔧 **Personalizar lista:** Usa el botón \"✏️ Personalizar\""
    
    secure_logger.safe_log("Usuario accedió a estrategias", "info", user_id)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return SELECTING_CRYPTO_FOR_STRATEGY

async def classify_intent_with_llm(user_message: str) -> dict:
    """
    Usa el LLM para clasificar la intención del usuario y extraer endpoint, símbolo y timeframe.
    """
    prompt = f'''
Eres un asistente que clasifica solicitudes de trading de criptomonedas. 
Dado el siguiente mensaje de usuario, responde SOLO en JSON con los siguientes campos:
- endpoint: "signal", "analyze", "generate", "macro", etc.
- symbol: símbolo detectado (ej: "BTC", "ETH", "SOL") o null si no hay.
- timeframe: timeframe detectado (ej: "1h", "5m", "1d") o null si no hay.
- user_prompt: el mensaje original.

Ejemplo de entrada: "dame una señal de bitcoin en 5 minutos"
Ejemplo de salida: {{"endpoint": "signal", "symbol": "BTC", "timeframe": "5m", "user_prompt": "dame una señal de bitcoin en 5 minutos"}}

Mensaje del usuario: "{user_message}"
'''
    
    payload = {"prompt": prompt}
    llm_url = os.getenv("AI_MODULE_URL", "http://localhost:9004")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{llm_url}/analyze_prompt", json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Intentar extraer el JSON de la respuesta del LLM
            analysis = data.get("analysis", "")
            try:
                # Buscar el primer bloque JSON en la respuesta
                start = analysis.find('{')
                end = analysis.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = analysis[start:end]
                    return json.loads(json_str)
            except Exception:
                pass
    except Exception as e:
        print(f"Error clasificando intención con LLM: {e}")
    # Fallback: si falla, usar analyze
    return {"endpoint": "analyze", "symbol": None, "timeframe": None, "user_prompt": user_message}

async def try_multiple_cryptos_and_timeframes(user_id: int, text: str) -> Optional[Dict[str, Any]]:
    """Analiza múltiples criptomonedas y timeframes para encontrar la mejor señal."""
    # Top 3 criptomonedas por capitalización de mercado
    top_cryptos = ["BTC", "ETH", "SOL"]
    timeframes_to_try = ["5m", "15m", "1h", "30m", "4h", "1d"]
    
    secure_logger.safe_log(f"Analizando top 3 cryptos: {top_cryptos}", "info", user_id)
    
    best_signal = None
    best_confidence = 0.0
    best_score = 0.0
    
    for crypto in top_cryptos:
        secure_logger.safe_log(f"Analizando {crypto}...", "info", user_id)
        for tf in timeframes_to_try:
            try:
                # Crear payload para este crypto y timeframe
                test_payload = {
                    "strategy_type": "scalping",
                    "symbol": crypto,
                    "timeframe": tf,
                    "user_id": str(user_id)
                }
                # Llamar al AI Module
                data = await secure_ai_call("advanced-strategy", test_payload, user_id)
                if data and "result" in data:
                    result = data.get("result", {})
                    signal = result.get("signal", "NEUTRAL")
                    confidence = result.get("confidence", 0.0)
                    entry_price = result.get("entry_price")
                    # Si encontramos una señal válida, calcular score
                    if isinstance(signal, str) and signal.upper() not in ["NEUTRAL", "NONE", "-"] and entry_price is not None and confidence > 0:
                        score = confidence
                        timeframe_bonus = {"5m": 0.1, "15m": 0.08, "30m": 0.06, "1h": 0.04, "4h": 0.02, "1d": 0.0}
                        score += timeframe_bonus.get(tf, 0.0)
                        crypto_bonus = {"BTC": 0.05, "ETH": 0.03, "SOL": 0.02}
                        score += crypto_bonus.get(crypto, 0.0)
                        if score > best_score:
                            best_score = score
                            best_confidence = confidence
                            best_signal = data
                            best_signal["found_crypto"] = crypto
                            best_signal["found_timeframe"] = tf
                            best_signal["score"] = score
                            secure_logger.safe_log(f"Nueva mejor señal: {crypto} en {tf} (score: {score:.3f})", "info", user_id)
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

if __name__ == "__main__":
    main() 