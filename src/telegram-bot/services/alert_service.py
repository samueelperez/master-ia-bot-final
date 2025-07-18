import os
import time
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Cargar .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv opcional en producción

# Dependencias Telegram
try:
    from telegram import Bot
    from telegram.constants import ParseMode
except ImportError:
    raise ImportError("Instala python-telegram-bot para usar el bot de Telegram")

# Gestor de memoria personalizado
from memory_manager import MemoryManager

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AI_MODULE_URL = os.getenv("AI_MODULE_URL", "http://localhost:9004")
CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "300"))  # 5 minutos por defecto

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta TELEGRAM_TOKEN en variables de entorno")

# Inicializar memoria
memory = MemoryManager(db_path=os.getenv("MEMORY_DB", "telegram_bot_memory.db"))
logger.info(f"MemoryManager inicializado con DB: {memory.db_path}")

# Inicializar bot
bot = Bot(token=TELEGRAM_TOKEN)

# Mapeo de tipos de condiciones a funciones de verificación
CONDITION_FORMATTERS = {
    "price_above": lambda value: f"precio por encima de ${value:,.2f}",
    "price_below": lambda value: f"precio por debajo de ${value:,.2f}",
    "rsi_above": lambda value: f"RSI por encima de {value:.2f}",
    "rsi_below": lambda value: f"RSI por debajo de {value:.2f}",
    "volume_above": lambda value: f"volumen por encima de {value:,.2f}",
    "volume_below": lambda value: f"volumen por debajo de {value:,.2f}",
    "macd_cross_above": lambda value: f"MACD cruzando por encima de la señal",
    "macd_cross_below": lambda value: f"MACD cruzando por debajo de la señal",
}

async def get_current_price(symbol: str) -> Optional[float]:
    """
    Obtiene el precio actual de una criptomoneda.
    """
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return float(resp.json().get("price", 0))
    except Exception as e:
        logger.error(f"Error al obtener precio de {symbol}: {e}")
        return None

