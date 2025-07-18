#!/usr/bin/env python3
"""
Script de validación de seguridad para el bot de Telegram securizado.
Verifica que todas las medidas de seguridad estén implementadas correctamente.
"""

import os
import sys
import importlib.util
from pathlib import Path

# Añadir src/telegram-bot al path
telegram_bot_path = Path(__file__).parent.parent.parent / "src" / "telegram-bot"
sys.path.insert(0, str(telegram_bot_path))

def test_security_config():
    """Prueba que la configuración de seguridad esté bien implementada."""
    try:
        from core.security_config import (
            TelegramSecurityConfig, 
            TelegramRateLimiter, 
            TelegramInputValidator, 
            TelegramSecureLogger
        )
        
        print("✅ Módulo de configuración de seguridad importado correctamente")
        
        # Verificar configuración
        assert hasattr(TelegramSecurityConfig, 'RATE_LIMIT_PER_MINUTE'), "Falta RATE_LIMIT_PER_MINUTE"
        assert hasattr(TelegramSecurityConfig, 'ALLOWED_SYMBOLS'), "Falta ALLOWED_SYMBOLS"
        assert hasattr(TelegramSecurityConfig, 'DANGEROUS_PATTERNS'), "Falta DANGEROUS_PATTERNS"
        
        print("✅ Configuración de seguridad válida")
        
        # Verificar rate limiter
        rate_limiter = TelegramRateLimiter()
        allowed, info = rate_limiter.is_allowed(12345)
        assert isinstance(allowed, bool), "Rate limiter no retorna boolean"
        assert isinstance(info, dict), "Rate limiter no retorna dict de info"
        
        print("✅ Rate limiter funcionando")
        
        # Verificar validador
        validator = TelegramInputValidator()
        sanitized = validator.sanitize_message("Hola <script>alert('test')</script>")
        assert "<script>" not in sanitized, "Sanitización no funcionó"
        
        print("✅ Validador de entrada funcionando")
        
        # Verificar logger
        logger = TelegramSecureLogger()
        logger.safe_log("Test log", "info", 12345)
        
        print("✅ Logger seguro funcionando")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando módulos de seguridad: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en configuración de seguridad: {e}")
        return False

def test_secure_memory_manager():
    """Prueba que el memory manager securizado esté bien implementado."""
    try:
        from core.secure_memory_manager import SecureMemoryManager
        
        print("✅ SecureMemoryManager importado correctamente")
        
        # Crear instancia de prueba
        memory = SecureMemoryManager("test_secure_memory.db")  # DB temporal para pruebas
        
        # Probar creación de usuario
        success = memory.create_or_update_user(12345, "testuser", "Test", "User")
        assert success, "No se pudo crear usuario"
        
        print("✅ Creación de usuario funcionando")
        
        # Probar añadir mensaje
        success = memory.add_message(12345, "user", "Mensaje de prueba")
        assert success, "No se pudo añadir mensaje"
        
        print("✅ Añadir mensaje funcionando")
        
        # Probar obtener historial
        history = memory.get_conversation_history(12345, limit=5)
        assert isinstance(history, list), "Historial no es una lista"
        
        print("✅ Obtener historial funcionando")
        
        # Limpiar archivo de prueba
        import os
        try:
            os.remove("test_secure_memory.db")
        except FileNotFoundError:
            pass
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando SecureMemoryManager: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en SecureMemoryManager: {e}")
        return False

def test_bot_secure():
    """Prueba que el bot securizado esté bien implementado."""
    try:
        # Verificar que el archivo existe
        bot_file = telegram_bot_path / "core" / "telegram_bot_secure.py"
        if not bot_file.exists():
            print("❌ Archivo telegram_bot_secure.py no encontrado")
            return False
        
        print("✅ Archivo telegram_bot_secure.py encontrado")
        
        # Verificar contenido del archivo
        with open(bot_file, 'r') as f:
            content = f.read()
        
        # Verificar que contiene elementos de seguridad críticos
        security_elements = [
            "require_auth",
            "rate_limit", 
            "validate_input",
            "secure_ai_call",
            "TelegramSecurityConfig",
            "secure_logger",
            "rate_limiter"
        ]
        
        missing_elements = []
        for element in security_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Elementos de seguridad faltantes: {missing_elements}")
            return False
        
        print("✅ Todos los elementos de seguridad presentes")
        
        # Verificar que no contiene vulnerabilidades comunes
        vulnerabilities = [
            "print(TELEGRAM_TOKEN)",
            "logging.info(token",
            "allow_origins=[\"*\"]",
            ".execute(f\"",  # SQL injection
            "eval(",
            "exec("
        ]
        
        found_vulnerabilities = []
        for vuln in vulnerabilities:
            if vuln in content:
                found_vulnerabilities.append(vuln)
        
        if found_vulnerabilities:
            print(f"❌ Vulnerabilidades encontradas: {found_vulnerabilities}")
            return False
        
        print("✅ No se encontraron vulnerabilidades obvias")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando bot securizado: {e}")
        return False

def test_file_structure():
    """Verifica que la estructura de archivos sea correcta."""
    try:
        expected_files = [
            "core/security_config.py",
            "core/secure_memory_manager.py", 
            "core/telegram_bot_secure.py",
            "config.env.example"
        ]
        
        missing_files = []
        for file_path in expected_files:
            full_path = telegram_bot_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Archivos faltantes: {missing_files}")
            return False
        
        print("✅ Estructura de archivos correcta")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return False

def main():
    """Función principal de validación."""
    print("🔒 VALIDACIÓN DE SEGURIDAD - BOT DE TELEGRAM")
    print("=" * 50)
    
    tests = [
        ("Estructura de archivos", test_file_structure),
        ("Configuración de seguridad", test_security_config),
        ("Memory manager securizado", test_secure_memory_manager),
        ("Bot securizado", test_bot_secure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Probando: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASÓ")
                passed += 1
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡VALIDACIÓN EXITOSA! El bot está securizado correctamente.")
        return 0
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 