#!/usr/bin/env python3
"""
Script de validación de seguridad del módulo Backend.
Versión corregida que funciona desde el directorio raíz del proyecto.
"""

import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_paths():
    """Configurar paths para importar módulos del backend."""
    # Obtener directorio raíz del proyecto
    project_root = Path(__file__).parent.parent.parent
    backend_src = project_root / "src" / "backend"
    
    # Agregar al path de Python
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))
    
    # Cambiar al directorio del backend para imports relativos
    os.chdir(str(backend_src))
    
    return project_root, backend_src

def validate_imports():
    """Validar que todos los módulos de seguridad se importen correctamente."""
    logger.info("🔍 Validando importaciones de seguridad...")
    errors = []
    success_count = 0
    
    import_tests = [
        ("core.config.security_config", "SecurityConfig"),
        ("core.middleware.rate_limiter", "RateLimiter"),
        ("core.validation.input_validator", "InputValidator"),
        ("core.security.auth", "get_current_user"),
        ("core.security.middleware", "SecurityMiddleware")
    ]
    
    for module_name, class_name in import_tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            logger.info(f"✅ SUCCESS - Import {module_name}: {class_name}")
            success_count += 1
        except Exception as e:
            error_msg = f"Import {module_name}: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
    
    return success_count, len(import_tests), errors

def validate_security_config():
    """Validar configuración de seguridad."""
    logger.info("🔍 Validando configuración de seguridad...")
    errors = []
    success_count = 0
    
    try:
        from core.config.security_config import SecurityConfig
        
        # Validar configuraciones críticas
        config_tests = [
            ("RATE_LIMIT_PER_MINUTE", SecurityConfig.RATE_LIMIT_PER_MINUTE, int, 1, 1000),
            ("RATE_LIMIT_PER_HOUR", SecurityConfig.RATE_LIMIT_PER_HOUR, int, 1, 100000),
            ("RATE_LIMIT_PER_DAY", SecurityConfig.RATE_LIMIT_PER_DAY, int, 1, 1000000),
            ("ALLOWED_ORIGINS", SecurityConfig.ALLOWED_ORIGINS, list, 1, None),
            ("ALLOWED_HOSTS", SecurityConfig.ALLOWED_HOSTS, list, 1, None),
            ("API_SECRET_KEY", SecurityConfig.API_SECRET_KEY, str, 16, None),
            ("MAX_PAYLOAD_SIZE", SecurityConfig.MAX_PAYLOAD_SIZE, int, 1024, None),
            ("ALLOWED_SYMBOLS", SecurityConfig.ALLOWED_SYMBOLS, set, 10, None)
        ]
        
        for name, value, expected_type, min_val, max_val in config_tests:
            try:
                # Verificar tipo
                if not isinstance(value, expected_type):
                    raise ValueError(f"Tipo incorrecto: {type(value)} != {expected_type}")
                
                # Verificar rangos
                if expected_type in [int, str, list, set]:
                    length = len(value) if hasattr(value, '__len__') else value
                    if min_val and length < min_val:
                        raise ValueError(f"Valor muy pequeño: {length} < {min_val}")
                    if max_val and length > max_val:
                        raise ValueError(f"Valor muy grande: {length} > {max_val}")
                
                logger.info(f"✅ SUCCESS - Config {name}: OK")
                success_count += 1
                
            except Exception as e:
                error_msg = f"Config {name}: {str(e)}"
                logger.info(f"❌ FAIL - {error_msg}")
                errors.append(error_msg)
        
    except Exception as e:
        error_msg = f"Configuración de seguridad: {str(e)}"
        logger.info(f"❌ FAIL - {error_msg}")
        errors.append(error_msg)
    
    return success_count, len(config_tests) if 'config_tests' in locals() else 0, errors

