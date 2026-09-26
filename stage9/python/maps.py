"""
maps.py

Spatial 2D difference mapping utilities for aerosol-meteorology feedback visualization.
"""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def plot_difference(difference, title, output_file, label):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 6))

    # Determine balanced colormap bounds
    vmax = max(abs(np.nanmin(difference)), abs(np.nanmax(difference)))
    if vmax == 0:
        vmax = 1.0

    image = plt.imshow(
        difference,
        origin="lower",
        aspect="auto",
        cmap="RdBu_r" if "temperature" in label.lower() or "pm2" in label.lower() or "radiation" in label.lower() else "coolwarm",
        vmin=-vmax,
        vmax=vmax,
    )

    plt.colorbar(image, label=label)
    plt.title(title)
    plt.xlabel("West-East grid")
    plt.ylabel("South-North grid")
    plt.tight_layout()

    plt.savefig(output_file, dpi=200)
    plt.close()


def plot_multiple(comparison, output_directory):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    labels = {
        "PM25": "PM2.5 difference (ug/m3)",
        "PBLH": "PBLH difference (m)",
        "T2": "Temperature difference (K)",
        "SWDOWN": "Surface Shortwave Radiation difference (W/m2)",
        "O3": "Ozone difference (ppb)",
        "U10": "U10 Wind difference (m/s)",
        "V10": "V10 Wind difference (m/s)",
        "NO2": "NO2 difference (ppb)",
        "CO": "CO difference (ppm)",
    }

    # Standard filename aliases matching prompt specifications
    filename_aliases = {
        "T2": "delta_temperature.png",
        "SWDOWN": "delta_radiation.png",
        "PM25": "delta_pm25.png",
        "PBLH": "delta_pblh.png",
        "O3": "delta_o3.png",
        "U10": "delta_wind.png",
    }

    for variable, data in comparison.items():
        difference = data["difference"]

        # If time-dimension present, take daytime peak / mean step (e.g. index 12 or mean over time)
        if difference.ndim >= 3:
            difference_2d = np.nanmean(difference, axis=0)
        else:
            difference_2d = difference

        filename = filename_aliases.get(variable, f"delta_{variable.lower()}.png")

        plot_difference(
            difference_2d,
            f"Feedback - Control: {variable}",
            output_directory / filename,
            labels.get(variable, variable),
        )

        # Also save specific named files if alias used
        if variable in filename_aliases:
            orig_filename = f"delta_{variable.lower()}.png"
            if orig_filename != filename:
                plot_difference(
                    difference_2d,
                    f"Feedback - Control: {variable}",
                    output_directory / orig_filename,
                    labels.get(variable, variable),
                )
