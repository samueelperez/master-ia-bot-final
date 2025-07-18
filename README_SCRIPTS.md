# 🚀 Scripts de Gestión - Crypto AI Bot

Este documento describe los scripts principales para gestionar el sistema Crypto AI Bot.

## 📋 Scripts Principales

### 1. `start_crypto_ai_bot.sh` - Script de Inicio Definitivo

**Descripción:** Script principal para iniciar, detener y gestionar todos los servicios del sistema.

**Uso:**
```bash
# Iniciar todo el sistema
./start_crypto_ai_bot.sh start

# Ver estado de servicios
./start_crypto_ai_bot.sh status

# Ver logs de un servicio específico
./start_crypto_ai_bot.sh logs ai-module

# Detener todo el sistema
./start_crypto_ai_bot.sh stop

# Reiniciar todo el sistema
./start_crypto_ai_bot.sh restart

# Mostrar ayuda
./start_crypto_ai_bot.sh help
```

**Características:**
- ✅ Inicia todos los servicios en el orden correcto
- ✅ Verifica conectividad de cada servicio
- ✅ Manejo de PIDs para control de procesos
- ✅ Logs centralizados en `/logs/`
- ✅ Verificación de variables de entorno
- ✅ Manejo de errores y limpieza automática

### 2. `backup_important_files.sh` - Script de Backup Inteligente

**Descripción:** Crea y gestiona backups de archivos importantes manteniendo solo un backup por archivo.

**Uso:**
```bash
# Crear backups de archivos importantes
./backup_important_files.sh create

# Restaurar backups
./backup_important_files.sh restore

# Ver backups disponibles
./backup_important_files.sh list

# Limpiar backups antiguos
./backup_important_files.sh clean
```

**Archivos que se respaldan:**
- `.env` - Variables de entorno
- `src/telegram-bot/core/telegram_bot_secure.py` - Bot principal
- `src/ai-module/main.py` - Módulo AI
- `src/backend/main.py` - Backend
- `src/data-service/main.py` - Servicio de datos
- `src/telegram-bot/telegram_bot_memory_secure.db` - Base de datos del bot
- Archivos de configuración de ejemplo

### 3. `cleanup_automated.sh` - Script de Limpieza Automática

**Descripción:** Limpia archivos temporales, caché y organiza el proyecto.

**Uso:**
```bash
# Ejecutar limpieza automática
./cleanup_automated.sh
```

**Funciones:**
- 🧹 Limpia archivos de caché de Python
- 📁 Organiza archivos de prueba en `/tests/debug_scripts/`
- 📊 Consolida logs en `/logs/consolidated/`
- 🗑️ Elimina archivos temporales y vacíos
- ⏰ Limpia logs antiguos (más de 7 días)

## 🏗️ Estructura de Directorios

```
crypto-ai-bot/
├── start_crypto_ai_bot.sh          # Script principal de inicio
├── backup_important_files.sh        # Script de backup
├── cleanup_automated.sh            # Script de limpieza
├── logs/                           # Logs centralizados
│   └── consolidated/               # Logs consolidados
├── pids/                           # Archivos PID de servicios
├── backup_env/                     # Backups de archivos importantes
└── tests/
    └── debug_scripts/              # Scripts de prueba y debug
```

## 🔧 Configuración Requerida

### Variables de Entorno (.env)

El archivo `.env` debe contener las siguientes variables:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_AUTHORIZED_USERS=user_id1,user_id2

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Servicios
AI_MODULE_URL=http://localhost:8001
BACKEND_URL=http://localhost:8000
DATA_SERVICE_URL=http://localhost:8002

# Base de datos
DATABASE_URL=your_database_url

# Seguridad
API_SECRET_KEY=your_secret_key
```

## 🚀 Flujo de Trabajo Recomendado

### 1. Configuración Inicial
```bash
# 1. Crear archivo .env con las variables necesarias
cp config/development/telegram-bot.env.example .env
# Editar .env con tus credenciales

# 2. Crear backup inicial
./backup_important_files.sh create

# 3. Instalar dependencias
pip install -r requirements/ai-module.txt
pip install -r requirements/backend.txt
pip install -r requirements/data-service.txt
```

### 2. Uso Diario
```bash
# Iniciar sistema
./start_crypto_ai_bot.sh start

# Verificar estado
./start_crypto_ai_bot.sh status

# Ver logs si hay problemas
./start_crypto_ai_bot.sh logs ai-module

# Detener sistema
./start_crypto_ai_bot.sh stop
```

### 3. Mantenimiento Semanal
```bash
# Limpiar archivos temporales
./cleanup_automated.sh

# Crear backup de archivos importantes
./backup_important_files.sh create

# Verificar backups disponibles
./backup_important_files.sh list
```

## 🛠️ Solución de Problemas

### Servicio no inicia
```bash
# Verificar logs del servicio
./start_crypto_ai_bot.sh logs [servicio]

# Verificar variables de entorno
cat .env | grep -v '^#'

# Reiniciar servicio específico
./start_crypto_ai_bot.sh restart
```

### Restaurar configuración
```bash
# Ver backups disponibles
./backup_important_files.sh list

# Restaurar archivo específico
./backup_important_files.sh restore
```

### Limpiar completamente
```bash
# Detener todos los servicios
./start_crypto_ai_bot.sh stop

# Limpiar archivos temporales
./cleanup_automated.sh

# Reiniciar sistema
./start_crypto_ai_bot.sh start
```

## 📊 Monitoreo

### Verificar estado de servicios
```bash
./start_crypto_ai_bot.sh status
```

### Ver logs en tiempo real
```bash
# Ver logs de todos los servicios
tail -f logs/*.log

# Ver logs de un servicio específico
tail -f logs/ai-module.log
```

### Verificar conectividad
```bash
# AI Module
curl http://localhost:8001/health

# Backend
curl http://localhost:8000/health

# Data Service
curl http://localhost:8002/health
```

## 🔒 Seguridad

- Los scripts verifican variables de entorno críticas antes de iniciar
- Los logs no contienen información sensible
- Los backups se almacenan localmente
- Los PIDs se gestionan de forma segura

## 📝 Notas Importantes

1. **Siempre** crea un backup antes de hacer cambios importantes
2. **Verifica** el estado de servicios antes de reiniciar
3. **Revisa** los logs si hay problemas
4. **Ejecuta** la limpieza semanal para mantener el proyecto organizado
5. **Mantén** actualizado el archivo `.env` con las credenciales correctas

## 🆘 Soporte

Si encuentras problemas:

1. Verifica los logs: `./start_crypto_ai_bot.sh logs [servicio]`
2. Revisa el estado: `./start_crypto_ai_bot.sh status`
3. Restaura desde backup: `./backup_important_files.sh restore`
4. Limpia y reinicia: `./cleanup_automated.sh && ./start_crypto_ai_bot.sh restart` 