# 🚀 Guía de Despliegue en Railway - Crypto AI Bot

## 📋 Resumen

Esta guía te ayudará a desplegar tu Crypto AI Bot en Railway.app de forma rápida y segura. Railway es una plataforma de despliegue que ofrece escalabilidad automática, bases de datos gestionadas y un entorno de producción robusto.

## 🎯 Ventajas de Railway

- ✅ **Despliegue automático** desde GitHub
- ✅ **Bases de datos gestionadas** (PostgreSQL, Redis)
- ✅ **Escalabilidad automática** según tráfico
- ✅ **SSL automático** y dominios personalizados
- ✅ **Variables de entorno** seguras
- ✅ **Logs en tiempo real** y monitoreo
- ✅ **Rollbacks** automáticos en caso de errores

## 📦 Archivos de Configuración Creados

### ✅ Archivos Principales
- `railway.json` - Configuración principal de Railway
- `docker-compose.railway.yml` - Orquestación de servicios
- `Dockerfile.railway` - Imagen optimizada para Railway
- `.railwayignore` - Archivos a excluir del despliegue
- `railway.toml` - Configuración TOML para Railway
- `scripts/railway-start.sh` - Script de inicio optimizado

## 🚀 Pasos de Despliegue

### **Paso 1: Preparar el Repositorio**

1. **Subir cambios a GitHub:**
   ```bash
   git add .
   git commit -m "🚀 Configuración Railway lista para despliegue"
   git push origin main
   ```

2. **Verificar que todos los archivos estén incluidos:**
   ```bash
   ls -la | grep railway
   ls -la scripts/railway-start.sh
   ```

### **Paso 2: Crear Proyecto en Railway**

