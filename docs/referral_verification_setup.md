# Configuración de Verificación de Referidos

## Descripción
El sistema de verificación de referidos permite que solo usuarios referidos de exchanges específicos puedan usar el bot. Soporta verificación automática en:

- **Bitget**
- **Blofin** 
- **Bitunix**
- **BingX**

## Configuración

### 1. Variables de Entorno

Copia estas variables a tu archivo `.env`:

```bash
# Activar verificación de referidos
REQUIRE_REFERRAL_VERIFICATION=true

# Bitget
BITGET_API_KEY=tu_api_key_bitget
BITGET_API_SECRET=tu_api_secret_bitget
BITGET_PASSPHRASE=tu_passphrase_bitget

# Blofin
BLOFIN_API_KEY=tu_api_key_blofin
BLOFIN_API_SECRET=tu_api_secret_blofin

# Bitunix
BITUNIX_API_KEY=tu_api_key_bitunix
BITUNIX_API_SECRET=tu_api_secret_bitunix

# BingX
BINGX_API_KEY=tu_api_key_bingx
BINGX_API_SECRET=tu_api_secret_bingx
```

### 2. Obtener Credenciales de Exchange

#### Bitget
1. Ir a **API Management** en tu cuenta Bitget
2. Crear nueva API Key con permisos de solo lectura
3. Configurar whitelist de IPs si es necesario
4. Habilitar permisos de broker/referidos

#### Blofin
1. Acceder a **API Settings** en Blofin
2. Generar API Key y Secret
3. Asignar permisos de affiliate/referidos

#### Bitunix
1. Ir a **Partner API** en Bitunix
2. Solicitar acceso a API de partners
3. Configurar API Key con permisos de consulta

#### BingX
1. Crear API Key en **API Management**
2. Habilitar permisos para agent/affiliate

### 3. Configuración por Exchange

No es necesario configurar todos los exchanges. El sistema funcionará con cualquier exchange que tengas configurado.

**Ejemplo - Solo Bitget:**
```bash
REQUIRE_REFERRAL_VERIFICATION=true
BITGET_API_KEY=tu_api_key_real
BITGET_API_SECRET=tu_secret_real
BITGET_PASSPHRASE=tu_passphrase
```

### 4. Desactivar Verificación

Para permitir acceso sin verificación:
```bash
REQUIRE_REFERRAL_VERIFICATION=false
```

## Funcionamiento

### Para Usuarios
1. Al usar `/start`, si no están verificados, ven mensaje de verificación
2. Deben proporcionar su UID del exchange donde son referidos
3. El sistema verifica automáticamente en todos los exchanges configurados
4. Una vez verificados, tienen acceso completo al bot

### Límites de Seguridad
- **3 intentos** por usuario cada hora
- **Cooldown de 1 hora** después de agotar intentos
- **Validación de formato** de UID (5-15 dígitos)
- **Logs detallados** de intentos de verificación

### Para Administradores
- Panel admin muestra estadísticas de verificación
- Logs de intentos exitosos y fallidos
- Posibilidad de verificar usuarios manualmente

## Inicio con Verificación

Usar el script especial que valida la configuración:

```bash
chmod +x start_with_referral_verification.sh
./start_with_referral_verification.sh
```

Este script:
- ✅ Verifica configuración de tokens
- ✅ Valida APIs de exchanges configuradas  
- ✅ Muestra estado de verificación
- ✅ Inicia servicios con verificación habilitada

## Base de Datos

El sistema crea automáticamente `user_verification.db` con:

### Tabla `user_verification`
- Estado de verificación por usuario
- Exchange usado para verificación
- UID verificado
- Intentos y cooldowns

### Tabla `verification_attempts`
- Log completo de intentos
- Timestamps y resultados
- Mensajes de error para debugging

## Troubleshooting

### "No hay exchanges configurados"
- Verifica que al menos un exchange tenga API Key válida
- Revisa que las variables no contengan texto placeholder

### "UID no encontrado"
- Usuario no es referido en los exchanges configurados
- UID incorrecto o formato inválido
- Problemas de conectividad con API del exchange

### "Error técnico"
- Revisar logs del bot para detalles
- Verificar conectividad de red
- Validar credenciales de API

## Seguridad

- 🔒 Las API Keys solo necesitan permisos de **solo lectura**
- 🔐 No se almacenan credenciales de usuarios
- 📝 Todos los intentos quedan registrados
- ⏱️ Rate limiting previene abuso
- 🛡️ Validación de entrada previene inyecciones

## Comandos de Gestión

### Limpiar intentos antiguos
```python
from core.user_verification import user_verification
user_verification.cleanup_old_attempts(days=30)
```

### Verificar usuario manualmente
```python
user_verification.mark_verified(user_id, method="manual")
```

### Ver estadísticas
```python
stats = user_verification.get_verification_stats()
print(stats)
``` 