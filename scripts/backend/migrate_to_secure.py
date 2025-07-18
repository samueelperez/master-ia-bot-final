#!/usr/bin/env python3
"""
Script de migración para el módulo Backend.
Reemplaza main.py inseguro con main_secure.py y configura el entorno.
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
    logger.info("🔒 MIGRACIÓN DEL MÓDULO BACKEND A VERSIÓN SECURIZADA")
    logger.info("=" * 60)
    
    # Obtener directorio del proyecto
    project_root = Path(__file__).parent.parent.parent
    backend_src = project_root / "src" / "backend"
    
    logger.info(f"📁 Directorio del proyecto: {project_root}")
    logger.info(f"📁 Directorio del backend: {backend_src}")
    
    steps_completed = 0
    total_steps = 4
    
    try:
        # Paso 1: Crear backup del archivo original
        logger.info("\n📋 Paso 1/4: Creando backup del archivo original")
        
        original_file = backend_src / "main.py"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backend_src / f"main_backup_{timestamp}.py"
        
        if original_file.exists():
            shutil.copy2(original_file, backup_file)
            logger.info(f"✅ Backup creado: {backup_file.name}")
        else:
            logger.info("ℹ️  Archivo original no existe, saltando backup")
        
        steps_completed += 1
        
        # Paso 2: Reemplazar con versión securizada
        logger.info("\n📋 Paso 2/4: Reemplazando con versión securizada")
        
        secure_file = backend_src / "main_secure.py"
        if secure_file.exists():
            shutil.copy2(secure_file, original_file)
            logger.info(f"✅ Archivo securizado copiado a main.py")
        else:
            raise FileNotFoundError(f"Archivo securizado no encontrado: {secure_file}")
        
        steps_completed += 1
        
        # Paso 3: Crear archivo de configuración de ejemplo
        logger.info("\n📋 Paso 3/4: Creando archivo de configuración")
        
        config_content = """# Configuración de Seguridad del Backend
# Copiar este archivo a .env y configurar los valores apropiados

# OBLIGATORIO: Clave secreta para autenticación (mínimo 32 caracteres)
BACKEND_API_SECRET_KEY=your-very-secure-secret-key-here-change-this-in-production

# Rate Limiting (opcional - defaults seguros)
BACKEND_RATE_LIMIT_PER_MINUTE=60
BACKEND_RATE_LIMIT_PER_HOUR=1000
BACKEND_RATE_LIMIT_PER_DAY=10000
BACKEND_RATE_LIMIT_BURST=10

# CORS y Hosts (opcional - defaults para desarrollo)
BACKEND_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
BACKEND_ALLOWED_HOSTS=localhost,127.0.0.1

# Timeouts (opcional - defaults seguros)
BACKEND_HTTP_TIMEOUT=30
BACKEND_DB_TIMEOUT=10
BACKEND_CCXT_TIMEOUT=15

# Límites de datos (opcional - defaults seguros)
BACKEND_MAX_LIMIT_OHLCV=1000
BACKEND_MAX_INDICATORS_PER_REQUEST=50
BACKEND_MAX_PAYLOAD_SIZE=1048576

# Exchange (opcional - defaults seguros)
BACKEND_DEFAULT_EXCHANGE=binance
BACKEND_EXCHANGE_SANDBOX=true

# Documentación (opcional - deshabilitar en producción)
ENABLE_DOCS=true
"""
        
        config_file = backend_src / "config.env.example"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"✅ Configuración creada: {config_file.name}")
        steps_completed += 1
        
        # Paso 4: Crear Dockerfile securizado
        logger.info("\n📋 Paso 4/4: Creando Dockerfile securizado")
        
        dockerfile_content = """# Dockerfile para Backend Securizado
FROM python:3.11-slim

# Crear usuario no-root
RUN useradd --create-home --shell /bin/bash backend

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio de logs
RUN mkdir -p logs && chown backend:backend logs

# Cambiar a usuario no-root
USER backend

# Exponer puerto
EXPOSE 8001

# Variables de entorno por defecto
ENV BACKEND_API_SECRET_KEY=""
ENV BACKEND_RATE_LIMIT_PER_MINUTE=60
ENV BACKEND_ALLOWED_ORIGINS="http://localhost:3000"
ENV ENABLE_DOCS=false

# Comando de inicio
CMD ["python", "main.py"]
"""
        
        dockerfile_secure = backend_src / "Dockerfile.secure"
        with open(dockerfile_secure, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        logger.info(f"✅ Dockerfile securizado creado: {dockerfile_secure.name}")
        steps_completed += 1
        
        # Resumen final
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DE MIGRACIÓN")
        logger.info("=" * 60)
        logger.info(f"✅ Pasos completados: {steps_completed}/{total_steps}")
        
        if steps_completed == total_steps:
            logger.info("\n🎉 ¡MIGRACIÓN EXITOSA!")
            logger.info("🔒 El módulo Backend ha sido securizado completamente")
            logger.info("\n📋 PRÓXIMOS PASOS:")
            logger.info("1. Configurar variables de entorno usando config.env.example")
            logger.info("2. Ejecutar: python main.py")
            logger.info("3. Validar: python scripts/backend/validate_backend_security_fixed.py")
            logger.info("\n⚠️  IMPORTANTE:")
            logger.info("• Cambiar BACKEND_API_SECRET_KEY en producción")
            logger.info("• Configurar BACKEND_ALLOWED_ORIGINS para tu dominio")
            logger.info("• Deshabilitar documentación en producción (ENABLE_DOCS=false)")
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