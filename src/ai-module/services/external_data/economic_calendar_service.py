"""
Servicio para obtener eventos económicos del calendario de Investing.com y ForexFactory.
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes
CACHE_DURATION = 3600  # 1 hora en segundos
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "economic_calendar_cache.json")

class EconomicCalendarService:
    """Servicio para obtener eventos económicos del calendario."""
    
    def __init__(self):
        """Inicializa el servicio de calendario económico."""
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Carga el caché de eventos económicos desde el archivo."""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                    # Verificar si el caché ha expirado
                    if time.time() - cache.get("timestamp", 0) < CACHE_DURATION:
                        logger.info("Caché de eventos económicos cargado correctamente")
                        return cache
                    else:
                        logger.info("Caché de eventos económicos expirado")
            return {"timestamp": 0, "events": {}}
        except Exception as e:
            logger.error(f"Error al cargar el caché de eventos económicos: {e}")
            return {"timestamp": 0, "events": {}}
    
    def _save_cache(self) -> None:
        """Guarda el caché de eventos económicos en el archivo."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
            logger.info("Caché de eventos económicos guardado correctamente")
        except Exception as e:
            logger.error(f"Error al guardar el caché de eventos económicos: {e}")
    
    async def get_investing_events(self, days: int = 3) -> List[Dict[str, Any]]:
        """
        Obtiene eventos económicos del calendario de Investing.com.
        
        Args:
            days: Número de días para obtener eventos (por defecto 3)
            
        Returns:
            Lista de eventos económicos
        """
        cache_key = f"investing_{days}"
        
        # Verificar si hay eventos en caché y no han expirado
        if (cache_key in self.cache["events"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info(f"Usando eventos de Investing.com en caché para {days} días")
            return self.cache["events"][cache_key]
        
        events = []
        
        # Intentar obtener eventos de Investing.com
        try:
            # En una implementación real, se haría scraping de Investing.com
            # Aquí simulamos los eventos
            today = datetime.now()
            
            # Eventos simulados para los próximos días
            simulated_events = [
                {
                    "title": "Decisión de Tipos de Interés de la FED",
                    "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "time": "14:00",
                    "country": "Estados Unidos",
                    "impact": "high",
                    "forecast": "5.25%",
                    "previous": "5.25%"
                },
                {
                    "title": "IPC de Estados Unidos",
                    "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "time": "08:30",
                    "country": "Estados Unidos",
                    "impact": "high",
                    "forecast": "3.2%",
                    "previous": "3.4%"
                },
                {
                    "title": "PIB de la Eurozona",
                    "date": today.strftime("%Y-%m-%d"),
                    "time": "10:00",
                    "country": "Eurozona",
                    "impact": "medium",
                    "forecast": "0.3%",
                    "previous": "0.2%"
                },
                {
                    "title": "Ventas Minoristas de China",
                    "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                    "time": "03:00",
                    "country": "China",
                    "impact": "medium",
                    "forecast": "3.5%",
                    "previous": "3.1%"
                },
                {
                    "title": "Decisión de Tipos de Interés del BCE",
                    "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "time": "13:45",
                    "country": "Eurozona",
                    "impact": "high",
                    "forecast": "4.25%",
                    "previous": "4.25%"
                }
            ]
            
            # Filtrar eventos para los días solicitados
            for event in simulated_events:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                if (event_date - today).days < days:
                    events.append(event)
            
            logger.info(f"Simulados {len(events)} eventos de Investing.com")
        except Exception as e:
            logger.error(f"Error al simular eventos de Investing.com: {e}")
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["events"][cache_key] = events
        self._save_cache()
        
        return events
    
    async def get_forexfactory_events(self, days: int = 3) -> List[Dict[str, Any]]:
        """
        Obtiene eventos económicos del calendario de ForexFactory.
        
        Args:
            days: Número de días para obtener eventos (por defecto 3)
            
        Returns:
            Lista de eventos económicos
        """
        cache_key = f"forexfactory_{days}"
        
        # Verificar si hay eventos en caché y no han expirado
        if (cache_key in self.cache["events"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info(f"Usando eventos de ForexFactory en caché para {days} días")
            return self.cache["events"][cache_key]
        
        events = []
        
        # Intentar obtener eventos de ForexFactory
        try:
            # En una implementación real, se haría scraping de ForexFactory
            # Aquí simulamos los eventos
            today = datetime.now()
            
            # Eventos simulados para los próximos días
            simulated_events = [
                {
                    "title": "Tasa de Desempleo de EE.UU.",
                    "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "time": "08:30",
                    "country": "USD",
                    "impact": "high",
                    "forecast": "3.9%",
                    "previous": "3.8%"
                },
                {
                    "title": "Declaraciones de Powell",
                    "date": today.strftime("%Y-%m-%d"),
                    "time": "15:00",
                    "country": "USD",
                    "impact": "high",
                    "forecast": "",
                    "previous": ""
                },
                {
                    "title": "Índice de Precios al Productor de EE.UU.",
                    "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "time": "08:30",
                    "country": "USD",
                    "impact": "medium",
                    "forecast": "0.2%",
                    "previous": "0.3%"
                },
                {
                    "title": "Ventas Minoristas de Reino Unido",
                    "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                    "time": "09:30",
                    "country": "GBP",
                    "impact": "medium",
                    "forecast": "0.3%",
                    "previous": "-0.1%"
                },
                {
                    "title": "PMI Manufacturero de Japón",
                    "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "time": "01:30",
                    "country": "JPY",
                    "impact": "medium",
                    "forecast": "49.5",
                    "previous": "49.2"
                }
            ]
            
            # Filtrar eventos para los días solicitados
            for event in simulated_events:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                if (event_date - today).days < days:
                    events.append(event)
            
            logger.info(f"Simulados {len(events)} eventos de ForexFactory")
        except Exception as e:
            logger.error(f"Error al simular eventos de ForexFactory: {e}")
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["events"][cache_key] = events
        self._save_cache()
        
        return events
    
    async def get_crypto_specific_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtiene eventos específicos de criptomonedas.
        
        Args:
            days: Número de días para obtener eventos (por defecto 7)
            
        Returns:
            Lista de eventos de criptomonedas
        """
        cache_key = f"crypto_events_{days}"
        
        # Verificar si hay eventos en caché y no han expirado
        if (cache_key in self.cache["events"] and 
            time.time() - self.cache.get("timestamp", 0) < CACHE_DURATION):
            logger.info(f"Usando eventos de criptomonedas en caché para {days} días")
            return self.cache["events"][cache_key]
        
        events = []
        
        # Intentar obtener eventos de criptomonedas
        try:
            # En una implementación real, se obtendrían de alguna API o mediante scraping
            # Aquí simulamos los eventos
            today = datetime.now()
            
            # Eventos simulados para los próximos días
            simulated_events = [
                {
                    "title": "Actualización de Ethereum",
                    "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                    "description": "Actualización importante de la red Ethereum",
                    "impact": "high",
                    "coins": ["ETH"]
                },
                {
                    "title": "Conferencia Bitcoin 2023",
                    "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "description": "Conferencia anual de Bitcoin con posibles anuncios importantes",
                    "impact": "medium",
                    "coins": ["BTC"]
                },
                {
                    "title": "Lanzamiento de Solana DeFi",
                    "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                    "description": "Lanzamiento de nueva plataforma DeFi en Solana",
                    "impact": "medium",
                    "coins": ["SOL"]
                },
                {
                    "title": "Audiencia del Congreso sobre Regulación Cripto",
                    "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "description": "El Congreso de EE.UU. discutirá nuevas regulaciones para criptomonedas",
                    "impact": "high",
                    "coins": ["BTC", "ETH", "SOL", "XRP"]
                },
                {
                    "title": "Listado de Nuevos Tokens en Binance",
                    "date": today.strftime("%Y-%m-%d"),
                    "description": "Binance listará nuevos tokens en su plataforma",
                    "impact": "medium",
                    "coins": ["BNB"]
                }
            ]
            
            # Filtrar eventos para los días solicitados
            for event in simulated_events:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                if (event_date - today).days < days:
                    events.append(event)
            
            logger.info(f"Simulados {len(events)} eventos de criptomonedas")
        except Exception as e:
            logger.error(f"Error al simular eventos de criptomonedas: {e}")
        
        # Actualizar caché
        self.cache["timestamp"] = time.time()
        self.cache["events"][cache_key] = events
        self._save_cache()
        
        return events

