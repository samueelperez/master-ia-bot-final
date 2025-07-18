#!/usr/bin/env python3
"""
Simulador del bot de Telegram para demostrar su funcionamiento
sin necesidad de un token de Telegram válido.
"""
import os
import sys
import asyncio
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Cliente HTTP asíncrono
try:
    import httpx
except ImportError:
    print("httpx no está instalado. Instala con `pip install httpx`.")
    sys.exit(1)

# Configuración del módulo AI - usando llm_inference.py
AI_MODULE_URL = "http://localhost:9004"  # Puerto del servidor llm_inference.py
print(f"Using AI_MODULE_URL: {AI_MODULE_URL}")

# Endpoints del módulo AI
ANALYZE_ENDPOINT = "/generate"  # Endpoint del llm_inference.py

async def simulate_ai_response(prompt: str) -> dict:
    """
    Llama al endpoint analyze_prompt del módulo AI.
    Si no se puede obtener una respuesta válida, lanza excepción.
    """
    # Extraer símbolo y timeframe del prompt
    symbol = "BTC"  # Valor por defecto
    timeframes = ["1d"]  # Valor por defecto
    
    # Detectar símbolo
    common_symbols = ["BTC", "ETH", "ADA", "DOT", "SOL", "MATIC", "AVAX", "LINK", "DOGE", "SHIB", "XRP"]
    for s in common_symbols:
        if s.lower() in prompt.lower():
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
        if any(pattern in prompt.lower() for pattern in patterns):
            detected_timeframe = tf
            break
    
    if detected_timeframe:
        timeframes = [detected_timeframe]
    
    # Obtener precio actual de Binance para el símbolo
    current_price = await get_current_price(symbol)
    
    # Crear payload según la estructura esperada por el endpoint /analyze
    payload = {
        "symbol": symbol,
        "timeframes": timeframes,
        "user_prompt": prompt,
        "current_price": current_price  # Añadir precio actual al payload
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Health check
            health = await client.get(f"{AI_MODULE_URL}/health", timeout=5.0)
            health.raise_for_status()

            print(f"Enviando solicitud a: {AI_MODULE_URL}{ANALYZE_ENDPOINT}")
            print(f"Payload: {payload}")
            
            # Llamada principal sin autenticación (llm_inference.py no requiere auth)
            resp = await client.post(
                f"{AI_MODULE_URL}{ANALYZE_ENDPOINT}",
                json=payload,
                timeout=30.0
            )
            resp.raise_for_status()
            response_data = resp.json()
            
            # Asegurarse de que el precio esté en la respuesta
            if "price" in response_data and response_data["price"] == 0:
                response_data["price"] = current_price
                
            return response_data
    except Exception as e:
        print(f"❌ Error llamando al módulo AI: {e}")
        print(traceback.format_exc())
        raise RuntimeError(f"No se pudo obtener respuesta del módulo AI en {AI_MODULE_URL}: {e}")

async def get_current_price(symbol: str) -> float:
    """
    Obtiene el precio actual de Binance para el símbolo.
    """
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("price", 0))
    except Exception as e:
        print(f"Error obteniendo precio de Binance: {e}")
        # Precios de fallback
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

async def process_message(text: str) -> None:
    """
    Simula el flujo de Telegram: imprime la interacción en consola.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Tú: {text}")
    print("[Bot] 🔎 Procesando mensaje...")

    # Verificar si es una solicitud de señal y detectar timeframe
    signal_keywords = ["dame una señal", "señal de trading", "señal para", "dame señal", 
                      "generar señal", "necesito una señal", "quiero una señal"]
    
    is_signal_request = any(keyword in text.lower() for keyword in signal_keywords)
    
    if is_signal_request:
        print(f"[Bot] 🔍 Detectada solicitud de señal: '{text}'")
        
        # Detectar timeframe en la solicitud
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
            if any(pattern in text.lower() for pattern in patterns):
                detected_timeframe = tf
                print(f"[Bot] 🕒 Timeframe detectado: {tf}")
                break
        
        # Modificar el prompt si se detectó un timeframe
        if detected_timeframe:
            modified_text = f"{text} (TIMEFRAME={detected_timeframe})"
            print(f"[Bot] 📝 Prompt modificado: '{modified_text}'")
            text = modified_text
        else:
            print("[Bot] ⚠️ No se detectó timeframe explícito, se usará el default: 1d")
    
    try:
        data = await simulate_ai_response(text)
    except Exception as e:
        print(f"[Bot] ❌ {e}")
        return

    # Verificar si la respuesta contiene un análisis
    if "analysis" in data:
        symbol = data.get("symbol", "Crypto")
        timeframes = data.get("timeframes", ["1d"])
        timeframe = timeframes[0] if timeframes else "1d"
        current_price = data.get("price", 0)
        analysis = data.get("analysis", "<sin análisis>")
        
        # No añadir nota sobre los factores fundamentales, ya que queremos que se obtengan de fuentes externas
        
        msg = (
            f"🧠 Análisis IA para {symbol} ({timeframe}):\n\n"
            f"💰 Precio actual: ${current_price}\n\n"
            f"{analysis}\n\n"
            "⚠️ No es asesoramiento financiero."
        )
    # Si es una señal de trading (para compatibilidad futura)
    elif "signal" in data:
        signal_text = data.get("signal", "")
        print(f"Señal de trading recibida: {signal_text}")
        msg = signal_text
    else:
        msg = data.get("response", "No he podido procesar tu mensaje. ¿Puedes intentarlo de nuevo?")

    print(f"[Bot] {msg}")

async def main() -> None:
    print("=== Simulador del Bot de Telegram ===")
    print("Escribe tus mensajes o 'salir' para terminar.\n")

    # Mensaje de bienvenida
    print("[Bot] ¡Hola! Puedes preguntarme sobre criptomonedas, por ejemplo: 'Analiza Bitcoin en 4h'.")

    while True:
        try:
            text = input("Tú: ")
            if text.lower() in ("salir", "exit", "quit"):
                print("¡Hasta luego!")
                break
            await process_message(text)
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            break
        except Exception as e:
            print(f"Error inesperado: {e}")
            print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
