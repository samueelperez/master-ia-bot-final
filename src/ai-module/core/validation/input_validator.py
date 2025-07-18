"""
Sistema de validación de entrada robusto para el módulo AI.
Previene inyecciones, XSS y otros ataques de entrada.
"""

import re
import logging
from typing import List, Any, Dict, Optional
from html import escape
from urllib.parse import urlparse, unquote

from ..config.security_config import ValidationConfig, SecurityConfig

logger = logging.getLogger(__name__)


class InputValidationError(Exception):
    """Excepción específica para errores de validación."""
    
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validación fallida en '{field}': {reason}")


class InputValidator:
    """
    Validador avanzado de entradas con múltiples capas de seguridad.
    Implementa sanitización, validación de formato y detección de patrones peligrosos.
    """
    
    @classmethod
    def _check_dangerous_patterns(cls, value: str, field_name: str) -> None:
        """Verificar patrones peligrosos en el input."""
        for pattern in ValidationConfig.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Patrón peligroso detectado en '{field_name}': {pattern}")
                raise InputValidationError(
                    field_name, 
                    value[:50] + "..." if len(value) > 50 else value,
                    f"Contiene patrón peligroso: {pattern}"
                )
    
    @classmethod
    def _sanitize_string(cls, value: str) -> str:
        """Sanitizar string básico."""
        if not isinstance(value, str):
            raise InputValidationError("string", str(value), "Debe ser un string")
        
        # Decodificar URL encoding
        try:
            value = unquote(value)
        except Exception:
            pass
        
        # Escapar HTML
        value = escape(value, quote=True)
        
        # Remover caracteres de control
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # Normalizar espacios
        value = ' '.join(value.split())
        
        return value.strip()
    
    @classmethod
    def validate_symbol(cls, symbol: str) -> str:
        """
        Validar símbolo de criptomoneda.
        
        Args:
            symbol: Símbolo a validar (ej: 'BTC', 'ETH')
            
        Returns:
            Símbolo validado en mayúsculas
            
        Raises:
            InputValidationError: Si el símbolo es inválido
        """
        if not symbol:
            raise InputValidationError("symbol", "", "El símbolo no puede estar vacío")
        
        # Sanitizar entrada
        symbol = cls._sanitize_string(symbol).upper()
        
        # Verificar patrones peligrosos
        cls._check_dangerous_patterns(symbol, "symbol")
        
        # Validar formato
        if not re.match(ValidationConfig.get_symbol_validation_pattern(), symbol):
            raise InputValidationError(
                "symbol", 
                symbol, 
                "Formato inválido. Debe ser 2-10 caracteres alfabéticos"
            )
        
        # Verificar contra lista blanca
        if symbol not in ValidationConfig.ALLOWED_SYMBOLS:
            allowed_symbols = ', '.join(sorted(list(ValidationConfig.ALLOWED_SYMBOLS)[:10]))
            raise InputValidationError(
                "symbol", 
                symbol, 
                f"Símbolo no permitido. Símbolos válidos incluyen: {allowed_symbols}..."
            )
        
        logger.debug(f"Símbolo validado: {symbol}")
        return symbol
    
    @classmethod
    def validate_timeframe(cls, timeframe: str) -> str:
        """
        Validar timeframe.
        
        Args:
            timeframe: Timeframe a validar (ej: '1h', '1d')
            
        Returns:
            Timeframe validado
            
        Raises:
            InputValidationError: Si el timeframe es inválido
        """
        if not timeframe:
            raise InputValidationError("timeframe", "", "El timeframe no puede estar vacío")
        
        # Sanitizar entrada
        timeframe = cls._sanitize_string(timeframe).lower()
        
        # Verificar patrones peligrosos
        cls._check_dangerous_patterns(timeframe, "timeframe")
        
        # Validar formato
        if not re.match(ValidationConfig.get_timeframe_validation_pattern(), timeframe):
            raise InputValidationError(
                "timeframe", 
                timeframe, 
                "Formato inválido. Ejemplos válidos: 1m, 5m, 1h, 1d"
            )
        
        # Verificar contra lista permitida
        if timeframe not in ValidationConfig.ALLOWED_TIMEFRAMES:
            allowed_tf = ', '.join(sorted(ValidationConfig.ALLOWED_TIMEFRAMES))
            raise InputValidationError(
                "timeframe", 
                timeframe, 
                f"Timeframe no permitido. Válidos: {allowed_tf}"
            )
        
        logger.debug(f"Timeframe validado: {timeframe}")
        return timeframe
    
    @classmethod
    def validate_prompt(cls, prompt: str, max_length: Optional[int] = None) -> str:
        """
        Validar prompt del usuario.
        
        Args:
            prompt: Prompt a validar
            max_length: Longitud máxima (usa config por defecto si no se especifica)
            
        Returns:
            Prompt validado y sanitizado
            
        Raises:
            InputValidationError: Si el prompt es inválido
        """
        if not prompt:
            raise InputValidationError("prompt", "", "El prompt no puede estar vacío")
        
        max_len = max_length or SecurityConfig.MAX_PROMPT_LENGTH
        
        # Verificar longitud antes de sanitizar
        if len(prompt) > max_len:
            raise InputValidationError(
                "prompt", 
                prompt[:50] + "...", 
                f"Prompt demasiado largo. Máximo {max_len} caracteres"
            )
        
        # Sanitizar entrada
        prompt = cls._sanitize_string(prompt)
        
        # Verificar patrones peligrosos
        cls._check_dangerous_patterns(prompt, "prompt")
        
        # Validaciones específicas de prompt
        if len(prompt.strip()) < 3:
            raise InputValidationError(
                "prompt", 
                prompt, 
                "Prompt demasiado corto. Mínimo 3 caracteres"
            )
        
        # Verificar que no sea solo números o caracteres especiales
        if not re.search(r'[a-zA-Z]', prompt):
            raise InputValidationError(
                "prompt", 
                prompt, 
                "El prompt debe contener al menos algunas letras"
            )
        
        logger.debug(f"Prompt validado: {prompt[:50]}...")
        return prompt
    
    @classmethod
    def validate_symbols_list(cls, symbols: List[str]) -> List[str]:
        """
        Validar lista de símbolos.
        
        Args:
            symbols: Lista de símbolos a validar
            
        Returns:
            Lista de símbolos validados
            
        Raises:
            InputValidationError: Si algún símbolo es inválido
        """
        if not symbols:
            raise InputValidationError("symbols", "[]", "La lista de símbolos no puede estar vacía")
        
        if not isinstance(symbols, list):
            raise InputValidationError("symbols", str(symbols), "Debe ser una lista")
        
        if len(symbols) > ValidationConfig.MAX_SYMBOLS_PER_REQUEST:
            raise InputValidationError(
                "symbols", 
                str(symbols), 
                f"Demasiados símbolos. Máximo {ValidationConfig.MAX_SYMBOLS_PER_REQUEST}"
            )
        
        validated_symbols = []
        for i, symbol in enumerate(symbols):
            try:
                validated_symbol = cls.validate_symbol(symbol)
                if validated_symbol not in validated_symbols:  # Evitar duplicados
                    validated_symbols.append(validated_symbol)
            except InputValidationError as e:
                raise InputValidationError(
                    f"symbols[{i}]", 
                    symbol, 
                    f"Símbolo inválido: {e.reason}"
                )
        
        return validated_symbols
    
    @classmethod
    def validate_timeframes_list(cls, timeframes: List[str]) -> List[str]:
        """
        Validar lista de timeframes.
        
        Args:
            timeframes: Lista de timeframes a validar
            
        Returns:
            Lista de timeframes validados
            
        Raises:
            InputValidationError: Si algún timeframe es inválido
        """
        if not timeframes:
            raise InputValidationError("timeframes", "[]", "La lista de timeframes no puede estar vacía")
        
        if not isinstance(timeframes, list):
            raise InputValidationError("timeframes", str(timeframes), "Debe ser una lista")
        
        if len(timeframes) > 10:  # Límite razonable
            raise InputValidationError(
                "timeframes", 
                str(timeframes), 
                "Demasiados timeframes. Máximo 10"
            )
        
        validated_timeframes = []
        for i, timeframe in enumerate(timeframes):
            try:
                validated_tf = cls.validate_timeframe(timeframe)
                if validated_tf not in validated_timeframes:  # Evitar duplicados
                    validated_timeframes.append(validated_tf)
            except InputValidationError as e:
                raise InputValidationError(
                    f"timeframes[{i}]", 
                    timeframe, 
                    f"Timeframe inválido: {e.reason}"
                )
        
        return validated_timeframes
    
    @classmethod
    def validate_conversation_history(cls, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Validar historial de conversación.
        
        Args:
            history: Lista de mensajes de conversación
            
        Returns:
            Historial validado
            
        Raises:
            InputValidationError: Si el historial es inválido
        """
        if not isinstance(history, list):
            raise InputValidationError("conversation_history", str(history), "Debe ser una lista")
        
        if len(history) > SecurityConfig.MAX_CONVERSATION_HISTORY:
            raise InputValidationError(
                "conversation_history",
                f"[{len(history)} mensajes]",
                f"Demasiados mensajes. Máximo {SecurityConfig.MAX_CONVERSATION_HISTORY}"
            )
        
        validated_history = []
        
        for i, message in enumerate(history):
            if not isinstance(message, dict):
                raise InputValidationError(
                    f"conversation_history[{i}]", 
                    str(message), 
                    "Cada mensaje debe ser un objeto"
                )
            
            required_fields = {"role", "content"}
            if not required_fields.issubset(message.keys()):
                raise InputValidationError(
                    f"conversation_history[{i}]", 
                    str(message.keys()), 
                    f"Faltan campos requeridos: {required_fields - set(message.keys())}"
                )
            
            role = message["role"]
            content = message["content"]
            
            # Validar role
            if role not in {"user", "assistant", "system"}:
                raise InputValidationError(
                    f"conversation_history[{i}].role", 
                    role, 
                    "Role debe ser 'user', 'assistant' o 'system'"
                )
            
            # Validar y sanitizar content
            try:
                validated_content = cls.validate_prompt(content, max_length=2000)
                validated_history.append({
                    "role": role,
                    "content": validated_content
                })
            except InputValidationError as e:
                raise InputValidationError(
                    f"conversation_history[{i}].content", 
                    content[:50] + "...", 
                    f"Contenido inválido: {e.reason}"
                )
        
        return validated_history
    
    @classmethod
    def validate_api_parameters(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validar parámetros generales de API.
        
        Args:
            params: Diccionario de parámetros a validar
            
        Returns:
            Parámetros validados
            
        Raises:
            InputValidationError: Si algún parámetro es inválido
        """
        validated_params = {}
        
        for key, value in params.items():
            # Validar nombres de parámetros
            if not re.match(r'^[a-z_][a-z0-9_]*$', key):
                raise InputValidationError(
                    "parameter_name", 
                    key, 
                    "Nombre de parámetro inválido. Solo letras minúsculas, números y underscore"
                )
            
            # Sanitizar strings
            if isinstance(value, str):
                cls._check_dangerous_patterns(value, key)
                validated_params[key] = cls._sanitize_string(value)
            elif isinstance(value, (int, float, bool)):
                validated_params[key] = value
            elif isinstance(value, list):
                # Validar lista (longitud limitada)
                if len(value) > 50:
                    raise InputValidationError(
                        key, 
                        f"[{len(value)} items]", 
                        "Lista demasiado larga"
                    )
                validated_params[key] = value
            else:
                raise InputValidationError(
                    key, 
                    str(type(value)), 
                    "Tipo de parámetro no permitido"
                )
        
        return validated_params
