from src.providers.meteostat import MeteostatProvider
from src.providers.weatherapi import WeatherAPIProvider

PROVIDER_LIST = {
    "weatherapi": WeatherAPIProvider,
    "meteostat": MeteostatProvider,
}


def build_providers(names):
    providers = []
    for name in names:
        if name not in PROVIDER_LIST:
            raise ValueError(
                f"Unknown provider '{name}'"
            )
        providers.append(PROVIDER_LIST[name]())
    return providers