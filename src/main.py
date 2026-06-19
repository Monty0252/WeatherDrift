
from datetime import date, datetime, timedelta
from pathlib import Path
from itertools import combinations

from src.comparator import compare_weather_observations
from src.config_loader import load_config, load_locations, load_providers
from src.models import WeatherData, Location
from src.providers import build_providers
from src.reporting import create_csv_report
from src.providers.base import WeatherTemplate


OUTPUT_FILE = Path(f"output/weather_drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

def get_target_date():
    return date.today() - timedelta(days=1)

def safe_try(provider: WeatherTemplate, location: Location, target_date: date) -> WeatherData:

    """Fetch a provider's weather, returning an empty observation if the fetch fails."""

    try:
        return provider.get_daily_weather(location, target_date)
    except Exception as exc:
        print(f"WARNING: {provider.name} failed for {location.code}: {exc}")
        return WeatherData(
            location_code=location.code,
            weather_date=target_date,
            provider_name=provider.name,
            avg_temp_f=None,
            min_temp_f=None,
            max_temp_f=None,
            avg_humidity_percentage=None,
            avg_wind_speed_mph=None,
            max_wind_speed_mph=None,
            total_precipitation_inches=None,
        )

def run_drift():
    
    """Run the full pipeline: fetch each provider, compare pairs, and write the report."""

    config = load_config()
    locations = load_locations(config)
    providers = build_providers(load_providers(config))
    target_date = get_target_date()

    report_data = []

    for location in locations:
        location_weather_data = []

        for provider in providers:
            daily_weather_data = safe_try(provider, location, target_date) 
            location_weather_data.append(daily_weather_data)

        for provider_a, provider_b in combinations(location_weather_data, 2):
            comparison = compare_weather_observations(provider_a, provider_b)
            report_data.append(comparison)

    create_csv_report(report_data, OUTPUT_FILE)

    print(f"CSV report written to: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_drift()