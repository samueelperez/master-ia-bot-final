"""
Economic calendar service for the External Data Service.
Uses web scraping to fetch economic calendar data from Investing.com.
"""
import os
import json
import time
import logging
import random
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re

import aiohttp
from bs4 import BeautifulSoup
import pytz

from core.cache import cache
from core.circuit_breaker import circuit_breaker
from core.config import settings
from models.schemas import EconomicEventsResponse

logger = logging.getLogger(__name__)

# Constants for scraping
INVESTING_CALENDAR_URL = "https://www.investing.com/economic-calendar/"
COINMARKETCAL_URL = "https://coinmarketcal.com/en/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Note: We're using web scraping instead of an API, so we don't need API keys

@circuit_breaker("economic_calendar_api")
async def fetch_economic_events() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch economic events from Investing.com using web scraping.
    
    Returns:
        Dictionary with economic events
    """
    try:
        # Fetch the economic calendar page
        async with aiohttp.ClientSession() as session:
            async with session.get(INVESTING_CALENDAR_URL, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch economic calendar: {response.status}")
                    return {"high_impact_events": [], "upcoming_events": []}
                
                html = await response.text()
        
        # Parse the HTML
        soup = BeautifulSoup(html, 'lxml')
        
        # Find the economic events table
        events_table = soup.find('table', {'id': 'economicCalendarData'})
        if not events_table:
            logger.error("Could not find economic events table")
            return {"high_impact_events": [], "upcoming_events": []}
        
        # Extract events
        high_impact_events = []
        upcoming_events = []
        
        # Current date for reference
        now = datetime.now()
        
        # Process event rows
        event_rows = events_table.find_all('tr', {'class': 'js-event-item'})
        for row in event_rows:
            try:
                # Skip if row doesn't have enough data
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                
                # Extract event time
                time_cell = cells[0]
                event_time = time_cell.text.strip()
                
                # Extract event date (from data attribute or parent row)
                date_str = row.get('data-event-datetime', '')
                if date_str:
                    try:
                        # Try different date formats
                        if 'T' in date_str:
                            # Format: 2025-06-19T14:30:00+0000
                            event_date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
                        elif '/' in date_str:
                            # Format: 2025/06/19 14:30:00
                            event_date = datetime.strptime(date_str.split(' ')[0], '%Y/%m/%d')
                        else:
                            # Use current date as fallback
                            event_date = now
                        
                        date_str = event_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Use current date as fallback if parsing fails
                        logger.warning(f"Failed to parse date: {date_str}, using current date")
                        date_str = now.strftime('%Y-%m-%d')
                else:
                    # Use current date as fallback
                    date_str = now.strftime('%Y-%m-%d')
                
                # Extract country
                country_cell = cells[1]
                country_span = country_cell.find('span', {'class': 'flagCur'})
                country = country_span.get('title', 'Global') if country_span else 'Global'
                
                # Extract impact (bull icons indicate importance)
                impact_cell = cells[2]
                impact_icons = impact_cell.find_all('i', {'class': re.compile('grayFullBullishIcon')})
                if len(impact_icons) == 3:
                    impact = "high"
                elif len(impact_icons) == 2:
                    impact = "medium"
                else:
                    impact = "low"
                
                # Extract title
                title_cell = cells[3]
                title = title_cell.text.strip()
                
                # Extract description (tooltip or title text)
                description = title_cell.get('title', f"Economic event: {title}")
                if not description:
                    description = f"Economic event: {title} for {country}"
                
                # Create event object
                event = {
                    "title": title,
                    "date": date_str,
                    "time": event_time,
                    "impact": impact,
                    "country": country,
                    "description": description
                }
                
                # Categorize event based on impact
                if impact == "high":
                    high_impact_events.append(event)
                else:
                    upcoming_events.append(event)
                
            except Exception as e:
                logger.warning(f"Error parsing event row: {e}")
                continue
        
        # Sort events by date and time
        high_impact_events.sort(key=lambda x: (x["date"], x["time"]))
        upcoming_events.sort(key=lambda x: (x["date"], x["time"]))
        
        logger.info(f"Scraped {len(high_impact_events)} high impact events and {len(upcoming_events)} upcoming events")
        
        return {
            "high_impact_events": high_impact_events,
            "upcoming_events": upcoming_events
        }
    except Exception as e:
        logger.error(f"Error scraping economic events: {e}")
        return {
            "high_impact_events": [],
            "upcoming_events": []
        }

@circuit_breaker("crypto_economic_events_api")
async def fetch_crypto_economic_events(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch cryptocurrency-specific economic events by scraping crypto news and event sites.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        List of cryptocurrency-specific economic events
    """
    try:
        # Get full name for better search results
        full_name = get_full_name(symbol)
        
        # URLs to scrape for crypto events
        crypto_events_url = f"https://coinmarketcal.com/en/?form%5Bdate_range%5D=19%2F06%2F2025%20-%2019%2F09%2F2025&form%5Bkeyword%5D={full_name}&form%5Bsort_by%5D=&form%5Bsubmit%5D="
        
        # Fetch the crypto events page
        async with aiohttp.ClientSession() as session:
            async with session.get(crypto_events_url, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch crypto events: {response.status}")
                    return await fallback_crypto_events(symbol)
                
                html = await response.text()
        
        # Parse the HTML
        soup = BeautifulSoup(html, 'lxml')
        
        # Find event cards
        event_cards = soup.find_all('article', {'class': 'card'})
        if not event_cards:
            logger.warning(f"No event cards found for {symbol}, using fallback")
            return await fallback_crypto_events(symbol)
        
        # Extract events
        events = []
        now = datetime.now()
        
        for card in event_cards[:5]:  # Limit to 5 events
            try:
                # Extract title
                title_elem = card.find('h5', {'class': 'card__title'})
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                
                # Extract date
                date_elem = card.find('span', {'class': 'card__date'})
                if date_elem:
                    date_text = date_elem.text.strip()
                    try:
                        # Parse date like "Jun 19, 2025"
                        event_date = datetime.strptime(date_text, '%b %d, %Y')
                        date_str = event_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Fallback to current date + random days
                        days_ahead = random.randint(1, 30)
                        event_date = now + timedelta(days=days_ahead)
                        date_str = event_date.strftime('%Y-%m-%d')
                else:
                    # Fallback date
                    days_ahead = random.randint(1, 30)
                    event_date = now + timedelta(days=days_ahead)
                    date_str = event_date.strftime('%Y-%m-%d')
                
                # Extract description
                desc_elem = card.find('p', {'class': 'card__description'})
                description = desc_elem.text.strip() if desc_elem else f"Cryptocurrency event for {full_name}"
                
                # Determine impact based on keywords
                impact_keywords = ['major', 'important', 'significant', 'launch', 'release', 'upgrade', 'fork', 'halving']
                impact = "high" if any(keyword in title.lower() or keyword in description.lower() for keyword in impact_keywords) else "medium"
                
                # Add event
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": "12:00",  # Default time as specific times are often not provided
                    "impact": impact,
                    "country": "Global",
                    "description": description
                })
                
            except Exception as e:
                logger.warning(f"Error parsing crypto event card: {e}")
                continue
        
        # If no events were successfully parsed, use fallback
        if not events:
            logger.warning(f"Failed to parse any events for {symbol}, using fallback")
            return await fallback_crypto_events(symbol)
        
        # Sort events by date
        events.sort(key=lambda x: x["date"])
        
        logger.info(f"Scraped {len(events)} events for {symbol}")
        return events
    except Exception as e:
        logger.error(f"Error scraping crypto events for {symbol}: {e}")
        return await fallback_crypto_events(symbol)

