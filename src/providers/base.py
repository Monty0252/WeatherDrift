from abc import ABC, abstractmethod
from datetime import date
import time
import requests

from src.models import Location, WeatherData

class WeatherTemplate(ABC):

    # shared by all providers: retry transient failures
    # required get_daily_weather method
    
    name: str

    @abstractmethod
    def get_daily_weather(self, location: Location, target_date: date) -> WeatherData:
        raise NotImplementedError
    
    def retry_request(self, url, *, headers=None, params=None, retries=3):
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=60)
                if response.status_code in (401, 403):
                    raise ValueError(
                        f"Invalid or unauthorized API key ({response.status_code}). "
                        "Check your .env file."
                    )
                if response.status_code == 400:
                    raise ValueError(
                        f"{self.name}: bad request (400) — the date may be unavailable "
                        "or outside the supported range."
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)