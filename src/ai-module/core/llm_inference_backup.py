import os
import sys
import traceback
import time
import json
from typing import List, Dict, Any, Optional, Tuple

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

async def get_historical_data(symbol: str, timeframe: str, limit: int = 100) -> Dict[str, List[Any]]:
    """
    Obtiene datos OHLCV del backend o directamente de Binance si el backend no está disponible.
    """
    try:
        # 1. Intentar obtener datos del backend
        if BACKEND_AVAILABLE:
            print(f"Solicitando datos OHLCV para {symbol} en timeframe {timeframe}")
            try:
                df = fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
                if not df.empty:
                    print(f"Datos obtenidos correctamente: {len(df)} filas")
                    return {
                        "open": df["open"].tolist(),
                        "high": df["high"].tolist(),
                        "low": df["low"].tolist(),
                        "close": df["close"].tolist(),
                        "volume": df["volume"].tolist()
                    }
                else:
                    print(f"No se obtuvieron datos para {symbol} en {timeframe}")
            except Exception as e:
                print(f"Error al obtener datos OHLCV del backend: {e}")
                traceback.print_exc()
        
        # 2. Si el backend no está disponible o falló, intentar obtener datos directamente de Binance
        print("Intentando obtener datos directamente de Binance")
        try:
            # Mapeo de timeframes a formato de Binance
            binance_timeframe_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"
            }
            
            binance_tf = binance_timeframe_map.get(timeframe, "1h")
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={binance_tf}&limit={limit}"
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                if data:
                    # Convertir datos de Binance al formato requerido
                    # Formato Binance: [timestamp, open, high, low, close, volume, ...]
                    opens = [float(item[1]) for item in data]
                    highs = [float(item[2]) for item in data]
                    lows = [float(item[3]) for item in data]
                    closes = [float(item[4]) for item in data]
                    volumes = [float(item[5]) for item in data]
                    
                    print(f"Datos obtenidos de Binance: {len(data)} puntos")
                    return {
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes
                    }
        except Exception as e:
            print(f"Error al obtener datos de Binance: {e}")
            traceback.print_exc()
        
        # Si llegamos aquí, no se pudieron obtener datos
        print(f"No se pudieron obtener datos históricos para {symbol} en {timeframe}")
        return {}
    except Exception as e:
        print(f"Error general al obtener datos históricos: {e}")
        traceback.print_exc()
        return {}

def calculate_basic_indicators(historical_data: Dict[str, List[Any]]) -> Dict[str, Any]:
    """
    Calcula indicadores técnicos básicos cuando el backend no está disponible.
    """
    result = {}
    
    try:
        closes = historical_data.get("close", [])
        if not closes:
            return {}
        
        # Calcular RSI (Relative Strength Index)
        try:
            # Implementación simple de RSI
            gains = []
            losses = []
            
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change >= 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            if not gains or not losses:
                result["rsi"] = 50  # Valor neutral si no hay suficientes datos
            else:
                avg_gain = sum(gains) / len(gains)
                avg_loss = sum(losses) / len(losses)
                
                if avg_loss == 0:
                    result["rsi"] = 100
                else:
                    rs = avg_gain / avg_loss
                    result["rsi"] = 100 - (100 / (1 + rs))
                
                print(f"RSI calculado: {result['rsi']}")
        except Exception as e:
            print(f"Error al calcular RSI: {e}")
            traceback.print_exc()
        
        # Calcular MACD (Moving Average Convergence Divergence)
        try:
            # Implementación simple de MACD
            if len(closes) >= 26:
                # EMA 12
                ema12 = sum(closes[-12:]) / 12
                # EMA 26
                ema26 = sum(closes[-26:]) / 26
                
                macd_line = ema12 - ema26
                # Signal line (EMA 9 del MACD)
                signal_line = macd_line  # Simplificado, normalmente sería EMA de 9 períodos del MACD
                histogram = macd_line - signal_line
                
                result["macd"] = {
                    "macd_line": macd_line,
                    "signal_line": signal_line,
                    "histogram": histogram
                }
                
                print(f"MACD calculado: {result['macd']}")
        except Exception as e:
            print(f"Error al calcular MACD: {e}")
            traceback.print_exc()
        
        # Calcular volumen promedio
        try:
            volumes = historical_data.get("volume", [])
            if volumes:
                avg_volume = sum(volumes) / len(volumes)
                result["volume_avg"] = avg_volume
                print(f"Volumen promedio calculado: {result['volume_avg']}")
        except Exception as e:
            print(f"Error al calcular volumen promedio: {e}")
            traceback.print_exc()
        
        return result
    except Exception as e:
        print(f"Error general al calcular indicadores básicos: {e}")
        traceback.print_exc()
        return {}

async def get_technical_indicators(symbol: str, timeframe: str) -> Dict[str, Any]:
    """
    Calcula indicadores técnicos usando backend o fallback.
    """
    try:
        historical = await get_historical_data(symbol, timeframe)
        if BACKEND_AVAILABLE:
            try:
                return compute_indicators(historical)
            except Exception as e:
                print(f"Error al calcular indicadores con backend: {e}")
                traceback.print_exc()
                print("Usando cálculo básico de indicadores como fallback")
                return calculate_basic_indicators(historical)
        else:
            print("Backend no disponible, usando cálculo básico de indicadores")
            return calculate_basic_indicators(historical)
    except Exception as e:
        print(f"Error en get_technical_indicators: {e}")
        traceback.print_exc()
        return {}

