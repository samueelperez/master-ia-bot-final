#!/usr/bin/env python3
"""
Script para validar la nueva arquitectura modular del módulo AI.
Verifica que todos los componentes estén correctamente separados y funcionen.
"""

import sys
import os
import logging
from typing import Dict, List, Tuple
import importlib.util

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar el directorio del módulo AI al path
AI_MODULE_PATH = os.path.join(os.getcwd(), "src", "ai-module")
sys.path.insert(0, AI_MODULE_PATH)


class ArchitectureValidator:
    """Validador de la nueva arquitectura modular."""
    
    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []
    
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
    
    def validate_file_structure(self) -> bool:
        """Validar que la estructura de archivos sea correcta."""
        logger.info("🔍 Validando estructura de archivos...")
        
        required_files = [
            "src/ai-module/core/__init__.py",
            "src/ai-module/core/config/__init__.py",
            "src/ai-module/core/config/security_config.py",
            "src/ai-module/core/middleware/__init__.py",
            "src/ai-module/core/middleware/rate_limiter.py",
            "src/ai-module/core/validation/__init__.py",
            "src/ai-module/core/validation/input_validator.py",
            "src/ai-module/core/services/__init__.py",
            "src/ai-module/core/services/ai_service.py",
            "src/ai-module/core/services/data_service.py",
            "src/ai-module/core/models/__init__.py",
            "src/ai-module/core/models/request_models.py",
            "src/ai-module/main.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self.log_result(
                "Estructura de archivos", 
                False, 
                f"Archivos faltantes: {', '.join(missing_files)}"
            )
            return False
        
        self.log_result("Estructura de archivos", True, f"{len(required_files)} archivos encontrados")
        
        # Verificar que los archivos no estén vacíos
        for file_path in required_files:
            if os.path.getsize(file_path) == 0:
                self.log_result(f"Archivo vacío: {file_path}", False)
                return False
        
        self.log_result("Estructura de archivos", True, f"{len(required_files)} archivos verificados")
        return True
    
    def validate_imports(self) -> bool:
        """Validar que las importaciones funcionen correctamente."""
        logger.info("🔍 Validando importaciones de módulos...")
        
        import_tests = [
            ("core.config.security_config", "SecurityConfig"),
            ("core.middleware.rate_limiter", "RateLimiter"),
            ("core.validation.input_validator", "InputValidator"),
            ("core.services.ai_service", "AIService"),
            ("core.services.data_service", "DataService"),
            ("core.models.request_models", "CryptoAnalysisRequest")
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
            except Exception as e:
                self.log_result(f"Import {module_name}", False, f"Error inesperado: {e}")
                all_passed = False
        
        return all_passed
    
    def validate_configuration(self) -> bool:
        """Validar que la configuración sea correcta."""
        logger.info("🔍 Validando configuración de seguridad...")
        
        try:
            from core.config.security_config import SecurityConfig, ValidationConfig
            
            # Verificar que SecurityConfig tenga los atributos requeridos
            required_attrs = [
                'RATE_LIMIT_PER_MINUTE', 'RATE_LIMIT_PER_HOUR', 'HTTP_TIMEOUT',
                'ALLOWED_ORIGINS', 'ALLOWED_HOSTS'
            ]
            
            missing_attrs = []
            for attr in required_attrs:
                if not hasattr(SecurityConfig, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                self.log_result(
                    "Configuración SecurityConfig", 
                    False, 
                    f"Atributos faltantes: {', '.join(missing_attrs)}"
                )
                return False
            
            # Verificar ValidationConfig
            if not hasattr(ValidationConfig, 'ALLOWED_SYMBOLS'):
                self.log_result("Configuración ValidationConfig", False, "ALLOWED_SYMBOLS no encontrado")
                return False
            
            # Verificar que validate_config funcione
            try:
                SecurityConfig.validate_config()
                self.log_result("Validación de configuración", True)
            except Exception as e:
                self.log_warning("Validación de configuración", f"Error en validate_config: {e}")
            
            self.log_result("Configuración", True, f"{len(required_attrs)} atributos verificados")
            return True
            
        except Exception as e:
            self.log_result("Configuración", False, str(e))
            return False
    
    def validate_services(self) -> bool:
        """Validar que los servicios se puedan instanciar."""
        logger.info("🔍 Validando servicios...")
        
        services_passed = 0
        total_services = 0
        
        # Validar DataService
        try:
            from core.services.data_service import DataService
            data_service = DataService()
            
            # Verificar métodos clave
            required_methods = ['get_current_price', 'get_service_status', 'clear_cache']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(data_service, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_result(
                    "DataService", 
                    False, 
                    f"Métodos faltantes: {', '.join(missing_methods)}"
                )
            else:
                self.log_result("DataService", True, f"{len(required_methods)} métodos verificados")
                services_passed += 1
            
            total_services += 1
            
        except Exception as e:
            self.log_result("DataService", False, str(e))
            total_services += 1
        
        # Validar AIService (puede fallar por OpenAI API key)
        try:
            from core.services.ai_service import AIService
            
            # Verificar que la clase existe y tiene métodos requeridos
            required_methods = ['generate_crypto_analysis', 'generate_trading_signal', 'get_service_status']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(AIService, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_result(
                    "AIService (estructura)", 
                    False, 
                    f"Métodos faltantes: {', '.join(missing_methods)}"
                )
            else:
                self.log_result("AIService (estructura)", True, f"{len(required_methods)} métodos verificados")
                services_passed += 1
            
            total_services += 1
            
        except Exception as e:
            self.log_result("AIService", False, str(e))
            total_services += 1
        
        return services_passed == total_services
    
    def validate_models(self) -> bool:
        """Validar modelos de datos."""
        logger.info("🔍 Validando modelos de datos...")
        
        try:
            from core.models.request_models import (
                CryptoAnalysisRequest, TradingSignalRequest, 
                CustomPromptRequest, RequestFactory
            )
            
            # Probar creación de modelo básico
            try:
                analysis_request = CryptoAnalysisRequest(
                    symbol="BTC",
                    timeframes=["1d", "4h"]
                )
                self.log_result("CryptoAnalysisRequest", True, "Modelo creado correctamente")
            except Exception as e:
                self.log_result("CryptoAnalysisRequest", False, str(e))
                return False
            
            # Probar RequestFactory
            try:
                factory_request = RequestFactory.create_request(
                    "analysis",
                    symbol="ETH",
                    timeframes=["1d"]
                )
                self.log_result("RequestFactory", True, "Factory funcionando")
            except Exception as e:
                self.log_result("RequestFactory", False, str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_result("Modelos de datos", False, str(e))
            return False
    
    def validate_validation_system(self) -> bool:
        """Validar sistema de validación."""
        logger.info("🔍 Validando sistema de validación...")
        
        try:
            from core.validation.input_validator import InputValidator, InputValidationError
            
            # Probar validación de símbolo válido
            try:
                valid_symbol = InputValidator.validate_symbol("BTC")
                if valid_symbol == "BTC":
                    self.log_result("Validación símbolo válido", True)
                else:
                    self.log_result("Validación símbolo válido", False, f"Resultado inesperado: {valid_symbol}")
                    return False
            except Exception as e:
                self.log_result("Validación símbolo válido", False, str(e))
                return False
            
            # Probar validación de símbolo inválido
            try:
                InputValidator.validate_symbol("INVALID_SYMBOL_123")
                self.log_result("Validación símbolo inválido", False, "Debería haber fallado")
                return False
            except InputValidationError:
                self.log_result("Validación símbolo inválido", True, "Correctamente rechazado")
            except Exception as e:
                self.log_result("Validación símbolo inválido", False, f"Error inesperado: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.log_result("Sistema de validación", False, str(e))
            return False
    
    def validate_rate_limiter(self) -> bool:
        """Validar rate limiter."""
        logger.info("🔍 Validando rate limiter...")
        
        try:
            from core.middleware.rate_limiter import RateLimiter
            
            rate_limiter = RateLimiter()
            
            # Probar funcionalidad básica
            test_ip = "192.168.1.100"
            
            allowed, reason = rate_limiter.is_allowed(test_ip)
            if allowed:
                self.log_result("Rate limiter permitir", True)
                rate_limiter.record_request(test_ip)
                self.log_result("Rate limiter registrar", True)
            else:
                self.log_result("Rate limiter", False, f"No permitió request inicial: {reason}")
                return False
            
            # Probar estadísticas
            stats = rate_limiter.get_global_stats()
            if isinstance(stats, dict) and 'total_clients' in stats:
                self.log_result("Rate limiter estadísticas", True)
            else:
                self.log_result("Rate limiter estadísticas", False, "Formato de estadísticas incorrecto")
                return False
            
            return True
            
        except Exception as e:
            self.log_result("Rate limiter", False, str(e))
            return False
    
    def validate_main_app(self) -> bool:
        """Validar aplicación principal."""
        logger.info("🔍 Validando aplicación principal...")
        
        try:
            # Importar la app principal
            from main import app
            
            if hasattr(app, 'routes') and len(app.routes) > 0:
                self.log_result("Aplicación principal", True, f"{len(app.routes)} rutas encontradas")
                return True
            else:
                self.log_result("Aplicación principal", False, "No se encontraron rutas")
                return False
                
        except Exception as e:
            self.log_result("Aplicación principal", False, str(e))
            return False
    
    def run_full_validation(self) -> bool:
        """Ejecutar validación completa."""
        logger.info("🏗️ INICIANDO VALIDACIÓN DE ARQUITECTURA MODULAR")
        logger.info("=" * 60)
        
        validation_steps = [
            ("Estructura de archivos", self.validate_file_structure),
            ("Importaciones", self.validate_imports),
            ("Configuración", self.validate_configuration),
            ("Servicios", self.validate_services),
            ("Modelos de datos", self.validate_models),
            ("Sistema de validación", self.validate_validation_system),
            ("Rate limiter", self.validate_rate_limiter),
            ("Aplicación principal", self.validate_main_app)
        ]
        
        passed_tests = 0
        total_tests = len(validation_steps)
        
        for step_name, validation_func in validation_steps:
            logger.info(f"\n📋 Ejecutando: {step_name}")
            try:
                if validation_func():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Error en {step_name}: {e}")
                self.errors.append(f"{step_name}: Error inesperado - {e}")
        
        # Mostrar resumen
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DE VALIDACIÓN")
        logger.info("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"✅ Pruebas pasadas: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if self.warnings:
            logger.info(f"⚠️ Advertencias: {len(self.warnings)}")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        if self.errors:
            logger.info(f"❌ Errores: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        # Conclusión
        if passed_tests == total_tests:
            logger.info("\n🎉 ¡VALIDACIÓN EXITOSA! La arquitectura modular está funcionando correctamente.")
            return True
        elif passed_tests >= total_tests * 0.8:
            logger.info("\n⚠️ VALIDACIÓN PARCIAL. La mayoría de componentes funcionan, pero hay algunos problemas.")
            return False
        else:
            logger.info("\n❌ VALIDACIÓN FALLIDA. Hay problemas significativos en la arquitectura.")
            return False


def main():
    """Función principal."""
    try:
        validator = ArchitectureValidator()
        success = validator.run_full_validation()
        
        if success:
            logger.info("\n🚀 ARQUITECTURA MODULAR VALIDADA - LISTA PARA USAR")
            sys.exit(0)
        else:
            logger.error("\n🛠️ SE REQUIEREN CORRECCIONES ANTES DE USAR")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Validación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Error crítico durante la validación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 