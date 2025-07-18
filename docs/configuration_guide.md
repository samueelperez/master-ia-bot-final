# Configuración Centralizada - Crypto AI Bot

## 📋 Resumen

La configuración del proyecto ha sido consolidada en el directorio `config/` para simplificar la gestión y evitar duplicaciones.

## 🗂️ Estructura de Configuración

```
config/
├── .env                    # Configuración principal
├── .env.secrets           # Secretos sensibles (NO subir a git)
├── .env.development       # Configuración para desarrollo
├── .env.production        # Configuración para producción
├── .env.example          # Plantilla para nuevos desarrolladores
└── .env.secrets.example  # Plantilla para secretos
```

## 🚀 Setup Rápido

### Para Nuevos Desarrolladores

1. **Clonar configuración básica:**
   ```bash
   cd config/
   cp .env.example .env
   cp .env.secrets.example .env.secrets
   ```

2. **Configurar credenciales en `.env.secrets`:**
   - OpenAI API Key
   - Telegram Bot Token
   - Otras API keys necesarias

3. **Iniciar el proyecto:**
   ```bash
   ./start_crypto_ai_bot.sh
   ```

## 🔧 Configuración por Entorno

### Desarrollo Local
- Usar: `.env` + `.env.secrets`
- URLs apuntan a localhost
- Debug habilitado

### Producción
- Usar: `.env.production` + `.env.secrets`
- URLs de producción
- Debug deshabilitado
- Logs en nivel WARNING

## 🔐 Gestión de Secretos

### Variables Sensibles (en `.env.secrets`):
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `HF_TOKEN`
- `CRYPTOPANIC_API_KEY`
- `NEWSAPI_KEY`
- `TWITTER_BEARER_TOKEN`

### ⚠️ Importante:
- **NUNCA** subir `.env.secrets` a control de versiones
- Mantener secretos separados de configuración pública
- Usar variables de entorno del sistema en producción

## 🐳 Docker Compose

El archivo `docker-compose.yml` ha sido actualizado para:
- Cargar automáticamente `.env` y `.env.secrets`
- Usar variables centralizadas
- Configuración consistente entre servicios

## 📜 Scripts de Inicio

### Script Principal: `start_crypto_ai_bot.sh`
- Verifica configuración automáticamente
- Carga variables de entorno apropiadas
- Inicia todos los servicios
- Proporciona URLs de acceso

### Uso:
```bash
# Desarrollo
ENVIRONMENT=development ./start_crypto_ai_bot.sh

# Producción
ENVIRONMENT=production ./start_crypto_ai_bot.sh
```

## 🔄 Migración desde Configuración Anterior

Si tienes configuración anterior, el sistema:
1. ✅ Creó backup automático en `config_backup/`
2. ✅ Consolidó todas las variables
3. ✅ Mantuvo valores existentes
4. ✅ Actualizó referencias

## 🛠️ Troubleshooting

### Error: "config/.env.secrets no encontrado"
```bash
cp config/.env.secrets.example config/.env.secrets
# Editar y configurar credenciales
```

### Error: "Variable no definida"
- Verificar que la variable existe en `.env` o `.env.secrets`
- Comprobar que no hay espacios alrededor del `=`
- Verificar que el archivo se está cargando correctamente

### Variables no se cargan
- Verificar permisos de archivos de configuración
- Comprobar formato del archivo (sin espacios extra)
- Verificar que `docker-compose.yml` referencia los archivos correctos

## 📞 Soporte

Si encuentras problemas con la configuración:
1. Verificar backup en `config_backup/`
2. Comprobar logs de Docker: `docker-compose logs`
3. Validar formato de archivos `.env`

---

*Configuración consolidada automáticamente el 2025-06-19 18:30:35*
