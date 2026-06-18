# Weather Drift Report
This application pulls daily weather data for a set of locations from
different providers, normalizes data into a single schema, compares them metric
by metric, and writes a CSV "drift" report showing where the sources differ.
The two providers currently configured are **WeatherAPI** and **Meteostat** (via
RapidAPI). Additional locations and providers can be added with minimal code changes.
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
### Configuration
Both the locations and the active providers are config-driven (`config.yaml`). Adding or removing a location, or changing which providers run, requires only a config
edit — no code changes.
```yaml
locations:
 - code: DTW
   name: Detroit Metropolitan Wayne County Airport
   latitude: 42.2162
   longitude: -83.3554
   altitude: 197
providers:
 - weatherapi
 - meteostat
```
---
## Design decisions
### Normalization: match the comparison basis per metric
The two providers portray their data differently, so 
field-to-field comparison would report differences that are really *aggregation
artifacts* rather than real disagreement. The guiding principle is **whatever method is
used for a metric, the same method is used on both providers**, so a reported difference
reflects genuine drift.
Inspecting real responses for DTW and ATL drove these rules:
- **Temperature (avg / min / max)** — taken from each provider's **daily** summary.
 Both providers publish real daily temperature fields, so these are directly
 comparable.
- **Precipitation** — taken from each provider's **daily** total. Both publish a daily
 precipitation field.
- **Wind (average and max)** — computed from each provider's **hourly** series on both
 sides. WeatherAPI's daily summary exposes only a *max* wind, not a daily average, so an
 average must be computed from hourly data; to keep the comparison like-for-like,
 Meteostat's wind is computed from hourly too. (Meteostat's daily `wspd` is intentionally
 not used, because there is no equivalent daily average on the WeatherAPI side to compare
 it against.)
- **Humidity** — computed from each provider's **hourly** mean on both sides. Meteostat's
 daily summary has no humidity field, so it is computed from hourly; WeatherAPI's humidity
 is computed the same way for parity.
A further observation from the data: Meteostat's daily summary and its hourly series do
not always reconcile (they are sourced from different underlying stations), so the choice
of basis is not cosmetic — it materially changes the numbers. Choosing the basis
deliberately, and applying it identically to both providers, is what keeps the report
honest.
### Units
All values are normalized to imperial units: temperature in °F, precipitation in inches,
wind speed in mph, humidity in percent. WeatherAPI's history endpoint returns imperial
fields directly; Meteostat is requested with `units=imperial`.
### Comparison and drift status
For each metric, the difference is `round(abs(source_a − source_b), 2)`. The absolute
value is used because the report is concerned with the *magnitude* of disagreement, not
its direction. Rounding is applied after the subtraction (not only to the inputs) because
floating-point subtraction of rounded values can still produce noise.
Each metric is assigned a status:
- **Missing Data** — one or both providers returned no value for that metric.
- **Drift Detected** — the values differ at all.
- **OK** — the values are identical.
This uses an "any difference is drift" rule rather than per-metric thresholds. For an
audit-style report whose purpose is to surface *every* discrepancy, flagging any
difference is a reasonable default; configurable thresholds are listed under Future
improvements as the natural next step.
### Comparison is pairwise
Comparison operates on a pair of providers. For N providers, every pair is compared
(`itertools.combinations`), so two providers produce one comparison and three would
produce three. This keeps the comparison logic simple and provider-count-agnostic.
### Error handling
Two layers work together so that a single failing provider never sinks the whole run:
1. **Retry (transient failures)** — each HTTP request retries up to three times with a
  short delay (`retry_request` in the provider base class). This absorbs momentary
  blips and rate-limit responses.
2. **Boundary (genuine failures)** — if all retries are exhausted, the orchestration
  layer (`safe_try` in `main`) catches the error, logs which provider and location
  failed, and substitutes an empty observation. That provider's metrics then appear as
  **Missing Data** in the report, and the run continues with the remaining
  providers and locations.
Missing values are represented as empty cells in the CSV (never as `0`), so "no data"
stays distinct from a real zero reading.
### Extensibility — adding a provider
The system is designed so a new provider can be added with minimal, localized changes:
1. Add a new class under `src/providers/` that subclasses `WeatherTemplate` and
  implements `get_daily_weather`, returning a normalized `WeatherData`.
2. Register it in the provider registry (`PROVIDER_LIST` in `src/providers/__init__.py`).
3. Add its name to the `providers:` list in `config.yaml`.
No changes are required to `main`, the comparator, the reporting layer, or the data
models. The new provider is automatically fetched and included in all pairwise
comparisons.
### Project structure
```
config.yaml              # locations and active providers
requirements.txt
.env                     # API keys (not committed)
src/
 main.py                # orchestration: fetch -> compare -> report
 config_loader.py       # loads locations and provider names from config
 models.py              # Location, WeatherData, MetricDrift, DriftReport
 comparator.py          # pairwise metric comparison and drift status
 reporting.py           # CSV output
 utils.py               # small numeric helpers (average, max, rounding)
 providers/
   __init__.py          # provider registry + build_providers
   base.py              # WeatherTemplate abstract base + shared retry
   weatherapi.py        # WeatherAPI implementation
   meteostat.py         # Meteostat implementation
output/                  # generated reports (created at runtime)
```
---
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
- **Reference / consensus comparison for many providers.** Pairwise comparison grows
 combinatorially; with more than a few providers, comparing each against a designated
 reference provider (or a median consensus) keeps the report linear and easier to read.
- **Parallel fetching.** Provider/location requests are independent and could be run
 concurrently to speed up larger runs.
- **Additional output formats** (JSON, or a formatted spreadsheet) alongside CSV.
- **Automated tests** covering normalization, the comparator, the retry logic, and the
 error boundary.
- **Stronger config validation** (schema validation of `config.yaml`, clearer errors for
 malformed entries).
- **Run summary** printed at the end (e.g. how many comparisons were complete vs. missing
 data).
