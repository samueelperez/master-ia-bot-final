# Estructura del Proyecto Crypto AI Bot

Este documento describe la estructura del proyecto Crypto AI Bot, explicando la organización de directorios y archivos.

## Estructura General

```
crypto-ai-bot/
├── src/                      # Todo el código fuente
│   ├── ai-module/            # Módulo de IA
│   ├── backend/              # Backend API
│   └── telegram-bot/         # Servicio de bot de Telegram
├── webapp/                   # Aplicación web frontend
├── scripts/                  # Scripts de inicio y utilidades
├── tests/                    # Pruebas unitarias y de integración
├── docs/                     # Documentación
├── config/                   # Archivos de configuración centralizados
└── logs/                     # Logs centralizados
```

## Descripción Detallada

### Código Fuente (`src/`)

#### Módulo de IA (`src/ai-module/`)

- **core/**: Funcionalidad principal del módulo de IA
  - `llm_inference.py`: Servicio de inferencia de IA
  - `index_strategies.py`: Indexación de estrategias
- **services/**: Servicios auxiliares
  - **external_data/**: Servicios de datos externos
    - `data_integration_service.py`: Integración de datos externos
    - `news_service.py`: Servicio de noticias
    - `social_media_service.py`: Servicio de redes sociales
    - `economic_calendar_service.py`: Servicio de calendario económico

#### Backend (`src/backend/`)

- `main.py`: Punto de entrada de la API
- **services/**: Servicios del backend
  - `ta_service.py`: Servicio de análisis técnico
  - **indicators/**: Indicadores técnicos
    - `momentum.py`: Indicadores de momentum
    - `volatility.py`: Indicadores de volatilidad
    - `volume.py`: Indicadores de volumen
    - `support_resistance.py`: Niveles de soporte y resistencia
    - `patterns.py`: Patrones de velas
- **strategies/**: Estrategias de trading
  - `base.py`: Clase base para estrategias
  - `holding_memecoins.py`: Estrategia de holding de memecoins
  - `scalping_memecoins.py`: Estrategia de scalping de memecoins
  - `monday_range.py`: Estrategia de rango del lunes
  - `risk_management.py`: Gestión de riesgos

#### Bot de Telegram (`src/telegram-bot/`)

- **core/**: Funcionalidad principal del bot
  - `telegram_bot.py`: Bot principal
  - `memory_manager.py`: Gestor de memoria
- **services/**: Servicios del bot
  - `alert_service.py`: Servicio de alertas
  - `simulate_bot.py`: Simulador de bot

#### Webapp (`src/webapp/`)

- Aplicación web Next.js para visualización de análisis y estrategias

### Scripts (`scripts/`)

- **start/**: Scripts de inicio
  - `start_crypto_bot.sh`: Inicia el bot básico
  - `start_crypto_bot_with_menus.sh`: Inicia el bot con menús
  - `start_crypto_ai_bot_with_external_data.sh`: Inicia el sistema completo
  - `restart_crypto_ai_bot.sh`: Reinicia todos los servicios

### Pruebas (`tests/`)

- **ai-module/**: Pruebas del módulo de IA
- **backend/**: Pruebas del backend
- **telegram-bot/**: Pruebas del bot de Telegram
- **integration/**: Pruebas de integración

### Documentación (`docs/`)

- `project_structure.md`: Este documento
- `telegram_bot_menus.md`: Documentación del sistema de menús
- `telegram_bot_timeframes.md`: Documentación de timeframes
- `timeframe_signals.md`: Documentación de señales por timeframe

### Configuración (`config/`)

- **examples/**: Ejemplos de configuración
  - `.env.example`: Ejemplo de variables de entorno
- `ai-module.env`: Variables de entorno del módulo de IA
- `telegram-bot.env`: Variables de entorno del bot de Telegram
- `infra.env`: Variables de entorno de infraestructura
- `docker-compose.yml`: Configuración de Docker Compose

### Logs (`logs/`)

- Archivos de registro de los diferentes servicios
