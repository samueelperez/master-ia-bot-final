#!/bin/bash

# =============================================================================
# SCRIPT DE BACKUP INTELIGENTE - CRYPTO AI BOT
# =============================================================================
# Este script crea backups de archivos importantes manteniendo solo uno por archivo
# Versión: 1.0
# =============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backup_env"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

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

# Función para crear backup de un archivo
backup_file() {
    local source_file="$1"
    local backup_name="$2"
    
    if [ -f "$source_file" ]; then
        local backup_file="$BACKUP_DIR/${backup_name}_backup"
        
        # Eliminar backup anterior si existe
        if [ -f "$backup_file" ]; then
            rm -f "$backup_file"
            log_warn "Backup anterior eliminado: $backup_name"
        fi
        
        # Crear nuevo backup
        cp "$source_file" "$backup_file"
        log_info "Backup creado: $backup_name"
    else
        log_warn "Archivo no encontrado: $source_file"
    fi
}

# Función para restaurar backup
restore_file() {
    local backup_name="$1"
    local target_file="$2"
    local backup_file="$BACKUP_DIR/${backup_name}_backup"
    
    if [ -f "$backup_file" ]; then
        cp "$backup_file" "$target_file"
        log_info "Backup restaurado: $backup_name"
    else
        log_error "Backup no encontrado: $backup_name"
    fi
}

# Función para mostrar backups disponibles
show_backups() {
    echo ""
    log_step "📋 BACKUPS DISPONIBLES:"
    echo "========================"
    
    if [ -d "$BACKUP_DIR" ]; then
        for backup_file in "$BACKUP_DIR"/*_backup; do
            if [ -f "$backup_file" ]; then
                local backup_name=$(basename "$backup_file" _backup)
                local file_size=$(du -h "$backup_file" | cut -f1)
                local file_date=$(stat -f "%Sm" "$backup_file" 2>/dev/null || stat -c "%y" "$backup_file" 2>/dev/null)
                echo "• $backup_name ($file_size, $file_date)"
            fi
        done
    else
        log_warn "No hay backups disponibles"
    fi
}

# Función para limpiar backups antiguos
cleanup_old_backups() {
    log_step "Limpiando backups antiguos..."
    
    # Eliminar backups con más de 30 días
    find "$BACKUP_DIR" -name "*_backup" -mtime +30 -delete 2>/dev/null || true
    
    log_info "Backups antiguos eliminados"
}

# Función principal de backup
create_backups() {
    echo ""
    log_step "💾 CREANDO BACKUPS DE ARCHIVOS IMPORTANTES"
    echo "============================================="
    
    # Crear directorio de backup si no existe
    mkdir -p "$BACKUP_DIR"
    
    # Lista de archivos importantes para backup
    local important_files=(
        ".env:env"
        "src/telegram-bot/core/telegram_bot_secure.py:telegram_bot_secure"
        "src/ai-module/main.py:ai_module_main"
        "src/backend/main.py:backend_main"
        "src/data-service/main.py:data_service_main"
        "src/telegram-bot/telegram_bot_memory_secure.db:telegram_bot_db"
        "config/development/telegram-bot.env.example:telegram_bot_env_example"
        "config/development/ai-module.env.example:ai_module_env_example"
        "config/development/data-service.env.example:data_service_env_example"
    )
    
    for file_info in "${important_files[@]}"; do
        local source_file="${file_info%:*}"
        local backup_name="${file_info#*:}"
        backup_file "$source_file" "$backup_name"
    done
    
    # Limpiar backups antiguos
    cleanup_old_backups
    
    echo ""
    log_info "🎉 BACKUP COMPLETADO"
    show_backups
}

# Función para restaurar backups
restore_backups() {
    echo ""
    log_step "🔄 RESTAURANDO BACKUPS"
    echo "========================"
    
    show_backups
    
    echo ""
    echo "¿Qué backup quieres restaurar?"
    echo "1. Variables de entorno (.env)"
    echo "2. Telegram Bot"
    echo "3. AI Module"
    echo "4. Backend"
    echo "5. Data Service"
    echo "6. Base de datos del bot"
    echo "7. Todos los archivos de configuración"
    echo "0. Cancelar"
    
    read -p "Selecciona una opción: " choice
    
    case $choice in
        1)
            restore_file "env" ".env"
            ;;
        2)
            restore_file "telegram_bot_secure" "src/telegram-bot/core/telegram_bot_secure.py"
            ;;
        3)
            restore_file "ai_module_main" "src/ai-module/main.py"
            ;;
        4)
            restore_file "backend_main" "src/backend/main.py"
            ;;
        5)
            restore_file "data_service_main" "src/data-service/main.py"
            ;;
        6)
            restore_file "telegram_bot_db" "src/telegram-bot/telegram_bot_memory_secure.db"
            ;;
        7)
            restore_file "telegram_bot_env_example" "config/development/telegram-bot.env.example"
            restore_file "ai_module_env_example" "config/development/ai-module.env.example"
            restore_file "data_service_env_example" "config/development/data-service.env.example"
            ;;
        0)
            log_info "Restauración cancelada"
            ;;
        *)
            log_error "Opción inválida"
            ;;
    esac
}

# Función para mostrar ayuda
show_help() {
    echo ""
    echo "💾 SCRIPT DE BACKUP INTELIGENTE - CRYPTO AI BOT"
    echo "=============================================="
    echo ""
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  create    - Crear backups de archivos importantes"
    echo "  restore   - Restaurar backups"
    echo "  list      - Mostrar backups disponibles"
    echo "  clean     - Limpiar backups antiguos"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 create        # Crear backups"
    echo "  $0 restore       # Restaurar backups"
    echo "  $0 list          # Ver backups disponibles"
    echo ""
}

# Procesar argumentos
case "${1:-create}" in
    "create")
        create_backups
        ;;
    "restore")
        restore_backups
        ;;
    "list")
        show_backups
        ;;
    "clean")
        cleanup_old_backups
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