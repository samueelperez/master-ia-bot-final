import os
import sys
import traceback
import time
import json
from typing import List, Dict, Any, Optional, Tuple

# Importar pandas para cálculos de indicadores
try:
    import pandas as pd  # type: ignore
except ImportError:
    pd = None

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️ python-dotenv no disponible, usando variables de entorno del sistema")

# Dependencias externas (asegúrate de instalarlas en tu entorno)
try:
    import httpx  # type: ignore
except ImportError:
    httpx = None

try:
    import uvicorn  # type: ignore
except ImportError:
    uvicorn = None

try:
    from fastapi import FastAPI, HTTPException  # type: ignore
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
except ImportError:
    FastAPI = None  # type: ignore
    HTTPException = Exception  # type: ignore
    CORSMiddleware = None  # type: ignore

try:
    from pydantic import BaseModel  # type: ignore
except ImportError:
    BaseModel = object  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except ImportError:
    OpenAI = None  # type: ignore

# Importar sistema de estrategias
try:
    from strategies.signal_generator import SignalGenerator
    from strategies.strategy_engine import StrategyEngine
    STRATEGIES_AVAILABLE = True
    print("🎯 Sistema de estrategias avanzadas disponible")
except ImportError as e:
    STRATEGIES_AVAILABLE = False
    print(f"⚠️ Sistema de estrategias no disponible: {e}")

# Importar servicios de datos externos
try:
    from services.external_data.data_integration_service import get_formatted_data_for_prompt
    EXTERNAL_DATA_AVAILABLE = True
    # print("Servicios de datos externos disponibles")
except ImportError as e:
    # Intentar importar desde la ruta relativa
    try:
        import sys
        import os
        # Añadir el directorio actual al path
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services.external_data.data_integration_service import get_formatted_data_for_prompt
        EXTERNAL_DATA_AVAILABLE = True
        # print("Servicios de datos externos disponibles (importación relativa)")
    except ImportError as e2:
        EXTERNAL_DATA_AVAILABLE = False
        # print(f"Servicios de datos externos no disponibles: {e2}")

# Añadir directorio raíz para importaciones backend
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(ROOT_DIR))

# Importar servicios de backend, si están disponibles
try:
    from backend.app.services.fetcher import fetch_ohlcv
    from backend.app.services.ta_service import compute_indicators
    BACKEND_AVAILABLE = True
    # print("Backend disponible: servicios importados correctamente")
except ImportError as e:
    BACKEND_AVAILABLE = False
    # print(f"Backend no disponible: {e}")

# Configuración de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY no encontrada. Funcionará en modo limitado.")
    OPENAI_API_KEY = None

# Inicializar FastAPI
if OPENAI_API_KEY:
token_preview = OPENAI_API_KEY[:4] + '...' + OPENAI_API_KEY[-4:]
print(f"Iniciando servicio con API Key: {token_preview} y BACKEND_URL: {BACKEND_URL}")
else:
    print(f"Iniciando servicio sin API Key (modo limitado) y BACKEND_URL: {BACKEND_URL}")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar cliente según el formato de la API key
USE_ANTHROPIC = False
client = None

# Inicializar cliente OpenAI
if OPENAI_API_KEY:
try:
    # Usar la API key de OpenAI proporcionada
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("Cliente OpenAI inicializado correctamente.")
    USE_ANTHROPIC = False
except Exception as e:
    print(f"Error al inicializar OpenAI: {e}")
        client = None
else:
    print("Cliente OpenAI no disponible - funcionando en modo fallback")

# Inicializar sistema de estrategias
signal_generator = None
if STRATEGIES_AVAILABLE:
    try:
        signal_generator = SignalGenerator()
        print("✅ Sistema de estrategias inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando sistema de estrategias: {e}")
        signal_generator = None

# Modelos de datos
class AnalyzeRequest(BaseModel):
    symbol: str
    timeframes: List[str]
    user_prompt: str = ""

class SignalRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    strategy_name: Optional[str] = None

class FullPromptRequest(BaseModel):
    prompt: str
    user_context: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = []

