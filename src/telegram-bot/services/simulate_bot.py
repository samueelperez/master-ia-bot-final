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

# Configuración del módulo AI
AI_MODULE_URL = "http://localhost:9001"  # Valor fijo para pruebas
print(f"Using AI_MODULE_URL: {AI_MODULE_URL}")

async def simulate_ai_response(prompt: str) -> dict:
    """
    Llama al endpoint analyze del módulo AI.
    Si no se puede obtener una respuesta válida, lanza excepción.
    """
    payload = {"prompt": prompt}
    headers = {"Authorization": "Bearer test-demo-token"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Health check
            health = await client.get(f"{AI_MODULE_URL}/health", timeout=5.0)
            health.raise_for_status()

            # Llamada principal
            resp = await client.post(
                f"{AI_MODULE_URL}/analyze",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"❌ Error llamando al módulo AI: {e}")
        print(traceback.format_exc())
        raise RuntimeError(f"No se pudo obtener respuesta del módulo AI en {AI_MODULE_URL}: {e}")

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

    response_type = data.get("response_type", "")
    is_analysis = data.get("is_analysis_request", False) or response_type == "analysis"
    
    # Si es una señal de trading
    if response_type == "signal":
        signal_text = data.get("signal", "")
        print(f"Señal de trading recibida: {signal_text}")
        msg = signal_text
    # Si es un análisis
    elif is_analysis:
        symbol = data.get("symbol", "Crypto")
        timeframe = data.get("timeframe", "1d")
        analysis = data.get("analysis", "<sin análisis>")
        msg = (
            f"🧠 Análisis IA para {symbol} ({timeframe}):\n\n"
            f"{analysis}\n\n"
            "⚠️ No es asesoramiento financiero."
        )
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