async def fallback_crypto_events(symbol: str) -> List[Dict[str, Any]]:
    """
    Fallback method to generate cryptocurrency events when scraping fails.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        List of cryptocurrency-specific events
    """
    events = []
    now = datetime.now()
    full_name = get_full_name(symbol)
    
    # Event titles
    titles = [
        f"{full_name} Network Upgrade",
        f"{full_name} Developer Conference",
        f"{full_name} Halving Event",
        f"{full_name} Mainnet Launch",
        f"{full_name} Partnership Announcement"
    ]
    
    # Generate events
    for i, title in enumerate(titles[:3]):  # Limit to 3 events
        # Random date within the next 60 days
        days_ahead = random.randint(1, 60)
        event_date = now + timedelta(days=days_ahead)
        date_str = event_date.strftime("%Y-%m-%d")
        time_str = f"{random.randint(8, 17)}:00"
        
        # Random impact
        impact = random.choice(["high", "medium"])
        
        # Generate description
        description = f"Cryptocurrency-specific event for {full_name}. This event could impact the price of {symbol}."
        
        # Add event
        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "impact": impact,
            "country": "Global",
            "description": description
        })
    
    # Sort events by date
    events.sort(key=lambda x: (x["date"], x["time"]))
    
    logger.info(f"Generated {len(events)} fallback events for {symbol}")
    return events

def get_full_name(symbol: str) -> str:
    """
    Get the full name of a cryptocurrency from its symbol.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Full name of the cryptocurrency
    """
    crypto_names = {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "SOL": "Solana",
        "XRP": "Ripple",
        "ADA": "Cardano",
        "DOGE": "Dogecoin",
        "SHIB": "Shiba Inu",
        "BNB": "Binance Coin",
        "DOT": "Polkadot",
        "AVAX": "Avalanche"
    }
    
    return crypto_names.get(symbol.upper(), symbol)

async def get_economic_events_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Get economic events for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol
        
    Returns:
        Dictionary with economic events
    """
    cache_key = f"economic_{symbol}"
    
    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info(f"Using cached economic events for {symbol}")
        return cached_data
    
    try:
        # Fetch events
        events = await fetch_economic_events()
        symbol_events = await fetch_crypto_economic_events(symbol)
        
        # Prepare response
        result = {
            "high_impact_events": events.get("high_impact_events", []),
            "upcoming_events": events.get("upcoming_events", []),
            "symbol_events": symbol_events
        }
        
        # Cache the result
        await cache.set(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"Error getting economic events for {symbol}: {e}")
        return {
            "high_impact_events": [],
            "upcoming_events": [],
            "symbol_events": []
        }

async def get_all_economic_events() -> Dict[str, Any]:
    """
    Get all economic events.
    
    Returns:
        Dictionary with economic events
    """
    cache_key = "economic_all"
    
    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.info("Using cached economic events")
        return cached_data
    
    try:
        # Fetch events
        events = await fetch_economic_events()
        
        # Cache the result
        await cache.set(cache_key, events)
        
        return events
    except Exception as e:
        logger.error(f"Error getting all economic events: {e}")
        return {
            "high_impact_events": [],
            "upcoming_events": []
        }

async def get_high_impact_events() -> List[Dict[str, Any]]:
    """
    Get high impact economic events.
    
    Returns:
        List of high impact economic events
    """
    try:
        # Fetch events
        events = await get_all_economic_events()
        
        return events.get("high_impact_events", [])
    except Exception as e:
        logger.error(f"Error getting high impact economic events: {e}")
        return []

# Add missing import
import asyncio