# Precios de fallback
FALLBACK_PRICES: Dict[str, float] = {
    "BTC": 50000.0,
    "ETH": 2000.0,
    "SOL": 20.0,
}

async def fetch_price_coingecko(symbol: str) -> Optional[float]:
    """
    Implementación de ejemplo para solicitar el precio a CoinGecko.
    """
    if not httpx:
        return None
    coin_id = symbol.lower()
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data.get(coin_id, {}).get("usd", 0))
    except Exception:
        return None

async def fetch_price_backend(symbol: str) -> Optional[float]:
    """
    Solicita precio al backend si está disponible.
    """
    if not BACKEND_AVAILABLE:
        return None
    try:
        df = fetch_ohlcv(symbol, timeframe='1m', limit=1)
        return float(df['close'].iloc[-1])
    except Exception:
        return None

async def fetch_price_binance(symbol: str) -> Optional[float]:
    """
    Solicita precio a Binance directamente.
    """
    if not httpx:
        return None
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return float(resp.json().get("price", 0))
    except Exception:
        return None

async def get_current_price(symbol: str) -> float:
    """
    Obtiene el precio actual mediante varias fuentes con fallback.
    """
    for fetcher in (fetch_price_coingecko, fetch_price_backend, fetch_price_binance):
        try:
            price = await fetcher(symbol)
            if price and price > 0:
                return price
        except Exception:
            continue
    return FALLBACK_PRICES.get(symbol.upper(), 0.0)