async def get_indicator_value(symbol: str, indicator: str, timeframe: str) -> Optional[float]:
    """
    Obtiene el valor de un indicador técnico.
    """
    try:
        # Intentar obtener del módulo IA
        url = f"{AI_MODULE_URL}/prompt"
        payload = {
            "prompt": f"Dame el valor actual de {indicator} para {symbol} en {timeframe}",
            "user_context": "",
            "conversation_history": []
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            # Health check opcional
            resp = await client.get(f"{AI_MODULE_URL}/health", timeout=5)
            resp.raise_for_status()
            
            # Llamada principal
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            
            # Extraer valor del indicador
            if data.get("is_analysis_request", False) or data.get("response_type") == "analysis":
                indicators = data.get("indicators", {})
                if indicator == "rsi" and "rsi" in indicators:
                    return float(indicators["rsi"])
                elif indicator == "macd" and "macd" in indicators:
                    macd_data = indicators["macd"]
                    return {
                        "macd_line": float(macd_data.get("macd_line", 0)),
                        "signal_line": float(macd_data.get("signal_line", 0)),
                        "histogram": float(macd_data.get("histogram", 0))
                    }
                elif indicator == "volume" and "volume" in indicators:
                    return float(indicators["volume"])
            
            return None
    except Exception as e:
        logger.error(f"Error al obtener indicador {indicator} para {symbol}: {e}")
        return None

async def check_condition(alert: Dict[str, Any]) -> bool:
    """
    Verifica si se cumple la condición de una alerta.
    """
    symbol = alert["symbol"]
    condition_type = alert["condition_type"]
    condition_value = alert["condition_value"]
    timeframe = alert["timeframe"]
    
    try:
        # Verificar condiciones de precio
        if condition_type == "price_above":
            current_price = await get_current_price(symbol)
            return current_price is not None and current_price > condition_value
        
        elif condition_type == "price_below":
            current_price = await get_current_price(symbol)
            return current_price is not None and current_price < condition_value
        
        # Verificar condiciones de RSI
        elif condition_type == "rsi_above":
            rsi_value = await get_indicator_value(symbol, "rsi", timeframe)
            return rsi_value is not None and rsi_value > condition_value
        
        elif condition_type == "rsi_below":
            rsi_value = await get_indicator_value(symbol, "rsi", timeframe)
            return rsi_value is not None and rsi_value < condition_value
        
        # Verificar condiciones de volumen
        elif condition_type == "volume_above":
            volume_value = await get_indicator_value(symbol, "volume", timeframe)
            return volume_value is not None and volume_value > condition_value
        
        elif condition_type == "volume_below":
            volume_value = await get_indicator_value(symbol, "volume", timeframe)
            return volume_value is not None and volume_value < condition_value
        
        # Verificar condiciones de MACD
        elif condition_type == "macd_cross_above":
            macd_data = await get_indicator_value(symbol, "macd", timeframe)
            if macd_data is not None:
                return macd_data["macd_line"] > macd_data["signal_line"]
            return False
        
        elif condition_type == "macd_cross_below":
            macd_data = await get_indicator_value(symbol, "macd", timeframe)
            if macd_data is not None:
                return macd_data["macd_line"] < macd_data["signal_line"]
            return False
        
        else:
            logger.warning(f"Tipo de condición desconocido: {condition_type}")
            return False
    
    except Exception as e:
        logger.error(f"Error al verificar condición: {e}")
        return False

async def format_alert_message(alert: Dict[str, Any], is_triggered: bool = False) -> str:
    """
    Formatea un mensaje para una alerta.
    """
    symbol = alert["symbol"]
    condition_type = alert["condition_type"]
    condition_value = alert["condition_value"]
    timeframe = alert["timeframe"]
    
    # Obtener precio actual
    current_price = await get_current_price(symbol)
    price_str = f"${current_price:,.2f}" if current_price is not None else "desconocido"
    
    # Formatear condición
    condition_formatter = CONDITION_FORMATTERS.get(condition_type, lambda v: f"condición: {v}")
    condition_str = condition_formatter(condition_value)
    
    if is_triggered:
        return (
            f"🔔 *ALERTA ACTIVADA* 🔔\n\n"
            f"*{symbol}* ha alcanzado {condition_str}\n"
            f"Precio actual: {price_str}\n"
            f"Timeframe: {timeframe}\n\n"
            f"⚠️ Esta información es solo para fines informativos y no constituye asesoramiento financiero."
        )
    else:
        return (
            f"⏳ *Alerta configurada* ⏳\n\n"
            f"Te avisaré cuando *{symbol}* alcance {condition_str}\n"
            f"Precio actual: {price_str}\n"
            f"Timeframe: {timeframe}"
        )

async def send_notification(user_id: int, alert: Dict[str, Any]) -> bool:
    """
    Envía una notificación al usuario.
    """
    try:
        message = await format_alert_message(alert, is_triggered=True)
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    except Exception as e:
        logger.error(f"Error al enviar notificación: {e}")
        return False

async def check_alerts() -> None:
    """
    Verifica todas las alertas activas.
    """
    logger.info("Verificando alertas activas...")
    
    # Obtener todas las alertas activas
    alerts = memory.get_all_active_alerts()
    logger.info(f"Encontradas {len(alerts)} alertas activas")
    
    for alert in alerts:
        alert_id = alert["id"]
        user_id = alert["user_id"]
        
        # Verificar si ya se envió notificación
        if alert.get("notification_sent", False):
            continue
        
        # Verificar condición
        is_triggered = await check_condition(alert)
        
        if is_triggered:
            logger.info(f"Alerta {alert_id} activada para usuario {user_id}")
            
            # Enviar notificación
            notification_sent = await send_notification(user_id, alert)
            
            # Actualizar estado de la alerta
            if notification_sent:
                memory.update_alert(alert_id, notification_sent=True)
                logger.info(f"Notificación enviada para alerta {alert_id}")
            else:
                logger.error(f"Error al enviar notificación para alerta {alert_id}")

async def alert_service_loop() -> None:
    """
    Bucle principal del servicio de alertas.
    """
    logger.info(f"Iniciando servicio de alertas (intervalo: {CHECK_INTERVAL} segundos)")
    
    while True:
        try:
            await check_alerts()
        except Exception as e:
            logger.error(f"Error en el servicio de alertas: {e}")
        
        # Esperar hasta la próxima verificación
        await asyncio.sleep(CHECK_INTERVAL)

def main() -> None:
    """
    Función principal para ejecutar el servicio de alertas.
    """
    logger.info("Iniciando servicio de alertas...")
    
    # Ejecutar bucle de alertas
    asyncio.run(alert_service_loop())

if __name__ == "__main__":
    main()
