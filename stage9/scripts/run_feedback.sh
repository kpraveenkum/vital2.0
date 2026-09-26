#!/bin/bash

set -e

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
WRF="$PROJECT/WRF"
RUN_DIR="$WRF/run_feedback"
CORES=${1:-4}

mkdir -p "$RUN_DIR"

echo "======================================"
echo "STAGE 9 - AEROSOL FEEDBACK (Feedback ON)"
echo "======================================"

cd "$RUN_DIR"

if [ -f "$PROJECT/config/namelist_feedback_on" ]; then
    cp "$PROJECT/config/namelist_feedback_on" namelist.input
fi

if [ -f "$WRF/main/real.exe" ]; then
    echo "Running real.exe..."
    "$WRF/main/real.exe"
fi

if [ -f "$WRF/main/wrf.exe" ]; then
    echo "Running feedback WRF-Chem..."
    mpirun -np "$CORES" "$WRF/main/wrf.exe"
fi

echo "FEEDBACK simulation completed."
