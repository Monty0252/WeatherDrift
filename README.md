# Weather Drift Report

This application pulls daily weather data for a set of locations from different providers,
normalizes the data into a single schema, compares them metric by metric, and writes a CSV
"drift" report showing where the sources differ.

Additional locations and providers can be added with minimal code changes. The two providers
currently configured are:

- **WeatherAPI**
- **Meteostat** (via RapidAPI)
---
## Setup
**Requirements:** Python 3.9 or newer — download from https://www.python.org/downloads/
1. Clone the repository and change into the project root:

```bash
   git clone https://github.com/Monty0252/WeatherDrift.git
   cd WeatherDrift
```

     Or download the ZIP from GitHub, unzip it, and navigate to the root of the directory
   
2. (Optional but recommended) Create and activate a virtual environment. Skip if you can install dependencies on local machine.

```bash
   # Create the virtual environment (macOS, Linux, and Windows)
   python -m venv .venv

   # Activate it (Windows)
   .venv\Scripts\activate

   # Activate it (macOS / Linux)
   source .venv/bin/activate

   # If PowerShell blocks activation with a "running scripts is disabled" error, run the following:
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

   # Then run activate again
   .venv\Scripts\activate
   
```
3. Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
4. Provide API keys. Copy the example env file and fill in your keys:

```bash
    # Windows (PowerShell)
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env

   # Or manually duplicate .env.example and rename to .env

```

   Then open `.env` and add your keys:

```
   WEATHERAPI_KEY=your_key_here
   RAPIDAPI_KEY=your_key_here
```

   - `WEATHERAPI_KEY` — from https://www.weatherapi.com
   - `RAPIDAPI_KEY` — from https://rapidapi.com, subscribe to the Meteostat API
---
## How to run
From the project root:
```bash

# Run for yesterday's weather data (the default)
python -m src.main

# Run for a specific past date (recommended for a full comparison)
python -m src.main --date 2026-06-17

```
The tool writes a CSV named by the report date to the `output/`
directory, for example:

```
output/weather_drift_report_2026-06-17.csv
```

> **Note on recent dates:** Meteostat's daily endpoint may not be updated with
> yesterday's data — this is expected provider behavior, not a bug.
> If it happens, the missing provider's fields are left empty and the report is still
> generated; use `--date` with an earlier past date to get a fully populated comparison.
> See Assumptions for details.
---

## Design decisions

### Data model

Every provider's raw response is converted into one shared set of immutable (`frozen`)
dataclasses before the rest of the components access it:

- **`Location`** — a configured site (`code`, `name`, `latitude`, `longitude`, optional `altitude`).
- **`WeatherData`** — one provider's normalized daily weather: avg/min/max temperature (°F), avg humidity (%), avg/max wind (mph), total precipitation (inches).
- **`MetricDrift`** — one metric compared between two providers (both values, difference, status).
- **`DriftReport`** — the full result for one location/date.

Each provider is its own class (e.g. `WeatherAPIProvider`, `MeteostatProvider`) that extends a
shared `WeatherTemplate` base class. The base class holds the common logic (the request/retry
handling), and each provider implements `get_daily_weather`, which fetches its own data and maps
it into `WeatherData`. So every provider looks different on the inside but returns the same structure.

Decisions behind this model:

- **One shared schema.** Each provider maps its own response into `WeatherData`, so the comparator,
  reporter, and main logic only ever work with `WeatherData` and never deal with a raw JSON.
- **Add New Provider with minimal code changes.** Adding one takes three small steps: write a class that extends
  `WeatherTemplate` and implements `get_daily_weather` (mapping the new API's response into
  `WeatherData`), register it in `PROVIDER_LIST` with a config name, and add that name to the
  `providers:` list in `config.yaml`. Nothing else changes — the comparator and reporting read
  `WeatherData`, so they work with any number of providers unchanged, and shared request/retry
  logic is inherited from `WeatherTemplate`. All provider-specific code stays inside the new class.
- **Easy to add a location.** Locations come from config, so adding one is a config edit, not a
  code change.
- **`Optional` metrics.** A missing reading is kept as `None`, never turned into `0`, so
  "no data" stays separate from a real zero.

### Data Normalization

Each provider maps its response into `WeatherData` so everything compared is like-for-like. 

The key rule: for a given metric, every provider must derive it the same way. If one provider can only supply 
that metric by computing it from hourly data, then it's computed from hourly for all providers — so the comparison stays fair.

- **Taken directly (daily):** temperature (avg/min/max) and precipitation — both providers publish
  real daily values.
- **Computed (hourly mean) on both:** wind (avg + max) and humidity. WeatherAPI has no daily
  average wind (only max) and Meteostat has no daily humidity, so both are computed from hourly on
  each side. 

Meteostat’s daily and hourly data can differ because they may come from different nearby stations, 
so the chosen data source affects the final numbers. All values are converted to imperial units (°F, inches, mph, %) 
and rounded to each source’s precision — 1 decimal place for most values and 2 decimals for precipitation.

### Comparison & status

Comparison runs on a **pair** of providers; for more than two, every pair is compared
(`itertools.combinations`), so the comparator works for any number of providers with no change.

Each metric's difference is `round(abs(a - b), 2)` and rounded after subtracting, since subtracting two rounded values can 
still produce extra decimal places from floating-point math.
Status is **Missing Data**, **Drift Detected** (any difference),
or **OK**. It flags if rounded values are not exact. 

### Error handling — retry + boundary
Two layers: requests retry 3× with a short delay
if retries are exhausted, `safe_try` in `main` logs the failure and
substitutes an empty **`WeatherData`**, so those metrics show **Missing Data** and the run continues.
Missing values are blank CSV cells, never `0`.

### Project structure
```
config.yaml              # locations and active providers
.env              # env file holds API Keys = not commited to repo
src/
  main.py                # Pipeline: fetch data -> compare -> report
  config_loader.py       # loads locations and providers
  models.py              # Location, WeatherData, MetricDrift, DriftReport
  comparator.py          # pairwise comparison and drift status
  reporting.py           # CSV output
  utils.py               # numeric helpers
  providers/
    __init__.py          # Providers list and class initilization
    base.py              # WeatherTemplate (Template for provider classes) 
    weatherapi.py        # WeatherAPI implementation
    meteostat.py         # Meteostat implementation
output/                  # generated reports
```

## Assumptions
- **"Daily" means yesterday.** The tool reports on the most recent complete day
 (`today − 1`), since the current day is partial.
- **Locations are always identified by latitude/longitude** (with optional altitude) for any provider.
- **The tool assumes the locations and target date are within each provider's coverage.** If a provider has no data for the requested  location or date, the tool reports it per provider and continues.
- Meteostat's daily data is subject to a processing delay (per their documentation, typically 1–7 days), so the default date of yesterday may not yet be available.
- **API keys are supplied through `.env`.** The user must provide valid WeatherAPI and RapidAPI keys
   with access to the endpoints used by the application.
---
## Future improvements
- **Configurable drift thresholds** per metric (e.g. flag temperature only if it differs
 by more than 1°F), so the status reflects notable drift rather than any difference.
- **Parallel fetching.** Provider/location requests are independent and could be run
  in parallel to speed up larger runs. Worth implementing as locations and providers increase.
- **Automated tests** covering normalization, the comparator, the retry logic, and
 error handling.
- **Additional output formats** (JSON, Console output)



