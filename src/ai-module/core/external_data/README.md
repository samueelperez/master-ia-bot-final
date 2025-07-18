# Servicios de Datos Externos

Este módulo proporciona integración con fuentes de datos externos para enriquecer los análisis de criptomonedas con información fundamental y de mercado.

## Estructura

```
external_data/
├── __init__.py                    # Inicialización del módulo
├── news_service.py                # Servicio de noticias
├── social_media_service.py        # Servicio de redes sociales
├── economic_calendar_service.py   # Servicio de calendario económico
└── data_integration_service.py    # Integración de todos los datos
```

## Servicios Disponibles

### Servicio de Noticias (`news_service.py`)

Recopila noticias relevantes sobre criptomonedas y eventos económicos/políticos importantes.

**Funciones principales:**
- `get_news_for_symbol(symbol)`: Obtiene noticias específicas para una criptomoneda
- `get_all_relevant_news()`: Obtiene noticias generales del mercado cripto

**Fuentes de datos:**
- CryptoPanic API (requiere API key)
- NewsAPI (requiere API key)
- Fuentes simuladas (fallback cuando no hay API keys)

### Servicio de Redes Sociales (`social_media_service.py`)

Analiza tendencias y sentimiento en Twitter y otras plataformas sociales.

**Funciones principales:**
- `get_social_data_for_symbol(symbol)`: Obtiene datos sociales para una criptomoneda
- `get_all_social_data()`: Obtiene datos sociales generales del mercado

**Fuentes de datos:**
- Twitter API (requiere Bearer Token)
- CoinGecko API (tendencias)
- Datos simulados (fallback)

### Calendario Económico (`economic_calendar_service.py`)

Monitorea eventos económicos que pueden impactar el mercado de criptomonedas.

**Funciones principales:**
- `get_economic_events()`: Obtiene eventos económicos importantes
- `get_events_for_symbol(symbol)`: Obtiene eventos relevantes para una criptomoneda

**Fuentes de datos:**
- Simulación de eventos de Investing.com
- Simulación de eventos de ForexFactory
- Eventos específicos de criptomonedas

### Servicio de Integración (`data_integration_service.py`)

Combina todos los datos externos para proporcionar un contexto completo.

**Funciones principales:**
- `get_external_data_for_symbol(symbol)`: Obtiene todos los datos externos para una criptomoneda
- `get_all_external_data()`: Obtiene todos los datos externos generales
- `get_formatted_data_for_prompt(symbol)`: Formatea los datos para su uso en prompts de LLM

## Configuración

Para habilitar todas las funcionalidades, configura las siguientes variables en el archivo `.env`:

```
CRYPTOPANIC_API_KEY=tu_api_key_aquí
NEWSAPI_KEY=tu_api_key_aquí
TWITTER_BEARER_TOKEN=tu_token_aquí
```

Si no se proporcionan estas claves, el sistema utilizará datos simulados para demostración.

## Sistema de Caché

Todos los servicios implementan un sistema de caché para:
- Reducir el número de llamadas a APIs externas
- Mejorar el rendimiento
- Funcionar sin conexión cuando sea necesario

Los datos se almacenan en caché durante un período configurable (por defecto: 1 hora para noticias, 30 minutos para datos sociales, 24 horas para eventos económicos).

## Uso en el Análisis de Criptomonedas

Los datos externos se integran en el análisis de criptomonedas para proporcionar:

1. **Contexto fundamental**: Noticias y eventos que pueden explicar movimientos de precio
2. **Sentimiento del mercado**: Percepción general en redes sociales
3. **Alertas de eventos**: Próximos eventos que podrían impactar el precio

## Ejemplo de Uso

```python
import asyncio
from data_integration_service import get_formatted_data_for_prompt

async def analyze_bitcoin():
    # Obtener datos externos formateados para Bitcoin
    external_data = await get_formatted_data_for_prompt("BTC")
    
    # Usar estos datos en el prompt para el LLM
    prompt = f"""
    Analiza Bitcoin basándote en los siguientes datos externos:
    
    {external_data}
    
    ¿Cómo podrían estos factores afectar el precio?
    """
    
    # Enviar prompt al LLM...

# Ejecutar la función
asyncio.run(analyze_bitcoin())
```

## Extensión

Para añadir nuevas fuentes de datos:

1. Crea un nuevo servicio en un archivo separado
2. Implementa las funciones necesarias para obtener los datos
3. Integra el servicio en `data_integration_service.py`

## Limitaciones

- Las APIs externas pueden tener límites de uso
- Los datos simulados son solo para demostración y no reflejan información real del mercado
- El análisis de sentimiento es básico y puede no capturar todos los matices
