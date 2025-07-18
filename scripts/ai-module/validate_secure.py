#!/usr/bin/env python3
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
