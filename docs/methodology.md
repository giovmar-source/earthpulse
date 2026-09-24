# EarthPulse — Methodology

## Objective

EarthPulse uses Earth Observation data to communicate environmental changes in a simple and transparent way.

## V0.1 indicator

The first environmental indicator implemented is NDVI (Normalized Difference Vegetation Index).

## NDVI

NDVI is calculated as:

NDVI = (NIR - RED) / (NIR + RED)

For Sentinel-2:

- RED = Band 4 (B04)
- NIR = Band 8 (B08)

## Scientific interpretation

Higher NDVI values generally indicate stronger vegetation activity.

A decrease in NDVI may indicate a change in vegetation conditions, but NDVI alone cannot determine the exact cause of the change.

## Data source

The first version of EarthPulse will use Sentinel-2 imagery.

## Transparency

Every result should provide:

- satellite
- sensor
- acquisition date
- spatial resolution
- indicator
- methodology
- relevant limitations