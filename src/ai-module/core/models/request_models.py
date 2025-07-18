"""
Modelos de datos para requests del módulo AI.
Implementa validación robusta con Pydantic.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..validation.input_validator import InputValidator, InputValidationError


class RequestPriority(Enum):
    """Prioridades de request."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisType(Enum):
    """Tipos de análisis disponibles."""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    COMBINED = "combined"


class SignalType(Enum):
    """Tipos de señales de trading."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WAIT = "wait"


class BaseRequest(BaseModel):
    """Modelo base para todas las requests."""
    
    request_id: Optional[str] = Field(None, description="ID único de la request")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de la request")
    priority: RequestPriority = Field(RequestPriority.NORMAL, description="Prioridad de la request")
    user_context: Optional[str] = Field(None, max_length=500, description="Contexto adicional del usuario")
    
    class Config:
        """Configuración del modelo."""
        use_enum_values = True
        validate_assignment = True
        
    @validator('user_context')
    def validate_user_context(cls, v):
        """Validar contexto del usuario."""
        if v and v.strip():
            try:
                return InputValidator.validate_prompt(v, max_length=500)
            except InputValidationError:
                raise ValueError("Contexto de usuario contiene contenido inválido")
        return v


class CryptoAnalysisRequest(BaseRequest):
    """Request para análisis de criptomonedas."""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Símbolo de criptomoneda")
    timeframes: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=5, 
        description="Timeframes a analizar"
    )
    analysis_type: AnalysisType = Field(
        AnalysisType.TECHNICAL, 
        description="Tipo de análisis a realizar"
    )
    user_prompt: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Prompt específico del usuario"
    )
    include_risk_analysis: bool = Field(True, description="Incluir análisis de riesgo")
    include_price_targets: bool = Field(True, description="Incluir objetivos de precio")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validar símbolo de criptomoneda."""
        try:
            return InputValidator.validate_symbol(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('timeframes')
    def validate_timeframes(cls, v):
        """Validar lista de timeframes."""
        try:
            return InputValidator.validate_timeframes_list(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('user_prompt')
    def validate_user_prompt(cls, v):
        """Validar prompt del usuario."""
        if v and v.strip():
            try:
                return InputValidator.validate_prompt(v)
            except InputValidationError as e:
                raise ValueError(e.reason)
        return v


class TradingSignalRequest(BaseRequest):
    """Request para generar señales de trading."""
    
    symbol: str = Field(..., min_length=1, max_length=10, description="Símbolo de criptomoneda")
    timeframe: str = Field("1d", max_length=5, description="Timeframe para la señal")
    strategy_name: Optional[str] = Field(
        None, 
        max_length=50, 
        description="Nombre de la estrategia"
    )
    risk_tolerance: float = Field(
        0.02, 
        ge=0.001, 
        le=0.1, 
        description="Tolerancia al riesgo (0.001-0.1)"
    )
    position_size: Optional[float] = Field(
        None, 
        ge=0.01, 
        le=1.0, 
        description="Tamaño de posición (0.01-1.0)"
    )
    max_drawdown: float = Field(
        0.05, 
        ge=0.01, 
        le=0.2, 
        description="Máximo drawdown permitido"
    )
    take_profit_ratio: float = Field(
        2.0, 
        ge=1.0, 
        le=10.0, 
        description="Ratio take profit / stop loss"
    )
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validar símbolo."""
        try:
            return InputValidator.validate_symbol(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Validar timeframe."""
        try:
            return InputValidator.validate_timeframe(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('strategy_name')
    def validate_strategy_name(cls, v):
        """Validar nombre de estrategia."""
        if v and v.strip():
            # Solo permitir caracteres alfanuméricos, espacios y guiones
            import re
            if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
                raise ValueError("Nombre de estrategia contiene caracteres no permitidos")
            return v.strip()
        return v


class CustomPromptRequest(BaseRequest):
    """Request para prompts personalizados."""
    
    prompt: str = Field(..., min_length=3, max_length=1000, description="Prompt personalizado")
    conversation_history: List[Dict[str, str]] = Field(
        [], 
        max_items=10, 
        description="Historial de conversación"
    )
    model_parameters: Optional[Dict[str, Any]] = Field(
        None, 
        description="Parámetros específicos del modelo"
    )
    expected_response_length: int = Field(
        500, 
        ge=50, 
        le=2000, 
        description="Longitud esperada de la respuesta"
    )
    creativity_level: float = Field(
        0.6, 
        ge=0.0, 
        le=1.0, 
        description="Nivel de creatividad (temperatura)"
    )
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Validar prompt principal."""
        try:
            return InputValidator.validate_prompt(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('conversation_history')
    def validate_conversation_history(cls, v):
        """Validar historial de conversación."""
        if v:
            try:
                return InputValidator.validate_conversation_history(v)
            except InputValidationError as e:
                raise ValueError(e.reason)
        return v
    
    @validator('model_parameters')
    def validate_model_parameters(cls, v):
        """Validar parámetros del modelo."""
        if v:
            allowed_params = {
                'temperature', 'max_tokens', 'top_p', 'frequency_penalty', 
                'presence_penalty', 'stop', 'model'
            }
            
            for param in v.keys():
                if param not in allowed_params:
                    raise ValueError(f"Parámetro '{param}' no permitido")
            
            # Validar rangos específicos
            if 'temperature' in v:
                temp = v['temperature']
                if not isinstance(temp, (int, float)) or not 0.0 <= temp <= 1.0:
                    raise ValueError("Temperature debe estar entre 0.0 y 1.0")
            
            if 'max_tokens' in v:
                tokens = v['max_tokens']
                if not isinstance(tokens, int) or not 50 <= tokens <= 2000:
                    raise ValueError("max_tokens debe estar entre 50 y 2000")
        
        return v


class MultiSymbolRequest(BaseRequest):
    """Request para análisis de múltiples símbolos."""
    
    symbols: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=10, 
        description="Lista de símbolos a analizar"
    )
    timeframe: str = Field("1d", description="Timeframe común para todos los símbolos")
    analysis_type: AnalysisType = Field(
        AnalysisType.TECHNICAL, 
        description="Tipo de análisis"
    )
    compare_symbols: bool = Field(
        True, 
        description="Comparar símbolos entre sí"
    )
    include_correlation: bool = Field(
        True, 
        description="Incluir análisis de correlación"
    )
    
    @validator('symbols')
    def validate_symbols(cls, v):
        """Validar lista de símbolos."""
        try:
            validated = InputValidator.validate_symbols_list(v)
            # Verificar que no haya demasiados símbolos duplicados
            if len(set(validated)) != len(validated):
                raise ValueError("No se permiten símbolos duplicados")
            return validated
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Validar timeframe."""
        try:
            return InputValidator.validate_timeframe(v)
        except InputValidationError as e:
            raise ValueError(e.reason)


class HealthCheckRequest(BaseRequest):
    """Request para verificación de salud del sistema."""
    
    check_type: str = Field("basic", description="Tipo de verificación")
    include_dependencies: bool = Field(True, description="Incluir estado de dependencias")
    include_performance_metrics: bool = Field(False, description="Incluir métricas de rendimiento")
    
    @validator('check_type')
    def validate_check_type(cls, v):
        """Validar tipo de verificación."""
        allowed_types = {"basic", "detailed", "performance", "security"}
        if v not in allowed_types:
            raise ValueError(f"check_type debe ser uno de: {', '.join(allowed_types)}")
        return v


class BatchRequest(BaseRequest):
    """Request para procesamiento en lote."""
    
    requests: List[Dict[str, Any]] = Field(
        ..., 
        min_items=1, 
        max_items=5, 
        description="Lista de requests a procesar"
    )
    parallel_processing: bool = Field(
        True, 
        description="Procesar requests en paralelo"
    )
    fail_fast: bool = Field(
        False, 
        description="Fallar rápido si una request falla"
    )
    timeout_seconds: int = Field(
        120, 
        ge=30, 
        le=300, 
        description="Timeout total para el lote"
    )
    
    @validator('requests')
    def validate_requests(cls, v):
        """Validar lista de requests."""
        for i, req in enumerate(v):
            if not isinstance(req, dict):
                raise ValueError(f"Request {i} debe ser un objeto")
            
            if 'type' not in req:
                raise ValueError(f"Request {i} debe tener un campo 'type'")
            
            allowed_types = {
                'analysis', 'signal', 'prompt', 'multi_symbol', 'health_check'
            }
            if req['type'] not in allowed_types:
                raise ValueError(f"Request {i} tipo '{req['type']}' no válido")
        
        return v


class AdvancedStrategyType(Enum):
    """Tipos de estrategias avanzadas disponibles."""
    DIVERGENCIA_CORRELACIONADA = "divergencia_correlacionada"
    ESTOCASTICO = "estocastico"
    SCALPING_ESTOCASTICO = "scalping_estocastico"
    FAIR_VALUE_GAP = "fair_value_gap"
    INTRADIA = "intradia"
    RSI = "rsi"
    SCALPING = "scalping"
    SMART_MONEY = "smart_money"
    VOLATILIDAD = "volatilidad"


class AdvancedStrategyRequest(BaseRequest):
    """Request para estrategias avanzadas de trading."""
    
    strategy_type: AdvancedStrategyType = Field(
        ..., 
        description="Tipo de estrategia avanzada"
    )
    symbol: str = Field(..., min_length=1, max_length=10, description="Símbolo principal")
    secondary_symbol: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=10, 
        description="Símbolo secundario (para divergencias correlacionadas)"
    )
    timeframe: str = Field("5m", max_length=5, description="Timeframe para análisis")
    technical_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Datos técnicos del activo principal (opcional, se obtiene internamente)"
    )
    secondary_technical_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Datos técnicos del activo secundario"
    )
    risk_reward_ratio: float = Field(
        1.5, 
        ge=1.0, 
        le=5.0, 
        description="Ratio riesgo/beneficio mínimo"
    )
    include_volume_analysis: bool = Field(
        True, 
        description="Incluir análisis de volumen"
    )
    include_momentum_analysis: bool = Field(
        True, 
        description="Incluir análisis de momentum"
    )
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validar símbolo principal."""
        try:
            return InputValidator.validate_symbol(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('secondary_symbol')
    def validate_secondary_symbol(cls, v):
        """Validar símbolo secundario."""
        if v:
            try:
                return InputValidator.validate_symbol(v)
            except InputValidationError as e:
                raise ValueError(e.reason)
        return v
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Validar timeframe."""
        try:
            return InputValidator.validate_timeframe(v)
        except InputValidationError as e:
            raise ValueError(e.reason)
    
    @validator('technical_data')
    def validate_technical_data(cls, v):
        """Validar datos técnicos."""
        if v is not None:
            required_fields = ['close', 'high', 'low', 'volume']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Campo requerido '{field}' no encontrado en technical_data")
        return v
    
    @validator('secondary_technical_data')
    def validate_secondary_technical_data(cls, v, values):
        """Validar datos técnicos secundarios."""
        if v and 'strategy_type' in values:
            if values['strategy_type'] == AdvancedStrategyType.DIVERGENCIA_CORRELACIONADA:
                required_fields = ['close', 'high', 'low', 'volume']
                for field in required_fields:
                    if field not in v:
                        raise ValueError(f"Campo requerido '{field}' no encontrado en secondary_technical_data")
        return v


