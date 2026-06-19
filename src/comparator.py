from src.models import DriftReport, MetricDrift, WeatherData

METRICS = [
    ("Average Temperature (F)", "avg_temp_f"),
    ("Minimum Temperature (F)", "min_temp_f"),
    ("Maximum Temperature (F)", "max_temp_f"),
    ("Average Humidity (%)", "avg_humidity_percentage"),
    ("Average Wind Speed (MPH)", "avg_wind_speed_mph"),
    ("Maximum Wind Speed (MPH)", "max_wind_speed_mph"),
    ("Total Precipitation (Inches)", "total_precipitation_inches"),
]


def calculate_diff(provider_a_value, provider_b_value):
    if provider_a_value is None or provider_b_value is None:
        return None

    return round(abs(provider_a_value - provider_b_value),2)

def drift_status(diff):
    if diff is None:
        return "Missing Data"
    return "Drift Detected" if diff != 0 else "OK"

def compare_weather_observations(provider_a: WeatherData, provider_b: WeatherData) -> DriftReport:

    metric_drifts = []

    for display_name, metric_name in METRICS:
        provider_a_value = getattr(provider_a, metric_name)
        provider_b_value = getattr(provider_b, metric_name)
        diff = calculate_diff(provider_a_value, provider_b_value)

        metric_drifts.append(
            MetricDrift(
                metric=display_name,
                source_a_value=provider_a_value,
                source_b_value=provider_b_value,
                diff=diff,
                status=drift_status(diff)
            )
        )

    return DriftReport(
        location_code=provider_a.location_code,
        weather_date=provider_a.weather_date,
        source_a=provider_a.provider_name,
        source_b=provider_b.provider_name,
        metrics=metric_drifts,
    )