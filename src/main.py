
from datetime import date, datetime, timedelta
from pathlib import Path
from itertools import combinations

from src.comparator import compare_weather_observations
from src.config_loader import load_config, load_locations
from src.models import DriftReport
from src.providers.meteostat import MeteostatProvider
from src.providers.weatherapi import WeatherAPIProvider
from src.reporting import create_csv_report


OUTPUT_FILE = Path(f"output/weather_drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

def get_target_date():
    return date.today() - timedelta(days=1)

def get_providers():
    return [
        WeatherAPIProvider(),
        MeteostatProvider(),
    ]

def run_drift():
    config = load_config()
    locations = load_locations(config)
    providers = get_providers()
    target_date = get_target_date()

    report_data = []

    for location in locations:
        location_weather_data = []

        for provider in providers:
            daily_weather_data = provider.get_daily_weather(location, target_date)
            location_weather_data.append(daily_weather_data)

        for providerA, providerB in combinations(location_weather_data, 2):
            comparison = compare_weather_observations(providerA, providerB)
            report_data.append(comparison)

    create_csv_report(report_data, OUTPUT_FILE)

    print(f"CSV report written to: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_drift()