
from datetime import date, datetime, timedelta
from pathlib import Path
from itertools import combinations
import argparse

from src.comparator import compare_weather_observations
from src.config_loader import load_config, load_locations, load_providers
from src.models import WeatherData, Location
from src.providers import build_providers
from src.reporting import create_csv_report
from src.providers.base import WeatherTemplate


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

def run_drift(target_date: date):
    
    """Run the full pipeline: fetch each provider, compare pairs, and write the report."""

    config = load_config()
    locations = load_locations(config)
    providers = build_providers(load_providers(config))
  
    report_data = []

    for location in locations:
        location_weather_data = []

        for provider in providers:
            daily_weather_data = safe_try(provider, location, target_date) 
            location_weather_data.append(daily_weather_data)

        for provider_a, provider_b in combinations(location_weather_data, 2):
            comparison = compare_weather_observations(provider_a, provider_b)
            report_data.append(comparison)

    output_file = Path(f"output/weather_drift_report_{target_date.isoformat()}.csv")
    create_csv_report(report_data, output_file)

    print(f"CSV report written to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to yesterday")
    args = parser.parse_args()

    target_date = (
        date.fromisoformat(args.date) if args.date
        else date.today() - timedelta(days=1)
    )

    print(f"Generating drift report for: {target_date}")
    run_drift(target_date)