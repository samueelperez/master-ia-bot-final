# Dockerfile simple y directo para Railway
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Copiar archivos de configuración
COPY requirements/ ./requirements/
COPY railway.json ./

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements/common.txt

# Copiar código fuente
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY config/ ./config/

# Instalar dependencias de Node.js para webapp
WORKDIR /app/src/webapp
RUN npm ci --only=production
WORKDIR /app

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/pids

# Crear script de inicio simple directamente
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo 'echo "🚀 Iniciando Crypto AI Bot..."' >> /app/start.sh && \
    echo 'mkdir -p /app/logs /app/pids' >> /app/start.sh && \
    echo 'if [ -z "$TELEGRAM_BOT_TOKEN" ]; then echo "❌ TELEGRAM_BOT_TOKEN no configurado"; exit 1; fi' >> /app/start.sh && \
    echo 'if [ -z "$OPENAI_API_KEY" ]; then echo "❌ OPENAI_API_KEY no configurado"; exit 1; fi' >> /app/start.sh && \
    echo 'echo "✅ Variables verificadas"' >> /app/start.sh && \
    echo 'echo "🔄 Iniciando servicios..."' >> /app/start.sh && \
    echo 'cd /app/src/backend && python main_secure.py > /app/logs/backend.log 2>&1 &' >> /app/start.sh && \
    echo 'cd /app/src/ai-module && python main.py > /app/logs/ai-module.log 2>&1 &' >> /app/start.sh && \
    echo 'cd /app/src/data-service && python main.py > /app/logs/data-service.log 2>&1 &' >> /app/start.sh && \
    echo 'cd /app/src/telegram-bot && python -m core.telegram_bot_secure > /app/logs/telegram-bot.log 2>&1 &' >> /app/start.sh && \
    echo 'echo "✅ Servicios iniciados"' >> /app/start.sh && \
    echo 'echo "🎉 Crypto AI Bot ejecutándose..."' >> /app/start.sh && \
    echo 'while true; do sleep 30; echo "✅ Funcionando - $(date)"; done' >> /app/start.sh && \
    chmod +x /app/start.sh

# Exponer puertos
EXPOSE 3000 8000 9004 9005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["/app/start.sh"]
