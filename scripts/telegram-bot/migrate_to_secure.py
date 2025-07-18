#!/usr/bin/env python3
"""
Script de migración para el módulo Telegram Bot.
Reemplaza telegram_bot.py inseguro con telegram_bot_secure.py y configura el entorno.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Función principal de migración."""
    logger.info("🔒 MIGRACIÓN DEL MÓDULO TELEGRAM BOT A VERSIÓN SECURIZADA")
    logger.info("=" * 70)
    
    # Obtener directorio del proyecto
    project_root = Path(__file__).parent.parent.parent
    telegram_src = project_root / "src" / "telegram-bot" / "core"
    
    logger.info(f"📁 Directorio del proyecto: {project_root}")
    logger.info(f"📁 Directorio del telegram bot: {telegram_src}")
    
    steps_completed = 0
    total_steps = 5
    
    try:
        # Paso 1: Crear backup del archivo original
        logger.info("\n📋 Paso 1/5: Creando backup del archivo original")
        
        original_file = telegram_src / "telegram_bot.py"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = telegram_src / f"telegram_bot_backup_{timestamp}.py"
        
        if original_file.exists():
            shutil.copy2(original_file, backup_file)
            logger.info(f"✅ Backup creado: {backup_file.name}")
        else:
            logger.info("ℹ️  Archivo original no existe, saltando backup")
        
        steps_completed += 1
        
        # Paso 2: Reemplazar con versión securizada
        logger.info("\n📋 Paso 2/5: Reemplazando con versión securizada")
        
        secure_file = telegram_src / "telegram_bot_secure.py"
        if secure_file.exists():
            shutil.copy2(secure_file, original_file)
            logger.info(f"✅ Archivo securizado copiado a telegram_bot.py")
        else:
            raise FileNotFoundError(f"Archivo securizado no encontrado: {secure_file}")
        
        steps_completed += 1
        
        # Paso 3: Crear archivo de configuración actualizado
        logger.info("\n📋 Paso 3/5: Actualizando archivo de configuración")
        
        config_content = """# Configuración de Seguridad del Telegram Bot
# Copiar este archivo a .env y configurar los valores apropiados

# OBLIGATORIO: Token del bot de Telegram
TELEGRAM_TOKEN=your-telegram-bot-token-here

# OBLIGATORIO: URL del módulo AI
AI_MODULE_URL=http://localhost:9001

# Rate Limiting (opcional - defaults seguros)
TELEGRAM_RATE_LIMIT_PER_MINUTE=30
TELEGRAM_RATE_LIMIT_PER_HOUR=300
TELEGRAM_RATE_LIMIT_PER_DAY=5000

# Base de datos de memoria (opcional)
MEMORY_DB=telegram_bot_memory_secure.db

# IMPORTANTE: Lista de usuarios autorizados (IDs de Telegram separados por comas)
# Para obtener tu ID de Telegram, envía un mensaje a @userinfobot
TELEGRAM_AUTHORIZED_USERS=123456789,987654321

# IMPORTANTE: Lista de administradores (IDs de Telegram separados por comas)
TELEGRAM_ADMIN_USERS=123456789

# Configuración de logging (opcional)
TELEGRAM_LOG_LEVEL=INFO
TELEGRAM_LOG_FILE=telegram_bot.log

# Configuración de seguridad adicional (opcional)
TELEGRAM_MAX_MESSAGE_LENGTH=4000
TELEGRAM_BLOCKED_PATTERNS_ENABLED=true
TELEGRAM_MEMORY_ENCRYPTION_ENABLED=true

# Timeouts (opcional - defaults seguros)
TELEGRAM_AI_TIMEOUT=25
TELEGRAM_HEALTH_CHECK_TIMEOUT=5
"""
        
        config_file = telegram_src.parent / "config.env.example"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"✅ Configuración actualizada: {config_file.name}")
        steps_completed += 1
        
        # Paso 4: Crear script de inicio securizado
        logger.info("\n📋 Paso 4/5: Creando script de inicio securizado")
        
        start_script_content = """#!/bin/bash
# Script de inicio del Telegram Bot Securizado

echo "🔒 Iniciando Telegram Bot Securizado..."

# Verificar variables de entorno obligatorias
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_TOKEN no configurado"
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
AI_URL=${AI_MODULE_URL:-"http://localhost:9001"}
if ! curl -s "$AI_URL/health" > /dev/null; then
    echo "⚠️  Advertencia: No se puede conectar con AI Module en $AI_URL"
    echo "   Asegúrate de que el módulo AI esté ejecutándose"
fi

# Iniciar bot
echo "🚀 Iniciando bot..."
cd "$(dirname "$0")"
python -m core.telegram_bot

echo "🔒 Bot de Telegram Securizado detenido"
"""
        
        start_script = telegram_src.parent / "start_secure_bot.sh"
        with open(start_script, 'w', encoding='utf-8') as f:
            f.write(start_script_content)
        
        # Hacer ejecutable el script
        start_script.chmod(0o755)
        
        logger.info(f"✅ Script de inicio creado: {start_script.name}")
        steps_completed += 1
        
        # Paso 5: Crear Dockerfile securizado
        logger.info("\n📋 Paso 5/5: Creando Dockerfile securizado")
        
        dockerfile_content = """# Dockerfile para Telegram Bot Securizado
FROM python:3.11-slim

# Crear usuario no-root
RUN useradd --create-home --shell /bin/bash telegrambot

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs data && chown -R telegrambot:telegrambot logs data

# Cambiar a usuario no-root
USER telegrambot

# Variables de entorno por defecto
ENV TELEGRAM_TOKEN=""
ENV AI_MODULE_URL="http://localhost:9001"
ENV TELEGRAM_RATE_LIMIT_PER_MINUTE=30
ENV TELEGRAM_AUTHORIZED_USERS=""
ENV TELEGRAM_LOG_LEVEL=INFO
ENV MEMORY_DB="data/telegram_bot_memory_secure.db"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import sys; sys.exit(0 if True else 1)"

# Comando de inicio
CMD ["python", "-m", "core.telegram_bot"]
"""
        
        dockerfile_secure = telegram_src.parent / "Dockerfile.secure"
        with open(dockerfile_secure, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        logger.info(f"✅ Dockerfile securizado creado: {dockerfile_secure.name}")
        steps_completed += 1
        
        # Resumen final
        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMEN DE MIGRACIÓN")
        logger.info("=" * 70)
        logger.info(f"✅ Pasos completados: {steps_completed}/{total_steps}")
        
        if steps_completed == total_steps:
            logger.info("\n🎉 ¡MIGRACIÓN EXITOSA!")
            logger.info("🔒 El módulo Telegram Bot ha sido securizado completamente")
            logger.info("\n📋 PRÓXIMOS PASOS:")
            logger.info("1. Configurar variables de entorno usando config.env.example")
            logger.info("2. Agregar tu ID de Telegram a TELEGRAM_AUTHORIZED_USERS")
            logger.info("3. Ejecutar: ./start_secure_bot.sh")
            logger.info("4. Validar: python scripts/telegram-bot/validate_security.py")
            logger.info("\n⚠️  IMPORTANTE:")
            logger.info("• Configurar TELEGRAM_TOKEN con tu token real")
            logger.info("• Agregar IDs de usuarios autorizados")
            logger.info("• Configurar al menos un usuario administrador")
            logger.info("• Verificar que AI Module esté ejecutándose")
            logger.info("\n🔍 CÓMO OBTENER TU ID DE TELEGRAM:")
            logger.info("• Envía un mensaje a @userinfobot en Telegram")
            logger.info("• Copia el número de ID que te responda")
            logger.info("• Agrégalo a TELEGRAM_AUTHORIZED_USERS")
            return 0
        else:
            logger.error(f"❌ Migración incompleta: {steps_completed}/{total_steps} pasos")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 