def validate_rate_limiter():
    """Validar funcionamiento del rate limiter."""
    logger.info("🔍 Validando rate limiter...")
    errors = []
    success_count = 0
    
    try:
        from core.middleware.rate_limiter import RateLimiter
        
        # Crear instancia
        rate_limiter = RateLimiter()
        test_ip = "192.168.1.100"
        
        # Test 1: Permitir request inicial
        try:
            allowed, info = rate_limiter.is_allowed(test_ip)
            if not allowed:
                raise ValueError("Primera request debería ser permitida")
            logger.info("✅ SUCCESS - Rate limiter permite request inicial")
            success_count += 1
        except Exception as e:
            error_msg = f"Rate limiter request inicial: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 2: Registrar request
        try:
            rate_limiter.record_request(test_ip)
            logger.info("✅ SUCCESS - Rate limiter registra request")
            success_count += 1
        except Exception as e:
            error_msg = f"Rate limiter registro: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 3: Obtener estadísticas
        try:
            stats = rate_limiter.get_stats(test_ip)
            if not isinstance(stats, dict):
                raise ValueError("Estadísticas deben ser un diccionario")
            logger.info("✅ SUCCESS - Rate limiter estadísticas")
            success_count += 1
        except Exception as e:
            error_msg = f"Rate limiter estadísticas: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
    except Exception as e:
        error_msg = f"Rate limiter: {str(e)}"
        logger.info(f"❌ FAIL - {error_msg}")
        errors.append(error_msg)
    
    return success_count, 3, errors

def validate_input_validator():
    """Validar sistema de validación de entrada."""
    logger.info("🔍 Validando sistema de validación...")
    errors = []
    success_count = 0
    
    try:
        from core.validation.input_validator import InputValidator, InputSanitizer
        
        validator = InputValidator()
        sanitizer = InputSanitizer()
        
        # Test 1: Validar símbolo válido
        try:
            result = validator.validate_symbol("BTC")
            if result != "BTC":
                raise ValueError(f"Símbolo válido rechazado: {result}")
            logger.info("✅ SUCCESS - Validador acepta símbolo válido")
            success_count += 1
        except Exception as e:
            error_msg = f"Validador símbolo válido: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 2: Rechazar símbolo inválido
        try:
            try:
                validator.validate_symbol("INVALID_SYMBOL_123")
                raise ValueError("Símbolo inválido fue aceptado")
            except ValueError as ve:
                if "no permitido" not in str(ve):
                    raise ValueError("Error incorrecto para símbolo inválido")
            logger.info("✅ SUCCESS - Validador rechaza símbolo inválido")
            success_count += 1
        except Exception as e:
            error_msg = f"Validador símbolo inválido: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 3: Sanitizar entrada
        try:
            dangerous_input = "<script>alert('xss')</script>BTC"
            clean_input = sanitizer.sanitize_string(dangerous_input)
            if "<script>" in clean_input:
                raise ValueError("Sanitización falló - script tag presente")
            logger.info("✅ SUCCESS - Sanitizador elimina contenido peligroso")
            success_count += 1
        except Exception as e:
            error_msg = f"Sanitizador: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 4: Validar timeframe
        try:
            result = validator.validate_timeframe("1h")
            if result != "1h":
                raise ValueError(f"Timeframe válido rechazado: {result}")
            logger.info("✅ SUCCESS - Validador acepta timeframe válido")
            success_count += 1
        except Exception as e:
            error_msg = f"Validador timeframe: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
    except Exception as e:
        error_msg = f"Sistema de validación: {str(e)}"
        logger.info(f"❌ FAIL - {error_msg}")
        errors.append(error_msg)
    
    return success_count, 4, errors

def validate_security_headers():
    """Validar headers de seguridad."""
    logger.info("🔍 Validando headers de seguridad...")
    errors = []
    success_count = 0
    
    try:
        from core.config.security_config import SecurityHeaders
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        for header_name in required_headers:
            try:
                header_value = getattr(SecurityHeaders, header_name.replace("-", "_").upper())
                if not header_value:
                    raise ValueError(f"Header {header_name} está vacío")
                logger.info(f"✅ SUCCESS - Header {header_name}: {header_value[:50]}...")
                success_count += 1
            except Exception as e:
                error_msg = f"Header {header_name}: {str(e)}"
                logger.info(f"❌ FAIL - {error_msg}")
                errors.append(error_msg)
        
    except Exception as e:
        error_msg = f"Headers de seguridad: {str(e)}"
        logger.info(f"❌ FAIL - {error_msg}")
        errors.append(error_msg)
    
    return success_count, len(required_headers) if 'required_headers' in locals() else 0, errors

