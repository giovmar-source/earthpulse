# EarthPulse

**See what satellites see. Understand what is changing.**

EarthPulse is an Earth Observation application designed to translate satellite data into simple and understandable information for everyone.

## Current project

Version: V0.1

Main use case:

> Monitor environmental changes in selected places using Sentinel-2 satellite data.

## Technology

- Sentinel-2
- Python
- NumPy
- Pandas
- Rasterio
- GeoPandas
- Matplotlib
- Jupyter
- Android / Kotlin
- Jetpack Compose

## Project pipeline

Satellite data
→
Python processing
→
Environmental indicators
→
Change detection
→
JSON
→
Android application


## EarthPulse — Satellite-based vegetation monitoring

EarthPulse is an Android prototype that uses Sentinel-2
satellite observations to explore vegetation dynamics through
the Normalized Difference Vegetation Index (NDVI).

### Current features

- Sentinel-2 Level-2A data processing
- NDVI calculation using B04 and B08
- SCL-based pixel quality filtering
- Historical NDVI time series
- Historical reference and anomaly analysis
- Before/after maps and NDVI difference visualization
- Android application built with Kotlin and Jetpack Compose
- Local JSON data and image assets for offline demonstration

### Methodology

NDVI is calculated as:

NDVI = (NIR - RED) / (NIR + RED)

Sentinel-2 bands B08 (NIR) and B04 (RED) have a spatial
resolution of 10 metres.

The current Forest Demo analyses historical observations
from June–August 2023–2025. It is a static demonstration,
not a real-time monitoring service.

### Limitations

An NDVI anomaly indicates a change in spectral response.
It does not, by itself, establish vegetation damage or its cause.
Clouds, shadows, observation conditions and pixel validity
must be considered when interpreting changes.

### Technology stack

- Python, NumPy, Pandas, Matplotlib
- Rasterio, GeoPandas, Shapely
- Sentinel-2 L2A and STAC
- Kotlin and Jetpack Compose
- Git and GitHub


## Validation and tests

The project includes automated tests for the exported Forest Demo
data and the consistency of the Android assets.

Run the tests from the repository root:

```bash
conda activate earthpulse
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests check:

- Required fields in the Forest Demo summary
- Valid NDVI ranges
- Chronological ordering of time-series observations
- Presence of the target date in the time series
- Consistency between Python JSON outputs and Android assets

These checks validate data structure and consistency.
They do not independently establish the scientific validity
of every satellite observation or change-detection result.