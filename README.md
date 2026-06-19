# Weather Drift Report
This application pulls daily weather data for a set of locations from
different providers, normalizes data into a single schema, compares them metric
by metric, and writes a CSV "drift" report showing where the sources differ.
The two providers currently configured are **WeatherAPI** and **Meteostat** (via
RapidAPI). Additional locations and providers can be added with minimal code changes.
The current implementation compares data from:

WeatherAPI /
Meteostat
---
## Setup
**Requirements:** Python 3.9 or newer.
1. Clone or unzip the project and change into the project root (the folder containing
  `config.yaml` and the `src/` directory).
2. (Recommended) Create and activate a virtual environment:
  ```bash
  python -m venv .venv
  # Windows
  .venv\Scripts\activate
  # macOS / Linux
  source .venv/bin/activate
  ```
3. Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
4. Provide API keys. The tool reads two keys from a `.env` file in the project root:
  ```
  WEATHERAPI_KEY=your_weatherapi_key
  RAPIDAPI_KEY=your_rapidapi_key
  ```
  - `WEATHERAPI_KEY` — from https://www.weatherapi.com (free tier includes history).
  - `RAPIDAPI_KEY` — from https://rapidapi.com, subscribed to the Meteostat API.
  `.env` is listed in `.gitignore` and should never be committed.
---
## How to run
From the project root:
```bash
python -m src.main
```
The tool fetches weather for **yesterday** (the most recent complete day) for every
location in `config.yaml`, compares every pair of providers, and writes a timestamped
CSV to the `output/` directory, for example:
```
output/weather_drift_report_20260618_020002.csv
```
---
## Design decisions

### Data model

Every provider's raw response is converted into one shared set of immutable (`frozen`)
dataclasses before the rest of the system sees it:

- **`Location`** — a configured site (`code`, `name`, `latitude`, `longitude`, optional `altitude`).
- **`WeatherData`** — one provider's normalized daily weather: avg/min/max temperature (°F), avg humidity (%), avg/max wind (mph), total precipitation (inches).
- **`MetricDrift`** — one metric compared between two providers (both values, difference, status).
- **`DriftReport`** — the full result for one location/date.

Each provider is its own class (e.g. `WeatherAPIProvider`, `MeteostatProvider`) that extends a
shared `WeatherTemplate` base class. The base class holds the common logic (the request/retry
handling), and each provider implements `get_daily_weather`, which fetches its own data and maps
it into `WeatherData`. So every provider looks different on the inside but returns the same thing.

Decisions behind this model:

- **One shared schema.** Each provider maps its own response into `WeatherData`, so the comparator,
  reporter, and orchestration only ever work with `WeatherData` and never deal with raw provider JSON.
- **Easy to add a provider.** Every provider returns the same `WeatherData`, so a new one only maps
  its response into that schema — the comparator and reporting read `WeatherData` and work with it
  unchanged. Provider-specific code stays in the provider class, and shared request/retry logic is
  inherited from `WeatherTemplate`.
- **Easy to add a location.** Locations come from config, so adding one is a config edit, not a
  code change.
- **`Optional` metrics.** A missing reading is kept as `None`, never faked or turned into `0`, so
  "no data" stays separate from a real zero.

### Data Normalization

Each provider maps its response into `WeatherData` so everything compared is like-for-like. The
key rule: both providers must derive a metric the same way. Comparing one provider's daily average
against another's hourly value measures the *method*, not the weather — so each metric uses the
same basis on both sides.

- **Taken directly (daily):** temperature (avg/min/max) and precipitation — both providers publish
  real daily values.
- **Computed (hourly mean) on both:** wind (avg + max) and humidity. WeatherAPI has no daily
  average wind (only max) and Meteostat has no daily humidity, so both are computed from hourly on
  each side. Meteostat's daily `wspd` is not used, since WeatherAPI has no daily average to match it.

Meteostat's daily and hourly data don't reconcile (different stations), so the basis changes the
numbers. All values are imperial (°F, inches, mph, %) and rounded to source precision — 1 decimal,
2 for precipitation.

### Comparison & status

Comparison runs on a **pair** of providers; for more than two, every pair is compared
(`itertools.combinations`), so the comparator works for any number of providers with no change.

Each metric's difference is `round(abs(a - b), 2)` — absolute (magnitude, not direction) and
rounded *after* subtracting, since subtracting rounded floats can still leave noise
(e.g. `65.9 - 67.3` → `1.3999…`). Status is **Missing Data**, **Drift Detected** (any difference),
or **OK**. It flags any difference rather than using a threshold — a sensible default for an audit
report; thresholds are a future improvement.

### Error handling — retry + boundary
Two layers: requests retry 3× with a short delay (`retry_request`, base class) for transient
blips and rate limits; if retries are exhausted, `safe_try` in `main` logs the failure and
substitutes an empty observation, so those metrics show **Missing Data** and the run continues.
Missing values are blank CSV cells, never `0`.

### Project structure
```
config.yaml              # locations and active providers
src/
  main.py                # orchestration: fetch -> compare -> report
  config_loader.py       # loads locations and providers
  models.py              # Location, WeatherData, MetricDrift, DriftReport
  comparator.py          # pairwise comparison and drift status
  reporting.py           # CSV output
  utils.py               # numeric helpers
  providers/
    __init__.py          # provider registry + build_providers
    base.py              # WeatherTemplate base + shared retry
    weatherapi.py        # WeatherAPI implementation
    meteostat.py         # Meteostat implementation
output/                  # generated reports (created at runtime)
```











## Assumptions
- **"Daily" means yesterday.** The tool reports on the most recent complete day
 (`today − 1`), since the current day is partial.
- **Both providers' daily summaries are authoritative for temperature and
 precipitation.** Where a provider's daily and hourly data disagree, the daily figure
 is treated as that provider's reported daily value.
- **Values are normalized to each provider's reported precision** — generally one decimal
 place, two for precipitation — and this rounded value is treated as canonical for
 comparison.
- **A missing value is genuinely missing, not zero.** Null fields (e.g. a daily
 precipitation field that is absent) are kept as missing rather than coerced to `0`.
- **Locations are identified by latitude/longitude** (with optional altitude for
 Meteostat), not by station ID, so each provider resolves the nearest station(s) itself.
- **API keys are supplied via `.env`** and the user has access to both services'
 required tiers (WeatherAPI history, RapidAPI Meteostat subscription).
---
## Future improvements
- **Configurable drift thresholds** per metric (e.g. flag temperature only if it differs
 by more than 1°F), so the status reflects meaningful drift rather than any difference.
- **Parallel fetching.** Provider/location requests are independent and could be run
 concurrently to speed up larger runs.
- **Automated tests** covering normalization, the comparator, the retry logic, and the
 error boundary.
- **Additional output formats** (JSON, or a formatted spreadsheet) alongside CSV.



