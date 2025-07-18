#!/usr/bin/env python3
"""
Script de migración para actualizar el módulo AI a la versión securizada.
Reemplaza el archivo inseguro con la nueva implementación.
"""

import os
import sys
import shutil
import time
from pathlib import Path

def create_backup():
    """Crear backup del archivo original."""
    original_file = "src/ai-module/core/llm_inference.py"
    backup_file = f"src/ai-module/core/llm_inference_backup_{int(time.time())}.py"
    
    if os.path.exists(original_file):
        shutil.copy2(original_file, backup_file)
        print(f"✅ Backup creado: {backup_file}")
        return backup_file
    return None

def migrate_to_secure():
    """Migrar a la versión securizada."""
    original_file = "src/ai-module/core/llm_inference.py"
    secure_file = "src/ai-module/core/llm_inference_secure.py"
    
    if not os.path.exists(secure_file):
        print(f"❌ Archivo securizado no encontrado: {secure_file}")
        return False
    
    # Crear backup
    backup = create_backup()
    
    try:
        # Reemplazar archivo original con versión segura
        shutil.copy2(secure_file, original_file)
        print(f"✅ Archivo migrado exitosamente")
        
        # Opcional: remover archivo temporal securizado
        # os.remove(secure_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante migración: {e}")
        
        # Restaurar backup si existe
        if backup and os.path.exists(backup):
            shutil.copy2(backup, original_file)
            print(f"✅ Backup restaurado")
        
        return False

def create_env_example():
    """Crear archivo .env.example para configuración."""
    env_content = """# ============================================
# CONFIGURACIÓN DEL MÓDULO AI SECURIZADO
# ============================================

# API Keys (OBLIGATORIAS)
OPENAI_API_KEY=your-openai-api-key-here
API_SECRET_KEY=your-secure-secret-key-here

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Timeouts (en segundos)
HTTP_TIMEOUT=15
OPENAI_TIMEOUT=30

# CORS - Orígenes permitidos (separados por comas)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,https://yourdomain.com

# Hosts permitidos (separados por comas)
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Backend URL (si está disponible)
BACKEND_URL=http://localhost:8000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/llm_inference.log

# Configuración OpenAI
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.6

# Configuración de servicio
SERVICE_PORT=8001
SERVICE_HOST=0.0.0.0

# Entorno (development, staging, production)
ENVIRONMENT=development
"""
    
    env_file = "ai-module/config.env.example"
    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Archivo de configuración creado: {env_file}")
    return True

def update_dockerfile():
    """Actualizar Dockerfile para usar versión securizada."""
    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio de logs
RUN mkdir -p /app/logs

# Copiar código fuente
COPY src/ai-module/ .

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# Exponer puerto
EXPOSE 8001

# Comando de inicio
CMD ["python", "core/llm_inference.py"]
"""
    
    dockerfile_path = "ai-module/Dockerfile.secure"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    print(f"✅ Dockerfile securizado creado: {dockerfile_path}")
    return True

def create_validation_script():
    """Crear script de validación."""
    validation_content = """#!/usr/bin/env python3
'''
Script de validación para el módulo AI securizado.
'''

import sys
import os
sys.path.append('src/ai-module')

def test_imports():
    '''Probar importaciones críticas.'''
    try:
        from core.llm_inference_secure import SecurityConfig, InputValidator, RateLimiter
        print("✅ Importaciones exitosas")
        return True
    except ImportError as e:
        print(f"❌ Error en importaciones: {e}")
        return False

def test_security_config():
    '''Probar configuración de seguridad.'''
    try:
        os.environ['OPENAI_API_KEY'] = 'test-key'
        os.environ['API_SECRET_KEY'] = 'test-secret'
        
        from core.llm_inference_secure import SecurityConfig
        SecurityConfig.validate_config()
        print("✅ Configuración de seguridad válida")
        return True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_input_validation():
    '''Probar validación de entrada.'''
    try:
        from core.llm_inference_secure import InputValidator
        
        # Test símbolo válido
        symbol = InputValidator.validate_symbol('BTC')
        assert symbol == 'BTC'
        
        # Test timeframe válido
        timeframe = InputValidator.validate_timeframe('1h')
        assert timeframe == '1h'
        
        print("✅ Validación de entrada funcionando")
        return True
    except Exception as e:
        print(f"❌ Error en validación: {e}")
        return False

def main():
    '''Función principal.'''
    print("🔍 Validando módulo AI securizado...")
    
    tests = [
        test_imports,
        test_security_config,
        test_input_validation
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Resultados: {passed}/{len(tests)} tests pasaron")
    
    if passed == len(tests):
        print("🎉 ¡Módulo AI securizado funcionando correctamente!")
        return 0
    else:
        print("⚠️ Algunos tests fallaron. Revisar configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
    
    validation_path = "scripts/ai-module/validate_secure.py"
    os.makedirs(os.path.dirname(validation_path), exist_ok=True)
    
    with open(validation_path, 'w') as f:
        f.write(validation_content)
    
    os.chmod(validation_path, 0o755)  # Hacer ejecutable
    print(f"✅ Script de validación creado: {validation_path}")
    return True

def main():
    """Función principal de migración."""
    print("🔒 MIGRACIÓN DEL MÓDULO AI A VERSIÓN SECURIZADA")
    print("=" * 50)
    
    steps = [
        ("Migrar archivo principal", migrate_to_secure),
        ("Crear configuración de ejemplo", create_env_example),
        ("Actualizar Dockerfile", update_dockerfile),
        ("Crear script de validación", create_validation_script)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n🔄 {step_name}...")
        try:
            if step_func():
                success_count += 1
                print(f"✅ {step_name} - COMPLETADO")
            else:
                print(f"❌ {step_name} - FALLÓ")
        except Exception as e:
            print(f"❌ {step_name} - ERROR: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"📊 RESUMEN: {success_count}/{len(steps)} pasos completados")
    
    if success_count == len(steps):
        print("🎉 ¡MIGRACIÓN EXITOSA!")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Configurar variables de entorno en ai-module/config.env")
        print("2. Ejecutar: python scripts/ai-module/validate_secure.py")
        print("3. Iniciar servicio: python src/ai-module/core/llm_inference.py")
        return True
    else:
        print("⚠️ MIGRACIÓN INCOMPLETA - Revisar errores arriba")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 