"""
main_stage9.py (Backend Root Wrapper)

Executes the Stage 9 aerosol-meteorology feedback pipeline from Backend root.
"""

from pathlib import Path
import sys

# Ensure python/ directory is in path
script_dir = Path(__file__).resolve().parent
python_dir = script_dir / "python"
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))

from python.main_stage9 import main

if __name__ == "__main__":
    main()
