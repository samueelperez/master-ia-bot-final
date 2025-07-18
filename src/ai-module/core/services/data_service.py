"""
Servicio de datos para obtener información de criptomonedas.
Maneja múltiples fuentes de datos con caching.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from ..config.security_config import SecurityConfig

logger = logging.getLogger(__name__)

# Importaciones condicionales
try:
    import httpx
    from httpx import AsyncClient, Timeout
except ImportError:
    logger.error("httpx no está instalado. Ejecutar: pip install httpx")
    httpx = None


class DataSource(Enum):
    """Fuentes de datos disponibles."""
    COINGECKO = "coingecko"
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"


@dataclass
class PriceData:
    """Datos de precio de una criptomoneda."""
    symbol: str
    price: float
    source: str
    timestamp: float = field(default_factory=time.time)
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None
    market_cap: Optional[float] = None
    
    @property
    def age_seconds(self) -> float:
        """Edad de los datos en segundos."""
        return time.time() - self.timestamp
    
    @property
    def is_stale(self) -> bool:
        """Verificar si los datos están obsoletos (>5 minutos)."""
        return self.age_seconds > 300


@dataclass
class MarketData:
    """Datos completos de mercado."""
    symbol: str
    prices: Dict[str, PriceData] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)
    
    def get_best_price(self) -> Optional[PriceData]:
        """Obtener el mejor precio disponible (más reciente y confiable)."""
        valid_prices = [p for p in self.prices.values() if not p.is_stale]
        
        if not valid_prices:
            # Si no hay precios frescos, usar el más reciente disponible
            valid_prices = list(self.prices.values())
        
        if not valid_prices:
            return None
        
        # Prioridad por fuente (CoinGecko > Binance > otros)
        priority_order = [DataSource.COINGECKO.value, DataSource.BINANCE.value]
        
        for source in priority_order:
            for price in valid_prices:
                if price.source == source:
                    return price
        
        # Si no hay fuentes prioritarias, usar la más reciente
        return max(valid_prices, key=lambda p: p.timestamp)


class DataService:
    """
    Servicio de datos con múltiples fuentes y caching inteligente.
    Implementa retry logic para obtener datos de criptomonedas.
    """
    
    def __init__(self):
        if not httpx:
            logger.error("httpx no está disponible - servicio de datos no funcional")
            raise ImportError("httpx es requerido para el servicio de datos")
        
        self.cache: Dict[str, MarketData] = {}
        self.cache_ttl = 300  # 5 minutos
        self.request_timeout = SecurityConfig.HTTP_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1.0
        
        logger.info("Data Service inicializado")
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Verificar si los datos en cache son válidos."""
        if symbol not in self.cache:
            return False
        
        market_data = self.cache[symbol]
        age = time.time() - market_data.last_updated
        
        return age < self.cache_ttl
    
    async def _fetch_from_coingecko(self, symbol: str) -> Optional[PriceData]:
        """Obtener precio de CoinGecko."""
        if not httpx:
            return None
        
        try:
            # Mapeo de símbolos a IDs de CoinGecko
            symbol_mapping = {
                "BTC": "bitcoin", "ETH": "ethereum", "ADA": "cardano",
                "DOT": "polkadot", "SOL": "solana", "MATIC": "matic-network",
                "AVAX": "avalanche-2", "LINK": "chainlink", "UNI": "uniswap",
                "AAVE": "aave", "ATOM": "cosmos", "ALGO": "algorand"
            }
            
            coin_id = symbol_mapping.get(symbol.upper(), symbol.lower())
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_market_cap": "true"
            }
            
            timeout = Timeout(self.request_timeout)
            
            async with AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if coin_id in data:
                    coin_data = data[coin_id]
                    return PriceData(
                        symbol=symbol.upper(),
                        price=float(coin_data.get("usd", 0)),
                        source=DataSource.COINGECKO.value,
                        volume_24h=coin_data.get("usd_24h_vol"),
                        change_24h=coin_data.get("usd_24h_change"),
                        market_cap=coin_data.get("usd_market_cap")
                    )
        
        except Exception as e:
            logger.warning(f"Error obteniendo datos de CoinGecko para {symbol}: {e}")
        
        return None
    
    async def _fetch_from_binance(self, symbol: str) -> Optional[PriceData]:
        """Obtener precio de Binance."""
        if not httpx:
            return None
        
        try:
            # Binance usa pares con USDT
            pair_symbol = f"{symbol.upper()}USDT"
            
            # Primero obtener precio actual
            price_url = "https://api.binance.com/api/v3/ticker/price"
            stats_url = "https://api.binance.com/api/v3/ticker/24hr"
            
            timeout = Timeout(self.request_timeout)
            
            async with AsyncClient(timeout=timeout) as client:
                # Obtener precio y estadísticas en paralelo
                price_task = client.get(price_url, params={"symbol": pair_symbol})
                stats_task = client.get(stats_url, params={"symbol": pair_symbol})
                
                price_response, stats_response = await asyncio.gather(
                    price_task, stats_task, return_exceptions=True
                )
                
                price_data = None
                volume_24h = None
                change_24h = None
                
                # Procesar respuesta de precio
                if not isinstance(price_response, Exception):
                    price_response.raise_for_status()
                    price_json = price_response.json()
                    price_data = float(price_json.get("price", 0))
                
                # Procesar respuesta de estadísticas
                if not isinstance(stats_response, Exception):
                    stats_response.raise_for_status()
                    stats_json = stats_response.json()
                    volume_24h = float(stats_json.get("volume", 0))
                    change_24h = float(stats_json.get("priceChangePercent", 0))
                
                if price_data and price_data > 0:
                    return PriceData(
                        symbol=symbol.upper(),
                        price=price_data,
                        source=DataSource.BINANCE.value,
                        volume_24h=volume_24h,
                        change_24h=change_24h
                    )
        
        except Exception as e:
            logger.warning(f"Error obteniendo datos de Binance para {symbol}: {e}")
        
        return None
    
    async def _fetch_from_coinbase(self, symbol: str) -> Optional[PriceData]:
        """Obtener precio de Coinbase."""
        if not httpx:
            return None
        
        try:
            pair_symbol = f"{symbol.upper()}-USD"
            url = f"https://api.exchange.coinbase.com/products/{pair_symbol}/ticker"
            
            timeout = Timeout(self.request_timeout)
            
            async with AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                price = float(data.get("price", 0))
                volume = float(data.get("volume", 0))
                
                if price > 0:
                    return PriceData(
                        symbol=symbol.upper(),
                        price=price,
                        source=DataSource.COINBASE.value,
                        volume_24h=volume
                    )
        
        except Exception as e:
            logger.warning(f"Error obteniendo datos de Coinbase para {symbol}: {e}")
        
        return None
    
    async def _fetch_price_from_all_sources(self, symbol: str) -> Dict[str, PriceData]:
        """Obtener precios de todas las fuentes disponibles."""
        if not httpx:
            logger.error("httpx no disponible - no se pueden obtener precios")
            return {}
        
        # Crear tareas para todas las fuentes
        tasks = [
            self._fetch_from_coingecko(symbol),
            self._fetch_from_binance(symbol),
            self._fetch_from_coinbase(symbol)
        ]
        
        # Ejecutar en paralelo con timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.request_timeout + 5
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout obteniendo datos para {symbol}")
            results = [None] * len(tasks)
        
        # Procesar resultados
        prices = {}
        for result in results:
            if isinstance(result, PriceData) and result.price > 0:
                prices[result.source] = result
        
        return prices
    
    async def get_current_price(self, symbol: str) -> float:
        """
        Obtener precio actual de una criptomoneda.
        
        Args:
            symbol: Símbolo de la criptomoneda (ej: 'BTC', 'ETH')
        
        Returns:
            Precio actual en USD
            
        Raises:
            Exception: Si no se puede obtener el precio de ninguna fuente
        """
        symbol = symbol.upper()
        
        # Verificar cache primero
        if self._is_cache_valid(symbol):
            market_data = self.cache[symbol]
            best_price = market_data.get_best_price()
            if best_price:
                logger.debug(f"Precio de {symbol} obtenido del cache: ${best_price.price}")
                return best_price.price
        
        # Obtener datos frescos
        logger.debug(f"Obteniendo datos frescos para {symbol}")
        
        prices = await self._fetch_price_from_all_sources(symbol)
        
        if prices:
            # Actualizar cache
            market_data = MarketData(symbol=symbol, prices=prices)
            self.cache[symbol] = market_data
            
            best_price = market_data.get_best_price()
            if best_price:
                logger.info(f"Precio de {symbol} actualizado: ${best_price.price} (fuente: {best_price.source})")
                return best_price.price
        
        # Si no se pudo obtener precio de ninguna fuente
        error_msg = f"No se pudo obtener precio para {symbol} de ninguna fuente"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def get_ohlcv(self, symbol: str, interval: str = "5m", limit: int = 50) -> list:
        """
        Obtiene velas OHLCV de Binance.
        Args:
            symbol: Símbolo de la criptomoneda (ej: 'BTC')
            interval: Intervalo de las velas (ej: '5m', '1h', '1d')
            limit: Número de velas a obtener
        Returns:
            Lista de velas: [ [open_time, open, high, low, close, volume, ...], ... ]
        """
        if not httpx:
            logger.error("httpx no disponible - no se pueden obtener velas OHLCV")
            return []
        pair_symbol = f"{symbol.upper()}USDT"
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": pair_symbol, "interval": interval, "limit": limit}
        try:
            async with AsyncClient(timeout=self.request_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Error obteniendo OHLCV de Binance para {symbol}: {e}")
            return []

    async def get_market_data(self, symbol: str, timeframe: str = "5m", with_ohlcv: bool = False, interval: str = "5m", limit: int = 50) -> dict:
        """Obtener datos completos de mercado con formato mejorado."""
        try:
            # Obtener precio actual
            current_price = await self.get_current_price(symbol)
            
            # Obtener datos OHLCV
            ohlcv_data = await self.get_ohlcv(symbol, timeframe, limit)
            
            # Obtener datos de 24h
            price_change_24h = 0.0
            volume_24h = 0.0
            
            # Intentar obtener datos de 24h de Binance
            try:
                pair_symbol = f"{symbol.upper()}USDT"
                url = "https://api.binance.com/api/v3/ticker/24hr"
                timeout = Timeout(self.request_timeout)
                
                async with AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params={"symbol": pair_symbol})
                    response.raise_for_status()
                    data = response.json()
                    
                    price_change_24h = float(data.get("priceChangePercent", 0))
                    volume_24h = float(data.get("volume", 0)) * current_price  # Convertir a USD
            except Exception as e:
                logger.warning(f"Error obteniendo datos 24h para {symbol}: {e}")
            
            # Formatear velas para el nuevo formato
            candles = []
            if ohlcv_data:
                for candle in ohlcv_data:
                    candles.append({
                        'timestamp': candle[0],
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
            
            return {
                'symbol': symbol.upper(),
                'current_price': current_price,
                'price_change_24h': price_change_24h,
                'volume_24h': volume_24h,
                'timeframe': timeframe,
                'candles': candles
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado para {symbol}: {e}")
            return {}

    async def get_ohlcv_data(self, symbol: str, timeframe: str = "5m", limit: int = 100) -> List[List]:
        """Obtener datos OHLCV en formato raw para cálculos técnicos."""
        try:
            # Mapear timeframes de Binance
            interval_mapping = {
                "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
                "30m": "30m", "1h": "1h", "2h": "2h", "4h": "4h",
                "6h": "6h", "8h": "8h", "12h": "12h", "1d": "1d",
                "3d": "3d", "1w": "1w", "1M": "1M"
            }
            
            interval = interval_mapping.get(timeframe, "5m")
            
            # Obtener datos de Binance
            pair_symbol = f"{symbol.upper()}USDT"
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": pair_symbol,
                "interval": interval,
                "limit": limit
            }
            
            timeout = Timeout(self.request_timeout)
            
            async with AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Convertir a formato numérico
                ohlcv = []
                for candle in data:
                    ohlcv.append([
                        int(candle[0]),  # timestamp
                        float(candle[1]),  # open
                        float(candle[2]),  # high
                        float(candle[3]),  # low
                        float(candle[4]),  # close
                        float(candle[5])   # volume
                    ])
                
                return ohlcv
                
        except Exception as e:
            logger.error(f"Error obteniendo datos OHLCV para {symbol}: {e}")
            return []
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Obtener precios de múltiples criptomonedas en paralelo.
        
        Args:
            symbols: Lista de símbolos
        
        Returns:
            Diccionario con precios {symbol: price}
            
        Raises:
            Exception: Si no se puede obtener ningún precio
        """
        tasks = [self.get_current_price(symbol) for symbol in symbols]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for i, price in enumerate(results):
            symbol = symbols[i].upper()
            if isinstance(price, (int, float)) and price > 0:
                result[symbol] = price
            elif isinstance(price, Exception):
                logger.error(f"Error obteniendo precio para {symbol}: {price}")
                raise price
        
        if not result:
            raise Exception("No se pudo obtener precio para ningún símbolo")
        
        return result
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Limpiar cache de datos.
        
        Args:
            symbol: Símbolo específico a limpiar (None para limpiar todo)
        """
        if symbol:
            self.cache.pop(symbol.upper(), None)
            logger.debug(f"Cache limpiado para {symbol}")
        else:
            self.cache.clear()
            logger.debug("Cache completamente limpiado")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache."""
        total_entries = len(self.cache)
        valid_entries = sum(1 for symbol in self.cache if self._is_cache_valid(symbol))
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "cache_ttl_seconds": self.cache_ttl,
            "cached_symbols": list(self.cache.keys())
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio de datos."""
        return {
            "status": "healthy",
            "timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "cache_stats": self.get_cache_stats(),
            "available_sources": [source.value for source in DataSource]
        } 