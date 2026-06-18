import os
from datetime import date

from dotenv import load_dotenv

from src.models import Location, WeatherData
from src.providers.base import WeatherTemplate
from src.utils import average, get_values, round_value, safe_max


class MeteostatProvider(WeatherTemplate):
    """Weather provider implementation for Meteostat."""

    name = "Meteostat"
    base_url = "https://meteostat.p.rapidapi.com"
    rapidapi_host = "meteostat.p.rapidapi.com"

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("RAPIDAPI_KEY")

        if not self.api_key:
            raise ValueError("Missing RAPIDAPI_KEY variable.")
        
    def send_request(self, endpoint, parameters):

        url = f"{self.base_url}/{endpoint}"

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.rapidapi_host,
            "Content-Type": "application/json",
        }

        return self.retry_request(url, headers=headers, params=parameters)

    def get_daily_weather(self, location: Location, target_date: date):

        parameters = {
            "lat": location.latitude,
            "lon": location.longitude,
            "start": target_date.isoformat(),
            "end": target_date.isoformat(),
            "units": "imperial",
        }

        if location.altitude is not None:
            parameters["alt"] = location.altitude

        daily_response = self.send_request("point/daily", parameters)
        hourly_response = self.send_request("point/hourly", parameters)

        day_metrics = self.extract_daily_data(daily_response)
        hourly_metrics = self.extract_hourly_data(hourly_response)

        hourly_humidity_values = get_values(hourly_metrics, "rhum")
        hourly_wind_values = get_values(hourly_metrics, "wspd")

        avg_humidity_percentage = average(hourly_humidity_values) 
        avg_wind_speed_mph = average(hourly_wind_values) 
        max_wind_speed_mph = safe_max(hourly_wind_values)

        return WeatherData(
            location_code = location.code,
            weather_date = target_date,
            provider_name = self.name,
            avg_temp_f = round_value(day_metrics.get("tavg")),
            min_temp_f = round_value(day_metrics.get("tmin")),
            max_temp_f = round_value(day_metrics.get("tmax")),
            avg_humidity_percentage = round_value(avg_humidity_percentage),
            avg_wind_speed_mph= round_value(avg_wind_speed_mph),
            max_wind_speed_mph= round_value(max_wind_speed_mph),
            total_precipitation_inches = round_value(day_metrics.get("prcp"), 2),
        )

    def extract_daily_data(self, response_data):
        try:
            return response_data["data"][0]

        except (KeyError, TypeError, IndexError) as exc:
            raise ValueError("Unexpected Meteostat daily response format.") from exc


    def extract_hourly_data(self, response_data):
        try:
            return response_data["data"]

        except (KeyError, TypeError) as exc:
            raise ValueError("Unexpected Meteostat hourly response format.") from exc