async def determine_needed_data(prompt: str) -> Dict[str, Any]:
    """
    Usa la IA para determinar qué datos se necesitan para responder a la consulta.
    """
    # Primero, intentar extraer información básica mediante reglas simples
    # Lista de símbolos comunes y sus variantes
    symbol_variants = {
        "BTC": ["btc", "bitcoin", "bitcoins", "xbt"],
        "ETH": ["eth", "ethereum", "ether"],
        "SOL": ["sol", "solana"],
        "XRP": ["xrp", "ripple"],
        "ADA": ["ada", "cardano"],
        "DOGE": ["doge", "dogecoin"],
        "SHIB": ["shib", "shiba", "shibainu"],
        "BNB": ["bnb", "binance", "binancecoin"],
        "DOT": ["dot", "polkadot"],
        "AVAX": ["avax", "avalanche"]
    }
    
    # Buscar símbolos en el prompt
    detected_symbol = None
    for symbol, variants in symbol_variants.items():
        if any(variant in prompt.lower() for variant in variants):
            detected_symbol = symbol
            break
    
    # Buscar timeframes comunes
    timeframe_patterns = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    detected_timeframe = None
    for tf in timeframe_patterns:
        if tf in prompt:
            detected_timeframe = tf
            break
    
    # Palabras clave que sugieren un análisis
    analysis_keywords = [
        "analiza", "análisis", "analizar", "análisis técnico", 
        "precio", "tendencia", "chart", "gráfico", "como está",
        "cómo está", "dame información", "qué opinas", "que opinas",
        "muéstrame", "muestrame", "dime sobre", "analizame", "analízame"
    ]
    
    # Verificar si parece ser una solicitud de análisis
    is_analysis_request = any(keyword in prompt.lower() for keyword in analysis_keywords)
    
    # Usar la IA para un análisis más detallado
    system_prompt = (
        "Eres un asistente que analiza consultas sobre criptomonedas. "
        "Tu tarea es determinar qué datos técnicos se necesitan para responder a la consulta del usuario. "
        "Responde SOLO con un objeto JSON que contenga los siguientes campos (solo si son relevantes):\n"
        "- symbol: símbolo de la criptomoneda (ej: BTC, ETH)\n"
        "- timeframe: marco temporal (ej: 5m, 1h, 1d)\n"
        "- indicators: lista de indicadores necesarios (ej: ['price', 'rsi', 'macd', 'volume'])\n"
        "- is_analysis: booleano que indica si se requiere un análisis completo\n\n"
        "Ejemplo 1: Para 'Analiza Bitcoin en 4h', responderías: "
        "{'symbol': 'BTC', 'timeframe': '4h', 'indicators': ['price', 'volume', 'rsi', 'macd'], 'is_analysis': true}\n\n"
        "Ejemplo 2: Para '¿Cuál es el precio actual de Ethereum?', responderías: "
        "{'symbol': 'ETH', 'indicators': ['price'], 'is_analysis': false}\n\n"
        "Ejemplo 3: Para '¿Cómo está el RSI de Bitcoin en 5 minutos?', responderías: "
        "{'symbol': 'BTC', 'timeframe': '5m', 'indicators': ['rsi'], 'is_analysis': false}\n\n"
        "Ejemplo 4: Para 'analizame eth', responderías: "
        "{'symbol': 'ETH', 'indicators': ['price', 'volume', 'rsi', 'macd'], 'is_analysis': true}\n\n"
        "Ejemplo 5: Para 'dame información sobre Solana', responderías: "
        "{'symbol': 'SOL', 'indicators': ['price', 'volume', 'rsi', 'macd'], 'is_analysis': true}\n\n"
        "Ejemplo 6: Para 'qué opinas de DOGE ahora mismo', responderías: "
        "{'symbol': 'DOGE', 'indicators': ['price', 'volume', 'rsi', 'macd'], 'is_analysis': true}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.1,  # Baja temperatura para respuestas más deterministas
            max_tokens=150,
            response_format={"type": "json_object"}  # Forzar respuesta en formato JSON
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Si la IA no detectó un símbolo pero nosotros sí, usamos el nuestro
        if not result.get("symbol") and detected_symbol:
            result["symbol"] = detected_symbol
            print(f"Símbolo detectado manualmente: {detected_symbol}")
        
        # Si la IA no detectó un timeframe, usamos el detectado manualmente o '1h' como predeterminado
        if not result.get("timeframe"):
            if detected_timeframe:
                result["timeframe"] = detected_timeframe
                print(f"Timeframe detectado manualmente: {detected_timeframe}")
            else:
                result["timeframe"] = "1h"  # Timeframe predeterminado cuando no se especifica
                print(f"Usando timeframe predeterminado: 1h")
        
        # Si la IA no clasificó como análisis pero parece serlo, lo marcamos como tal
        if not result.get("is_analysis") and is_analysis_request:
            result["is_analysis"] = True
            # Asegurarnos de que tenga los indicadores necesarios para un análisis
            if "indicators" not in result or not result["indicators"]:
                result["indicators"] = ["price", "volume", "rsi", "macd"]
            print(f"Solicitud de análisis detectada manualmente")
        
        print(f"Resultado final de determine_needed_data: {result}")
        return result
    except Exception as e:
        print(f"Error al determinar datos necesarios: {e}")
        # Fallback con detección manual
        indicators = ["price"]
        if is_analysis_request:
            indicators = ["price", "volume", "rsi", "macd"]
        
        return {
            "symbol": detected_symbol, 
            "timeframe": detected_timeframe or "1h",  # Timeframe predeterminado: 1h
            "indicators": indicators, 
            "is_analysis": is_analysis_request
        }

async def fetch_requested_data(needed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene los datos solicitados del backend.
    """
    result = {}
    symbol = needed_data.get("symbol")
    timeframe = needed_data.get("timeframe", "1d")
    indicators = needed_data.get("indicators", [])
    
    if not symbol:
        return {"error": "No se pudo determinar el símbolo de la criptomoneda"}
    
    # Obtener precio actual si se solicita
    if "price" in indicators:
        try:
            result["price"] = await get_current_price(symbol)
        except Exception as e:
            print(f"Error al obtener precio: {e}")
            return {"error": "No se pudo obtener el precio actual"}
    
    # Obtener datos históricos si se necesitan para indicadores
    if any(ind in indicators for ind in ["rsi", "macd", "volume", "sma", "ema"]):
        try:
            historical_data = await get_historical_data(symbol, timeframe)
            print(f"Datos históricos obtenidos para {symbol} en {timeframe}: {len(historical_data.get('close', []))} puntos")
            
            if not historical_data or not historical_data.get('close'):
                return {"error": f"No se pudieron obtener datos históricos para {symbol} en timeframe {timeframe}"}
            
            # Calcular indicadores solicitados
            try:
                if BACKEND_AVAILABLE:
                    try:
                        technical_indicators = compute_indicators(historical_data)
                        print(f"Indicadores calculados con backend: {technical_indicators.keys()}")
                    except Exception as e:
                        print(f"Error al calcular indicadores con backend: {e}")
                        technical_indicators = calculate_basic_indicators(historical_data)
                        print(f"Indicadores calculados con método básico: {technical_indicators.keys()}")
                else:
                    technical_indicators = calculate_basic_indicators(historical_data)
                    print(f"Backend no disponible, indicadores calculados con método básico: {technical_indicators.keys()}")
                
                # Mapear indicadores que tienen nombres diferentes
                indicator_mapping = {
                    "volume": "volume_avg"  # Si se solicita 'volume', usar 'volume_avg'
                }
                
                for indicator in indicators:
                    if indicator in technical_indicators:
                        result[indicator] = technical_indicators[indicator]
                    elif indicator in indicator_mapping and indicator_mapping[indicator] in technical_indicators:
                        # Usar el indicador alternativo si está disponible
                        result[indicator] = technical_indicators[indicator_mapping[indicator]]
                        print(f"Usando {indicator_mapping[indicator]} como alternativa para {indicator}")
                    else:
                        print(f"Indicador {indicator} no disponible en los resultados")
            except Exception as e:
                print(f"Error al calcular indicadores: {e}")
                traceback.print_exc()
                return {"error": f"Error al calcular indicadores: {str(e)}"}
        except Exception as e:
            print(f"Error al procesar indicadores: {e}")
            traceback.print_exc()
            return {"error": f"Error al calcular indicadores: {str(e)}"}
    
    # Verificar si hay indicadores solicitados que no se obtuvieron
    missing_indicators = []
    for ind in indicators:
        if ind not in result and ind != "price":
            missing_indicators.append(ind)
    
    if missing_indicators:
        return {"error": f"No se pudieron obtener los siguientes indicadores: {', '.join(missing_indicators)}"}
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data": result,
        "is_analysis": needed_data.get("is_analysis", False)
    }

async def generate_response_with_data(prompt: str, data_context: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Genera una respuesta basada en los datos obtenidos.
    """
    is_analysis = data_context.get("is_analysis_request", False)
    symbol = data_context.get("symbol")
    timeframe = data_context.get("timeframe")
    
    # Detectar saludos y preguntas conversacionales comunes
    greeting_patterns = [
        "hola", "hey", "saludos", "buenas", "qué tal", "que tal", 
        "cómo estás", "como estas", "qué hay", "que hay"
    ]
    
    # Verificar si es un saludo simple
    is_greeting = any(pattern in prompt.lower() for pattern in greeting_patterns)
    
    if is_greeting:
        # Respuesta amigable para saludos con emojis
        responses = [
            "¡Hola! 👋 Soy tu asistente de criptomonedas. ✨ ¿En qué puedo ayudarte hoy? Puedes pedirme análisis como 'analiza Bitcoin' 📊 o 'cómo está ETH' 📈",
            "¡Hey! 😎 Estoy aquí para ayudarte con análisis de criptomonedas. 🚀 Prueba a preguntarme sobre BTC, ETH o cualquier otra cripto. ¿Qué quieres saber? 💰",
            "¡Saludos! 🌟 Soy tu analista de criptomonedas favorito. 🤖 Puedo darte información sobre precios 💲, tendencias 📈 y análisis técnico. ¿Qué te gustaría saber hoy? 🔍",
            "¡Hola! 🎯 ¿Listo para explorar el mundo cripto? 🌍 Pregúntame sobre cualquier criptomoneda y te daré un análisis detallado. ¡Vamos a ello! 💪",
            "¡Qué tal! 🌈 Tu experto en criptomonedas está listo para ayudarte. 🧠 ¿Quieres saber sobre Bitcoin? ¿Ethereum? ¿O tal vez alguna altcoin? ¡Pregúntame lo que quieras! 🚀"
        ]
        import random
        response = random.choice(responses)
        
        return {
            "is_analysis_request": False,
            "response_type": "conversation",
            "response": response
        }
    
    if "error" in data_context:
        # Si no es un saludo pero hay un error, dar una respuesta más útil
        response = (
            "Parece que estás intentando tener una conversación. Estoy especializado en análisis de criptomonedas. "
            "Puedes preguntarme cosas como 'analiza Bitcoin', 'cómo está ETH en 4h' o 'dame un análisis de Solana'."
        )
        
        return {
            "is_analysis_request": False,
            "response_type": "conversation",
            "response": response
        }
    
    # Preparar contexto técnico para la IA
    technical_context = f"""
    Símbolo: {symbol}
    Timeframe: {timeframe or 'No especificado'}
    """
    
    # Añadir datos obtenidos al contexto
    data = data_context.get("data", {})
    if data:
        technical_context += "\nDatos disponibles:\n"
        for key, value in data.items():
            technical_context += f"- {key}: {value}\n"
    
    # Añadir datos externos si están disponibles
    external_data = ""
    if EXTERNAL_DATA_AVAILABLE and symbol:
        try:
            # Obtener datos externos de manera asíncrona
            external_data = await get_formatted_data_for_prompt(symbol)
            if external_data:
                technical_context += f"\n{external_data}\n"
        except Exception as e:
            print(f"Error al obtener datos externos: {e}")
            # No añadir nada si hay un error
    
    # Seleccionar el prompt del sistema según el tipo de consulta
    if is_analysis:
        # Usar el prompt de análisis completo
        system_prompt = (
            "Eres un asistente especializado en análisis de criptomonedas para usuarios principiantes. "
            "Cuando te pidan analizar una criptomoneda, proporciona SIEMPRE:\n\n"
            "1. DIRECCIÓN GENERAL: Indica claramente si la tendencia es alcista, bajista o lateral.\n\n"
            "2. ANÁLISIS GENERAL: Explica en 4-5 frases por qué has llegado a esa conclusión sobre la dirección. "
            "Usa lenguaje sencillo y evita jerga técnica. Incluye:\n"
            "   - Patrones de precio visibles explicados de manera sencilla\n"
            "   - Confirmación o divergencia del volumen (explica si el volumen respalda o contradice el movimiento del precio)\n"
            "   - Estado del RSI (sobrecompra >70, sobreventa <30, o zona neutral) en términos simples\n"
            "   - Señales del MACD (impulso positivo/negativo) explicadas de forma sencilla\n"
            "   - Contexto relevante del mercado general y noticias importantes\n"
            "   - Si el timeframe es corto (1m, 5m, 15m), menciona que el análisis es de muy corto plazo\n"
            "   - Si el timeframe es 1h, menciona brevemente la tendencia diaria (1d) como contexto adicional\n\n"
            "3. FACTORES FUNDAMENTALES: Incluye información sobre noticias relevantes, eventos económicos y tendencias en redes sociales que puedan afectar al precio. Menciona el sentimiento general en redes sociales (positivo, negativo o neutral) y cómo podría influir en el precio.\n\n"
            "4. SOPORTES Y RESISTENCIAS: Identifica SIEMPRE 2-3 niveles clave para la temporalidad solicitada:\n"
            "   - Al menos 1-2 soportes importantes (explicando brevemente por qué son importantes)\n"
            "   - Al menos 1-2 resistencias importantes (explicando brevemente por qué son importantes)\n"
            "   - Usa números concretos, no rangos demasiado amplios\n\n"
            "5. ESCENARIO PROBABLE: Describe brevemente qué podría ocurrir en los próximos días/semanas según la temporalidad analizada, considerando tanto factores técnicos como fundamentales.\n\n"
            "6. VALIDEZ DEL ANALISIS: Especifica claramente para qué periodo aplica este análisis.\n\n"
            "7. DISCLAIMER: Incluye siempre una advertencia sobre los riesgos de inversión.\n\n"
            "8. No menciones el marco temporal en el analisis.\n\n"
            "REGLAS ESTRICTAS DE FORMATO:\n\n"
            "1. NUNCA incluyas frases introductorias como '¡Claro!', '¡Por supuesto!', 'Aquí tienes', etc. Ve directo al formato.\n\n"
            "2. NUNCA menciones el timeframe en el texto del análisis. NO escribas frases como 'En el timeframe de 5m' o 'En el marco de tiempo de 1h'. El timeframe ya está en el título.\n\n"
            "3. NO empieces con frases como 'Bitcoin se encuentra en un patrón lateral' o 'Ethereum muestra una tendencia alcista'. La dirección ya está en la sección DIRECCIÓN.\n\n"
            "4. Comienza el análisis directamente con los patrones de precio, volumen, RSI, MACD, etc. sin mencionar la dirección ni el timeframe.\n\n"
            "5. NUNCA uses frases como 'Ethereum ha estado experimentando una tendencia bajista' o 'Bitcoin muestra una tendencia alcista'. Estas frases son redundantes.\n\n"
            "Usa este formato exacto con emojis:\n\n"
            "📊 ANÁLISIS DE [SÍMBOLO] ([TEMPORALIDAD])\n\n"
            "📈 DIRECCIÓN: [ALCISTA/BAJISTA/LATERAL]\n\n"
            "💡 ANÁLISIS TÉCNICO:\n"
            "[Análisis general en 4-5 frases incluyendo patrones, volumen, RSI, MACD y contexto de mercado]\n\n"
            "📰 FACTORES FUNDAMENTALES:\n"
            "[Análisis de noticias, eventos económicos, datos macroeconomicos y tendencias en redes sociales relevantes para la criptomoneda]\n\n"
            "🔑 NIVELES IMPORTANTES:\n"
            "- Soporte: $[PRECIO] ([breve explicación])\n"
            "- Soporte: $[PRECIO] ([breve explicación]) (si aplica)\n"
            "- Resistencia: $[PRECIO] ([breve explicación])\n"
            "- Resistencia: $[PRECIO] ([breve explicación]) (si aplica)\n\n"
            "🔮 ESCENARIO PROBABLE:\n"
            "[Descripción del escenario más probable considerando factores técnicos y fundamentales]\n\n"
            "⏱️ HORIZONTE TEMPORAL: [Periodo de validez del análisis]\n\n"
            "⚠️ No es asesoramiento financiero.\n\n"
            "IMPORTANTE: SIEMPRE proporciona un análisis completo con todos los elementos anteriores, independientemente del timeframe solicitado. Nunca respondas pidiendo más datos o diciendo que necesitas información adicional, ya que todos los datos necesarios ya están incluidos en el contexto técnico proporcionado."
        )
    else:
        # Prompt para consultas específicas
        system_prompt = (
            "Eres un asistente especializado en criptomonedas que responde consultas específicas. "
            "Usa los datos proporcionados para dar una respuesta precisa y directa. "
            "Si te preguntan por un precio, incluye el valor exacto. "
            "Si te preguntan por un indicador técnico como el RSI, proporciona su valor actual "
            "y explica brevemente qué significa ese valor (sobrecompra, sobreventa o neutral). "
            "Si no tienes acceso a los datos solicitados, indica claramente que no puedes "
            "proporcionar esa información en este momento debido a limitaciones técnicas, "
            "y sugiere al usuario que intente más tarde o que consulte una plataforma especializada. "
            "Nunca inventes datos ni proporciones aproximaciones cuando no tengas información precisa. "
            "Usa lenguaje sencillo y evita jerga técnica innecesaria."
        )
    
    # Generar respuesta con OpenAI
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{technical_context}\n\nUsuario pregunta: {prompt}"}
    ]
    
    # Añadir historial de conversación si existe
    if conversation_history:
        for msg in conversation_history:
            if len(messages) < 10:
                messages.append(msg)
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.6,
            max_tokens=500,
        )
        
        reply = response.choices[0].message.content.strip()
        
        return {
            "is_analysis_request": is_analysis,
            "response_type": "specific_data" if not is_analysis else "analysis",
            "symbol": symbol,
            "timeframe": timeframe,
            "data": data,
            "response": reply
        }
    except Exception as e:
        print(f"Error al generar respuesta: {e}")
        return {
            "is_analysis_request": False,
            "response_type": "error",
            "response": "Lo siento, no pude procesar tu consulta en este momento."
        }

