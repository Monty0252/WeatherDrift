from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Location:
    """
    Represents an airport/location
    """
    code: str
    name: str
    latitude: float
    longitude: float
    altitude: Optional[int] = None


@dataclass(frozen=True)
class WeatherData:
    """
    Normalized daily weather data from any provider.

    Normalization decisions:
    - Temperature values come from each provider's daily summary.
    - Precipitation comes from each provider's daily summary.
    - Humidity is averaged from hourly observations.
    - Wind speed is calculated from hourly observations so average wind and max wind are comparable across providers.
    """
    location_code: str
    weather_date: date
    provider_name: str
    avg_temp_f: Optional[float]
    min_temp_f: Optional[float]
    max_temp_f: Optional[float]
    avg_humidity_percentage: Optional[float]
    avg_wind_speed_mph: Optional[float]
    max_wind_speed_mph: Optional[float]
    total_precipitation_inches: Optional[float]


@dataclass(frozen=True)
class MetricDrift:
    """
    Represents the difference for one weather metric between two sources.

    diff is calculated as:
        abs(source_a_value - source_b_value)

    If either value is missing, diff should be None.
    """

    metric: str
    source_a_value: Optional[float]
    source_b_value: Optional[float]
    diff: Optional[float]
    status: str


@dataclass(frozen=True)
class DriftReport:
    """
    Represents the full comparison result for one location and date.
    """
    location_code: str
    weather_date: date
    source_a: str
    source_b: str
    metrics: list[MetricDrift]