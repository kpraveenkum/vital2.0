"""
main_stage9.py

Stage 9 Main Execution Script:
Evaluates two-way aerosol-meteorology feedback by comparing CONTROL (Feedback OFF)
and FEEDBACK (Feedback ON) WRF-Chem atmospheric numerical experiment outputs.
Automatically generates realistic synthetic control & feedback datasets if no live WRF-Chem
executable outputs are present, computes spatial differences & statistics, and outputs summary CSVs & maps.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import xarray as xr

# Ensure python directory and backend root are in path
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from wrfchem_feedback_reader import FeedbackReader
    from experiment_comparison import compare
    from statistics import summary
    from maps import plot_multiple
except ImportError:
    from python.wrfchem_feedback_reader import FeedbackReader
    from python.experiment_comparison import compare
    from python.statistics import summary
    from python.maps import plot_multiple


BASE_DIR = backend_dir
WRF_DIR = BASE_DIR / "WRF"
CONTROL_DIR = WRF_DIR / "run_control"
FEEDBACK_DIR = WRF_DIR / "run_feedback"

ALT_CONTROL_DIR = BASE_DIR / "data" / "control"
ALT_FEEDBACK_DIR = BASE_DIR / "data" / "feedback"
OUTPUT_DIR = BASE_DIR / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ALT_CONTROL_DIR.mkdir(parents=True, exist_ok=True)
ALT_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def create_synthetic_experiment_pair(control_file: Path, feedback_file: Path):
    """
    Generates synthetic CONTROL (Feedback OFF) and FEEDBACK (Feedback ON) NetCDF files
    demonstrating realistic aerosol radiative forcing, surface cooling, boundary-layer suppression,
    and aerosol trapping feedback effects.
    """
    control_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_file.parent.mkdir(parents=True, exist_ok=True)

    for p in [control_file, feedback_file]:
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    times = pd.date_range("2026-10-15 00:00:00", periods=24, freq="1h")
    lats = np.linspace(28.3, 28.9, 30)
    lons = np.linspace(76.8, 77.5, 30)
    levels = np.arange(10)

    shape = (len(times), len(levels), len(lats), len(lons))
    surface_shape = (len(times), len(lats), len(lons))

    # Spatial emission hotspot mask over central Delhi
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    spatial_mask = np.exp(-((lat_grid - 28.61)**2 / 0.04 + (lon_grid - 77.23)**2 / 0.04))

    # --- CONTROL Simulation (Feedback OFF) ---
    diurnal_sun = np.maximum(0, np.sin(np.linspace(-np.pi/2, 3*np.pi/2, len(times))))
    swdown_ctrl = diurnal_sun[:, None, None] * 750.0 + np.zeros(surface_shape)
    t2_ctrl = 295.0 + 6.0 * np.sin(np.linspace(0, 2 * np.pi, len(times)))[:, None, None] + np.random.randn(*surface_shape) * 0.3
    u10_ctrl = 3.5 + np.random.randn(*surface_shape) * 0.5
    v10_ctrl = 2.0 + np.random.randn(*surface_shape) * 0.5
    pblh_ctrl = 350.0 + 950.0 * diurnal_sun[:, None, None] + np.zeros(surface_shape)

    pm25_ctrl = 160.0 - 50.0 * (pblh_ctrl[:, None, :, :] / 1200.0) + spatial_mask[None, None, :, :] * 80.0 + np.random.randn(*shape) * 5.0
    pm25_ctrl = np.clip(pm25_ctrl, 15.0, 500.0)
    pm25_dry_ctrl = pm25_ctrl * 0.95
    o3_ctrl = 0.025 + 0.045 * diurnal_sun[:, None, None, None] + np.random.randn(*shape) * 0.003
    no2_ctrl = 0.035 - 0.015 * diurnal_sun[:, None, None, None] + np.random.randn(*shape) * 0.003
    co_ctrl = 1.1 + spatial_mask[None, None, :, :] * 0.5 + np.random.randn(*shape) * 0.05

    # --- FEEDBACK Simulation (Feedback ON) ---
    # 1. Shortwave Radiation Attenuation by aerosols (SWDOWN drop)
    aerosol_extinction = (pm25_ctrl[:, 0, :, :] / 200.0) * spatial_mask[None, :, :]
    swdown_attenuation = diurnal_sun[:, None, None] * 70.0 * aerosol_extinction
    swdown_fdb = np.clip(swdown_ctrl - swdown_attenuation, 0, None)

    # 2. Surface cooling due to radiation reduction (T2 drop -0.8K average)
    t2_cooling = 1.2 * (swdown_attenuation / 70.0)
    t2_fdb = t2_ctrl - t2_cooling

    # 3. PBL suppression due to surface cooling (PBLH drop -120m average)
    pblh_drop = 150.0 * (swdown_attenuation / 70.0)
    pblh_fdb = np.clip(pblh_ctrl - pblh_drop, 100.0, None)

    # 4. Secondary aerosol trapping feedback (PM2.5 accumulation +18.5 ug/m3 average)
    pm25_trapping = 25.0 * (pblh_drop / 150.0)[:, None, :, :]
    pm25_fdb = pm25_ctrl + pm25_trapping
    pm25_dry_fdb = pm25_fdb * 0.95

    # 5. Wind and Ozone response
    u10_fdb = u10_ctrl - 0.2 * (pblh_drop / 150.0)
    v10_fdb = v10_ctrl - 0.1 * (pblh_drop / 150.0)
    o3_fdb = np.clip(o3_ctrl - 0.004 * (swdown_attenuation / 70.0)[:, None, :, :], 0, None)
    no2_fdb = no2_ctrl + 0.003 * (pm25_trapping / 25.0)
    co_fdb = co_ctrl + 0.08 * (pm25_trapping / 25.0)

    # Save CONTROL NetCDF
    ds_ctrl = xr.Dataset(
        data_vars={
            "T2": (("Time", "south_north", "west_east"), t2_ctrl),
            "U10": (("Time", "south_north", "west_east"), u10_ctrl),
            "V10": (("Time", "south_north", "west_east"), v10_ctrl),
            "PBLH": (("Time", "south_north", "west_east"), pblh_ctrl),
            "SWDOWN": (("Time", "south_north", "west_east"), swdown_ctrl),
            "o3": (("Time", "bottom_top", "south_north", "west_east"), o3_ctrl),
            "no2": (("Time", "bottom_top", "south_north", "west_east"), no2_ctrl),
            "co": (("Time", "bottom_top", "south_north", "west_east"), co_ctrl),
            "pm25": (("Time", "bottom_top", "south_north", "west_east"), pm25_ctrl),
            "PM2_5_DRY": (("Time", "bottom_top", "south_north", "west_east"), pm25_dry_ctrl),
        },
        coords={"Time": times, "south_north": lats, "west_east": lons, "bottom_top": levels},
    )
    ds_ctrl.to_netcdf(control_file)

    # Save FEEDBACK NetCDF
    ds_fdb = xr.Dataset(
        data_vars={
            "T2": (("Time", "south_north", "west_east"), t2_fdb),
            "U10": (("Time", "south_north", "west_east"), u10_fdb),
            "V10": (("Time", "south_north", "west_east"), v10_fdb),
            "PBLH": (("Time", "south_north", "west_east"), pblh_fdb),
            "SWDOWN": (("Time", "south_north", "west_east"), swdown_fdb),
            "o3": (("Time", "bottom_top", "south_north", "west_east"), o3_fdb),
            "no2": (("Time", "bottom_top", "south_north", "west_east"), no2_fdb),
            "co": (("Time", "bottom_top", "south_north", "west_east"), co_fdb),
            "pm25": (("Time", "bottom_top", "south_north", "west_east"), pm25_fdb),
            "PM2_5_DRY": (("Time", "bottom_top", "south_north", "west_east"), pm25_dry_fdb),
        },
        coords={"Time": times, "south_north": lats, "west_east": lons, "bottom_top": levels},
    )
    ds_fdb.to_netcdf(feedback_file)


def find_output(directory: Path, alt_directory: Path, name: str) -> Path:
    files = sorted(directory.glob("wrfout_d01_*"))
    if not files:
        files = sorted(alt_directory.glob("wrfout_d01_*"))
    return files[-1] if files else None


def main():
    print("======================================")
    print("STAGE 9 - TWO-WAY AEROSOL FEEDBACK")
    print("======================================")

    ctrl_file = find_output(CONTROL_DIR, ALT_CONTROL_DIR, "control")
    fdb_file = find_output(FEEDBACK_DIR, ALT_FEEDBACK_DIR, "feedback")

    if ctrl_file is None or fdb_file is None:
        synth_ctrl = ALT_CONTROL_DIR / "wrfout_d01_2026-10-15_00-00-00.nc"
        synth_fdb = ALT_FEEDBACK_DIR / "wrfout_d01_2026-10-15_00-00-00.nc"
        print("[INFO] No live WRF-Chem experiment runs found.")
        print("Creating synthetic CONTROL (Feedback OFF) and FEEDBACK (Feedback ON) datasets at:")
        print(f"  CONTROL:  {synth_ctrl}")
        print(f"  FEEDBACK: {synth_fdb}")
        create_synthetic_experiment_pair(synth_ctrl, synth_fdb)
        ctrl_file = synth_ctrl
        fdb_file = synth_fdb

    print("\nCONTROL File:")
    print(f"  {ctrl_file}")
    print("\nFEEDBACK File:")
    print(f"  {fdb_file}")

    comparison = compare(ctrl_file, fdb_file)

    records = []
    for variable, data in comparison.items():
        res = summary(data["feedback"], data["control"], variable)
        records.append(res)

    summary_df = pd.DataFrame(records)
    output_csv = OUTPUT_DIR / "feedback_summary.csv"
    summary_df.to_csv(output_csv, index=False)

    # --------------------------------------------------------
    # Maps Generation
    # --------------------------------------------------------
    print("\nGenerating spatial 2D difference maps...")
    plot_multiple(comparison, OUTPUT_DIR)

    print("\nAerosol-Meteorology Feedback Summary:")
    print(summary_df.to_string(index=False))

    print("\nSaved output summary:")
    print(f"  {output_csv}")
    print("\nStage 9 two-way aerosol feedback analysis complete.")


if __name__ == "__main__":
    main()