@app.get('/health')
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.post('/generate')
async def generate(req: AnalyzeRequest) -> Dict[str, Any]:
    if not req.symbol or not req.timeframes:
        raise HTTPException(status_code=400, detail="symbol y timeframes son obligatorios")
    symbol = req.symbol.upper()
    timeframe = req.timeframes[0]

    # Obtener precio actual (usar el proporcionado en la solicitud si está disponible)
    current_price = req.current_price if hasattr(req, 'current_price') and req.current_price else await get_current_price(symbol)
    indicators = await get_technical_indicators(symbol, timeframe)

    # Obtener datos externos si están disponibles
    external_data = ""
    if EXTERNAL_DATA_AVAILABLE:
        try:
            external_data = await get_formatted_data_for_prompt(symbol)
            print(f"Datos externos obtenidos para {symbol}: {len(external_data)} caracteres")
        except Exception as e:
            print(f"Error al obtener datos externos: {e}")
            external_data = "No se pudieron obtener datos externos."

    # Usar IA para detectar tipo de solicitud incluyendo consultas conversacionales
    async def detect_request_type(prompt: str) -> str:
        """
        Usa IA para detectar si la solicitud es de análisis, señal o consulta conversacional.
        Retorna: 'signal', 'analysis', o 'conversation'
        """
        detection_prompt = (
            "Analiza esta consulta sobre criptomonedas y determina si el usuario está pidiendo:\n"
            "- 'signal': Una señal de trading con niveles específicos (entrada, stop loss, take profit)\n"
            "- 'analysis': Un análisis general de la criptomoneda (tendencia, indicadores, contexto)\n"
            "- 'conversation': Una consulta conversacional sobre una posición específica o decisión de trading\n\n"
            "Ejemplos de SEÑAL:\n"
            "- 'Dame una señal de BTC'\n"
            "- 'Necesito una señal de trading para ETH'\n"
            "- 'Señal para SOL en 30m'\n\n"
            "Ejemplos de ANÁLISIS:\n"
            "- 'Analiza Bitcoin'\n"
            "- 'Cómo está ETH'\n"
            "- 'Análisis de SOL'\n\n"
            "Ejemplos de CONVERSACIÓN:\n"
            "- 'Compré BTC a $95,000, ¿fue buena compra?'\n"
            "- 'Tengo ETH desde $3,200, ¿qué hago?'\n"
            "- '¿Debería vender mi SOL que compré a $180?'\n"
            "- 'Invertí en DOGE a $0.30, ¿cómo ves la situación?'\n\n"
            "Responde SOLO con 'signal', 'analysis' o 'conversation'.\n\n"
            f"Consulta del usuario: '{prompt}'"
        )
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": detection_prompt}],
                temperature=0.1,
                max_tokens=15
            )
            
            result = response.choices[0].message.content.strip().lower()
            if 'signal' in result:
                return 'signal'
            elif 'conversation' in result:
                return 'conversation'
            else:
                return 'analysis'
        except Exception as e:
            print(f"Error en detección automática: {e}")
            # Fallback a detección por palabras clave
            signal_keywords = ["dame una señal", "señal de trading", "señal para", "dame señal", 
                             "generar señal", "necesito una señal", "quiero una señal", "dame la señal", 
                             "señal de", "trading signal", "signal", "dame una señal de trading"]
            conversation_keywords = ["compré", "tengo", "invertí", "debería vender", "fue buena compra", 
                                   "qué hago", "cómo ves", "entrada a", "posición en", "holdeo"]
            
            if any(keyword in prompt.lower() for keyword in signal_keywords):
                return 'signal'
            elif any(keyword in prompt.lower() for keyword in conversation_keywords):
                return 'conversation'
            else:
                return 'analysis'
    
    async def extract_conversation_info(prompt: str) -> Dict[str, Any]:
        """
        Extrae información de consultas conversacionales (símbolo, precio de compra, etc.)
        """
        extraction_prompt = (
            "Extrae la siguiente información de esta consulta sobre criptomonedas:\n"
            "1. Símbolo de la criptomoneda (BTC, ETH, SOL, etc.)\n"
            "2. Precio de compra mencionado (si existe)\n"
            "3. Tipo de consulta (compra_pasada, decision_venta, evaluacion_posicion, etc.)\n\n"
            "Responde en formato JSON con las claves: symbol, purchase_price, query_type\n"
            "Si no encuentras algún dato, usa null.\n\n"
            f"Consulta: '{prompt}'"
        )
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=100
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception as e:
            print(f"Error extrayendo información conversacional: {e}")
            # Fallback manual
            import re
            
            # Buscar símbolo
            symbols = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOT", "DOGE", "SHIB", "MATIC", "AVAX", "LINK"]
            symbol = None
            for sym in symbols:
                if sym.lower() in prompt.lower() or sym in prompt:
                    symbol = sym
                    break
            
            # Buscar precio
            price_match = re.search(r'[\$]?([0-9]{1,6}[,.]?[0-9]*)', prompt)
            purchase_price = float(price_match.group(1).replace(',', '')) if price_match else None
            
            return {
                "symbol": symbol,
                "purchase_price": purchase_price,
                "query_type": "evaluacion_posicion"
            }
    
    # Detectar tipo de solicitud usando IA
    request_type = await detect_request_type(req.user_prompt)
    is_signal_request = (request_type == 'signal')
    is_conversation_request = (request_type == 'conversation')
    
    # Logging para debug
    print(f"DEBUG: Prompt recibido: '{req.user_prompt}'")
    print(f"DEBUG: Tipo detectado por IA: {request_type}")
    print(f"DEBUG: Es solicitud de señal: {is_signal_request}")
    print(f"DEBUG: Es consulta conversacional: {is_conversation_request}")
    
    # Manejar consultas conversacionales
    if is_conversation_request:
        conversation_info = await extract_conversation_info(req.user_prompt)
        print(f"DEBUG: Información conversacional extraída: {conversation_info}")
        
        # Usar el símbolo extraído si está disponible
        if conversation_info.get('symbol'):
            symbol = conversation_info['symbol']
        
        # Obtener precio actual para comparación
        current_price = await get_current_price(symbol)
        
        # Obtener indicadores técnicos
        indicators = await get_technical_indicators(symbol, timeframe)
        
        # Calcular rentabilidad si hay precio de compra
        profit_loss_info = ""
        transaction_details = ""
        
        if conversation_info.get('transactions') and len(conversation_info['transactions']) > 1:
            # Información detallada de múltiples transacciones
            transactions = conversation_info['transactions']
            total_investment = sum(t['quantity'] * t['price'] for t in transactions)
            total_quantity = sum(t['quantity'] for t in transactions)
            breakeven_price = total_investment / total_quantity
            
            transaction_details = f"📋 RESUMEN DE TRANSACCIONES:\n"
            for i, t in enumerate(transactions, 1):
                transaction_details += f"   • Operación {i}: {t['quantity']} unidades a ${t['price']:.2f}\n"
            transaction_details += f"   • Total invertido: ${total_investment:,.2f}\n"
            transaction_details += f"   • Total unidades: {total_quantity}\n"
            transaction_details += f"   • Precio promedio: ${breakeven_price:.2f}\n\n"
            
            if current_price:
                profit_loss = ((current_price - breakeven_price) / breakeven_price) * 100
                total_value = total_quantity * current_price
                profit_loss_amount = total_value - total_investment
                
                if profit_loss > 0:
                    profit_loss_info = f"📈 GANANCIA ACTUAL: +{profit_loss:.2f}% (+${profit_loss_amount:,.2f})\n"
                    profit_loss_info += f"   Valor actual: ${total_value:,.2f} | Inversión: ${total_investment:,.2f}\n\n"
                else:
                    profit_loss_info = f"📉 PÉRDIDA ACTUAL: {profit_loss:.2f}% (-${abs(profit_loss_amount):,.2f})\n"
                    profit_loss_info += f"   Valor actual: ${total_value:,.2f} | Inversión: ${total_investment:,.2f}\n\n"
        
        elif conversation_info.get('purchase_price') and current_price:
            # Información de transacción única
            purchase_price = conversation_info['purchase_price']
            profit_loss = ((current_price - purchase_price) / purchase_price) * 100
            
            if profit_loss > 0:
                profit_loss_info = f"📈 GANANCIA ACTUAL: +{profit_loss:.2f}%\n"
                profit_loss_info += f"   Compraste a ${purchase_price:,.2f}, ahora está a ${current_price:,.2f}\n\n"
            else:
                profit_loss_info = f"📉 PÉRDIDA ACTUAL: {profit_loss:.2f}%\n"
                profit_loss_info += f"   Compraste a ${purchase_price:,.2f}, ahora está a ${current_price:,.2f}\n\n"
        
        # Calcular niveles técnicos críticos usando la función mejorada
        def calculate_technical_levels(current_price: float, rsi: float, purchase_price: float = None, transactions: list = None) -> Dict[str, float]:
            """Calcula niveles técnicos críticos basados en el precio actual y condiciones del mercado"""
            
            # Si hay múltiples transacciones, calcular métricas adicionales
            if transactions and len(transactions) > 1:
                # Calcular punto de equilibrio
                total_investment = sum(t['quantity'] * t['price'] for t in transactions)
                total_quantity = sum(t['quantity'] for t in transactions)
                breakeven_price = total_investment / total_quantity
                print(f"📊 Análisis múltiples transacciones: {len(transactions)} operaciones, punto equilibrio: ${breakeven_price:.2f}")
            else:
                breakeven_price = purchase_price
            
            # Análisis de rentabilidad actual
            if breakeven_price:
                current_profit_loss = ((current_price - breakeven_price) / breakeven_price) * 100
                is_profitable = current_profit_loss > 0
                print(f"💹 Rentabilidad actual: {current_profit_loss:.2f}%")
            else:
                current_profit_loss = 0
                is_profitable = False
            
            # Stop Loss adaptativo basado en contexto
            if breakeven_price:
                if is_profitable:
                    # Si hay ganancia, stop loss más conservador
                    if current_profit_loss > 20:  # Ganancia alta (>20%)
                        stop_loss = max(breakeven_price * 1.05, current_price * 0.92)  # 5% arriba del breakeven o 8% del actual
                    elif current_profit_loss > 10:  # Ganancia media (10-20%)
                        stop_loss = max(breakeven_price * 1.02, current_price * 0.94)  # 2% arriba del breakeven o 6% del actual
                    else:  # Ganancia baja (0-10%)
                        stop_loss = max(breakeven_price * 0.98, current_price * 0.95)  # 2% por debajo del breakeven o 5% del actual
                else:
                    # Si hay pérdida, stop loss más amplio pero definido
                    if current_profit_loss < -15:  # Pérdida alta
                        stop_loss = current_price * 0.88  # 12% más abajo
                    elif current_profit_loss < -5:  # Pérdida media
                        stop_loss = current_price * 0.90  # 10% más abajo
                    else:  # Pérdida pequeña
                        stop_loss = current_price * 0.92  # 8% más abajo
            else:
                # Sin precio de compra, usar RSI para determinar stop loss
                if rsi and rsi < 30:  # Muy sobreventa
                    stop_loss = current_price * 0.92  # Stop loss más amplio
                elif rsi and rsi > 70:  # Muy sobrecompra
                    stop_loss = current_price * 0.96  # Stop loss más ajustado
                else:
                    stop_loss = current_price * 0.94  # Stop loss estándar
            
            # Take Profit 1: Objetivo conservador adaptativo
            if rsi and rsi < 35:  # Muy sobreventa, objetivo más ambicioso
                tp1_multiplier = 1.08  # 8%
            elif rsi and rsi > 65:  # Sobrecompra, objetivo más conservador
                tp1_multiplier = 1.04  # 4%
            else:
                tp1_multiplier = 1.06  # 6% estándar
            
            tp1 = current_price * tp1_multiplier
            
            # Take Profit 2: Objetivo optimista adaptativo
            if rsi and rsi < 30:  # Muy sobreventa, muy ambicioso
                tp2_multiplier = 1.25  # 25%
            elif rsi and rsi < 40:  # Sobreventa, ambicioso
                tp2_multiplier = 1.18  # 18%
            elif rsi and rsi > 70:  # Muy sobrecompra, conservador
                tp2_multiplier = 1.10  # 10%
            elif rsi and rsi > 60:  # Sobrecompra, moderado
                tp2_multiplier = 1.12  # 12%
            else:
                tp2_multiplier = 1.15  # 15% estándar
            
            tp2 = current_price * tp2_multiplier
            
            # Re-entrada: Nivel de corrección saludable
            if rsi and rsi > 65:  # Si está sobrecomprado, corrección más probable
                reentry_multiplier = 0.88  # 12% abajo
            elif rsi and rsi < 35:  # Si está sobreventa, corrección menor
                reentry_multiplier = 0.92  # 8% abajo
            else:
                reentry_multiplier = 0.90  # 10% abajo estándar
            
            reentry = current_price * reentry_multiplier
            
            # Invalidación: Nivel que cambiaría completamente el análisis
            if breakeven_price and not is_profitable:
                # Si ya hay pérdida, invalidación más abajo
                invalidation = current_price * 0.82  # 18% más abajo
            elif rsi and rsi < 30:
                # Si está muy sobreventa, invalidación más abajo
                invalidation = current_price * 0.80  # 20% más abajo
            else:
                # Invalidación estándar
                invalidation = current_price * 0.85  # 15% más abajo
            
            return {
                'stop_loss': round(stop_loss, 2),
                'tp1': round(tp1, 2),
                'tp2': round(tp2, 2),
                'reentry': round(reentry, 2),
                'invalidation': round(invalidation, 2),
                'breakeven': round(breakeven_price, 2) if breakeven_price else None,
                'current_profit_loss': round(current_profit_loss, 2)
            }
        
        # Calcular niveles técnicos
        rsi_value = indicators.get('rsi', 50)
        purchase_price = conversation_info.get('purchase_price')
        tech_levels = calculate_technical_levels(current_price, rsi_value, purchase_price, conversation_info.get('transactions'))
        
        # Prompt especializado para consultas conversacionales mejorado
        conversation_prompt = (
            "Eres un asesor financiero especializado en criptomonedas con experiencia en análisis técnico. "
            "El usuario te está consultando sobre una posición específica que ya tiene. "
            "Debes proporcionar un análisis técnico completo y recomendaciones específicas de trading.\n\n"
            
            "ANÁLISIS REQUERIDO:\n"
            "1. EVALUACIÓN DE LA POSICIÓN: Determina si fue una buena compra considerando:\n"
            "   - Precio de entrada vs situación técnica actual\n"
            "   - Timing de la compra en relación a niveles técnicos\n"
            "   - Contexto del mercado en ese momento\n"
            "   - Si hay múltiples transacciones, analiza la estrategia de DCA empleada\n\n"
            
            "2. ANÁLISIS TÉCNICO INTERNO (NO MOSTRAR EN RESPUESTA):\n"
            "   - RSI: Interpretación del nivel actual (sobrecompra >70, sobreventa <30, neutral 30-70)\n"
            "   - MACD: Estado de momentum (convergencia/divergencia, señales de cambio)\n"
            "   - Tendencia: Dirección general del precio (alcista/bajista/lateral)\n"
            "   - Volumen: Si confirma o contradice el movimiento de precios\n"
            "   - Estructura de mercado: Soportes y resistencias relevantes\n"
            "   USAR ESTE ANÁLISIS PARA FUNDAMENTAR LAS RECOMENDACIONES PERO NO MOSTRARLO\n\n"
            
            "3. PLAN DE ACCIÓN ESPECÍFICO:\n"
            "   - Decisión principal: MANTENER, VENDER PARCIAL, VENDER TOTAL, o COMPRAR MÁS\n"
            "   - Razones técnicas claras para la decisión\n"
            "   - Porcentaje específico si es venta parcial\n"
            "   - Consideraciones especiales para múltiples transacciones\n\n"
            
            "4. NIVELES TÉCNICOS CRÍTICOS (con precios exactos):\n"
            "   - Stop Loss sugerido: Precio específico donde cortar pérdidas\n"
            "   - Take Profit 1: Primer objetivo de ganancia\n"
            "   - Take Profit 2: Segundo objetivo más ambicioso\n"
            "   - Zona de re-entrada: Si baja, dónde considerar comprar más\n"
            "   - Punto de equilibrio: Para múltiples transacciones\n\n"
            
            "5. ESCENARIOS PROBABLES:\n"
            "   - Escenario alcista (probabilidad %): Qué esperar y niveles objetivo\n"
            "   - Escenario bajista (probabilidad %): Hasta dónde podría caer\n"
            "   - Invalidación: Nivel que cambiaría completamente el análisis\n\n"
            
            f"FORMATO OBLIGATORIO:\n\n"
            f"💭 EVALUACIÓN DE TU POSICIÓN EN {symbol}\n\n"
            f"{transaction_details}"
            f"{profit_loss_info}"
            f"[Aquí tu análisis y recomendación basada en los datos técnicos actuales. "
            f"NO MOSTRAR valores de RSI, MACD, etc. Solo usar para fundamentar tu recomendación]\n\n"
            f"🎯 NIVELES TÉCNICOS CRÍTICOS:\n"
            f"• Stop Loss: ${tech_levels['stop_loss']:,.2f}\n"
            f"• Take Profit 1: ${tech_levels['tp1']:,.2f}\n"
            f"• Take Profit 2: ${tech_levels['tp2']:,.2f}\n"
            f"• Re-entrada: ${tech_levels['reentry']:,.2f}\n"
            f"• Invalidación: ${tech_levels['invalidation']:,.2f}\n"
            + (f"• Punto equilibrio: ${tech_levels['breakeven']:.2f}\n" if tech_levels.get('breakeven') else "") +
            f"\n📈 ESCENARIOS PROBABLES:\n"
            f"[Alcista (X%): Descripción y niveles]\n"
            f"[Bajista (X%): Descripción y niveles]\n\n"
            f"⚖️ GESTIÓN DE RIESGO:\n"
            f"[Recomendación específica de acción con porcentajes si aplica]\n\n"
            
            "DATOS DISPONIBLES:\n"
            f"- Criptomoneda: {symbol}\n"
            f"- Precio actual: ${current_price:,.2f}\n"
            f"- RSI: {rsi_value:.1f}\n"
            f"- MACD: {indicators.get('macd', {}).get('macd_line', 'N/A')}\n"
            f"- Volumen promedio: {indicators.get('volume_avg', 'N/A')}\n"
            + (f"- Precio de compra: ${purchase_price:.2f}\n" if purchase_price else "") +
            + (f"- Rentabilidad: {tech_levels['current_profit_loss']:+.2f}%\n" if 'current_profit_loss' in tech_levels else "") +
            
            "INSTRUCCIONES FINALES:\n"
            "- Sé específico y directo en tus recomendaciones\n"
            "- Usa un lenguaje conversacional pero profesional\n"
            "- No muestres los valores técnicos crudos, úsalos para fundamentar\n"
            "- Da porcentajes específicos para ventas parciales si recomiendas eso\n"
            "- Responde en español\n"
            "- NO añadas información técnica explícita como '📊 ANÁLISIS TÉCNICO DETALLADO'"
        )
        
        # Generar respuesta conversacional con OpenAI
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": conversation_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            conversation_response = response.choices[0].message.content.strip()
            
            return {
                "is_analysis_request": False,
                "response_type": "conversation",
                "response": conversation_response,
                "technical_data": {
                    "symbol": symbol,
                    "current_price": current_price,
                    "purchase_price": purchase_price,
                    "profit_loss_percent": tech_levels.get('current_profit_loss', 0),
                    "indicators": indicators,
                    "technical_levels": tech_levels,
                    "transactions": conversation_info.get('transactions')
                }
            }
            
        except Exception as e:
            print(f"❌ Error generando respuesta conversacional: {e}")
            return {
                "is_analysis_request": False,
                "response_type": "conversation",
                "response": f"💡 Basándome en tus datos de {symbol}, te recomiendo revisar los niveles técnicos actuales. El precio está en ${current_price:,.2f} y considerando tu entrada, podrías evaluar los objetivos en ${tech_levels['tp1']:,.2f} y stop loss en ${tech_levels['stop_loss']:,.2f}."
            }
    
    # Preparar mensajes para OpenAI con prompt específico según el tipo de solicitud
    if is_signal_request:
        # Prompt para señales de trading
        system_prompt = (
            "Eres un asistente especializado en señales de trading de criptomonedas para futuros perpetuos. "
            "Cuando te pidan una señal de trading, proporciona SIEMPRE:\n\n"
            "1. DIRECCIÓN DE LA SEÑAL: Long o Short basado en análisis técnico\n"
            "2. PRECIOS ESPECÍFICOS: Entrada, TP1, TP2 y Stop Loss con precios exactos\n"
            "3. APALANCAMIENTO RECOMENDADO: Entre 5X y 20X según la confianza de la señal\n"
            "4. FUNDAMENTO TÉCNICO: Explicación del análisis que justifica la señal\n\n"
            "REGLAS ESTRICTAS DE FORMATO:\n\n"
            "1. NUNCA incluyas frases introductorias como '¡Claro!', '¡Por supuesto!', 'Aquí tienes', etc.\n"
            "2. Ve directo al formato de señal sin explicaciones previas.\n"
            "3. Usa números concretos y específicos para todos los niveles\n"
            "4. TP1 debe estar más lejos que TP2 (TP1 > TP2 para Long, TP1 < TP2 para Short)\n"
            "5. Stop Loss debe estar cerca del precio de entrada para limitar riesgo\n"
            "6. Si los indicadores no son claros, no fuerces una señal, di que no hay oportunidad clara\n\n"
            "Usa este formato exacto:\n\n"
            "Señal de Trading (Futuros Perpetuos)\n"
            "⚡ Cripto: [SÍMBOLO]/USDT - [TEMPORALIDAD]\n\n"
            "👉 Entrada: [PRECIO] $\n"
            "✅ TP1: [PRECIO] $\n"
            "✅ TP2: [PRECIO] $\n"
            "❌ SL: [PRECIO] $\n\n"
            "📈 Dirección: [Long/Short]\n"
            "⚠️ Apalancamiento: [X]X\n\n"
            "[Párrafo explicativo del análisis técnico que justifica la señal, mencionando estructura de mercado, soportes/resistencias, e indicadores relevantes]\n\n"
            "⚠️ No es recomendación de inversión.\n\n"
            "IMPORTANTE: Los niveles deben ser realistas basados en el precio actual y el análisis técnico. Para Long: TP1 > TP2 > Entrada > SL. Para Short: TP1 < TP2 < Entrada < SL."
        )
    else:
        # Prompt para análisis general
    system_prompt = (
        "Eres un asistente especializado en análisis de criptomonedas para usuarios principiantes. "
        "Cuando te pidan analizar una criptomoneda, proporciona SIEMPRE:\n\n"
        "1. DIRECCIÓN GENERAL: Indica claramente si la tendencia es alcista, bajista o lateral.\n\n"
        "2. ANÁLISIS GENERAL: Explica en 4-5 frases por qué has llegado a esa conclusión sobre la dirección. "
        "Usa lenguaje sencillo y evita jerga técnica. Incluye:\n"
        "   - Patrones de precio visibles explicados de manera sencilla\n"
        "   - Confirmación o divergencia del volumen (explica si el volumen respalda o contradice el movimiento del precio)\n"
        "   - Estado del RSI (sobrecompra >70, sobreventa <30, o zona neutral) en términos simples\n"
        "   - Señales del MACD (impulso positivo/negativo) explicadas de forma sencilla\n"
        "   - Contexto relevante del mercado general y noticias importantes\n"
        "   - Si el timeframe es corto (1m, 5m, 15m), menciona que el análisis es de muy corto plazo\n"
        "   - Si el timeframe es 1h, menciona brevemente la tendencia diaria (1d) como contexto adicional\n\n"
        "3. FACTORES FUNDAMENTALES: Incluye información sobre noticias relevantes, eventos económicos y tendencias en redes sociales que puedan afectar al precio. Menciona el sentimiento general en redes sociales (positivo, negativo o neutral) y cómo podría influir en el precio.\n\n"
        "4. SOPORTES Y RESISTENCIAS: Identifica SIEMPRE 2-3 niveles clave para la temporalidad solicitada:\n"
        "   - Al menos 1-2 soportes importantes (explicando brevemente por qué son importantes)\n"
        "   - Al menos 1-2 resistencias importantes (explicando brevemente por qué son importantes)\n"
        "   - Usa números concretos, no rangos demasiado amplios\n\n"
        "5. ESCENARIO PROBABLE: Describe brevemente qué podría ocurrir en los próximos días/semanas según la temporalidad analizada, considerando tanto factores técnicos como fundamentales.\n\n"
        "6. VALIDEZ DEL ANALISIS: Especifica claramente para qué periodo aplica este análisis.\n\n"
        "7. DISCLAIMER: Incluye siempre una advertencia sobre los riesgos de inversión.\n\n"
        "8. No menciones el marco temporal en el analisis.\n\n"
        "REGLAS ESTRICTAS DE FORMATO:\n\n"
        "1. NUNCA incluyas frases introductorias como '¡Claro!', '¡Por supuesto!', 'Aquí tienes', etc. Ve directo al formato.\n\n"
        "2. NUNCA menciones el timeframe en el texto del análisis. NO escribas frases como 'En el timeframe de 5m' o 'En el marco de tiempo de 1h'. El timeframe ya está en el título.\n\n"
        "3. NO empieces con frases como 'Bitcoin se encuentra en un patrón lateral' o 'Ethereum muestra una tendencia alcista'. La dirección ya está en la sección DIRECCIÓN.\n\n"
        "4. Comienza el análisis directamente con los patrones de precio, volumen, RSI, MACD, etc. sin mencionar la dirección ni el timeframe.\n\n"
        "5. NUNCA uses frases como 'Ethereum ha estado experimentando una tendencia bajista' o 'Bitcoin muestra una tendencia alcista'. Estas frases son redundantes.\n\n"
        "Usa este formato exacto con emojis:\n\n"
        "📊 ANÁLISIS DE [SÍMBOLO] ([TEMPORALIDAD])\n\n"
        "📈 DIRECCIÓN: [ALCISTA/BAJISTA/LATERAL]\n\n"
        "💡 ANÁLISIS TÉCNICO:\n"
        "[Análisis general en 4-5 frases incluyendo patrones, volumen, RSI, MACD y contexto de mercado]\n\n"
        "📰 FACTORES FUNDAMENTALES:\n"
        "[Análisis de noticias, eventos económicos y tendencias en redes sociales relevantes para la criptomoneda]\n\n"
        "🔑 NIVELES IMPORTANTES:\n"
        "- Soporte: $[PRECIO] ([breve explicación])\n"
        "- Soporte: $[PRECIO] ([breve explicación]) (si aplica)\n"
        "- Resistencia: $[PRECIO] ([breve explicación])\n"
        "- Resistencia: $[PRECIO] ([breve explicación]) (si aplica)\n\n"
        "🔮 ESCENARIO PROBABLE:\n"
        "[Descripción del escenario más probable considerando factores técnicos y fundamentales]\n\n"
        "⏱️ HORIZONTE TEMPORAL: [Periodo de validez del análisis]\n\n"
        "⚠️ No es asesoramiento financiero.\n\n"
        "IMPORTANTE: SIEMPRE proporciona un análisis completo con todos los elementos anteriores, independientemente del timeframe solicitado. Nunca respondas pidiendo más datos o diciendo que necesitas información adicional, ya que todos los datos necesarios ya están incluidos en el contexto técnico proporcionado."
    )
    user_prompt_content = (
        f"Usuario pide: {req.user_prompt}\n"
        f"Símbolo: {symbol}\n"
        f"Timeframe: {timeframe}\n"
        f"Precio actual: {current_price}$\n"
        f"RSI: {indicators.get('rsi', 'No disponible')}\n"
        f"MACD: {indicators.get('macd', {}).get('macd_line', 'No disponible')}\n"
        f"Volumen promedio: {indicators.get('volume_avg', 'No disponible')}\n\n"
    )
    
    # Añadir datos externos si están disponibles
    if external_data:
        user_prompt_content += f"\n{external_data}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_content},
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.6,
        max_tokens=800,
        top_p=0.9,
    )

    analysis = response.choices[0].message.content.strip()
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": current_price,
        "analysis": analysis,
        "indicators": indicators,
        "external_data_available": bool(external_data)
    }