@app.get('/health')
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.post('/analyze')
async def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Endpoint principal para análisis de criptomonedas.
    """
    if not req.symbol or not req.timeframes:
        raise HTTPException(status_code=400, detail="symbol y timeframes son obligatorios")
    
    symbol = req.symbol.upper()
    timeframe = req.timeframes[0]
    
    # Obtener precio actual
    current_price = await get_current_price(symbol)
    
    # Generar análisis con IA
    if client:
        try:
            system_prompt = f"""
            Eres un analista experto en criptomonedas. Debes proporcionar un análisis técnico 
            con la siguiente estructura EXACTA:

            📊 ANÁLISIS DE {symbol} ({timeframe})

            📈 DIRECCIÓN: [ALCISTA/BAJISTA/LATERAL]

            💡 ANÁLISIS TÉCNICO:
            [Análisis técnico detallado incluyendo RSI, MACD, volumen, tendencias, etc.]

            📰 FACTORES FUNDAMENTALES:
            [Análisis de factores fundamentales, noticias relevantes, sentimiento del mercado]

            🔑 NIVELES IMPORTANTES:
            - Soporte: $[precio] ([explicación del nivel de soporte])
            - Resistencia: $[precio] ([explicación del nivel de resistencia])

            🔮 ESCENARIO PROBABLE:
            [Predicción de lo que probablemente sucederá en el corto plazo]

            ⏱️ HORIZONTE TEMPORAL: [tiempo específico]

            IMPORTANTE: Mantén esta estructura exacta con los emojis y formato. Usa datos reales y análisis técnico profesional.
            """
            
    messages = [
        {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Análisis solicitado para: {symbol}\nPrecio actual: ${current_price:,.2f}\nTimeframes: {', '.join(req.timeframes)}\n\nConsulta: {req.user_prompt}"}
            ]
            
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.6,
                max_tokens=600
        )
        
            analysis = response.choices[0].message.content.strip()
        
        return {
            "symbol": symbol,
                "timeframes": req.timeframes,
        "price": current_price,
        "analysis": analysis,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"Error en análisis: {e}")
            raise HTTPException(status_code=500, detail="Error procesando análisis")
    else:
        raise HTTPException(status_code=500, detail="Servicio de IA no disponible")

@app.post('/signal')
async def signal(req: SignalRequest) -> Dict[str, Any]:
    """
    Endpoint alternativo para generar señales de trading.
    Alias de /generate_signal para compatibilidad.
    """
    return await generate_signal(req)

@app.post('/generate_signal')
async def generate_signal(req: SignalRequest) -> Dict[str, Any]:
    """
    Genera una señal de trading para el símbolo y timeframe especificados.
    """
    try:
        symbol = req.symbol.upper()
        timeframe = req.timeframe
        strategy_name = req.strategy_name
        
        # Obtener precio actual
        current_price = await get_current_price(symbol)
        
        # Calcular indicadores técnicos básicos
        indicators = {}
        try:
            # Intentar obtener datos históricos para calcular indicadores
            if BACKEND_AVAILABLE:
                df = fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
                if not df.empty:
                    # Calcular RSI básico
                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs)).iloc[-1]
                    
                    # Calcular MACD básico
                    ema12 = df['close'].ewm(span=12).mean()
                    ema26 = df['close'].ewm(span=26).mean()
                    macd_line = ema12.iloc[-1] - ema26.iloc[-1]
                    signal_line = (ema12 - ema26).ewm(span=9).mean().iloc[-1]
                    
                    indicators = {
                        'rsi': rsi,
                        'macd': {'macd_line': macd_line, 'signal_line': signal_line}
                    }
            except Exception as e:
            print(f"Error calculando indicadores: {e}")
            indicators = {'rsi': 50, 'macd': {'macd_line': 0, 'signal_line': 0}}
        
        # Determinar dirección basado en indicadores
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', {}).get('macd_line', 0)
        signal = indicators.get('macd', {}).get('signal_line', 0)
        
        direction = "LONG"
        if rsi < 40 or (macd < 0 and macd < signal):
            direction = "SHORT"
        
        # Calcular niveles de trading
        entry = current_price
        
        # Porcentajes según timeframe
        timeframe_percentages = {
            "1m": {"sl": 0.005, "tp1": 0.005, "tp2": 0.01},
            "5m": {"sl": 0.01, "tp1": 0.01, "tp2": 0.02},
            "15m": {"sl": 0.015, "tp1": 0.015, "tp2": 0.025},
            "30m": {"sl": 0.02, "tp1": 0.02, "tp2": 0.03},
            "1h": {"sl": 0.025, "tp1": 0.025, "tp2": 0.04},
            "4h": {"sl": 0.03, "tp1": 0.03, "tp2": 0.045},
            "1d": {"sl": 0.03, "tp1": 0.03, "tp2": 0.05},
            "1w": {"sl": 0.05, "tp1": 0.05, "tp2": 0.08}
        }
        
        percentages = timeframe_percentages.get(timeframe, {"sl": 0.03, "tp1": 0.03, "tp2": 0.05})
        
        # Calcular niveles
        if direction == "LONG":
            sl = entry * (1 - percentages["sl"])
            tp1 = entry * (1 + percentages["tp1"])
            tp2 = entry * (1 + percentages["tp2"])
        else:
            sl = entry * (1 + percentages["sl"])
            tp1 = entry * (1 - percentages["tp1"])
            tp2 = entry * (1 - percentages["tp2"])
        
        # Generar explicación
        if client:
        system_prompt = (
            "Eres un experto en trading de criptomonedas. "
            "Genera una explicación clara y concisa para una señal de trading. "
                "La explicación debe ser de 2-3 frases, mencionando el análisis técnico."
        )
        
        user_prompt = (
            f"Genera una explicación para una señal de trading de {symbol} en dirección {direction}. "
            f"Entrada: {entry:.2f}, Stop Loss: {sl:.2f}, Take Profit 1: {tp1:.2f}, Take Profit 2: {tp2:.2f}. "
            f"RSI: {rsi:.2f}, MACD: {macd:.2f}."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=150,
        )
        
        explanation = response.choices[0].message.content.strip()
        else:
            explanation = f"Señal {direction} para {symbol} basada en análisis técnico. RSI: {rsi:.2f}"
        
        # Apalancamiento recomendado
        timeframe_leverage = {
            "1m": 5, "5m": 7, "15m": 8, "30m": 10,
            "1h": 12, "4h": 15, "1d": 20, "1w": 25
        }
        leverage = timeframe_leverage.get(timeframe, 10)
        
        # Formatear la señal para el bot de Telegram
        signal_text = f"""🎯 SEÑAL DE TRADING {symbol}/{timeframe}

