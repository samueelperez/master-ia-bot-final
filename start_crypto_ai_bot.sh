#!/bin/bash

# =============================================================================
# SCRIPT DE INICIO DEFINITIVO - CRYPTO AI BOT
# =============================================================================
# Este script inicia todos los servicios del sistema crypto-ai-bot
# Versión: 2.0
# Autor: Crypto AI Bot Team
# =============================================================================

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"

# Crear directorios necesarios
mkdir -p "$LOG_DIR" "$PID_DIR"

# Función para mostrar mensajes
log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

log_success() {
    echo -e "${GREEN}🎉 $1${NC}"
}

# Función para verificar si un proceso está ejecutándose
is_process_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Función para detener un proceso
stop_process() {
    local service_name="$1"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if is_process_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        log_step "Deteniendo $service_name (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 2
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
        log_info "$service_name detenido"
    else
        log_warn "$service_name no estaba ejecutándose"
    fi
}

# Función para iniciar un servicio
start_service() {
    local service_name="$1"
    local command="$2"
    local pid_file="$PID_DIR/${service_name}.pid"
    local log_file="$LOG_DIR/${service_name}.log"
    
    if is_process_running "$pid_file"; then
        log_warn "$service_name ya está ejecutándose"
        return 0
    fi
    
    log_step "Iniciando $service_name..."
    
    # Ejecutar comando en background
    cd "$PROJECT_ROOT"
    eval "$command" > "$log_file" 2>&1 &
    local pid=$!
    
    # Guardar PID
    echo "$pid" > "$pid_file"
    
    # Verificar que el proceso inició correctamente
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        log_info "$service_name iniciado (PID: $pid)"
        return 0
    else
        log_error "Error iniciando $service_name"
        rm -f "$pid_file"
        return 1
    fi
}

# Función para verificar conectividad
check_connectivity() {
    local url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=1
    
    log_step "Verificando conectividad con $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log_info "$service_name está disponible"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "$service_name no está disponible después de $max_attempts intentos"
    return 1
}

# Función para mostrar estado de servicios
show_status() {
    echo ""
    log_step "Estado de servicios:"
    echo "======================"
    
    local services=("ai-module" "backend" "telegram-bot" "data-service")
    
    for service in "${services[@]}"; do
        local pid_file="$PID_DIR/${service}.pid"
        if is_process_running "$pid_file"; then
            local pid=$(cat "$pid_file")
            echo -e "${GREEN}✅ $service (PID: $pid)${NC}"
        else
            echo -e "${RED}❌ $service (No ejecutándose)${NC}"
        fi
    done
}

# Función para mostrar logs
show_logs() {
    local service="$1"
    local log_file="$LOG_DIR/${service}.log"
    
    if [ -f "$log_file" ]; then
        echo ""
        log_step "Últimas líneas del log de $service:"
        echo "====================================="
        tail -n 20 "$log_file"
    else
        log_warn "No se encontró log para $service"
    fi
}

# Función para limpiar procesos
cleanup() {
    log_step "Limpiando procesos..."
    stop_process "ai-module"
    stop_process "backend"
    stop_process "telegram-bot"
    stop_process "data-service"
    log_success "Limpieza completada"
}

# Función para mostrar ayuda
show_help() {
    echo ""
    echo "🚀 SCRIPT DE INICIO DEFINITIVO - CRYPTO AI BOT"
    echo "=============================================="
    echo ""
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  start     - Iniciar todos los servicios"
    echo "  stop      - Detener todos los servicios"
    echo "  restart   - Reiniciar todos los servicios"
    echo "  status    - Mostrar estado de servicios"
    echo "  logs      - Mostrar logs de servicios"
    echo "  clean     - Limpiar procesos y archivos temporales"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 start          # Iniciar todo el sistema"
    echo "  $0 status         # Ver estado de servicios"
    echo "  $0 logs ai-module # Ver logs del módulo AI"
    echo ""
}

# Función principal de inicio
start_all_services() {
    echo ""
    log_step "🚀 INICIANDO SISTEMA CRYPTO AI BOT"
    echo "====================================="
    
    # Verificar variables de entorno
    if [ ! -f ".env" ]; then
        log_error "Archivo .env no encontrado"
        log_info "Crea un archivo .env con las variables necesarias"
        exit 1
    fi
    
    # Cargar variables de entorno
    log_step "Cargando variables de entorno..."
    export $(cat .env | grep -v '^#' | xargs)
    
    # Verificar variables críticas
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        log_error "TELEGRAM_BOT_TOKEN no configurado"
        exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ]; then
        log_error "OPENAI_API_KEY no configurado"
        exit 1
    fi
    
    log_info "Variables de entorno cargadas correctamente"
    
    # Iniciar servicios en orden
    log_step "Iniciando servicios..."
    
    # 1. AI Module
    start_service "ai-module" "cd src/ai-module && python main.py"
    check_connectivity "http://localhost:8001/health" "AI Module"
    
    # 2. Backend
    start_service "backend" "cd src/backend && python main.py"
    check_connectivity "http://localhost:8000/health" "Backend"
    
    # 3. Data Service
    start_service "data-service" "cd src/data-service && python main.py"
    check_connectivity "http://localhost:8002/health" "Data Service"
    
    # 4. Telegram Bot
    start_service "telegram-bot" "cd src/telegram-bot && python core/telegram_bot.py"
    
    # Mostrar estado final
    show_status
    
    echo ""
    log_success "🎉 SISTEMA CRYPTO AI BOT INICIADO EXITOSAMENTE"
    echo ""
    echo "📊 Servicios activos:"
    echo "   • AI Module: http://localhost:8001"
    echo "   • Backend: http://localhost:8000"
    echo "   • Data Service: http://localhost:8002"
    echo "   • Telegram Bot: Activo"
    echo ""
    echo "📝 Comandos útiles:"
    echo "   • Ver estado: $0 status"
    echo "   • Ver logs: $0 logs [servicio]"
    echo "   • Detener: $0 stop"
    echo ""
}

# Función para detener todos los servicios
stop_all_services() {
    echo ""
    log_step "🛑 DETENIENDO SISTEMA CRYPTO AI BOT"
    echo "====================================="
    
    stop_process "telegram-bot"
    stop_process "data-service"
    stop_process "backend"
    stop_process "ai-module"
    
    log_success "🎉 SISTEMA CRYPTO AI BOT DETENIDO"
}

# Función para reiniciar servicios
restart_all_services() {
    log_step "🔄 REINICIANDO SISTEMA CRYPTO AI BOT"
    echo "====================================="
    
    stop_all_services
    sleep 3
    start_all_services
}

# Función para mostrar logs
show_service_logs() {
    local service="$1"
    
    if [ -z "$service" ]; then
        echo ""
        log_step "📋 LOGS DISPONIBLES:"
        echo "====================="
        for log_file in "$LOG_DIR"/*.log; do
            if [ -f "$log_file" ]; then
                local service_name=$(basename "$log_file" .log)
                echo "• $service_name"
            fi
        done
        echo ""
        echo "Uso: $0 logs [servicio]"
        echo "Ejemplo: $0 logs ai-module"
    else
        show_logs "$service"
    fi
}

# Manejo de señales
trap cleanup EXIT
trap 'log_error "Interrumpido por el usuario"; exit 1' INT TERM

# Procesar argumentos
case "${1:-start}" in
    "start")
        start_all_services
        ;;
    "stop")
        stop_all_services
        ;;
    "restart")
        restart_all_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_service_logs "$2"
        ;;
    "clean")
        cleanup
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        log_error "Opción desconocida: $1"
        show_help
        exit 1
        ;;
esac 