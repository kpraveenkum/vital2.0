#!/bin/bash

set -e

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT"

echo "======================================"
echo "STAGE 9 - Feedback Comparison Analysis"
echo "======================================"

python3 python/main_stage9.py || python python/main_stage9.py || python main_stage9.py