# Factory para crear requests basados en tipo
class RequestFactory:
    """Factory para crear requests del tipo correcto."""
    
    _request_map = {
        'analysis': CryptoAnalysisRequest,
        'signal': TradingSignalRequest,
        'prompt': CustomPromptRequest,
        'multi_symbol': MultiSymbolRequest,
        'health_check': HealthCheckRequest,
        'batch': BatchRequest,
        'advanced_strategy': AdvancedStrategyRequest
    }
    
    @classmethod
    def create_request(cls, request_type: str, **kwargs) -> BaseRequest:
        """
        Crear una request del tipo especificado.
        
        Args:
            request_type: Tipo de request
            **kwargs: Parámetros para la request
        
        Returns:
            Instancia de request validada
        
        Raises:
            ValueError: Si el tipo de request no es válido
        """
        if request_type not in cls._request_map:
            allowed_types = ', '.join(cls._request_map.keys())
            raise ValueError(f"Tipo de request '{request_type}' no válido. Tipos permitidos: {allowed_types}")
        
        request_class = cls._request_map[request_type]
        return request_class(**kwargs)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Obtener tipos de request disponibles."""
        return list(cls._request_map.keys())
    
    @classmethod
    def get_request_schema(cls, request_type: str) -> Dict[str, Any]:
        """Obtener schema de un tipo de request."""
        if request_type not in cls._request_map:
            raise ValueError(f"Tipo de request '{request_type}' no válido")
        
        request_class = cls._request_map[request_type]
        return request_class.schema() 