# Instancia global del servicio
calendar_service = EconomicCalendarService()

async def get_economic_events(days: int = 3) -> Dict[str, Any]:
    """
    Obtiene eventos económicos de varias fuentes.
    
    Args:
        days: Número de días para obtener eventos (por defecto 3)
        
    Returns:
        Diccionario con eventos económicos
    """
    try:
        # Obtener eventos de Investing.com
        investing_events = await calendar_service.get_investing_events(days)
        
        # Obtener eventos de ForexFactory
        forexfactory_events = await calendar_service.get_forexfactory_events(days)
        
        # Obtener eventos específicos de criptomonedas
        crypto_events = await calendar_service.get_crypto_specific_events(days)
        
        # Clasificar eventos por impacto
        high_impact_events = []
        medium_impact_events = []
        
        for event in investing_events + forexfactory_events:
            if event.get("impact") == "high":
                high_impact_events.append(event)
            elif event.get("impact") == "medium":
                medium_impact_events.append(event)
        
        # Ordenar eventos por fecha
        high_impact_events.sort(key=lambda x: x.get("date", "") + " " + x.get("time", ""))
        medium_impact_events.sort(key=lambda x: x.get("date", "") + " " + x.get("time", ""))
        crypto_events.sort(key=lambda x: x.get("date", ""))
        
        return {
            "high_impact_events": high_impact_events[:5],  # Limitar a 5 eventos de alto impacto
            "medium_impact_events": medium_impact_events[:5],  # Limitar a 5 eventos de impacto medio
            "crypto_events": crypto_events[:5]  # Limitar a 5 eventos de criptomonedas
        }
    except Exception as e:
        logger.error(f"Error al obtener eventos económicos: {e}")
        return {
            "high_impact_events": [],
            "medium_impact_events": [],
            "crypto_events": []
        }

