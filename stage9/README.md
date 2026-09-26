# Stage 9 — Advanced Two-Way Aerosol–Meteorology Feedback

## Overview
Evaluates the physical feedback loop where aerosol loading attenuates shortwave radiation, cools the surface, suppresses boundary layer height, and traps ground-level pollution.

## Subdirectories & Files
- [`config/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage9/config): `namelist_feedback_off`, `namelist_feedback_on`
- [`scripts/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage9/scripts): `run_control.sh`, `run_feedback.sh`, `run_comparison.sh`
- [`python/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage9/python): `wrfchem_feedback_reader.py`, `aerosol_optics.py`, `statistics.py`, `feedback_analysis.py`, `experiment_comparison.py`, `maps.py`, `main_stage9.py`
- [`main_stage9.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage9/main_stage9.py)

## How to Run
```bash
py -3 main_stage9.py
```
