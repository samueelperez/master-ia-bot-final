"""
Sistema de validación de entrada y sanitización para el backend.
Detecta y previene inyecciones y patrones peligrosos.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union, Set
from urllib.parse import urlparse
import html
import unicodedata

from ..config.security_config import ValidationConfig

logger = logging.getLogger(__name__)

class InputSanitizer:
    """Sanitizador de entrada para prevenir inyecciones."""
    
    def __init__(self):
        # Compilar patrones peligrosos para mejor rendimiento
        self.dangerous_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for pattern in ValidationConfig.DANGEROUS_PATTERNS
        ]
    
    def detect_dangerous_patterns(self, text: str) -> List[str]:
        """
        Detectar patrones peligrosos en el texto.
        
        Args:
            text: Texto a analizar
        
        Returns:
            Lista de patrones peligrosos encontrados
        """
        if not isinstance(text, str):
            return []
        
        detected_patterns = []
        for i, pattern in enumerate(self.dangerous_patterns):
            if pattern.search(text):
                pattern_name = ValidationConfig.DANGEROUS_PATTERNS[i]
                detected_patterns.append(pattern_name)
                logger.warning(f"Patrón peligroso detectado: {pattern_name} en texto: {text[:100]}...")
        
        return detected_patterns
    
    def sanitize_string(self, text: str, max_length: int = 1000) -> str:
        """
        Sanitizar string de entrada.
        
        Args:
            text: Texto a sanitizar
            max_length: Longitud máxima permitida
        
        Returns:
            Texto sanitizado
        """
        if not isinstance(text, str):
            return str(text)
        
        # Truncar si es muy largo
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Texto truncado a {max_length} caracteres")
        
        # Normalizar unicode
        text = unicodedata.normalize('NFKC', text)
        
        # Escapar HTML
        text = html.escape(text)
        
        # Remover caracteres de control excepto espacios básicos
        text = ''.join(char for char in text if not unicodedata.category(char).startswith('C') or char in ['\n', '\r', '\t'])
        
        # Detectar patrones peligrosos
        dangerous_patterns = self.detect_dangerous_patterns(text)
        if dangerous_patterns:
            raise ValueError(f"Patrones peligrosos detectados: {', '.join(dangerous_patterns)}")
        
        return text.strip()
    
    def sanitize_json(self, data: Any, max_depth: int = 10, current_depth: int = 0) -> Any:
        """
        Sanitizar datos JSON recursivamente.
        
        Args:
            data: Datos a sanitizar
            max_depth: Profundidad máxima permitida
            current_depth: Profundidad actual (para recursión)
        
        Returns:
            Datos sanitizados
        """
        if current_depth > max_depth:
            raise ValueError(f"Profundidad JSON excedida: {current_depth} > {max_depth}")
        
        if isinstance(data, str):
            return self.sanitize_string(data)
        elif isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Sanitizar clave
                safe_key = self.sanitize_string(str(key), max_length=100)
                # Sanitizar valor recursivamente
                sanitized[safe_key] = self.sanitize_json(value, max_depth, current_depth + 1)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_json(item, max_depth, current_depth + 1) for item in data]
        elif isinstance(data, (int, float, bool)) or data is None:
            return data
        else:
            # Para otros tipos, convertir a string y sanitizar
            return self.sanitize_string(str(data))


class URLValidator:
    """Validador de URLs para prevenir SSRF."""
    
    # IPs y dominios peligrosos
    BLOCKED_IPS = {
        '127.0.0.1', 'localhost', '0.0.0.0', '::1',
        '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
        '169.254.0.0/16', '224.0.0.0/4', '240.0.0.0/4'
    }
    
    BLOCKED_DOMAINS = {
        'localhost', 'metadata.google.internal', 'instance-data.amazonaws.com',
        'metadata.amazonaws.com', '169.254.169.254'
    }
    
    ALLOWED_SCHEMES = {'http', 'https'}
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Validar URL para prevenir SSRF.
        
        Args:
            url: URL a validar
        
        Returns:
            True si la URL es segura
        
        Raises:
            ValueError: Si la URL es peligrosa
        """
        try:
            parsed = urlparse(url)
            
            # Verificar esquema
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                raise ValueError(f"Esquema no permitido: {parsed.scheme}")
            
            # Verificar dominio
            hostname = parsed.hostname
            if not hostname:
                raise ValueError("Hostname no encontrado en URL")
            
            if hostname.lower() in cls.BLOCKED_DOMAINS:
                raise ValueError(f"Dominio bloqueado: {hostname}")
            
            # Verificar IPs privadas/locales (simplificado)
            if any(blocked_ip in hostname for blocked_ip in cls.BLOCKED_IPS):
                raise ValueError(f"IP bloqueada detectada: {hostname}")
            
            return True
            
        except Exception as e:
            logger.warning(f"URL validation failed para {url}: {e}")
            raise ValueError(f"URL inválida: {e}")


