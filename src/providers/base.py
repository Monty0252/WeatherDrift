from abc import ABC, abstractmethod
from datetime import date

from src.models import Location, WeatherData

class WeatherTemplate(ABC):

    name: str

    @abstractmethod
    def get_daily_weather(self, location: Location, target_date: date) -> WeatherData:
        raise NotImplementedError