def detect_analysis_request(prompt: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Detecta si el prompt es una solicitud de análisis técnico.
    Retorna: (es_análisis, símbolo, timeframe)
    """
    # Patrones para detectar solicitudes de análisis
    analysis_keywords = ["analiza", "análisis", "analizar", "análisis técnico", 
                         "precio", "tendencia", "chart", "gráfico"]
    
    # Verificar si contiene palabras clave de análisis
    is_analysis = any(keyword in prompt.lower() for keyword in analysis_keywords)
    
    # Si parece ser análisis, intentar extraer símbolo y timeframe
    if is_analysis:
        # Lista de símbolos comunes para buscar
        common_symbols = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOT", "DOGE", "SHIB"]
        
        # Buscar símbolos en el prompt
        symbol = None
        for sym in common_symbols:
            if sym.lower() in prompt.lower():
                symbol = sym
                break
        
        # Buscar timeframes comunes
        timeframe_patterns = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        timeframe = None
        for tf in timeframe_patterns:
            if tf in prompt:
                timeframe = tf
                break
        
        return True, symbol, timeframe
    
    return False, None, None

@app.post('/generate_signal')
async def generate_signal(req: SignalRequest) -> Dict[str, Any]:
    """
    Genera una señal de trading para el símbolo y timeframe especificados.
    Opcionalmente puede usar una estrategia específica.
    """
    try:
        symbol = req.symbol.upper()
        timeframe = req.timeframe
        strategy_name = req.strategy_name
        
        # Obtener datos históricos para el análisis
        historical_data = await get_historical_data(symbol, timeframe)
        if not historical_data or not historical_data.get('close'):
            return {
                "error": f"No se pudieron obtener datos históricos para {symbol} en timeframe {timeframe}"
            }
        
        # Convertir a DataFrame para usar con las estrategias
        import pandas as pd
        df = pd.DataFrame(historical_data)
        
        # Obtener precio actual
        current_price = await get_current_price(symbol)
        
        # Calcular indicadores técnicos
        indicators = {}
        if BACKEND_AVAILABLE:
            try:
                indicators = calculate_all_indicators(historical_data)
            except Exception as e:
                print(f"Error al calcular indicadores con backend: {e}")
                indicators = calculate_basic_indicators(historical_data)
        else:
            indicators = calculate_basic_indicators(historical_data)
        
        # Determinar dirección (Long/Short) basado en indicadores
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', {}).get('macd_line', 0)
        signal = indicators.get('macd', {}).get('signal_line', 0)
        
        direction = "LONG"
        if rsi < 40 or (macd < 0 and macd < signal):
            direction = "SHORT"
        
        # Calcular puntos de entrada, stop loss y take profit ajustados según timeframe
        entry = current_price
        
        # Definir porcentajes según timeframe
        # Timeframes más cortos tienen menor volatilidad en términos absolutos
        # pero mayor volatilidad relativa, por lo que ajustamos los porcentajes
        timeframe_percentages = {
            "1m": {"sl": 0.005, "tp1": 0.005, "tp2": 0.01},    # 0.5% SL/TP1, 1% TP2
            "5m": {"sl": 0.01, "tp1": 0.01, "tp2": 0.02},      # 1% SL/TP1, 2% TP2
            "15m": {"sl": 0.015, "tp1": 0.015, "tp2": 0.025},  # 1.5% SL/TP1, 2.5% TP2
            "30m": {"sl": 0.02, "tp1": 0.02, "tp2": 0.03},     # 2% SL/TP1, 3% TP2
            "1h": {"sl": 0.025, "tp1": 0.025, "tp2": 0.04},    # 2.5% SL/TP1, 4% TP2
            "4h": {"sl": 0.03, "tp1": 0.03, "tp2": 0.045},     # 3% SL/TP1, 4.5% TP2
            "1d": {"sl": 0.03, "tp1": 0.03, "tp2": 0.05},      # 3% SL/TP1, 5% TP2
            "1w": {"sl": 0.05, "tp1": 0.05, "tp2": 0.08}       # 5% SL/TP1, 8% TP2
        }
        
        # Obtener porcentajes para el timeframe actual o usar valores por defecto
        percentages = timeframe_percentages.get(timeframe, {"sl": 0.03, "tp1": 0.03, "tp2": 0.05})
        
        # Para long
        if direction == "LONG":
            sl = entry * (1 - percentages["sl"])
            tp1 = entry * (1 + percentages["tp1"])
            tp2 = entry * (1 + percentages["tp2"])
        # Para short
        else:
            sl = entry * (1 + percentages["sl"])
            tp1 = entry * (1 - percentages["tp1"])
            tp2 = entry * (1 - percentages["tp2"])
        
        # Generar explicación de la señal
        system_prompt = (
            "Eres un experto en trading de criptomonedas. "
            "Genera una explicación clara y concisa para una señal de trading. "
            "La explicación debe ser de 2-3 frases, mencionando el análisis técnico, "
            "la estructura del mercado, y la lógica detrás de los niveles de entrada, "
            "stop loss y take profit. No uses jerga técnica compleja."
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
        
        # Determinar apalancamiento recomendado basado en timeframe
        # Timeframes más cortos -> menor apalancamiento por mayor riesgo
        # Timeframes más largos -> mayor apalancamiento por menor riesgo relativo
        timeframe_leverage = {
            "1m": 5,    # Muy arriesgado, apalancamiento bajo
            "5m": 7,    # Alto riesgo
            "15m": 8,   # Riesgo moderado-alto
            "30m": 10,  # Riesgo moderado
            "1h": 12,   # Riesgo moderado
            "4h": 15,   # Riesgo moderado-bajo
            "1d": 20,   # Riesgo bajo
            "1w": 25    # Riesgo muy bajo
        }
        
        leverage = timeframe_leverage.get(timeframe, 10)  # Valor predeterminado: 10
        
        # Formatear la respuesta
        return {
            "response_type": "signal",
            "symbol": symbol,
            "timeframe": timeframe,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "direction": direction,
            "leverage": leverage,
            "explanation": explanation
        }
    except Exception as e:
        print(f"Error al generar señal: {e}")
        traceback.print_exc()
        return {
            "response_type": "error",
            "error": f"Error al generar señal: {str(e)}"
        }

@app.post('/analyze_prompt')
async def analyze_prompt(req: FullPromptRequest) -> Dict[str, Any]:
    prompt = req.prompt
    user_context = req.user_context or ""
    conversation_history = req.conversation_history or []
    
    try:
        # Detectar tipo de solicitud usando la nueva función IA
        async def detect_request_type_simple(prompt: str) -> str:
            """Detecta el tipo de consulta de forma simplificada"""
            prompt_lower = prompt.lower()
            
            # Detectar consultas conversacionales (expandido)
            conversational_patterns = [
                'compré', 'compre', 'compraste', 'tengo', 'invertí', 'inverti', 
                'soy holder', 'holder de', 'holder desde', 'es buena inversión', 
                'es buena inversion', 'fue buena compra', 'que opinas', 'qué opinas',
                'desde', 'me recomiendas', 'debo vender', 'debería vender',
                'mantengo', 'mantener', 'vender', 'vendiste', 'vendiste ya',
                'es buen momento', 'good buy', 'good investment', 'bad investment',
                'estoy perdiendo', 'estoy ganando', 'profit', 'loss', 'perdida',
                'ganancia', 'mi posición', 'mi posicion', 'position', 'hold',
                'holding', 'sold', 'buy more', 'comprar más', 'comprar mas',
                # Nuevos patrones añadidos
                'he comprado', 'he invertido', 'entré en', 'entre en', 'mi entrada',
                'mis entradas', 'acumulé', 'acumule', 'dollar cost', 'dca',
                'promedio', 'average', 'breakeven', 'punto equilibrio',
                'en pérdida', 'en perdida', 'en ganancia', 'green', 'red',
                'portfolio', 'portafolio', 'cartera', 'bag', 'bags',
                'moonbag', 'hodl', 'diamond hands', 'paper hands',
                'tomar profit', 'take profit', 'stop loss',
                'salir de', 'exit', 'entrada', 'entry point',
                'mi crypto', 'mis cryptos', 'mis monedas', 'mis coins',
                'invertí todo', 'inverti todo', 'all in', 'diversificar'
            ]
            
            # Detectar señales de trading
            signal_patterns = [
                'señal', 'signal', 'dame una señal', 'trading signal',
                'recomendación', 'recomendacion', 'recommendation',
                'comprar ahora', 'vender ahora', 'buy signal', 'sell signal'
            ]
            
            # Detectar análisis técnico
            analysis_patterns = [
                'analiza', 'análisis', 'analizar', 'análisis técnico',
                'como está', 'cómo está', 'situación', 'situacion',
                'tendencia', 'trend', 'momentum', 'chart', 'gráfico',
                'technical analysis', 'ta', 'indicators', 'indicadores'
            ]
            
            # Prioridad: conversational > signal > analysis
            if any(pattern in prompt_lower for pattern in conversational_patterns):
                return "conversation"
            elif any(pattern in prompt_lower for pattern in signal_patterns):
                return "signal"
            elif any(pattern in prompt_lower for pattern in analysis_patterns):
                return "analysis"
            else:
                return "general"
        
        request_type = await detect_request_type_simple(prompt)
        is_signal_request = (request_type == 'signal')
        is_conversation_request = (request_type == 'conversation')
        
        print(f"DEBUG: Tipo detectado en analyze_prompt: {request_type}")
        
        if is_signal_request:
            # Lógica para señales de trading (implementar aquí si es necesario)
                return {
                    "is_analysis_request": False,
                "response_type": "signal",
                "response": "Función de señales por implementar en analyze_prompt"
            }
        
        # Manejar consultas conversacionales usando la lógica mejorada
        elif is_conversation_request:
            # Usar IA para extraer información conversacional automáticamente
            async def extract_conversation_info_with_ai(prompt: str) -> Dict[str, Any]:
                """Usa IA para detectar automáticamente información conversacional"""
                
                # Prompt para que la IA extraiga información conversacional
                extraction_prompt = """
                Analiza el siguiente mensaje del usuario y extrae la información relevante sobre criptomonedas.
                
                INSTRUCCIONES:
                1. Identifica si menciona alguna criptomoneda (nombres completos o símbolos)
                2. Detecta si hay información sobre precios de compra/venta
                3. Identifica si hay múltiples transacciones con cantidades específicas
                4. Determina el tipo de consulta conversacional
                
                RESPONDE ÚNICAMENTE EN FORMATO JSON con esta estructura exacta:
                {
                    "symbol": "SÍMBOLO_CRYPTO_O_NULL",
                    "is_conversational": true/false,
                    "purchase_info": {
                        "has_single_price": true/false,
                        "single_price": número_o_null,
                        "has_multiple_transactions": true/false,
                        "transactions": [
                            {"quantity": número, "price": número},
                            ...
                        ]
                    },
                    "query_type": "evaluacion_posicion/precio_simple/consulta_general",
                    "confidence": 0.0_a_1.0
                }
                
                EJEMPLOS:
                - "compré bitcoin en 110000" → {"symbol": "BTC", "is_conversational": true, "purchase_info": {"has_single_price": true, "single_price": 110000, "has_multiple_transactions": false, "transactions": []}, "query_type": "evaluacion_posicion", "confidence": 0.95}
                - "he comprado 50 solanas a 100 dólares y 20 solanas a 130 dólares" → {"symbol": "SOL", "is_conversational": true, "purchase_info": {"has_single_price": false, "single_price": null, "has_multiple_transactions": true, "transactions": [{"quantity": 50, "price": 100}, {"quantity": 20, "price": 130}]}, "query_type": "evaluacion_posicion", "confidence": 0.98}
                - "soy holder de avalanche desde 35 dólares" → {"symbol": "AVAX", "is_conversational": true, "purchase_info": {"has_single_price": true, "single_price": 35, "has_multiple_transactions": false, "transactions": []}, "query_type": "evaluacion_posicion", "confidence": 0.90}
                """
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": extraction_prompt},
                            {"role": "user", "content": f"Mensaje: {prompt}"}
                        ],
                        temperature=0.1,  # Baja temperatura para respuestas más consistentes
                        max_tokens=500,
                    )
                    
                    ai_response = response.choices[0].message.content.strip()
                    print(f"🤖 Respuesta de IA para extracción: {ai_response}")
                    
                    # Parsear respuesta JSON
                    import json
                    extracted_info = json.loads(ai_response)
                    
                    # Validar y procesar la información extraída
                    result = {
                        "symbol": extracted_info.get("symbol"),
                        "is_conversational": extracted_info.get("is_conversational", False),
                        "query_type": extracted_info.get("query_type", "consulta_general"),
                        "confidence": extracted_info.get("confidence", 0.0)
                    }
                    
                    # Procesar información de compra
                    purchase_info = extracted_info.get("purchase_info", {})
                    
                    if purchase_info.get("has_multiple_transactions", False):
                        # Múltiples transacciones
                        transactions = purchase_info.get("transactions", [])
                        if transactions:
                            total_investment = sum(t['quantity'] * t['price'] for t in transactions)
                            total_quantity = sum(t['quantity'] for t in transactions)
                            average_price = total_investment / total_quantity if total_quantity > 0 else None
                            
                            result.update({
                                "purchase_price": average_price,
                                "total_quantity": total_quantity,
                                "transactions": transactions
                            })
                            print(f"💰 IA detectó múltiples transacciones: {len(transactions)} operaciones, precio promedio: ${average_price:.2f}")
                    
                    elif purchase_info.get("has_single_price", False):
                        # Precio único
                        single_price = purchase_info.get("single_price")
                        if single_price:
                            result.update({
                                "purchase_price": float(single_price),
                                "total_quantity": None,
                                "transactions": None
                            })
                            print(f"💲 IA detectó precio único: ${single_price}")
                    
                    else:
                        # Sin información de precio
                        result.update({
                            "purchase_price": None,
                            "total_quantity": None,
                            "transactions": None
                        })
                    
                    return result
                
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing JSON de IA: {e}")
                    print(f"Respuesta recibida: {ai_response}")
                    # Fallback a detección manual básica
                    return {
                        "symbol": None,
                        "is_conversational": True,  # Asumimos que es conversacional si llegó aquí
                        "query_type": "consulta_general",
                        "confidence": 0.0,
                        "purchase_price": None,
                        "total_quantity": None,
                        "transactions": None
                    }
                
                except Exception as e:
                    print(f"❌ Error en extracción con IA: {e}")
                    return {
                        "symbol": None,
                        "is_conversational": True,
                        "query_type": "consulta_general", 
                        "confidence": 0.0,
                        "purchase_price": None,
                        "total_quantity": None,
                        "transactions": None
                    }
            
            conversation_info = await extract_conversation_info_with_ai(prompt)
            print(f"🤖 Información extraída por IA: {conversation_info}")
            
            # Validar confianza mínima
            if conversation_info.get("confidence", 0) < 0.5:
                return {
                    "is_analysis_request": False,
                    "response_type": "conversation",
                    "response": "No pude entender completamente tu consulta sobre criptomonedas. ¿Podrías ser más específico? Por ejemplo: 'Compré BTC a $95,000, ¿qué opinas?'"
                }
            
            if not conversation_info.get('symbol'):
                return {
                    "is_analysis_request": False,
                    "response_type": "conversation", 
                    "response": "Por favor, especifica de qué criptomoneda estás hablando. Por ejemplo: 'Compré BTC a $95,000, ¿fue buena compra?'"
                }
            
            symbol = conversation_info['symbol']
            timeframe = "1d"  # Usar diario para consultas conversacionales
            
            # Obtener precio actual
            current_price = await get_current_price(symbol)
            
            # Obtener indicadores técnicos
            indicators = await get_technical_indicators(symbol, timeframe)
            
            # Calcular rentabilidad si hay precio de compra
            profit_loss_info = ""
            transaction_details = ""
            
            if conversation_info.get('transactions') and len(conversation_info['transactions']) > 1:
                # Información detallada de múltiples transacciones
                transactions = conversation_info['transactions']
                total_investment = sum(t['quantity'] * t['price'] for t in transactions)
                total_quantity = sum(t['quantity'] for t in transactions)
                breakeven_price = total_investment / total_quantity
                
                transaction_details = f"📋 RESUMEN DE TRANSACCIONES:\n"
                for i, t in enumerate(transactions, 1):
                    transaction_details += f"   • Operación {i}: {t['quantity']} unidades a ${t['price']:.2f}\n"
                transaction_details += f"   • Total invertido: ${total_investment:,.2f}\n"
                transaction_details += f"   • Total unidades: {total_quantity}\n"
                transaction_details += f"   • Precio promedio: ${breakeven_price:.2f}\n\n"
                
                if current_price:
                    profit_loss = ((current_price - breakeven_price) / breakeven_price) * 100
                    total_value = total_quantity * current_price
                    profit_loss_amount = total_value - total_investment
                    
                    if profit_loss > 0:
                        profit_loss_info = f"📈 GANANCIA ACTUAL: +{profit_loss:.2f}% (+${profit_loss_amount:,.2f})\n"
                        profit_loss_info += f"   Valor actual: ${total_value:,.2f} | Inversión: ${total_investment:,.2f}\n\n"
                    else:
                        profit_loss_info = f"📉 PÉRDIDA ACTUAL: {profit_loss:.2f}% (-${abs(profit_loss_amount):,.2f})\n"
                        profit_loss_info += f"   Valor actual: ${total_value:,.2f} | Inversión: ${total_investment:,.2f}\n\n"
            
            elif conversation_info.get('purchase_price') and current_price:
                # Información de transacción única
                purchase_price = conversation_info['purchase_price']
                profit_loss = ((current_price - purchase_price) / purchase_price) * 100
                
                if profit_loss > 0:
                    profit_loss_info = f"📈 GANANCIA ACTUAL: +{profit_loss:.2f}%\n"
                    profit_loss_info += f"   Compraste a ${purchase_price:,.2f}, ahora está a ${current_price:,.2f}\n\n"
                else:
                    profit_loss_info = f"📉 PÉRDIDA ACTUAL: {profit_loss:.2f}%\n"
                    profit_loss_info += f"   Compraste a ${purchase_price:,.2f}, ahora está a ${current_price:,.2f}\n\n"
            
            # Calcular niveles técnicos críticos usando la función mejorada
            def calculate_technical_levels(current_price: float, rsi: float, purchase_price: float = None, transactions: list = None) -> Dict[str, float]:
                """Calcula niveles técnicos críticos basados en el precio actual y condiciones del mercado"""
                
                # Si hay múltiples transacciones, calcular métricas adicionales
                if transactions and len(transactions) > 1:
                    # Calcular punto de equilibrio
                    total_investment = sum(t['quantity'] * t['price'] for t in transactions)
                    total_quantity = sum(t['quantity'] for t in transactions)
                    breakeven_price = total_investment / total_quantity
                    print(f"📊 Análisis múltiples transacciones: {len(transactions)} operaciones, punto equilibrio: ${breakeven_price:.2f}")
                else:
                    breakeven_price = purchase_price
                
                # Análisis de rentabilidad actual
                if breakeven_price:
                    current_profit_loss = ((current_price - breakeven_price) / breakeven_price) * 100
                    is_profitable = current_profit_loss > 0
                    print(f"💹 Rentabilidad actual: {current_profit_loss:.2f}%")
                else:
                    current_profit_loss = 0
                    is_profitable = False
                
                # Stop Loss adaptativo basado en contexto
                if breakeven_price:
                    if is_profitable:
                        # Si hay ganancia, stop loss más conservador
                        if current_profit_loss > 20:  # Ganancia alta (>20%)
                            stop_loss = max(breakeven_price * 1.05, current_price * 0.92)  # 5% arriba del breakeven o 8% del actual
                        elif current_profit_loss > 10:  # Ganancia media (10-20%)
                            stop_loss = max(breakeven_price * 1.02, current_price * 0.94)  # 2% arriba del breakeven o 6% del actual
                        else:  # Ganancia baja (0-10%)
                            stop_loss = max(breakeven_price * 0.98, current_price * 0.95)  # 2% por debajo del breakeven o 5% del actual
                    else:
                        # Si hay pérdida, stop loss más amplio pero definido
                        if current_profit_loss < -15:  # Pérdida alta
                            stop_loss = current_price * 0.88  # 12% más abajo
                        elif current_profit_loss < -5:  # Pérdida media
                            stop_loss = current_price * 0.90  # 10% más abajo
                        else:  # Pérdida pequeña
                            stop_loss = current_price * 0.92  # 8% más abajo
                else:
                    # Sin precio de compra, usar RSI para determinar stop loss
                    if rsi and rsi < 30:  # Muy sobreventa
                        stop_loss = current_price * 0.92  # Stop loss más amplio
                    elif rsi and rsi > 70:  # Muy sobrecompra
                        stop_loss = current_price * 0.96  # Stop loss más ajustado
                    else:
                        stop_loss = current_price * 0.94  # Stop loss estándar
                
                # Take Profit 1: Objetivo conservador adaptativo
                if rsi and rsi < 35:  # Muy sobreventa, objetivo más ambicioso
                    tp1_multiplier = 1.08  # 8%
                elif rsi and rsi > 65:  # Sobrecompra, objetivo más conservador
                    tp1_multiplier = 1.04  # 4%
                else:
                    tp1_multiplier = 1.06  # 6% estándar
                
                tp1 = current_price * tp1_multiplier
                
                # Take Profit 2: Objetivo optimista adaptativo
                if rsi and rsi < 30:  # Muy sobreventa, muy ambicioso
                    tp2_multiplier = 1.25  # 25%
                elif rsi and rsi < 40:  # Sobreventa, ambicioso
                    tp2_multiplier = 1.18  # 18%
                elif rsi and rsi > 70:  # Muy sobrecompra, conservador
                    tp2_multiplier = 1.10  # 10%
                elif rsi and rsi > 60:  # Sobrecompra, moderado
                    tp2_multiplier = 1.12  # 12%
                else:
                    tp2_multiplier = 1.15  # 15% estándar
                
                tp2 = current_price * tp2_multiplier
                
                # Re-entrada: Nivel de corrección saludable
                if rsi and rsi > 65:  # Si está sobrecomprado, corrección más probable
                    reentry_multiplier = 0.88  # 12% abajo
                elif rsi and rsi < 35:  # Si está sobreventa, corrección menor
                    reentry_multiplier = 0.92  # 8% abajo
                else:
                    reentry_multiplier = 0.90  # 10% abajo estándar
                
                reentry = current_price * reentry_multiplier
                
                # Invalidación: Nivel que cambiaría completamente el análisis
                if breakeven_price and not is_profitable:
                    # Si ya hay pérdida, invalidación más abajo
                    invalidation = current_price * 0.82  # 18% más abajo
                elif rsi and rsi < 30:
                    # Si está muy sobreventa, invalidación más abajo
                    invalidation = current_price * 0.80  # 20% más abajo
                else:
                    # Invalidación estándar
                    invalidation = current_price * 0.85  # 15% más abajo
            
            return {
                    'stop_loss': round(stop_loss, 2),
                    'tp1': round(tp1, 2),
                    'tp2': round(tp2, 2),
                    'reentry': round(reentry, 2),
                    'invalidation': round(invalidation, 2),
                    'breakeven': round(breakeven_price, 2) if breakeven_price else None,
                    'current_profit_loss': round(current_profit_loss, 2)
                }
            
            # Calcular niveles técnicos
            rsi_value = indicators.get('rsi', 50)
            purchase_price = conversation_info.get('purchase_price')
            tech_levels = calculate_technical_levels(current_price, rsi_value, purchase_price, conversation_info.get('transactions'))
            
            # Prompt especializado para consultas conversacionales mejorado
            conversation_prompt = (
                "Eres un asesor financiero especializado en criptomonedas con experiencia en análisis técnico. "
                "El usuario te está consultando sobre una posición específica que ya tiene. "
                "Debes proporcionar un análisis técnico completo y recomendaciones específicas de trading.\n\n"
                
                "ANÁLISIS REQUERIDO:\n"
                "1. EVALUACIÓN DE LA POSICIÓN: Determina si fue una buena compra considerando:\n"
                "   - Precio de entrada vs situación técnica actual\n"
                "   - Timing de la compra en relación a niveles técnicos\n"
                "   - Contexto del mercado en ese momento\n"
                "   - Si hay múltiples transacciones, analiza la estrategia de DCA empleada\n\n"
                
                "2. ANÁLISIS TÉCNICO INTERNO (NO MOSTRAR EN RESPUESTA):\n"
                "   - RSI: Interpretación del nivel actual (sobrecompra >70, sobreventa <30, neutral 30-70)\n"
                "   - MACD: Estado de momentum (convergencia/divergencia, señales de cambio)\n"
                "   - Tendencia: Dirección general del precio (alcista/bajista/lateral)\n"
                "   - Volumen: Si confirma o contradice el movimiento de precios\n"
                "   - Estructura de mercado: Soportes y resistencias relevantes\n"
                "   USAR ESTE ANÁLISIS PARA FUNDAMENTAR LAS RECOMENDACIONES PERO NO MOSTRARLO\n\n"
                
                "3. PLAN DE ACCIÓN ESPECÍFICO:\n"
                "   - Decisión principal: MANTENER, VENDER PARCIAL, VENDER TOTAL, o COMPRAR MÁS\n"
                "   - Razones técnicas claras para la decisión\n"
                "   - Porcentaje específico si es venta parcial\n"
                "   - Consideraciones especiales para múltiples transacciones\n\n"
                
                "4. NIVELES TÉCNICOS CRÍTICOS (con precios exactos):\n"
                "   - Stop Loss sugerido: Precio específico donde cortar pérdidas\n"
                "   - Take Profit 1: Primer objetivo de ganancia\n"
                "   - Take Profit 2: Segundo objetivo más ambicioso\n"
                "   - Zona de re-entrada: Si baja, dónde considerar comprar más\n"
                "   - Punto de equilibrio: Para múltiples transacciones\n\n"
                
                "5. ESCENARIOS PROBABLES:\n"
                "   - Escenario alcista (probabilidad %): Qué esperar y niveles objetivo\n"
                "   - Escenario bajista (probabilidad %): Hasta dónde podría caer\n"
                "   - Invalidación: Nivel que cambiaría completamente el análisis\n\n"
                
                f"FORMATO OBLIGATORIO:\n\n"
                f"💭 EVALUACIÓN DE TU POSICIÓN EN {symbol}\n\n"
                f"{transaction_details}"
                f"{profit_loss_info}"
                f"[Aquí tu análisis y recomendación basada en los datos técnicos actuales. "
                f"NO MOSTRAR valores de RSI, MACD, etc. Solo usar para fundamentar tu recomendación]\n\n"
                f"🎯 NIVELES TÉCNICOS CRÍTICOS:\n"
                f"• Stop Loss: ${tech_levels['stop_loss']:,.2f}\n"
                f"• Take Profit 1: ${tech_levels['tp1']:,.2f}\n"
                f"• Take Profit 2: ${tech_levels['tp2']:,.2f}\n"
                f"• Re-entrada: ${tech_levels['reentry']:,.2f}\n"
                f"• Invalidación: ${tech_levels['invalidation']:,.2f}\n"
                + (f"• Punto equilibrio: ${tech_levels['breakeven']:.2f}\n" if tech_levels.get('breakeven') else "") +
                f"\n📈 ESCENARIOS PROBABLES:\n"
                f"[Alcista (X%): Descripción y niveles]\n"
                f"[Bajista (X%): Descripción y niveles]\n\n"
                f"⚖️ GESTIÓN DE RIESGO:\n"
                f"[Recomendación específica de acción con porcentajes si aplica]\n\n"
                
                "DATOS DISPONIBLES:\n"
                f"- Criptomoneda: {symbol}\n"
                f"- Precio actual: ${current_price:,.2f}\n"
                f"- RSI: {rsi_value:.1f}\n"
                f"- MACD: {indicators.get('macd', {}).get('macd_line', 'N/A')}\n"
                f"- Volumen promedio: {indicators.get('volume_avg', 'N/A')}\n"
                + (f"- Precio de compra: ${purchase_price:.2f}\n" if purchase_price else "") +
                + (f"- Rentabilidad: {tech_levels['current_profit_loss']:+.2f}%\n" if 'current_profit_loss' in tech_levels else "") +
                
                "INSTRUCCIONES FINALES:\n"
                "- Sé específico y directo en tus recomendaciones\n"
                "- Usa un lenguaje conversacional pero profesional\n"
                "- No muestres los valores técnicos crudos, úsalos para fundamentar\n"
                "- Da porcentajes específicos para ventas parciales si recomiendas eso\n"
                "- Responde en español\n"
                "- NO añadas información técnica explícita como '📊 ANÁLISIS TÉCNICO DETALLADO'"
            )
            
            # Generar respuesta conversacional con OpenAI
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": conversation_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                )
                
                conversation_response = response.choices[0].message.content.strip()
            
            return {
                    "is_analysis_request": False,
                    "response_type": "conversation",
                    "response": conversation_response,
                    "technical_data": {
                "symbol": symbol,
                        "current_price": current_price,
                        "purchase_price": purchase_price,
                        "profit_loss_percent": tech_levels.get('current_profit_loss', 0),
                        "indicators": indicators,
                        "technical_levels": tech_levels,
                        "transactions": conversation_info.get('transactions')
                    }
                }
                
            except Exception as e:
                print(f"❌ Error generando respuesta conversacional: {e}")
            return {
                "is_analysis_request": False,
                "response_type": "conversation",
                    "response": f"💡 Basándome en tus datos de {symbol}, te recomiendo revisar los niveles técnicos actuales. El precio está en ${current_price:,.2f} y considerando tu entrada, podrías evaluar los objetivos en ${tech_levels['tp1']:,.2f} y stop loss en ${tech_levels['stop_loss']:,.2f}."
                }
        
        # Resto del flujo para otros tipos de consultas (análisis, señales, etc.)
        try:
            needed_data = await determine_needed_data(prompt)
            data_context = await fetch_requested_data(needed_data)
            
            # Añadir el prompt original al contexto
            data_context["original_prompt"] = prompt
            
            return await generate_response_with_data(prompt, data_context, conversation_history)
            
    except Exception as e:
            print(f"Error en análisis: {e}")
        return {
            "is_analysis_request": False,
            "response_type": "error",
                "response": "Lo siento, ocurrió un error al procesar tu consulta. Por favor, inténtalo de nuevo."
            }
        
    except Exception as e:
        print(f"Error general en analyze_prompt: {e}")
        return {
            "is_analysis_request": False,
            "response_type": "error", 
            "response": "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo."
        }

if __name__ == '__main__':
    if uvicorn:
        uvicorn.run('llm_inference:app', host='0.0.0.0', port=int(os.getenv('PORT', 9004)))
    else:
        print("Uvicorn no está disponible. No se puede arrancar el servidor.")

def get_comprehensive_crypto_list():
    """ESTA FUNCIÓN YA NO SE USA - LA IA DETECTA AUTOMÁTICAMENTE LAS CRIPTOMONEDAS"""
    # Mantengo la función por compatibilidad pero vacía
    return [], {}
