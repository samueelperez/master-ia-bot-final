#!/usr/bin/env python3
"""
Script para validar la seguridad del módulo Backend.
Verifica autenticación, rate limiting, validación y headers de seguridad.
"""

import sys
import os
import logging
import time
import requests
import json
from typing import Dict, List, Tuple
import importlib.util

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar el directorio del backend al path
BACKEND_PATH = os.path.join(os.getcwd(), "../../src/backend")
sys.path.insert(0, BACKEND_PATH)

class BackendSecurityValidator:
    """Validador de seguridad del backend."""
    
    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []
        
        # URL base del backend (ajustar según configuración)
        self.base_url = "http://localhost:8001"
        
        # Token de prueba (debería obtenerse de variables de entorno en producción)
        self.test_token = os.getenv("BACKEND_API_SECRET_KEY", "test-backend-token")
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Registrar resultado de validación."""
        status = "✅ PASS" if passed else "❌ FAIL"
        full_message = f"{status} - {test_name}"
        if message:
            full_message += f": {message}"
        
        logger.info(full_message)
        self.validation_results.append((test_name, passed, message))
        
        if not passed:
            self.errors.append(f"{test_name}: {message}")
    
    def log_warning(self, test_name: str, message: str):
        """Registrar advertencia."""
        warning_msg = f"⚠️ WARNING - {test_name}: {message}"
        logger.warning(warning_msg)
        self.warnings.append(f"{test_name}: {message}")
    
    def validate_imports(self) -> bool:
        """Validar que las importaciones de seguridad funcionen."""
        logger.info("🔍 Validando importaciones de seguridad...")
        
        import_tests = [
            ("core.config.security_config", "SecurityConfig"),
            ("core.middleware.rate_limiter", "RateLimiter"),
            ("core.validation.input_validator", "InputValidator"),
            ("core.security.auth", "get_current_user"),
            ("core.security.middleware", "SecurityMiddleware")
        ]
        
        all_passed = True
        
        for module_name, class_name in import_tests:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    self.log_result(f"Import {module_name}.{class_name}", True)
                else:
                    self.log_result(f"Import {module_name}.{class_name}", False, f"Clase {class_name} no encontrada")
                    all_passed = False
            except ImportError as e:
                self.log_result(f"Import {module_name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def validate_configuration(self) -> bool:
        """Validar configuración de seguridad."""
        logger.info("🔍 Validando configuración de seguridad...")
        
        try:
            from core.config.security_config import SecurityConfig, ValidationConfig
            
            # Verificar configuración de SecurityConfig
            config_tests = [
                (SecurityConfig.RATE_LIMIT_PER_MINUTE > 0, "RATE_LIMIT_PER_MINUTE válido"),
                (SecurityConfig.RATE_LIMIT_PER_HOUR > 0, "RATE_LIMIT_PER_HOUR válido"),
                (len(SecurityConfig.ALLOWED_ORIGINS) > 0, "ALLOWED_ORIGINS configurado"),
                (len(SecurityConfig.API_SECRET_KEY) >= 32, "API_SECRET_KEY suficientemente segura"),
                (SecurityConfig.MAX_PAYLOAD_SIZE > 0, "MAX_PAYLOAD_SIZE configurado")
            ]
            
            all_passed = True
            for test_condition, test_name in config_tests:
                if test_condition:
                    self.log_result(test_name, True)
                else:
                    self.log_result(test_name, False)
                    all_passed = False
            
            # Verificar ValidationConfig
            validation_tests = [
                (len(ValidationConfig.ALLOWED_SYMBOLS) > 0, "ALLOWED_SYMBOLS configurado"),
                (len(ValidationConfig.ALLOWED_TIMEFRAMES) > 0, "ALLOWED_TIMEFRAMES configurado"),
                (len(ValidationConfig.DANGEROUS_PATTERNS) > 0, "DANGEROUS_PATTERNS configurado")
            ]
            
            for test_condition, test_name in validation_tests:
                if test_condition:
                    self.log_result(test_name, True)
                else:
                    self.log_result(test_name, False)
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_result("Configuración de seguridad", False, str(e))
            return False
    
    def validate_rate_limiter(self) -> bool:
        """Validar rate limiter."""
        logger.info("🔍 Validando rate limiter...")
        
        try:
            from core.middleware.rate_limiter import RateLimiter
            
            # Crear instancia del rate limiter
            rate_limiter = RateLimiter(
                requests_per_minute=5,  # Límite bajo para testing
                requests_per_hour=100,
                burst_limit=2
            )
            
            test_client_id = "test_client_001"
            
            # Test 1: Permitir requests normales
            allowed, info = rate_limiter.is_allowed(test_client_id)
            if allowed:
                rate_limiter.record_request(test_client_id)
                self.log_result("Rate limiter permite requests", True)
            else:
                self.log_result("Rate limiter permite requests", False)
                return False
            
            # Test 2: Verificar límite de ráfaga
            for i in range(3):  # Exceder límite de ráfaga (2)
                allowed, info = rate_limiter.is_allowed(test_client_id)
                if allowed:
                    rate_limiter.record_request(test_client_id)
            
            # El siguiente debería ser bloqueado
            allowed, info = rate_limiter.is_allowed(test_client_id)
            if not allowed:
                self.log_result("Rate limiter bloquea ráfagas", True)
            else:
                self.log_result("Rate limiter bloquea ráfagas", False)
            
            # Test 3: Estadísticas
            stats = rate_limiter.get_client_stats(test_client_id)
            if isinstance(stats, dict) and 'total_requests' in stats:
                self.log_result("Rate limiter estadísticas", True)
            else:
                self.log_result("Rate limiter estadísticas", False)
            
            return True
            
        except Exception as e:
            self.log_result("Rate limiter", False, str(e))
            return False
    
    def validate_input_validator(self) -> bool:
        """Validar sistema de validación de entrada."""
        logger.info("🔍 Validando sistema de validación...")
        
        try:
            from core.validation.input_validator import InputValidator
            
            validator = InputValidator()
            
            # Test 1: Validar símbolo válido
            try:
                result = validator.validate_symbol("BTC")
                if result == "BTC":
                    self.log_result("Validador símbolo válido", True)
                else:
                    self.log_result("Validador símbolo válido", False)
            except Exception:
                self.log_result("Validador símbolo válido", False)
            
            # Test 2: Rechazar símbolo inválido
            try:
                validator.validate_symbol("INVALID_SYMBOL")
                self.log_result("Validador rechaza símbolo inválido", False, "Debería haber fallado")
            except ValueError:
                self.log_result("Validador rechaza símbolo inválido", True)
            except Exception as e:
                self.log_result("Validador rechaza símbolo inválido", False, str(e))
            
            # Test 3: Validar timeframe
            try:
                result = validator.validate_timeframe("1h")
                if result == "1h":
                    self.log_result("Validador timeframe", True)
                else:
                    self.log_result("Validador timeframe", False)
            except Exception:
                self.log_result("Validador timeframe", False)
            
            # Test 4: Detectar patrones peligrosos
            try:
                validator.sanitizer.sanitize_string("<script>alert('xss')</script>")
                self.log_result("Validador detecta XSS", False, "Debería haber detectado XSS")
            except ValueError:
                self.log_result("Validador detecta XSS", True)
            except Exception as e:
                self.log_result("Validador detecta XSS", False, str(e))
            
            return True
            
        except Exception as e:
            self.log_result("Sistema de validación", False, str(e))
            return False
    
    def validate_security_headers(self) -> bool:
        """Validar headers de seguridad."""
        logger.info("🔍 Validando headers de seguridad...")
        
        try:
            from core.config.security_config import SecurityHeaders
            
            headers = SecurityHeaders.get_security_headers()
            
            # Verificar headers críticos
            critical_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy"
            ]
            
            all_passed = True
            for header in critical_headers:
                if header in headers:
                    self.log_result(f"Header {header}", True)
                else:
                    self.log_result(f"Header {header}", False, "Header faltante")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_result("Headers de seguridad", False, str(e))
            return False
    
    def validate_authentication(self) -> bool:
        """Validar sistema de autenticación."""
        logger.info("🔍 Validando sistema de autenticación...")
        
        try:
            from core.security.auth import token_validator, hash_token
            from core.config.security_config import SecurityConfig
            
            # Test 1: Validar token correcto
            valid_token = SecurityConfig.API_SECRET_KEY
            if token_validator.validate_token(valid_token):
                self.log_result("Autenticación token válido", True)
            else:
                self.log_result("Autenticación token válido", False)
            
            # Test 2: Rechazar token inválido
            invalid_token = "invalid_token_12345"
            if not token_validator.validate_token(invalid_token):
                self.log_result("Autenticación rechaza token inválido", True)
            else:
                self.log_result("Autenticación rechaza token inválido", False)
            
            # Test 3: Hash de tokens
            test_token = "test_token"
            hash1 = hash_token(test_token)
            hash2 = hash_token(test_token)
            if hash1 == hash2 and len(hash1) == 64:  # SHA256 = 64 hex chars
                self.log_result("Hash de tokens", True)
            else:
                self.log_result("Hash de tokens", False)
            
            return True
            
        except Exception as e:
            self.log_result("Sistema de autenticación", False, str(e))
            return False
    
    def run_full_validation(self) -> bool:
        """Ejecutar validación completa."""
        logger.info("🔒 INICIANDO VALIDACIÓN DE SEGURIDAD DEL BACKEND")
        logger.info("=" * 60)
        
        validation_steps = [
            ("Importaciones", self.validate_imports),
            ("Configuración", self.validate_configuration),
            ("Rate Limiter", self.validate_rate_limiter),
            ("Validación de entrada", self.validate_input_validator),
            ("Headers de seguridad", self.validate_security_headers),
            ("Autenticación", self.validate_authentication)
        ]
        
        passed_tests = 0
        total_tests = len(validation_steps)
        
        for step_name, step_function in validation_steps:
            logger.info(f"\n📋 Ejecutando: {step_name}")
            try:
                if step_function():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Error ejecutando {step_name}: {e}")
        
        # Resumen final
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DE VALIDACIÓN DE SEGURIDAD")
        logger.info("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"✅ Pruebas pasadas: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if self.errors:
            logger.info(f"❌ Errores: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        if self.warnings:
            logger.info(f"⚠️ Advertencias: {len(self.warnings)}")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        # Determinar resultado final
        if passed_tests == total_tests:
            logger.info("\n🎉 ¡VALIDACIÓN EXITOSA! Todos los componentes de seguridad funcionan correctamente.")
            return True
        elif passed_tests >= total_tests * 0.8:  # 80% o más
            logger.info("\n⚠️ VALIDACIÓN PARCIAL. La mayoría de componentes funcionan.")
            return False
        else:
            logger.info("\n❌ VALIDACIÓN FALLIDA. Hay problemas significativos de seguridad.")
            return False


def main():
    """Función principal."""
    validator = BackendSecurityValidator()
    
    try:
        success = validator.run_full_validation()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Validación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado durante la validación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 