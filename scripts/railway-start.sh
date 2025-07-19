#!/bin/bash

# Script de inicio optimizado para Railway
# Maneja la inicialización de todos los servicios del Crypto AI Bot

set -e

echo "🚀 Iniciando Crypto AI Bot en Railway..."

# Configurar variables de entorno por defecto
export ENVIRONMENT=${ENVIRONMENT:-production}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export NODE_ENV=${NODE_ENV:-production}

# Crear directorios necesarios
mkdir -p /app/logs /app/pids /app/backup_env

# Función para verificar variables de entorno críticas
check_required_env_vars() {
    local required_vars=(
        "OPENAI_API_KEY"
        "TELEGRAM_BOT_TOKEN"
        "API_SECRET_KEY"
        "BACKEND_API_SECRET_KEY"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo "❌ Variables de entorno requeridas faltantes:"
        printf '  - %s\n' "${missing_vars[@]}"
        echo "⚠️  Configura estas variables en Railway Dashboard"
        exit 1
    fi
    
    echo "✅ Todas las variables de entorno requeridas están configuradas"
}

# Función para esperar que un servicio esté listo
wait_for_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    echo "⏳ Esperando que $service_name esté listo..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url/health" > /dev/null 2>&1; then
            echo "✅ $service_name está listo"
            return 0
        fi
        
        echo "  Intento $attempt/$max_attempts - $service_name no está listo aún..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service_name no se pudo iniciar después de $max_attempts intentos"
    return 1
}

# Función para iniciar servicios en segundo plano
start_service() {
    local service_name=$1
    local service_dir=$2
    local start_command=$3
    
    echo "🚀 Iniciando $service_name..."
    
    cd "$service_dir"
    
    # Ejecutar comando de inicio en segundo plano
    eval "$start_command" > "/app/logs/${service_name}.log" 2>&1 &
    local pid=$!
    
    # Guardar PID
    echo $pid > "/app/pids/${service_name}.pid"
    
    echo "✅ $service_name iniciado con PID: $pid"
    cd /app
}

# Función para verificar salud de todos los servicios
health_check_all() {
    echo "🏥 Verificando salud de todos los servicios..."
    
    local services=(
        "backend:http://localhost:8000"
        "ai-module:http://localhost:9004"
        "data-service:http://localhost:9005"
        "webapp:http://localhost:3000"
    )
    
    local all_healthy=true
    
    for service in "${services[@]}"; do
        IFS=':' read -r name url <<< "$service"
        
        if ! wait_for_service "$name" "$url" 10; then
            all_healthy=false
        fi
    done
    
    if [[ "$all_healthy" == true ]]; then
        echo "🎉 Todos los servicios están funcionando correctamente!"
        return 0
    else
        echo "❌ Algunos servicios no están funcionando correctamente"
        return 1
    fi
}

# Función para mostrar logs en tiempo real
show_logs() {
    echo "📋 Mostrando logs en tiempo real..."
    tail -f /app/logs/*.log &
}

# Función para manejar señales de terminación
cleanup() {
    echo "🛑 Recibida señal de terminación, cerrando servicios..."
    
    # Terminar todos los procesos
    for pid_file in /app/pids/*.pid; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "  Terminando proceso $pid..."
                kill "$pid"
            fi
        fi
    done
    
    # Esperar a que los procesos terminen
    sleep 2
    
    # Forzar terminación si es necesario
    for pid_file in /app/pids/*.pid; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "  Forzando terminación del proceso $pid..."
                kill -9 "$pid"
            fi
        fi
    done
    
    echo "✅ Servicios cerrados correctamente"
    exit 0
}

# Configurar manejo de señales
trap cleanup SIGTERM SIGINT

# Verificar variables de entorno
check_required_env_vars

# Iniciar servicios en orden
echo "🔄 Iniciando servicios en secuencia..."

# 1. Backend
start_service "backend" "/app/src/backend" "python main_secure.py"

# 2. AI Module
start_service "ai-module" "/app/src/ai-module" "python main.py"

# 3. Data Service
start_service "data-service" "/app/src/data-service" "python main.py"

# 4. Webapp
start_service "webapp" "/app/src/webapp" "npm start"

# 5. Telegram Bot (último, depende de todos los demás)
echo "⏳ Esperando que los servicios base estén listos antes de iniciar Telegram Bot..."
sleep 10

start_service "telegram-bot" "/app/src/telegram-bot" "python -m core.telegram_bot_secure"

# Verificar salud de todos los servicios
if health_check_all; then
    echo "🎉 Crypto AI Bot iniciado exitosamente en Railway!"
    echo "📊 Servicios disponibles:"
    echo "  - Backend API: http://localhost:8000"
    echo "  - AI Module: http://localhost:9004"
    echo "  - Data Service: http://localhost:9005"
    echo "  - Webapp: http://localhost:3000"
    echo "  - Telegram Bot: Ejecutándose"
    
    # Mostrar logs en tiempo real
    show_logs
    
    # Mantener el script ejecutándose
    while true; do
        sleep 30
        
        # Verificar que todos los servicios sigan funcionando
        if ! health_check_all > /dev/null 2>&1; then
            echo "⚠️  Algunos servicios no están respondiendo, reiniciando..."
            cleanup
            exit 1
        fi
    done
else
    echo "❌ Error al iniciar Crypto AI Bot"
    cleanup
    exit 1
fi 