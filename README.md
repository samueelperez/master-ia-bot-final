# Crypto AI Bot

Este proyecto ha sido reorganizado para tener una estructura más clara y profesional.

## Nueva Estructura del Proyecto

```
crypto-ai-bot/
├── src/                      # Todo el código fuente
│   ├── ai-module/            # Módulo de IA
│   ├── telegram-bot/         # Bot de Telegram
│   ├── backend/              # Backend para análisis y backtesting
│   ├── data-service/         # Servicio de datos externos
│   ├── shared/               # Código compartido entre módulos
│   └── webapp/               # Aplicación web (frontend)
├── config/                   # Archivos de configuración centralizados
│   ├── development/          # Configuración de desarrollo
│   ├── production/           # Configuración de producción
│   └── testing/              # Configuración de pruebas
├── docker/                   # Archivos Docker
├── scripts/                  # Scripts de utilidad
├── tests/                    # Pruebas
│   ├── unit/                 # Pruebas unitarias
│   └── integration/          # Pruebas de integración
└── docs/                     # Documentación
```

## Cómo Ejecutar el Proyecto

Para iniciar el bot de Telegram:

```bash
cd src/telegram-bot
./start_bot.sh
```

Para iniciar el módulo de IA:

```bash
cd src/ai-module
./start_llm_service.sh
```

Para iniciar el servicio de datos externos:

```bash
cd src/data-service
./start_dev.sh
```

Para iniciar el backend:

```bash
cd src/backend
python dispatch_backtests.py
```

Para iniciar la webapp:

```bash
cd src/webapp
npm run dev
```

## Nota Importante

Esta reorganización se ha realizado preservando toda la funcionalidad original. Si encuentras algún problema, por favor reportarlo.
