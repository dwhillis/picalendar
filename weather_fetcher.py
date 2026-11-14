"""
Weather Fetcher - Fetch weather data from Open-Meteo API
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import requests
import time

logger = logging.getLogger(__name__)


@dataclass
class CurrentWeather:
    """Current weather conditions"""
    temperature: float
    weather_code: int
    condition: str
    
    @property
    def icon(self) -> str:
        """Get weather icon character"""
        return get_weather_icon(self.weather_code)


@dataclass
class DayForecast:
    """Weather forecast for a single day"""
    date: datetime
    day_name: str
    temp_max: float
    temp_min: float
    weather_code: int
    condition: str
    
    @property
    def icon(self) -> str:
        """Get weather icon character"""
        return get_weather_icon(self.weather_code)


@dataclass
class WeatherData:
    """Complete weather data"""
    current: CurrentWeather
    forecast: List[DayForecast]
    location_name: str
    units: str


WEATHER_DESCRIPTIONS = {
    0: 'Clear',
    1: 'Mostly Clear',
    2: 'Partly Cloudy',
    3: 'Cloudy',
    45: 'Foggy',
    48: 'Foggy',
    51: 'Light Drizzle',
    53: 'Drizzle',
    55: 'Heavy Drizzle',
    61: 'Light Rain',
    63: 'Rain',
    65: 'Heavy Rain',
    71: 'Light Snow',
    73: 'Snow',
    75: 'Heavy Snow',
    77: 'Snow Grains',
    80: 'Light Showers',
    81: 'Showers',
    82: 'Heavy Showers',
    85: 'Light Snow Showers',
    86: 'Snow Showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm',
    99: 'Thunderstorm'
}


def get_weather_description(code: int) -> str:
    """Get human-readable weather description from code"""
    return WEATHER_DESCRIPTIONS.get(code, 'Unknown')


def get_weather_icon(code: int) -> str:
    """Get weather icon character from code"""
    if code == 0 or code == 1:
        return '☀'
    if code == 2:
        return '⛅'
    if code == 3:
        return '☁'
    if code in (45, 48):
        return '🌫'
    if 51 <= code <= 55:
        return '🌦'
    if 61 <= code <= 65:
        return '🌧'
    if 71 <= code <= 77:
        return '❄'
    if 80 <= code <= 82:
        return '🌧'
    if 85 <= code <= 86:
        return '🌨'
    if 95 <= code <= 99:
        return '⛈'
    return '?'


class WeatherFetcher:
    """Fetches weather data from Open-Meteo API"""

    API_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, latitude: float, longitude: float,
                 location_name: str = "", units: str = "celsius",
                 timeout: int = 30, retries: int = 3, retry_delay: float = 2.0):
        """Fetch weather with on-disk fallback.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            location_name: Human-readable location name
            units: Temperature units ('celsius' or 'fahrenheit')
            timeout: Request timeout in seconds
            retries: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        from pathlib import Path as _Path
        self.latitude = latitude
        self.longitude = longitude
        self.location_name = location_name
        self.units = units
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self._last_used_cache = False
        self.cache_path = _Path("/tmp/picalendar_cache_weather.json")
    
    def fetch_weather(self) -> Optional[WeatherData]:
        """Fetch current weather and forecast
        
        Returns:
            WeatherData object or None on error
        """
        temp_unit = 'celsius' if self.units == 'celsius' else 'fahrenheit'
        
        params = {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'current': 'temperature_2m,weather_code',
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min',
            'temperature_unit': temp_unit,
            'timezone': 'auto',
            'forecast_days': 5
        }
        
        logger.info(f"Fetching weather for {self.location_name}...")
        
        last_error = None
        for attempt in range(self.retries):
            try:
                response = requests.get(self.API_URL, params=params, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()
                try:
                    self.cache_path.write_text(__import__("json").dumps(data))
                except Exception as e:
                    logger.warning(f"Failed to write weather cache: {e}")
                self._last_used_cache = False
                return self._parse_response(data)

            except requests.RequestException as e:
                last_error = e
                if attempt < self.retries - 1:
                    logger.warning(f"Weather fetch attempt {attempt + 1}/{self.retries} failed: {e}. Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch weather after {self.retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Error parsing weather data: {e}")
                return None

        # All retries failed: try cache so layout does not collapse
        try:
            if self.cache_path.exists():
                import json as _json
                data = _json.loads(self.cache_path.read_text())
                logger.info("Using cached weather data")
                self._last_used_cache = True
                return self._parse_response(data)
        except Exception as e:
            logger.warning(f"Failed to load weather cache: {e}")
        self._last_used_cache = True
        return None
    
    def _parse_response(self, data: dict) -> WeatherData:
        """Parse Open-Meteo API response
        
        Args:
            data: JSON response from API
            
        Returns:
            WeatherData object
        """
        # Parse current weather
        current_temp = round(data['current']['temperature_2m'])
        current_code = data['current']['weather_code']
        
        current = CurrentWeather(
            temperature=current_temp,
            weather_code=current_code,
            condition=get_weather_description(current_code)
        )
        
        # Parse forecast (skip today, get next 4 days)
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        forecast = []
        
        for i in range(1, 5):  # Days 1-4 (skip today at index 0)
            date = datetime.fromisoformat(data['daily']['time'][i])
            day_name = days[date.weekday() + 1] if date.weekday() < 6 else days[0]
            # Fix: use proper weekday mapping
            day_name = days[date.isoweekday() % 7]
            
            forecast.append(DayForecast(
                date=date,
                day_name=day_name,
                temp_max=round(data['daily']['temperature_2m_max'][i]),
                temp_min=round(data['daily']['temperature_2m_min'][i]),
                weather_code=data['daily']['weather_code'][i],
                condition=get_weather_description(data['daily']['weather_code'][i])
            ))
        
        return WeatherData(
            current=current,
            forecast=forecast,
            location_name=self.location_name,
            units=self.units
        )
