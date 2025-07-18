# Sistema de Menús con Botones para el Bot de Telegram

Este documento describe el nuevo sistema de menús con botones implementado en el bot de Telegram para análisis de criptomonedas.

## Características Principales

- **Menú Principal**: Acceso rápido a las funcionalidades principales (Análisis, Señales, Alertas)
- **Selección de Criptomonedas**: Interfaz intuitiva para elegir la criptomoneda a analizar
- **Selección de Timeframes**: Elección rápida del marco temporal para el análisis
- **Lista Personalizada**: Posibilidad de configurar qué criptomonedas aparecen en el menú

## Estructura de Menús

### 1. Menú Principal
Al iniciar el bot con `/start`, se muestra el menú principal con tres opciones:
- **📊 Análisis**: Para realizar análisis técnicos de criptomonedas
- **🎯 Señales**: Para obtener señales de trading
- **🔔 Alertas**: Para configurar alertas de precio e indicadores

### 2. Menú de Criptomonedas
Al seleccionar "Análisis" o "Señales", se muestra un menú con las criptomonedas disponibles:
- Lista de criptomonedas (personalizada o predeterminada)
- Opción "🔄 Más criptomonedas" para ver más opciones
- Opción "⚙️ Configurar lista" para personalizar las criptomonedas mostradas
- Opción "🔙 Volver" para regresar al menú principal

### 3. Menú de Timeframes
Al seleccionar una criptomoneda, se muestra un menú con los timeframes disponibles:
- Lista de timeframes (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
- Opción "🔙 Volver" para regresar al menú de criptomonedas

### 4. Configuración de Lista Personalizada
Al seleccionar "Configurar lista", se muestra una interfaz para personalizar las criptomonedas:
- Lista de todas las criptomonedas disponibles con checkboxes
- Opción "✅ Guardar" para guardar la configuración
- Opción "🔄 Restablecer" para volver a la lista predeterminada
- Opción "🔙 Volver" para regresar sin guardar cambios

## Uso del Sistema

### Análisis de Criptomonedas
1. Envía `/start` para mostrar el menú principal
2. Selecciona "📊 Análisis"
3. Elige una criptomoneda de la lista
4. Selecciona un timeframe
5. El bot generará y mostrará el análisis

### Obtención de Señales
1. Envía `/start` para mostrar el menú principal
2. Selecciona "🎯 Señales"
3. Elige una criptomoneda de la lista
4. Selecciona un timeframe
5. El bot generará y mostrará la señal de trading

### Personalización de Lista de Criptomonedas
1. Envía `/start` para mostrar el menú principal
2. Selecciona "📊 Análisis" o "🎯 Señales"
3. Selecciona "⚙️ Configurar lista"
4. Marca o desmarca las criptomonedas que deseas mostrar
5. Selecciona "✅ Guardar" para guardar la configuración

## Compatibilidad con Comandos de Texto

El sistema de menús con botones es complementario a la funcionalidad existente de comandos de texto. Los usuarios pueden seguir escribiendo consultas directamente, como:
- "Analiza Bitcoin en 4h"
- "Dame una señal de ETH en 1h"
- "Configura una alerta para BTC cuando el precio supere los 50000"

## Iniciar el Bot con el Nuevo Sistema

Para iniciar el bot con el nuevo sistema de menús, utiliza el script `start_bot_with_menus.sh`:

```bash
cd ai-module/telegram_bot_service
chmod +x start_bot_with_menus.sh
./start_bot_with_menus.sh
```

## Pruebas del Sistema

Para probar el sistema de menús sin interactuar con el bot real, puedes utilizar el script `test_menu_system.py`:

```bash
cd ai-module/telegram_bot_service
python3 test_menu_system.py
```

Este script simula la interacción con el bot y verifica que los menús funcionen correctamente.

## Notas Técnicas

- El sistema de menús utiliza `InlineKeyboardMarkup` y `CallbackQueryHandler` de la API de Telegram
- La configuración personalizada de criptomonedas se almacena en la base de datos SQLite
- El sistema está implementado utilizando el patrón de `ConversationHandler` para gestionar el flujo de la conversación
