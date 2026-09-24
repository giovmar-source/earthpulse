# EarthPulse — Architecture

## Overview

EarthPulse separates Earth Observation processing from the Android application.

## Processing pipeline

Sentinel-2
↓
Data discovery
↓
Cloud masking
↓
Band extraction
↓
NDVI calculation
↓
AOI statistics
↓
Time series
↓
Change detection
↓
JSON / visual products
↓
Android application

## Main components

### EO Processing

Python-based processing of satellite data.

### Analysis

Calculation of environmental indicators and temporal changes.

### API

Interface between processed Earth Observation results and the Android application.

### Android

Consumer-facing mobile application.

## Design principle

The application should remain simple for the user while maintaining a scientifically transparent processing chain underneath.