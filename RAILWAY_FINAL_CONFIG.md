# 🚀 Configuración Final Railway - Crypto AI Bot

## ✅ Variables Actualizadas con Valores Reales

### **🔐 API Keys Críticas (OBLIGATORIAS)**

```bash
# OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# Secret Keys para Autenticación
API_SECRET_KEY=your-secure-secret-key-32-chars-min
BACKEND_API_SECRET_KEY=your-backend-secret-key-32-chars-min
DATA_SERVICE_SECRET_KEY=your-data-service-secret-key-32-chars-min
```

### **📰 API Keys Externas (Configuradas)**

```bash
# News API
NEWS_API_KEY=your-news-api-key

# Twitter API
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
TWITTER_BEARER_TOKEN=your-twitter-bearer-token

# HuggingFace
HF_TOKEN=your-huggingface-token
HUGGINGFACE_API_KEY=your-huggingface-api-key

# Supabase (para Webapp)
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

### **🏦 APIs de Exchanges (Configuradas)**

```bash
# Bitget
BITGET_API_KEY=your-bitget-api-key
BITGET_API_SECRET=your-bitget-api-secret
BITGET_PASSPHRASE=your-bitget-passphrase

# Blofin
BLOFIN_API_KEY=your-blofin-api-key
BLOFIN_API_SECRET=your-blofin-api-secret

# Bitunix
BITUNIX_API_KEY=your-bitunix-api-key
BITUNIX_API_SECRET=your-bitunix-api-secret

# BingX
BINGX_API_KEY=your-bingx-api-key
BINGX_API_SECRET=your-bingx-api-secret
```

### **👥 Configuración de Usuarios**

```bash
# IDs de usuarios autorizados (CONFIGURAR)
TELEGRAM_AUTHORIZED_USERS=your_telegram_user_id
TELEGRAM_ADMIN_USERS=your_telegram_user_id

# Configuración de verificación de referidos
REQUIRE_REFERRAL_VERIFICATION=false
VERIFICATION_DB=user_verification.db
MEMORY_DB=telegram_bot_memory_secure.db
```

## 🚀 Pasos de Despliegue Inmediato

### **1. Subir Cambios a GitHub**
```bash
git add .
git commit -m "🚀 Configuración Railway actualizada con variables reales"
git push origin main
```

### **2. Crear Proyecto en Railway**
1. Ir a [Railway.app](https://railway.app)
2. Conectar repositorio de GitHub
3. Seleccionar `crypto-ai-bot`

### **3. Configurar Variables en Railway Dashboard**

**IMPORTANTE:** Copiar TODAS las variables de arriba al Railway Dashboard → Variables → Environment Variables

### **4. Configurar Base de Datos**
1. Railway Dashboard → New Service → Database
2. Seleccionar PostgreSQL 15
3. Seleccionar Redis 7

### **5. Configurar ID de Telegram**
1. Obtener tu ID enviando mensaje a @userinfobot en Telegram
2. Configurar `TELEGRAM_AUTHORIZED_USERS` y `TELEGRAM_ADMIN_USERS` en Railway Dashboard

## 📊 Servicios que se Desplegarán

- ✅ **Backend API** (puerto 8000)
- ✅ **AI Module** (puerto 9004) 
- ✅ **Data Service** (puerto 9005)
- ✅ **Telegram Bot** (ejecutándose)
- ✅ **Webapp** (puerto 3000)
- ✅ **PostgreSQL** (base de datos)
- ✅ **Redis** (caché y sesiones)

## 🔧 URLs de Verificación

Después del despliegue, verificar:

```bash
# Health checks
curl https://your-app.railway.app:8000/health
curl https://your-app.railway.app:9004/health
curl https://your-app.railway.app:9005/health

# Webapp
https://your-app.railway.app:3000
```

## ⚠️ Notas Importantes

1. **Configurar tu ID de Telegram** en Railway Dashboard
2. **Configurar `BITGET_PASSPHRASE`** si usas Bitget
3. **Verificar que todas las variables estén en Railway Dashboard**
4. **Las bases de datos se configuran automáticamente**

## 🎯 Estado Actual

- ✅ **Variables reales configuradas**
- ✅ **APIs externas incluidas**
- ✅ **Exchanges configurados**
- ✅ **Supabase configurado**
- ✅ **Docker Compose optimizado**
- ✅ **Scripts de inicio listos**

**¡Listo para desplegar en Railway!** 🚀 