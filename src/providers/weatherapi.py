import os
from datetime import date

from dotenv import load_dotenv

from src.models import Location, WeatherData
from src.providers.base import WeatherTemplate
from src.utils import average, get_values, round_value, safe_max

class WeatherAPIProvider(WeatherTemplate):
    """
    Weather provider implementation for WeatherAPI's history endpoint.
    """
    
    name = "WeatherAPI"
    base_url = "https://api.weatherapi.com/v1"

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("WEATHERAPI_KEY")

        if not self.api_key or self.api_key == "your_key_here":
            raise ValueError(
                "WEATHERAPI_KEY is missing or still the placeholder. Add your real key to .env."
            )
        
    def send_request(self, endpoint: str, parameters: dict) -> dict:

        url = f"{self.base_url}/{endpoint}"

        return self.retry_request(url, params=parameters)

    def get_daily_weather(self, location: Location, target_date: date) -> WeatherData:

        parameters = {
            "key": self.api_key,
            "q": f"{location.latitude},{location.longitude}",
            "dt": target_date.isoformat(),
        }

        endpoint = "history.json"

        response= self.send_request(endpoint, parameters)

        day_metrics, hourly_metrics = self.extract_weather_data(response)

        # wind and humidity are computed from hourly (not taken from the daily summary) so that both providers use the same basis 
        # WeatherAPI has no daily average wind, Meteostat has no daily humidity.

        hourly_humidity_values = get_values(hourly_metrics, "humidity")
        hourly_wind_values = get_values(hourly_metrics, "wind_mph")
       
        avg_humidity_percentage = average(hourly_humidity_values) 
        avg_wind_speed_mph = average(hourly_wind_values) 
        max_wind_speed_mph = safe_max(hourly_wind_values)

        return WeatherData(
            location_code = location.code,
            weather_date = target_date,
            provider_name = self.name,
            avg_temp_f = round_value(day_metrics.get("avgtemp_f")),
            min_temp_f = round_value(day_metrics.get("mintemp_f")),
            max_temp_f = round_value(day_metrics.get("maxtemp_f")),
            avg_humidity_percentage = round_value(avg_humidity_percentage),
            avg_wind_speed_mph = round_value(avg_wind_speed_mph),
            max_wind_speed_mph = round_value(max_wind_speed_mph),
            total_precipitation_inches = round_value(day_metrics.get("totalprecip_in"), 2)
        )
    
    def extract_weather_data(self, response: dict):
        
        try:
            forecast_day = response["forecast"]["forecastday"][0]
            return forecast_day["day"], forecast_day["hour"]

        except (KeyError, TypeError, IndexError) as exc:
            raise ValueError("Unexpected WeatherAPI response format.") from exc
