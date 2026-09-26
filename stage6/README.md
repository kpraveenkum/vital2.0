# Stage 6 — Satellite-Based Biomass & Stubble Burning Emissions

## Overview
Ingests VIIRS / MODIS active fire detections, filters agricultural stubble fires, computes FRP & biomass burned, applies emission factors, and grids emissions.

## Files
- [`satellite_fire_reader.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/satellite_fire_reader.py)
- [`fire_filter.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/fire_filter.py)
- [`frp_model.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/frp_model.py)
- [`biomass_burned_model.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/biomass_burned_model.py)
- [`emission_factors.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/emission_factors.py)
- [`biomass_emission_model.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/biomass_emission_model.py)
- [`fire_gridding.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/fire_gridding.py)
- [`main_stage6.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage6/main_stage6.py)

## How to Run
```bash
py -3 main_stage6.py
```
