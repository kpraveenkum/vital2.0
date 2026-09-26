#!/bin/bash

set -e

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
WRF="$PROJECT/WRF"
RUN_DIR="$WRF/run_forecast"
CORES=${1:-4}

mkdir -p "$RUN_DIR"

echo "======================================"
echo "WRF-Chem 72-Hour Forecast Simulation"
echo "======================================"

cd "$RUN_DIR"

if [ -f "$PROJECT/config/namelist.input" ]; then
    cp "$PROJECT/config/namelist.input" namelist.input
fi

if [ -f "$WRF/main/real.exe" ]; then
    echo "Running real.exe..."
    "$WRF/main/real.exe"
fi

if [ -f "$WRF/main/wrf.exe" ]; then
    echo "Starting WRF-Chem forecast..."
    mpirun -np "$CORES" "$WRF/main/wrf.exe"
fi

echo "Forecast simulation completed."