async def get_events_for_symbol(symbol: str, days: int = 7) -> Dict[str, Any]:
    """
    Obtiene eventos económicos relevantes para una criptomoneda específica.
    
    Args:
        symbol: Símbolo de la criptomoneda
        days: Número de días para obtener eventos (por defecto 7)
        
    Returns:
        Diccionario con eventos relevantes
    """
    try:
        # Obtener todos los eventos
        all_events = await get_economic_events(days)
        
        # Obtener eventos específicos de criptomonedas
        crypto_events = await calendar_service.get_crypto_specific_events(days)
        
        # Filtrar eventos específicos para el símbolo
        symbol_events = []
        for event in crypto_events:
            if symbol in event.get("coins", []):
                symbol_events.append(event)
        
        # Ordenar eventos por fecha
        symbol_events.sort(key=lambda x: x.get("date", ""))
        
        return {
            "symbol_events": symbol_events,  # Eventos específicos para el símbolo
            "high_impact_events": all_events["high_impact_events"],  # Eventos de alto impacto general
            "medium_impact_events": all_events["medium_impact_events"][:3]  # Limitar a 3 eventos de impacto medio
        }
    except Exception as e:
        logger.error(f"Error al obtener eventos para {symbol}: {e}")
        return {
            "symbol_events": [],
            "high_impact_events": [],
            "medium_impact_events": []
        }
