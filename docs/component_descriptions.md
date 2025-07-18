# Descripción de Componentes del Crypto AI Bot

Este documento proporciona una descripción detallada de cada componente principal del sistema Crypto AI Bot.

## Módulo de IA

El módulo de IA es el cerebro del sistema, encargado de procesar consultas en lenguaje natural, analizar datos de mercado y generar respuestas inteligentes.

### Componentes Principales

- **llm_inference.py**: Servicio de inferencia que utiliza modelos de lenguaje de gran escala (LLM) para procesar consultas y generar respuestas. Implementa técnicas de RAG (Retrieval Augmented Generation) para mejorar la calidad de las respuestas con información contextual.

- **index_strategies.py**: Indexa las estrategias de trading disponibles para que el LLM pueda recomendarlas según el contexto de la consulta del usuario.

- **Servicios de Datos Externos**:
  - **data_integration_service.py**: Integra datos de diferentes fuentes externas.
  - **news_service.py**: Recopila noticias relevantes sobre criptomonedas.
  - **social_media_service.py**: Analiza sentimiento en redes sociales.
  - **economic_calendar_service.py**: Proporciona información sobre eventos económicos relevantes.

## Backend

El backend proporciona servicios de análisis técnico y gestión de estrategias a través de una API REST.

### Componentes Principales

- **ta_service.py**: Servicio central de análisis técnico que coordina el cálculo de indicadores y la aplicación de estrategias.

- **Indicadores Técnicos**:
  - **momentum.py**: Implementa indicadores de momentum como RSI, MACD, Stochastic.
  - **volatility.py**: Implementa indicadores de volatilidad como Bollinger Bands, ATR.
  - **volume.py**: Implementa indicadores basados en volumen como OBV, Volume Profile.
  - **support_resistance.py**: Calcula niveles de soporte y resistencia.
  - **patterns.py**: Detecta patrones de velas japonesas.

- **Estrategias de Trading**:
  - **base.py**: Define la clase base para todas las estrategias.
  - **holding_memecoins.py**: Estrategia de inversión a largo plazo en memecoins.
  - **scalping_memecoins.py**: Estrategia de trading a corto plazo en memecoins.
  - **monday_range.py**: Estrategia basada en el rango de precios del lunes.
  - **risk_management.py**: Implementa reglas de gestión de riesgos.

## Bot de Telegram

El bot de Telegram es la interfaz principal para que los usuarios interactúen con el sistema.

### Componentes Principales

- **telegram_bot.py**: Implementación principal del bot que maneja comandos y consultas de los usuarios.

- **memory_manager.py**: Gestiona la memoria de conversaciones para mantener contexto entre interacciones.

- **alert_service.py**: Servicio de alertas que notifica a los usuarios sobre eventos importantes del mercado o señales de trading.

- **simulate_bot.py**: Herramienta para simular interacciones con el bot para pruebas y desarrollo.

## Webapp (`webapp/`)

La aplicación web proporciona una interfaz gráfica para visualizar análisis y estrategias.

### Componentes Principales

- **Páginas Principales**:
  - **page.tsx**: Página de inicio.
  - **analysis/page.tsx**: Visualización de análisis técnico.
  - **strategies/page.tsx**: Gestión y visualización de estrategias.

- **Componentes**:
  - **ChatBot.js**: Interfaz de chat para interactuar con el sistema.
  - **TechnicalCharts.js**: Visualización de gráficos técnicos.
  - **MouseTrail.js**: Efectos visuales para mejorar la experiencia de usuario.

- **Servicios**:
  - **api.ts**: Cliente para comunicarse con el backend.
  - **supabase.ts**: Integración con Supabase para almacenamiento y autenticación.

## Scripts de Inicio

Los scripts de inicio automatizan el proceso de arranque de los diferentes componentes del sistema.

### Componentes Principales

- **start_crypto_bot.sh**: Inicia el bot de Telegram con configuración básica.
- **start_crypto_bot_with_menus.sh**: Inicia el bot con sistema de menús avanzado.
- **start_crypto_ai_bot_with_external_data.sh**: Inicia el sistema completo incluyendo el módulo de IA con datos externos.
- **restart_crypto_ai_bot.sh**: Reinicia todos los servicios del sistema.