class InputValidator:
    """Validador principal de entrada."""
    
    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.url_validator = URLValidator()
    
    def validate_symbol(self, symbol: str) -> str:
        """
        Validar símbolo de criptomoneda.
        
        Args:
            symbol: Símbolo a validar
        
        Returns:
            Símbolo validado y normalizado
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Símbolo requerido y debe ser string")
        
        # Sanitizar
        symbol = self.sanitizer.sanitize_string(symbol, max_length=20)
        
        # Normalizar formato
        symbol = symbol.upper().replace('-USD', '').replace('/USDT', '').replace('-USDT', '')
        
        # Verificar contra lista blanca
        if symbol not in ValidationConfig.ALLOWED_SYMBOLS:
            raise ValueError(f"Símbolo no permitido: {symbol}")
        
        return symbol
    
    def validate_timeframe(self, timeframe: str) -> str:
        """
        Validar timeframe.
        
        Args:
            timeframe: Timeframe a validar
        
        Returns:
            Timeframe validado
        """
        if not timeframe or not isinstance(timeframe, str):
            raise ValueError("Timeframe requerido y debe ser string")
        
        # Sanitizar
        timeframe = self.sanitizer.sanitize_string(timeframe, max_length=10)
        
        # Verificar contra lista blanca
        if timeframe not in ValidationConfig.ALLOWED_TIMEFRAMES:
            raise ValueError(f"Timeframe no permitido: {timeframe}")
        
        return timeframe
    
    def validate_limit(self, limit: Union[int, str]) -> int:
        """
        Validar límite de datos.
        
        Args:
            limit: Límite a validar
        
        Returns:
            Límite validado
        """
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            raise ValueError("Límite debe ser un número entero")
        
        if limit < 1:
            raise ValueError("Límite debe ser mayor que 0")
        
        from ..config.security_config import SecurityConfig
        max_limit = SecurityConfig.MAX_LIMIT_OHLCV
        if limit > max_limit:
            raise ValueError(f"Límite excedido: {limit} > {max_limit}")
        
        return limit
    
    def validate_categories(self, categories: Optional[List[str]]) -> Optional[List[str]]:
        """
        Validar categorías de indicadores.
        
        Args:
            categories: Lista de categorías a validar
        
        Returns:
            Categorías validadas
        """
        if categories is None:
            return None
        
        if not isinstance(categories, list):
            raise ValueError("Categorías debe ser una lista")
        
        if len(categories) > 10:
            raise ValueError("Máximo 10 categorías permitidas")
        
        validated_categories = []
        for category in categories:
            if not isinstance(category, str):
                raise ValueError("Cada categoría debe ser string")
            
            category = self.sanitizer.sanitize_string(category, max_length=50)
            
            if category not in ValidationConfig.ALLOWED_INDICATOR_CATEGORIES:
                raise ValueError(f"Categoría no válida: {category}")
            
            validated_categories.append(category)
        
        return validated_categories
    
    def validate_profile(self, profile: Optional[str]) -> Optional[str]:
        """
        Validar perfil de indicadores.
        
        Args:
            profile: Perfil a validar
        
        Returns:
            Perfil validado
        """
        if profile is None:
            return None
        
        if not isinstance(profile, str):
            raise ValueError("Perfil debe ser string")
        
        profile = self.sanitizer.sanitize_string(profile, max_length=50)
        
        if profile not in ValidationConfig.ALLOWED_INDICATOR_PROFILES:
            raise ValueError(f"Perfil no válido: {profile}")
        
        return profile
    
    def validate_specific_indicators(self, specific_indicators: Optional[Dict[str, List[str]]]) -> Optional[Dict[str, List[str]]]:
        """
        Validar indicadores específicos.
        
        Args:
            specific_indicators: Diccionario de indicadores específicos
        
        Returns:
            Indicadores validados
        """
        if specific_indicators is None:
            return None
        
        if not isinstance(specific_indicators, dict):
            raise ValueError("Indicadores específicos debe ser un diccionario")
        
        from ..config.security_config import SecurityConfig
        max_indicators = SecurityConfig.MAX_INDICATORS_PER_REQUEST
        total_indicators = sum(len(indicators) for indicators in specific_indicators.values())
        
        if total_indicators > max_indicators:
            raise ValueError(f"Demasiados indicadores: {total_indicators} > {max_indicators}")
        
        validated_indicators = {}
        for category, indicators in specific_indicators.items():
            # Validar categoría
            category = self.sanitizer.sanitize_string(category, max_length=50)
            if category not in ValidationConfig.ALLOWED_INDICATOR_CATEGORIES:
                raise ValueError(f"Categoría no válida: {category}")
            
            # Validar lista de indicadores
            if not isinstance(indicators, list):
                raise ValueError(f"Indicadores para categoría {category} debe ser lista")
            
            validated_list = []
            for indicator in indicators:
                if not isinstance(indicator, str):
                    raise ValueError("Cada indicador debe ser string")
                
                indicator = self.sanitizer.sanitize_string(indicator, max_length=100)
                validated_list.append(indicator)
            
            validated_indicators[category] = validated_list
        
        return validated_indicators
    
    def validate_api_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validar request completo de API.
        
        Args:
            data: Datos del request
        
        Returns:
            Datos validados
        """
        # Sanitizar JSON completo
        data = self.sanitizer.sanitize_json(data)
        
        validated_data = {}
        
        # Validar campos requeridos
        if 'symbol' in data:
            validated_data['symbol'] = self.validate_symbol(data['symbol'])
        
        if 'timeframe' in data:
            validated_data['timeframe'] = self.validate_timeframe(data['timeframe'])
        
        if 'limit' in data:
            validated_data['limit'] = self.validate_limit(data['limit'])
        
        # Validar campos opcionales
        if 'categories' in data:
            validated_data['categories'] = self.validate_categories(data['categories'])
        
        if 'profile' in data:
            validated_data['profile'] = self.validate_profile(data['profile'])
        
        if 'specific_indicators' in data:
            validated_data['specific_indicators'] = self.validate_specific_indicators(data['specific_indicators'])
        
        return validated_data
    
    def validate_payload_size(self, payload: str, max_size: int = 1048576) -> bool:
        """
        Validar tamaño del payload.
        
        Args:
            payload: Payload a validar
            max_size: Tamaño máximo en bytes (default 1MB)
        
        Returns:
            True si el tamaño es válido
        
        Raises:
            ValueError: Si el payload es muy grande
        """
        payload_size = len(payload.encode('utf-8'))
        if payload_size > max_size:
            raise ValueError(f"Payload muy grande: {payload_size} bytes > {max_size} bytes")
        
        return True


# Instancia global del validador
input_validator = InputValidator() 