1. **Ir a [Railway.app](https://railway.app)**
2. **Iniciar sesión** con tu cuenta de GitHub
3. **Crear nuevo proyecto:**
   - Click en "New Project"
   - Seleccionar "Deploy from GitHub repo"
   - Buscar y seleccionar tu repositorio `crypto-ai-bot`
   - Click en "Deploy Now"

### **Paso 3: Configurar Variables de Entorno**

#### **🔐 Variables OBLIGATORIAS**

En Railway Dashboard → Variables → Add Variables:

```bash
# API Keys Críticas
OPENAI_API_KEY=sk-your-openai-api-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
API_SECRET_KEY=your-secure-secret-key-32-chars-min
BACKEND_API_SECRET_KEY=your-backend-secret-key-32-chars-min
DATA_SERVICE_SECRET_KEY=your-data-service-secret-key-32-chars-min

# Configuración de Base de Datos
POSTGRES_USER=crypto_bot
POSTGRES_PASSWORD=your-secure-postgres-password
POSTGRES_DB=crypto_bot_db
REDIS_PASSWORD=your-secure-redis-password

# URLs Públicas (se configurarán automáticamente después del despliegue)
NEXT_PUBLIC_API_URL=https://your-app.railway.app
NEXT_PUBLIC_AI_MODULE_URL=https://your-app.railway.app

# Usuarios Autorizados de Telegram
TELEGRAM_AUTHORIZED_USERS=123456789,987654321
TELEGRAM_ADMIN_USERS=123456789
```

#### **📰 Variables Opcionales**

```bash
# API Keys Externas (opcionales)
NEWS_API_KEY=your-news-api-key
TWITTER_BEARER_TOKEN=your-twitter-bearer-token
ECONOMIC_CALENDAR_API_KEY=your-economic-calendar-key

# Configuración de Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
BACKEND_RATE_LIMIT_PER_MINUTE=60
BACKEND_RATE_LIMIT_PER_HOUR=1000
TELEGRAM_RATE_LIMIT_PER_MINUTE=30
TELEGRAM_RATE_LIMIT_PER_HOUR=300

# Configuración de CORS
ALLOWED_ORIGINS=*
ALLOWED_HOSTS=*
BACKEND_ALLOWED_ORIGINS=*
BACKEND_ALLOWED_HOSTS=*
BACKEND_CORS_ORIGINS=*
```

### **Paso 4: Configurar Servicios de Base de Datos**

1. **En Railway Dashboard → New Service → Database**
2. **Seleccionar PostgreSQL 15**
3. **Seleccionar Redis 7**
4. **Railway generará automáticamente las variables de conexión**

### **Paso 5: Configurar Dominio Personalizado (Opcional)**

1. **En Railway Dashboard → Settings → Domains**
2. **Agregar dominio personalizado**
3. **Configurar DNS según las instrucciones de Railway**

## 🔧 Configuración Post-Despliegue

### **Actualizar URLs Públicas**

Después del primer despliegue exitoso, actualiza las variables:

```bash
# Obtener URLs de Railway Dashboard
NEXT_PUBLIC_API_URL=https://your-app.railway.app
NEXT_PUBLIC_AI_MODULE_URL=https://your-app.railway.app
```

### **Verificar Servicios**

1. **Backend API:** `https://your-app.railway.app:8000/health`
2. **AI Module:** `https://your-app.railway.app:9004/health`
3. **Data Service:** `https://your-app.railway.app:9005/health`
4. **Webapp:** `https://your-app.railway.app:3000`

## 📊 Monitoreo y Logs

### **Ver Logs en Tiempo Real**

1. **Railway Dashboard → Deployments → Latest**
2. **Click en "View Logs"**
3. **Filtrar por servicio si es necesario**

### **Métricas de Rendimiento**

- **CPU Usage:** Monitorear uso de CPU
- **Memory Usage:** Verificar uso de memoria
- **Network:** Tráfico de red
- **Disk:** Uso de almacenamiento

## 🛠️ Troubleshooting

### **Error: Variables de Entorno Faltantes**

```bash
# Verificar en Railway Dashboard
# Variables → Environment Variables
# Asegurar que todas las variables obligatorias estén configuradas
```

### **Error: Servicios No Inician**

```bash
# Verificar logs en Railway Dashboard
# Buscar errores específicos en los logs
# Verificar conectividad entre servicios
```

### **Error: Base de Datos No Conecta**

```bash
# Verificar variables de conexión
# Asegurar que PostgreSQL y Redis estén configurados
# Verificar credenciales en Railway Dashboard
```

### **Error: Telegram Bot No Responde**

```bash
# Verificar TELEGRAM_BOT_TOKEN
# Confirmar que el bot esté autorizado
# Verificar TELEGRAM_AUTHORIZED_USERS
```

## 🔄 Actualizaciones y Rollbacks

### **Despliegue Automático**

- Cada push a `main` activará un nuevo despliegue
- Railway mantiene historial de despliegues
- Rollback automático en caso de errores

### **Rollback Manual**

1. **Railway Dashboard → Deployments**
2. **Seleccionar versión anterior**
3. **Click en "Redeploy"**

## 💰 Costos y Límites

### **Plan Gratuito**
- **$5 de crédito mensual**
- **512MB RAM por servicio**
- **1GB de almacenamiento**
- **Ideal para desarrollo y pruebas**

### **Plan Pro ($20/mes)**
- **$20 de crédito mensual**
- **Hasta 8GB RAM por servicio**
- **Ideal para producción**

## 🔐 Seguridad

### **Buenas Prácticas**

1. **Nunca committear variables de entorno**
2. **Usar secretos seguros para API keys**
3. **Configurar CORS apropiadamente**
4. **Monitorear logs regularmente**
5. **Actualizar dependencias regularmente**

### **Variables Sensibles**

- ✅ **En Railway Dashboard:** Variables de entorno
- ❌ **En código:** Nunca hardcodear secretos
- ✅ **En .railwayignore:** Excluir archivos sensibles

## 📞 Soporte

### **Recursos Útiles**

- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [GitHub Issues](https://github.com/railwayapp/railway/issues)

### **Comandos Útiles**

```bash
# Instalar Railway CLI (opcional)
npm install -g @railway/cli

# Login a Railway
railway login

# Ver logs localmente
railway logs

# Abrir proyecto en navegador
railway open
```

## 🎉 ¡Listo!

Tu Crypto AI Bot ahora está desplegado en Railway y funcionando 24/7. El bot responderá automáticamente a mensajes de Telegram y estará disponible a través de la webapp.

### **Próximos Pasos**

1. **Probar el bot** enviando mensajes
2. **Configurar alertas** en Railway Dashboard
3. **Monitorear métricas** de rendimiento
4. **Configurar dominio personalizado** si es necesario

---

*Configuración creada automáticamente para Railway.app* 🚀 