def validate_authentication():
    """Validar sistema de autenticación."""
    logger.info("🔍 Validando sistema de autenticación...")
    errors = []
    success_count = 0
    
    try:
        from core.security.auth import TokenValidator, get_current_user, require_auth
        
        # Test 1: Crear validador de tokens
        try:
            validator = TokenValidator()
            logger.info("✅ SUCCESS - TokenValidator creado")
            success_count += 1
        except Exception as e:
            error_msg = f"TokenValidator creación: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 2: Verificar funciones de autenticación
        try:
            if not callable(get_current_user):
                raise ValueError("get_current_user no es callable")
            if not callable(require_auth):
                raise ValueError("require_auth no es callable")
            logger.info("✅ SUCCESS - Funciones de auth disponibles")
            success_count += 1
        except Exception as e:
            error_msg = f"Funciones de auth: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
        # Test 3: Validar token inválido
        try:
            if 'validator' in locals():
                result = validator.validate_token("invalid_token_123")
                if result:
                    raise ValueError("Token inválido fue aceptado")
                logger.info("✅ SUCCESS - Validador rechaza token inválido")
                success_count += 1
        except Exception as e:
            error_msg = f"Validación token inválido: {str(e)}"
            logger.info(f"❌ FAIL - {error_msg}")
            errors.append(error_msg)
        
    except Exception as e:
        error_msg = f"Sistema de autenticación: {str(e)}"
        logger.info(f"❌ FAIL - {error_msg}")
        errors.append(error_msg)
    
    return success_count, 3, errors

def main():
    """Función principal de validación."""
    logger.info("🔒 INICIANDO VALIDACIÓN DE SEGURIDAD DEL BACKEND")
    logger.info("=" * 60)
    
    # Configurar paths
    try:
        project_root, backend_src = setup_paths()
        logger.info(f"📁 Directorio del proyecto: {project_root}")
        logger.info(f"📁 Directorio del backend: {backend_src}")
    except Exception as e:
        logger.error(f"❌ Error configurando paths: {e}")
        return 1
    
    # Lista de validaciones
    validations = [
        ("Importaciones", validate_imports),
        ("Configuración", validate_security_config), 
        ("Rate Limiter", validate_rate_limiter),
        ("Validación de entrada", validate_input_validator),
        ("Headers de seguridad", validate_security_headers),
        ("Autenticación", validate_authentication)
    ]
    
    total_success = 0
    total_tests = 0
    all_errors = []
    
    # Ejecutar validaciones
    for validation_name, validation_func in validations:
        logger.info(f"\n📋 Ejecutando: {validation_name}")
        try:
            success, tests, errors = validation_func()
            total_success += success
            total_tests += tests
            all_errors.extend(errors)
            
            if errors:
                logger.info(f"⚠️  {validation_name}: {success}/{tests} pruebas pasadas")
            else:
                logger.info(f"✅ {validation_name}: {success}/{tests} pruebas pasadas")
                
        except Exception as e:
            logger.error(f"❌ Error en {validation_name}: {e}")
            all_errors.append(f"{validation_name}: {str(e)}")
    
    # Resumen final
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMEN DE VALIDACIÓN DE SEGURIDAD")
    logger.info("=" * 60)
    
    success_percentage = (total_success / total_tests * 100) if total_tests > 0 else 0
    logger.info(f"✅ Pruebas pasadas: {total_success}/{total_tests} ({success_percentage:.1f}%)")
    
    if all_errors:
        logger.info(f"❌ Errores: {len(all_errors)}")
        for error in all_errors:
            logger.error(f"  - {error}")
    
    # Resultado final
    if total_success == total_tests and not all_errors:
        logger.info("\n🎉 ¡VALIDACIÓN EXITOSA! Todos los componentes funcionan correctamente.")
        logger.info("🔒 El módulo Backend está completamente securizado.")
        return 0
    else:
        logger.info(f"\n❌ VALIDACIÓN FALLIDA. Hay problemas significativos de seguridad.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 