📈 DIRECCIÓN: {direction}
💰 ENTRADA: ${entry:,.2f}
🛑 STOP LOSS: ${sl:,.2f}
🎯 TAKE PROFIT 1: ${tp1:,.2f}
🎯 TAKE PROFIT 2: ${tp2:,.2f}
⚡ APALANCAMIENTO: {leverage}x

💡 EXPLICACIÓN:
{explanation}

⚠️ No es asesoramiento financiero. Trading conlleva riesgos."""

        return {
            "signal": {
                "recommendation": signal_text
            }
        }
    except Exception as e:
        print(f"Error al generar señal: {e}")
        return {
            "response_type": "error",
            "error": f"Error al generar señal: {str(e)}"
        }

@app.post('/generate')
async def generate(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Endpoint general que detecta automáticamente el tipo de solicitud.
    """
    if not req.symbol or not req.timeframes:
        raise HTTPException(status_code=400, detail="symbol y timeframes son obligatorios")
    
    symbol = req.symbol.upper()
    timeframe = req.timeframes[0]
    
    # Obtener precio actual
    current_price = await get_current_price(symbol)
    
    # Detectar tipo de solicitud
    prompt_lower = req.user_prompt.lower()
    
    # Detectar señales de trading
    signal_keywords = ["dame una señal", "señal de trading", "señal para", "dame señal", 
                      "generar señal", "necesito una señal", "quiero una señal", "dame la señal", 
                      "señal de", "trading signal", "signal"]
    
    # Detectar consultas conversacionales
    conversation_keywords = ["compré", "tengo", "invertí", "debería vender", "fue buena compra", 
                           "qué hago", "cómo ves", "entrada a", "posición en", "holdeo"]
    
    if any(keyword in prompt_lower for keyword in signal_keywords):
        # Es una solicitud de señal
        signal_req = SignalRequest(symbol=symbol, timeframe=timeframe)
        return await generate_signal(signal_req)
    elif any(keyword in prompt_lower for keyword in conversation_keywords):
        # Es una consulta conversacional
        if client:
            system_prompt = f"""
            Eres un asesor experto en criptomonedas. El usuario está consultando sobre una posición específica.
            Proporciona consejos útiles y análisis basado en el contexto de su consulta.
            
            Precio actual de {symbol}: ${current_price:,.2f}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.user_prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=400
            )
            
            analysis = response.choices[0].message.content.strip()
            
                return {
                "symbol": symbol,
                "timeframes": req.timeframes,
                "price": current_price,
                "analysis": analysis,
                    "response_type": "conversation",
                "timestamp": time.time()
            }
        else:
            return {
                "symbol": symbol,
                "timeframes": req.timeframes,
                "price": current_price,
                "analysis": "Servicio de IA no disponible para consultas conversacionales.",
                "response_type": "conversation",
                "timestamp": time.time()
            }
    else:
        # Es un análisis general
        return await analyze(req)

@app.post('/analyze_prompt')
async def analyze_prompt(req: FullPromptRequest) -> Dict[str, Any]:
    """
    Endpoint para análisis de prompts generales.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Servicio de IA no disponible")
    
    try:
        system_prompt = """
        Eres un experto analista de criptomonedas y mercados financieros.
        Proporciona análisis detallados y consejos útiles basados en la consulta del usuario.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.prompt}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=600
        )
        
        analysis = response.choices[0].message.content.strip()
            
            return {
            "prompt": req.prompt,
            "analysis": analysis,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"Error en análisis de prompt: {e}")
        raise HTTPException(status_code=500, detail="Error procesando análisis")

if __name__ == '__main__':
    if uvicorn:
        uvicorn.run('llm_inference:app', host='0.0.0.0', port=int(os.getenv('PORT', 9004)))
    else:
        print("Uvicorn no está disponible. No se puede arrancar el servidor.")