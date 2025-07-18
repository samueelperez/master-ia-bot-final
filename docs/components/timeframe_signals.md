# Implementación de Múltiples Timeframes para Señales de Trading

Este documento describe la implementación de soporte para múltiples timeframes en el módulo de generación de señales de trading del sistema.

## Cambios Realizados

1. **Detección de Timeframes en Prompts**
   - Se ha mejorado la función `analyze_prompt` en `llm_inference.py` para detectar correctamente el timeframe solicitado en las peticiones de señales.
   - Se agregaron patrones para reconocer diferentes formatos de solicitud de timeframes (ej: "5 minutos", "1h", "diario", etc.).

2. **Ajuste de Parámetros por Timeframe**
   - Se modificó la función `generate_signal` para ajustar los parámetros de trading según el timeframe:
     - Stop Loss y Take Profit: Porcentajes ajustados según la volatilidad típica de cada timeframe.
     - Apalancamiento: Valores recomendados específicos para cada timeframe.

3. **Soporte en Telegram Bot**
   - Se actualizó la lista de timeframes disponibles en el bot de Telegram para incluir todos los timeframes soportados.
   - Se mejoró la visualización de las señales para mostrar claramente el timeframe utilizado.

## Timeframes Soportados

El sistema ahora soporta los siguientes timeframes:

| Timeframe | Descripción      | Patrones de Detección                                      |
|-----------|------------------|-----------------------------------------------------------|
| 1m        | 1 minuto         | "1 minuto", "1m", "un minuto", "1 min"                    |
| 5m        | 5 minutos        | "5 minutos", "5m", "cinco minutos", "5 min"               |
| 15m       | 15 minutos       | "15 minutos", "15m", "quince minutos", "15 min"           |
| 30m       | 30 minutos       | "30 minutos", "30m", "treinta minutos", "30 min", "media hora" |
| 1h        | 1 hora           | "1 hora", "1h", "una hora"                                |
| 4h        | 4 horas          | "4 horas", "4h", "cuatro horas"                           |
| 1d        | 1 día (diario)   | "1 día", "1d", "un día", "diario", "daily"                |
| 1w        | 1 semana         | "1 semana", "1w", "una semana", "semanal", "weekly"       |

## Parámetros Ajustados por Timeframe

### Stop Loss y Take Profit

Los porcentajes de Stop Loss y Take Profit se ajustan automáticamente según el timeframe:

| Timeframe | Stop Loss | Take Profit 1 | Take Profit 2 |
|-----------|-----------|---------------|---------------|
| 1m        | 0.5%      | 0.5%          | 1.0%          |
| 5m        | 1.0%      | 1.0%          | 2.0%          |
| 15m       | 1.5%      | 1.5%          | 2.5%          |
| 30m       | 2.0%      | 2.0%          | 3.0%          |
| 1h        | 2.5%      | 2.5%          | 4.0%          |
| 4h        | 3.0%      | 3.0%          | 4.5%          |
| 1d        | 3.0%      | 3.0%          | 5.0%          |
| 1w        | 5.0%      | 5.0%          | 8.0%          |

### Apalancamiento Recomendado

El apalancamiento recomendado también se ajusta según el timeframe:

| Timeframe | Apalancamiento | Nivel de Riesgo |
|-----------|----------------|-----------------|
| 1m        | 5x             | Muy alto        |
| 5m        | 7x             | Alto            |
| 15m       | 8x             | Moderado-alto   |
| 30m       | 10x            | Moderado        |
| 1h        | 12x            | Moderado        |
| 4h        | 15x            | Moderado-bajo   |
| 1d        | 20x            | Bajo            |
| 1w        | 25x            | Muy bajo        |

## Scripts de Prueba

Se han creado varios scripts para probar la funcionalidad:

1. **test_timeframe_signals.py**
   - Prueba la generación de señales con diferentes timeframes directamente.
   - Muestra los porcentajes de SL/TP y apalancamiento para cada timeframe.

2. **test_timeframe_detection.py**
   - Prueba la detección de timeframes en diferentes formatos de prompt.
   - Verifica que el sistema interprete correctamente las solicitudes de usuario.

3. **test_bot_signals.py**
   - Simula interacciones con el bot de Telegram para probar el flujo completo.
   - Verifica que las señales generadas respeten el timeframe solicitado.

## Cómo Probar

Para probar la funcionalidad, ejecute los scripts de prueba:

```bash
# Probar generación de señales con diferentes timeframes
python ai-module/test_timeframe_signals.py

# Probar detección de timeframes en prompts
python ai-module/test_timeframe_detection.py

# Simular interacciones con el bot de Telegram
python ai-module/telegram_bot_service/test_bot_signals.py
```

## Ejemplos de Uso

### Solicitar una Señal con Timeframe Específico

Para solicitar una señal con un timeframe específico a través del bot de Telegram, use alguno de estos formatos:

- "Dame una señal de Bitcoin en 5 minutos"
- "Quiero una señal para ETH en timeframe de 15m"
- "Necesito una señal de trading para Solana en 1 hora"
- "Señal de trading para BNB en 4 horas por favor"
- "Genera una señal para ADA en timeframe diario"
- "Dame señal de XRP en semanal"

Si no se especifica un timeframe, el sistema utilizará el timeframe diario (1d) por defecto.
