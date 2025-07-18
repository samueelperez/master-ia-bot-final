#!/bin/bash
# Script de inicio del Telegram Bot Securizado

echo "🔒 Iniciando Telegram Bot Securizado..."

# Verificar variables de entorno obligatorias
if [ -z "$TELEGRAM_BOT_TOKEN" ] && [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN no configurado"
    echo "   Configura tu token en el archivo .env"
    exit 1
fi

if [ -z "$TELEGRAM_AUTHORIZED_USERS" ]; then
    echo "⚠️  Advertencia: TELEGRAM_AUTHORIZED_USERS no configurado"
    echo "   El bot será accesible por cualquier usuario"
fi

# Cargar variables de entorno si existe .env
if [ -f .env ]; then
    echo "📋 Cargando variables de entorno desde .env"
    export $(cat .env | xargs)
fi

# Verificar conectividad con AI Module
echo "🔍 Verificando conectividad con AI Module..."
AI_URL=${AI_MODULE_URL:-"http://localhost:9004"}
if ! curl -s "$AI_URL/health" > /dev/null; then
    echo "⚠️  Advertencia: No se puede conectar con AI Module en $AI_URL"
    echo "   Asegúrate de que el módulo AI esté ejecutándose"
fi

# Iniciar bot
echo "🚀 Iniciando bot..."
cd "$(dirname "$0")"
python -m core.telegram_bot_secure

echo "🔒 Bot de Telegram Securizado detenido"
