from pathlib import Path

import yaml

from src.models import Location

DEFAULT_CONFIG_PATH = "config.yaml"

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config


def load_locations(config: dict) -> list[Location]:

    locations = config.get("locations")

    if not locations:
        raise ValueError("Config must include at least one location.")

    return [
        Location(
            code=item["code"],
            name=item["name"],
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            altitude=item.get("altitude"),
        )
        for item in locations
    ]

def load_providers(config: dict) -> list[str]:
  
    names = config.get("providers")
    if not names:
        raise ValueError("Config must include at least one provider.")
    return names
