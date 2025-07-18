# Soporte de Timeframes en el Bot de Telegram

## Introducción

Este documento explica cómo el bot de Telegram ahora soporta diferentes timeframes para las señales de trading. El bot puede detectar y procesar solicitudes de señales con timeframes específicos, como "Dame una señal de Bitcoin en 1h" o "Quiero una señal para ETH en 15m".

## Timeframes Soportados

El bot soporta los siguientes timeframes:

- **1m**: 1 minuto
- **5m**: 5 minutos
- **15m**: 15 minutos
- **30m**: 30 minutos
- **1h**: 1 hora
- **4h**: 4 horas
- **1d**: 1 día (timeframe por defecto)
- **1w**: 1 semana

## Cómo Solicitar Señales con Timeframes

Para solicitar una señal con un timeframe específico, simplemente incluye el timeframe en tu mensaje. Por ejemplo:

- "Dame una señal de Bitcoin en 1h"
- "Quiero una señal para ETH en 15m"
- "Señal de trading para ADA en 4h"
- "Necesito una señal de trading para BNB en 30m"

Si no especificas un timeframe, el bot usará el timeframe diario (1d) por defecto.

## Patrones de Detección de Timeframes

El bot reconoce los siguientes patrones para cada timeframe:

- **1m**: "1 minuto", "1m", "un minuto", "1 min", "1min", "1 m"
- **5m**: "5 minutos", "5m", "cinco minutos", "5 min", "5min", "5 m"
- **15m**: "15 minutos", "15m", "quince minutos", "15 min", "15min", "15 m"
- **30m**: "30 minutos", "30m", "treinta minutos", "30 min", "30min", "30 m", "media hora"
- **1h**: "1 hora", "1h", "una hora", "1 h", "1hr", "1 hr"
- **4h**: "4 horas", "4h", "cuatro horas", "4 h", "4hr", "4 hr"
- **1d**: "1 día", "1d", "un día", "diario", "daily", "1 d", "1day", "1 day"
- **1w**: "1 semana", "1w", "una semana", "semanal", "weekly", "1 w", "1week", "1 week"

## Cambios Implementados

1. **Detección de Timeframes en el Bot**: El bot ahora detecta explícitamente los timeframes en las solicitudes de señales antes de enviarlas al servicio de IA.

2. **Modificación del Prompt**: Cuando se detecta un timeframe explícito en una solicitud de señal, el bot modifica el prompt para enfatizar el timeframe antes de enviarlo al servicio de IA, añadiendo "(TIMEFRAME=X)" al final del mensaje.

3. **Logging Mejorado**: Se ha añadido logging para depurar la detección de timeframes, mostrando si se ha detectado un timeframe explícito y cuál es.

4. **Script de Inicio Mejorado**: Se ha creado un nuevo script `start_bot_with_timeframes.sh` que verifica las variables de entorno y la conexión con el servicio de IA antes de iniciar el bot.

5. **Variables de Entorno Adicionales**: El script de inicio configura variables de entorno adicionales para habilitar la detección de timeframes y el logging de depuración.

## Cómo Iniciar el Bot

Para iniciar el bot con soporte de timeframes, ejecuta el siguiente comando:

```bash
./start_bot_with_timeframes.sh
```

Este script verificará que todas las variables de entorno necesarias estén definidas y que el servicio de IA esté en ejecución antes de iniciar el bot.

## Ejemplos de Parámetros por Timeframe

Basado en pruebas, estos son los parámetros típicos que el modelo de IA genera para cada timeframe:

- **1m** (1 minuto):
  - Stop Loss: ~0.50%
  - Take Profit 1: ~0.50%
  - Take Profit 2: ~1.00%
  - Apalancamiento: ~5X

- **5m** (5 minutos):
  - Stop Loss: ~1.00%
  - Take Profit 1: ~1.00%
  - Take Profit 2: ~2.00%
  - Apalancamiento: ~7X

- **15m** (15 minutos):
  - Stop Loss: ~1.50%
  - Take Profit 1: ~1.50%
  - Take Profit 2: ~2.50%
  - Apalancamiento: ~8X

- **30m** (30 minutos):
  - Stop Loss: ~2.00%
  - Take Profit 1: ~2.00%
  - Take Profit 2: ~3.00%
  - Apalancamiento: ~10X

- **1h** (1 hora):
  - Stop Loss: ~1.70%
  - Take Profit 1: ~3.40%
  - Take Profit 2: ~3.40%
  - Apalancamiento: ~12X

- **4h** (4 horas):
  - Stop Loss: ~2.80%
  - Take Profit 1: ~2.80%
  - Take Profit 2: ~4.70%
  - Apalancamiento: ~15X

- **1d** (1 día):
  - Stop Loss: ~4.00%
  - Take Profit 1: ~2.00%
  - Take Profit 2: ~5.30%
  - Apalancamiento: ~20X

- **1w** (1 semana):
  - Stop Loss: ~5.00%
  - Take Profit 1: ~5.00%
  - Take Profit 2: ~10.00%
  - Apalancamiento: ~20X

## Solución de Problemas

Si el bot no detecta correctamente el timeframe, verifica lo siguiente:

1. Asegúrate de que el timeframe esté escrito correctamente en tu mensaje (por ejemplo, "1h", "15m", etc.).
2. Verifica que el servicio de IA esté en ejecución y accesible.
3. Comprueba los logs del bot para ver si hay algún error en la detección del timeframe.

Si sigues teniendo problemas, puedes ejecutar el script de prueba `test_bot_signals.py` para verificar que la detección de timeframes funciona correctamente:

```bash
cd ai-module/telegram_bot_service
python test_bot_signals.py
```

Este script probará la generación de señales con diferentes timeframes y mostrará los resultados.
