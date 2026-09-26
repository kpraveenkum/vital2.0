#!/bin/bash

set -e

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
WRF="$PROJECT/WRF"
RUN_DIR="$WRF/run_control"
CORES=${1:-4}

mkdir -p "$RUN_DIR"

echo "======================================"
echo "STAGE 9 - CONTROL (Feedback OFF)"
echo "======================================"

cd "$RUN_DIR"

if [ -f "$PROJECT/config/namelist_feedback_off" ]; then
    cp "$PROJECT/config/namelist_feedback_off" namelist.input
fi

if [ -f "$WRF/main/real.exe" ]; then
    echo "Running real.exe..."
    "$WRF/main/real.exe"
fi

if [ -f "$WRF/main/wrf.exe" ]; then
    echo "Running control WRF-Chem..."
    mpirun -np "$CORES" "$WRF/main/wrf.exe"
fi

echo "CONTROL completed."
