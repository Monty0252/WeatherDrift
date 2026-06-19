from src.providers.meteostat import MeteostatProvider
from src.providers.weatherapi import WeatherAPIProvider
from src.providers.base import WeatherTemplate

# registry maps config names -> provider classes. Adding a provider = one line here

PROVIDER_LIST = {
    "weatherapi": WeatherAPIProvider,
    "meteostat": MeteostatProvider,
}


def build_providers(names: list[str]) -> list[WeatherTemplate]:

    providers = []
    for name in names:
        if name not in PROVIDER_LIST:
            raise ValueError(
                f"Unknown provider '{name}'"
            )
        providers.append(PROVIDER_LIST[name]())
    return providers